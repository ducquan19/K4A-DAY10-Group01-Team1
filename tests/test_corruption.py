from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from ingestion.corruption import NOISE_MARKER, corrupt_clean_dataframe


def clean_frame(rows: int = 20) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": f"10.1/{index}",
                "title": f"A sufficiently long title {index}",
                "summary": f"A valid summary with enough useful content for record {index}.",
                "published": f"2026-01-{(index % 20) + 1:02d}",
                "age_days": 20 - index,
                "authors_joined": "Alice, Bob",
                "categories_joined": "AI, Data",
                "summary_chars": 60,
                "text_for_embedding": f"original {index}",
            }
            for index in range(rows)
        ]
    )


class CorruptionTests(unittest.TestCase):
    def test_injects_all_six_scenarios_deterministically(self) -> None:
        captured: list[dict] = []
        with patch("ingestion.corruption.write_json", side_effect=lambda _path, payload: captured.append(payload)):
            first = corrupt_clean_dataframe(clean_frame(), Path("unused.json"))
            second = corrupt_clean_dataframe(clean_frame(), Path("unused.json"))

        self.assertTrue(first.equals(second))
        self.assertEqual(captured[0]["scenario_count"], 6)
        self.assertEqual(
            [item["type"] for item in captured[0]["scenarios"]],
            [
                "drop_latest_records",
                "blank_summary",
                "inject_noise",
                "truncate_title",
                "stale_date",
                "duplicate_rows",
            ],
        )
        self.assertTrue(first["paper_id"].duplicated().any())
        self.assertTrue(first["summary"].eq("").any())
        self.assertTrue(first["summary"].str.contains(NOISE_MARKER, regex=False).any())
        self.assertTrue(first["title"].str.len().lt(8).any())
        self.assertGreater((first["age_days"] > 180).mean(), 0.25)
        self.assertTrue(first["text_for_embedding"].str.startswith("Title:").all())

    def test_rejects_incomplete_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing columns"):
            corrupt_clean_dataframe(pd.DataFrame([{"paper_id": "10.1/x"}] * 10), Path("unused.json"))


if __name__ == "__main__":
    unittest.main()
