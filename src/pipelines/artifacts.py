from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.utils import read_json, write_csv, write_json


def dataframe_records(df: pd.DataFrame) -> list[dict]:
    """Convert a dataframe to JSON-safe records without leaking pandas scalars."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def save_dataframe(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, dataframe_records(df))


def load_dataframe(json_path: Path) -> pd.DataFrame:
    if not json_path.exists():
        raise FileNotFoundError(f"Required dataframe artifact does not exist: {json_path}")
    payload = read_json(json_path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON record list in {json_path}")
    return pd.DataFrame(payload)


def require_artifacts(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required artifacts: " + ", ".join(missing))
