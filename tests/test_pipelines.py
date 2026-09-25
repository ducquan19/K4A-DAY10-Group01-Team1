from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

import pandas as pd

from core.config import load_settings
from pipelines import corruption_flow, phase1


class PipelineOrchestrationTests(unittest.TestCase):
    def test_phase1_runs_quality_gate_before_evaluation(self) -> None:
        settings = load_settings()
        clean = pd.DataFrame([{"paper_id": "10.1/example"}])
        events: list[str] = []
        evaluation = SimpleNamespace(summary={"retrieval_hit_rate": 1.0, "mean_token_f1": 1.0})
        index = SimpleNamespace(collection_name=settings.baseline_collection_name)

        with (
            patch.object(phase1, "load_settings", return_value=settings),
            patch.object(phase1, "load_raw_records", return_value=[object()]),
            patch.object(phase1, "build_clean_dataframe", return_value=clean),
            patch.object(phase1, "save_dataframe"),
            patch.object(
                phase1,
                "run_data_quality_checks",
                side_effect=lambda *_args: events.append("quality") or {"success": True},
            ),
            patch.object(phase1, "build_freshness_report", return_value={"is_fresh": True}),
            patch.object(
                phase1.LocalEmbeddingIndex,
                "build",
                side_effect=lambda *_args: events.append("index") or index,
            ),
            patch.object(phase1, "build_test_set"),
            patch.object(
                phase1,
                "evaluate_pipeline",
                side_effect=lambda *_args: events.append("evaluate") or evaluation,
            ),
            patch.object(phase1, "generate_phase1_report"),
            redirect_stdout(StringIO()),
        ):
            phase1.main()

        self.assertEqual(events, ["quality", "index", "evaluate"])

    def test_corruption_flow_repairs_from_raw_lineage(self) -> None:
        settings = load_settings()
        clean = pd.DataFrame([{"paper_id": "10.1/clean"}])
        corrupted = pd.DataFrame([{"paper_id": "10.1/corrupted"}])
        repaired = pd.DataFrame([{"paper_id": "10.1/repaired"}])
        corrupted_eval = SimpleNamespace(summary={"retrieval_hit_rate": 0.2, "mean_token_f1": 0.1})
        repaired_eval = SimpleNamespace(summary={"retrieval_hit_rate": 1.0, "mean_token_f1": 1.0})

        with (
            patch.object(corruption_flow, "load_settings", return_value=settings),
            patch.object(corruption_flow, "require_artifacts"),
            patch.object(
                corruption_flow,
                "read_json",
                return_value={"retrieval_hit_rate": 1.0, "mean_token_f1": 1.0},
            ),
            patch.object(corruption_flow, "load_dataframe", return_value=clean),
            patch.object(corruption_flow, "corrupt_clean_dataframe", return_value=corrupted),
            patch.object(corruption_flow, "save_dataframe") as save_dataframe,
            patch.object(
                corruption_flow,
                "run_data_quality_checks",
                side_effect=[{"success": False}, {"success": True}],
            ),
            patch.object(
                corruption_flow,
                "build_freshness_report",
                side_effect=[{"is_fresh": False}, {"is_fresh": True}],
            ),
            patch.object(
                corruption_flow.LocalEmbeddingIndex,
                "build",
                side_effect=[SimpleNamespace(), SimpleNamespace()],
            ),
            patch.object(
                corruption_flow,
                "evaluate_pipeline",
                side_effect=[corrupted_eval, repaired_eval],
            ),
            patch.object(corruption_flow, "load_raw_records", return_value=["raw-record"]) as load_raw,
            patch.object(corruption_flow, "build_clean_dataframe", return_value=repaired) as rebuild,
            patch.object(corruption_flow, "generate_corruption_report"),
            patch.object(corruption_flow, "write_json") as write_json,
            redirect_stdout(StringIO()),
        ):
            corruption_flow.main()

        load_raw.assert_called_once_with(settings.paths.raw_records_json)
        rebuild.assert_called_once()
        self.assertEqual(rebuild.call_args.args[0], ["raw-record"])
        self.assertEqual(
            save_dataframe.call_args_list,
            [
                call(corrupted, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json),
                call(repaired, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json),
            ],
        )
        self.assertTrue(write_json.call_args.args[1]["triggered_automatically"])
        self.assertEqual(
            write_json.call_args.args[1]["trigger_reasons"],
            ["data_quality_gate_failed", "freshness_sla_failed"],
        )


if __name__ == "__main__":
    unittest.main()
