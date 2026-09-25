from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
import unittest
from unittest.mock import patch

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records, parse_crossref_payload


def payload() -> dict:
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1/alpha",
                    "title": ["  Alpha   Retrieval  "],
                    "abstract": "<jats:p>A sufficiently detailed abstract for the alpha paper.</jats:p>",
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "subject": ["Artificial Intelligence"],
                    "published": {"date-parts": [[2026, 1, 2]]},
                    "URL": "https://doi.org/10.1/alpha",
                },
                {
                    "DOI": "10.1/beta",
                    "title": "Beta Monitoring",
                    "abstract": "A sufficiently detailed abstract for the beta paper.",
                    "published": {"date-parts": [[2025, 12]]},
                },
                {
                    "DOI": "10.1/gamma",
                    "title": ["Gamma Agents"],
                    "abstract": "A sufficiently detailed abstract for the gamma paper.",
                    "published": {"date-parts": [[2024]]},
                },
                {"DOI": "", "title": ["Skipped"]},
                {"DOI": "10.1/untitled", "title": []},
            ]
        }
    }


class IngestionTests(unittest.TestCase):
    def test_parse_payload_normalizes_fields_and_date_precision(self) -> None:
        records = parse_crossref_payload(payload())

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].title, "Alpha Retrieval")
        self.assertNotIn("jats", records[0].summary)
        self.assertEqual(records[0].authors, ["Ada Lovelace"])
        self.assertEqual(records[0].published, "2026-01-02")
        self.assertEqual(records[1].published, "2025-12-01")
        self.assertEqual(records[2].published, "2024-01-01")
        self.assertEqual(records[1].primary_category, "General")

    def test_fetch_uses_snapshot_and_preserves_parsed_records(self) -> None:
        settings = load_settings()
        written: list[object] = []
        with (
            patch("ingestion.crossref.read_json", return_value=payload()),
            patch("ingestion.crossref.write_json", side_effect=lambda _path, value: written.append(value)),
        ):
            records = fetch_source_records(settings)

        self.assertEqual(len(records), 3)
        self.assertEqual(len(written[-1]), 3)

    def test_fetch_falls_back_to_existing_record_list(self) -> None:
        settings = load_settings()
        record = parse_crossref_payload(payload())[0]
        paths = replace(settings.paths, raw_api_response=Path("missing-response.json"))
        settings = replace(settings, paths=paths)
        with patch("ingestion.crossref.load_raw_records", return_value=[record]) as loader:
            self.assertEqual(fetch_source_records(settings), [record])
        loader.assert_called_once_with(settings.paths.raw_records_json)

    def test_load_raw_records_supports_payload_list_and_rejects_scalar(self) -> None:
        path = Path("unused.json")
        with patch("ingestion.crossref.read_json", return_value=payload()):
            self.assertEqual(len(load_raw_records(path)), 3)

        record = parse_crossref_payload(payload())[0]
        with patch("ingestion.crossref.read_json", return_value=[asdict(record)]):
            self.assertEqual(load_raw_records(path), [record])

        with patch("ingestion.crossref.read_json", return_value="invalid"):
            with self.assertRaisesRegex(ValueError, "Unsupported data format"):
                load_raw_records(path)

    def test_cleaning_filters_invalid_rows_deduplicates_and_builds_contract(self) -> None:
        record = parse_crossref_payload(payload())[0]
        duplicate = replace(record, title="Duplicate should be removed")
        invalid = replace(record, paper_id=" ")
        iso_date = replace(record, paper_id="10.1/iso", published="2026-01-01T12:00:00+00:00")

        frame = build_clean_dataframe(
            [record, duplicate, invalid, iso_date],
            datetime(2026, 1, 10, tzinfo=UTC),
        )

        self.assertEqual(len(frame), 2)
        self.assertTrue(frame["paper_id"].is_unique)
        self.assertIn("Title: Alpha Retrieval", frame.iloc[0]["text_for_embedding"])
        self.assertIn("Authors: Ada Lovelace", frame.iloc[0]["text_for_embedding"])
        self.assertGreaterEqual(int(frame.iloc[0]["age_days"]), 0)
        self.assertTrue(build_clean_dataframe([invalid], datetime.now(UTC)).empty)


if __name__ == "__main__":
    unittest.main()
