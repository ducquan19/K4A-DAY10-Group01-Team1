from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    if not items and "items" in payload:
        items = payload["items"]

    records: list[PaperRecord] = []
    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        title_field = item.get("title", [])
        if isinstance(title_field, list):
            title = title_field[0] if title_field else ""
        else:
            title = str(title_field)
        title = normalize_whitespace(title)
        if not title:
            continue

        abstract = item.get("abstract", "")
        summary = re.sub(r"<[^>]+>", " ", str(abstract))
        summary = normalize_whitespace(summary)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        categories: list[str] = [
            str(subj).strip() for subj in item.get("subject", []) if str(subj).strip()
        ]
        primary_category = categories[0] if categories else "General"

        pub_parts = (
            (item.get("published") or item.get("created") or {}).get("date-parts", [[]])[0]
        )
        if len(pub_parts) >= 3:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-{pub_parts[2]:02d}"
        elif len(pub_parts) == 2:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-01"
        elif len(pub_parts) == 1:
            published = f"{pub_parts[0]:04d}-01-01"
        elif "date-time" in item.get("created", {}):
            published = item["created"]["date-time"][:10]
        else:
            published = "2026-01-01"

        updated = published
        abs_url = item.get("URL") or f"https://doi.org/{paper_id}"
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API Crossref hoac doc fallback snapshot offline."""
    payload: dict[str, Any] | None = None
    if settings.refresh_source:
        url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
            "mailto": "student@example.com",
        }
        headers = {
            "User-Agent": "Day10DataObservabilityLab/1.0 (mailto:student@example.com)"
        }
        for attempt in range(3):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=20)
                if resp.status_code == 200:
                    payload = resp.json()
                    write_json(settings.paths.raw_api_response, payload)
                    break
                elif resp.status_code in {429, 503}:
                    time.sleep(2**attempt)
            except Exception:
                time.sleep(1)

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError("No raw response or records found.")

    records = parse_crossref_payload(payload)
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    data = read_json(path)
    if isinstance(data, dict):
        return parse_crossref_payload(data)
    elif isinstance(data, list):
        return [PaperRecord(**item) for item in data]
    raise ValueError(f"Unsupported data format in {path}")
