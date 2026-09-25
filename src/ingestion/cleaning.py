from __future__ import annotations

from datetime import datetime
import re
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    rows: list[dict[str, Any]] = []
    run_date_val = run_date.date() if isinstance(run_date, datetime) else run_date

    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title or not summary:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in record.categories if normalize_whitespace(c)]
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary_chars = len(summary)

        try:
            pub_date = datetime.strptime(record.published, "%Y-%m-%d").date()
            age_days = max(0, (run_date_val - pub_date).days)
        except Exception:
            try:
                pub_date = datetime.fromisoformat(record.published).date()
                age_days = max(0, (run_date_val - pub_date).days)
            except Exception:
                age_days = 0

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {record.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": record.primary_category or (categories[0] if categories else "General"),
                "published": record.published,
                "updated": record.updated or record.published,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Khử trùng lặp theo paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Loại bỏ bản ghi không hợp lệ
    df = df[
        df["paper_id"].notna()
        & (df["paper_id"].str.strip() != "")
        & df["title"].notna()
        & (df["title"].str.strip() != "")
        & df["summary"].notna()
        & (df["summary"].str.strip() != "")
        & df["text_for_embedding"].notna()
    ]

    # Sắp xếp và reset index
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
