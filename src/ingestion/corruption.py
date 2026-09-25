from __future__ import annotations

from datetime import timedelta
import math

import pandas as pd

from core.utils import write_json


NOISE_MARKER = " @@CORRUPTED_NOISE@@ !!! ### "


def _rebuild_embedding_text(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Deterministically inject the six corruption scenarios required by the lab."""
    required = {
        "paper_id",
        "title",
        "summary",
        "published",
        "age_days",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("At least 10 clean records are required for the corruption suite.")

    original = df.copy(deep=True).reset_index(drop=True)
    corrupted = original.copy(deep=True)
    scenarios: list[dict] = []

    # 1. Remove the newest 20%. Stable sorting keeps this reproducible.
    published = pd.to_datetime(corrupted["published"], errors="coerce")
    drop_count = max(1, math.ceil(len(corrupted) * 0.20))
    latest_indices = published.sort_values(ascending=False, kind="stable").index[:drop_count].tolist()
    dropped_ids = corrupted.loc[latest_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)
    scenarios.append(
        {
            "type": "drop_latest_records",
            "affected_count": drop_count,
            "paper_ids": dropped_ids,
            "parameters": {"fraction": 0.20},
        }
    )

    # Use fixed slices so repeated runs produce byte-for-byte equivalent data.
    blank_indices = list(range(min(2, len(corrupted))))
    blank_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    if "summary_chars" in corrupted.columns:
        corrupted.loc[blank_indices, "summary_chars"] = 0
    scenarios.append(
        {
            "type": "blank_summary",
            "affected_count": len(blank_indices),
            "paper_ids": blank_ids,
            "parameters": {"replacement": ""},
        }
    )

    noise_indices = list(range(2, min(5, len(corrupted))))
    noise_ids = corrupted.loc[noise_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[noise_indices, "summary"] = (
        corrupted.loc[noise_indices, "summary"].astype(str) + NOISE_MARKER * 8
    )
    if "summary_chars" in corrupted.columns:
        corrupted.loc[noise_indices, "summary_chars"] = corrupted.loc[noise_indices, "summary"].str.len()
    scenarios.append(
        {
            "type": "inject_noise",
            "affected_count": len(noise_indices),
            "paper_ids": noise_ids,
            "parameters": {"marker": NOISE_MARKER.strip(), "repetitions": 8},
        }
    )

    title_indices = list(range(5, min(7, len(corrupted))))
    title_ids = corrupted.loc[title_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].astype(str).str[:7]
    scenarios.append(
        {
            "type": "truncate_title",
            "affected_count": len(title_indices),
            "paper_ids": title_ids,
            "parameters": {"max_characters": 7},
        }
    )

    stale_count = max(1, math.ceil(len(corrupted) * 0.30))
    stale_indices = list(range(stale_count))
    stale_ids = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist()
    stale_dates = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="raise") - timedelta(days=365)
    corrupted.loc[stale_indices, "published"] = stale_dates.dt.strftime("%Y-%m-%d").to_numpy()
    corrupted.loc[stale_indices, "age_days"] = (
        pd.to_numeric(corrupted.loc[stale_indices, "age_days"], errors="coerce").fillna(0).astype(int) + 365
    )
    scenarios.append(
        {
            "type": "stale_date",
            "affected_count": stale_count,
            "paper_ids": stale_ids,
            "parameters": {"days_shifted_back": 365},
        }
    )

    duplicate_count = min(2, len(corrupted))
    duplicate_rows = corrupted.iloc[:duplicate_count].copy(deep=True)
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    scenarios.append(
        {
            "type": "duplicate_rows",
            "affected_count": duplicate_count,
            "paper_ids": duplicate_ids,
            "parameters": {"copies_added": 1},
        }
    )

    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_embedding_text, axis=1)
    log = {
        "deterministic": True,
        "original_rows": len(original),
        "final_rows": len(corrupted),
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
    write_json(output_log_path, log)
    return corrupted.reset_index(drop=True)
