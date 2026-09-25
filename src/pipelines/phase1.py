from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from pipelines.artifacts import save_dataframe
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the clean baseline flow and persist every required artifact."""
    settings = load_settings()
    paths = settings.paths
    run_time = now_utc()

    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
        source_mode = "crossref-api-or-fallback"
    else:
        records = load_raw_records(paths.raw_records_json)
        source_mode = "raw-records-snapshot"
    if not records:
        raise RuntimeError("The source produced no paper records; baseline pipeline stopped.")

    clean_df = build_clean_dataframe(records, run_time)
    save_dataframe(clean_df, paths.clean_csv, paths.clean_json)

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)
    if not quality.get("success", False):
        raise RuntimeError("Baseline data failed the quality gate; refusing to build the serving index.")

    index = LocalEmbeddingIndex.build(clean_df, settings, paths.embeddings_json)
    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(clean_df, paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings,
        index,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_answers,
    )
    source_summary = {
        "source": settings.source_api,
        "source_name": settings.source_api,
        "mode": source_mode,
        "query": settings.source_query,
        "run_date": run_time.date().isoformat(),
        "raw_count": len(records),
        "records_loaded": len(records),
        "clean_rows": len(clean_df),
        "duplicates_removed": max(0, len(records) - len(clean_df)),
        "avg_summary_chars": (
            round(float(clean_df["summary_chars"].mean()), 2)
            if "summary_chars" in clean_df.columns and not clean_df.empty
            else "N/A"
        ),
        "collection": settings.baseline_collection_name,
    }
    generate_phase1_report(
        paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )

    print(
        "Baseline complete: "
        f"rows={len(clean_df)}, collection={index.collection_name}, "
        f"hit_rate={evaluation.summary['retrieval_hit_rate']:.3f}, "
        f"token_f1={evaluation.summary['mean_token_f1']:.3f}"
    )
