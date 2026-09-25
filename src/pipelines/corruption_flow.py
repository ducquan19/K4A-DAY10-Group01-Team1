from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.artifacts import load_dataframe, require_artifacts, save_dataframe
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Measure corruption impact, rebuild from raw lineage, and compare results."""
    settings = load_settings()
    paths = settings.paths
    require_artifacts(
        paths.clean_json,
        paths.raw_records_json,
        paths.eval_testset,
        paths.baseline_metrics,
    )
    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = load_dataframe(paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        paths.quality_dir / "corrupted_freshness_report.json",
    )
    repair_reasons = []
    if not corrupted_quality.get("success", False):
        repair_reasons.append("data_quality_gate_failed")
    if not corrupted_freshness.get("is_fresh", True):
        repair_reasons.append("freshness_sla_failed")
    if not repair_reasons:
        raise RuntimeError("Corruption was not detected; automatic repair was not triggered.")

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        paths.corrupted_embeddings_json,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        paths.eval_testset,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )

    # Repair is intentionally rebuilt from immutable raw lineage instead of
    # patching the corrupted dataframe.  Re-running this block is idempotent.
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        paths.quality_dir / "repaired_freshness_report.json",
    )
    if not repaired_quality.get("success", False):
        raise RuntimeError("Repaired data still fails the quality gate; comparison aborted.")

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        paths.eval_testset,
        paths.repaired_metrics,
        paths.repaired_answers,
    )
    write_json(
        paths.repair_log,
        {
            "triggered_automatically": True,
            "trigger_reasons": repair_reasons,
            "repair_strategy": "rebuild_from_immutable_raw_lineage",
            "source_artifact": "data/raw/crossref_records.json",
            "repaired_rows": len(repaired_df),
            "quality_gate_passed": bool(repaired_quality.get("success", False)),
            "freshness_sla_passed": bool(repaired_freshness.get("is_fresh", False)),
            "metrics_recovered": {
                "retrieval_hit_rate": repaired_evaluation.summary["retrieval_hit_rate"],
                "mean_token_f1": repaired_evaluation.summary["mean_token_f1"],
            },
        },
    )
    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )

    print("Corruption comparison complete:")
    for label, metrics in (
        ("Baseline", baseline_metrics),
        ("Corrupted", corrupted_evaluation.summary),
        ("Repaired", repaired_evaluation.summary),
    ):
        print(
            f"  {label:<9} hit_rate={metrics['retrieval_hit_rate']:.3f} "
            f"token_f1={metrics['mean_token_f1']:.3f}"
        )
