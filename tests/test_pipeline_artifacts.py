from __future__ import annotations

import unittest

import pandas as pd

from pipelines.artifacts import dataframe_records


class PipelineArtifactTests(unittest.TestCase):
    def test_dataframe_records_converts_timestamps_and_nan(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "paper_id": "10.1/example",
                    "published": pd.Timestamp("2026-01-02"),
                    "optional": float("nan"),
                }
            ]
        )

        records = dataframe_records(frame)

        self.assertEqual(records[0]["paper_id"], "10.1/example")
        self.assertTrue(records[0]["published"].startswith("2026-01-02"))
        self.assertIsNone(records[0]["optional"])


if __name__ == "__main__":
    unittest.main()
