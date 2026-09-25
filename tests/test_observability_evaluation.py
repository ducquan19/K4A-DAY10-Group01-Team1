from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from core.config import load_settings
from evaluation.metrics import JudgeVerdict, _judge_answer, _run_ragas, _token_f1, evaluate_pipeline
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report, generate_phase1_report
from retrieval.qa import AnswerResult


def evaluation_frame(rows: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": f"10.1/{index}",
                "title": f"Reliable Research Paper Number {index}",
                "summary": f"This is a sufficiently detailed summary for research paper number {index}.",
                "authors_joined": f"Author {index}",
                "categories_joined": "Artificial Intelligence",
                "published": f"2026-01-{index + 1:02d}",
                "age_days": index,
                "text_for_embedding": f"Title and complete context for paper {index}",
            }
            for index in range(rows)
        ]
    )


class EvaluationTests(unittest.TestCase):
    def test_testset_has_required_ten_samples_and_four_types(self) -> None:
        output = Path("unused-test-set.json")
        written: list[list[dict]] = []
        with patch("evaluation.testset.write_json", side_effect=lambda _path, value: written.append(value)):
            samples = build_test_set(evaluation_frame(), output)

        self.assertEqual(len(samples), 10)
        self.assertEqual({item["question_type"] for item in samples}, {"summary", "authors", "date", "categories"})
        self.assertTrue(all(item["ground_truth_doc_ids"] for item in samples))
        self.assertEqual(written[0], samples)

        with patch("evaluation.testset.write_json"):
            with self.assertRaisesRegex(ValueError, "at least 10"):
                build_test_set(evaluation_frame(9), output)

    def test_metrics_evaluate_and_persist_answers(self) -> None:
        settings = replace(load_settings(), llm_provider="mock", model_name="mock")
        test_set_path = Path("unused-test-set.json")
        metrics_path = Path("unused-metrics.json")
        answers_path = Path("unused-answers.json")
        with patch("evaluation.testset.write_json"):
            samples = build_test_set(evaluation_frame(), test_set_path)

            def answer(question: str, settings, index) -> AnswerResult:
                del settings, index
                item = next(sample for sample in samples if sample["question"] == question)
                return AnswerResult(
                    question=question,
                    answer=item["ground_truth"],
                    retrieved_doc_ids=item["ground_truth_doc_ids"],
                    retrieved_contexts=["context"],
                    retrieved_titles=["title"],
                )

        written: dict[Path, object] = {}
        verdict = JudgeVerdict(score=5, correct=True, reasoning="test judge")
        with (
            patch("evaluation.metrics.read_json", return_value=samples),
            patch("evaluation.metrics.write_json", side_effect=lambda path, value: written.__setitem__(path, value)),
            patch("evaluation.metrics.answer_question", side_effect=answer),
            patch("evaluation.metrics._judge_answer", return_value=verdict),
            patch("evaluation.metrics._run_ragas", return_value={"skipped": "test"}),
        ):
            result = evaluate_pipeline(settings, object(), test_set_path, metrics_path, answers_path)

        self.assertEqual(result.summary["samples"], 10)
        self.assertEqual(result.summary["retrieval_hit_rate"], 1.0)
        self.assertEqual(result.summary["mean_token_f1"], 1.0)
        self.assertEqual(len(written[answers_path]), 10)
        self.assertEqual(written[metrics_path], result.summary)

    def test_token_f1_judge_fallback_and_ragas_default(self) -> None:
        self.assertEqual(_token_f1("", "answer"), 0.0)
        self.assertEqual(_token_f1("alpha", "beta"), 0.0)
        self.assertEqual(_token_f1("alpha beta", "alpha beta"), 1.0)

        settings = replace(load_settings(), llm_provider="mock", model_name="mock")
        verdict = _judge_answer(settings, "question", "alpha beta", "alpha beta")
        self.assertTrue(verdict.correct)
        self.assertEqual(verdict.score, 5)
        self.assertIn("Fallback", verdict.reasoning)
        self.assertIn("skipped", _run_ragas(settings, []))


class ObservabilityTests(unittest.TestCase):
    def test_quality_gate_and_freshness_detect_corruption(self) -> None:
        settings = load_settings()
        clean = evaluation_frame()
        with patch("observability.quality.write_json"):
            baseline = run_data_quality_checks(clean, settings, "baseline")
        self.assertTrue(baseline["success"])
        self.assertEqual(baseline["statistics"]["evaluated_expectations"], 7)

        corrupted = clean.copy()
        corrupted.loc[1, "paper_id"] = corrupted.loc[0, "paper_id"]
        corrupted.loc[2, "summary"] = ""
        corrupted.loc[3, "title"] = "short"
        corrupted.loc[:4, "age_days"] = 365
        with patch("observability.quality.write_json"):
            result = run_data_quality_checks(corrupted, settings, "corrupted")

        self.assertFalse(result["success"])
        self.assertFalse(result["is_fresh"])

    def test_freshness_empty_frame_and_markdown_reports(self) -> None:
        settings = load_settings()
        with patch("observability.quality.write_json"):
            freshness = build_freshness_report(pd.DataFrame(), settings, Path("fresh.json"))
        self.assertTrue(freshness["is_fresh"])
        self.assertEqual(freshness["total_rows"], 0)

        metrics = {
            "samples": 10,
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 1.0,
            "judge_accuracy": 1.0,
            "mean_judge_score": 5.0,
        }
        reports: list[str] = []
        with patch("observability.reporting.write_text", side_effect=lambda _path, value: reports.append(value)):
            generate_phase1_report(
                Path("phase.md"),
                {"run_date": "2026-09-25", "raw_count": 10},
                metrics,
                {"success": True, "gx_success": True},
                {"is_fresh": True, "stale_rows": 0, "total_rows": 10, "stale_ratio": 0.0},
            )
        self.assertIn("Baseline Data Pipeline", reports[-1])

        with patch("observability.reporting.write_text", side_effect=lambda _path, value: reports.append(value)):
            generate_corruption_report(
                Path("comparison.md"),
                metrics,
                {**metrics, "retrieval_hit_rate": 0.4, "mean_token_f1": 0.3},
                metrics,
                {"success": False},
                {"success": True},
                {"is_fresh": False, "stale_rows": 5},
                {"is_fresh": True, "stale_rows": 0},
            )
        self.assertIn("Baseline vs Corrupted vs Repaired", reports[-1])
        self.assertIn("FAIL (Phát hiện lỗi)", reports[-1])


if __name__ == "__main__":
    unittest.main()
