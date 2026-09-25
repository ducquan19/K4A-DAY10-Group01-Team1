from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Tao bo evaluation test set 10 cau hoi qua 4 nhom nghiep vu tu cleaned dataframe."""
    if len(df) < 10:
        raise ValueError(f"Cleaned dataframe must have at least 10 documents, found {len(df)}.")

    # Chon 10 bai bao khac nhau de tao 10 cau hoi
    sample_records = df.iloc[:10].to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    # 3 cau hoi loai summary (sample 0, 1, 2)
    for i in range(3):
        rec = sample_records[i]
        gt = first_sentence(rec["summary"])
        test_set.append(
            {
                "id": f"eval_{len(test_set) + 1:03d}",
                "question_type": "summary",
                "question": f"What is the summary of the paper '{rec['title']}'?",
                "ground_truth": gt,
                "ground_truth_doc_ids": [rec["paper_id"]],
            }
        )

    # 3 cau hoi loai authors (sample 3, 4, 5)
    for i in range(3, 6):
        rec = sample_records[i]
        gt = rec["authors_joined"]
        test_set.append(
            {
                "id": f"eval_{len(test_set) + 1:03d}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{rec['title']}'?",
                "ground_truth": gt,
                "ground_truth_doc_ids": [rec["paper_id"]],
            }
        )

    # 2 cau hoi loai date (sample 6, 7)
    for i in range(6, 8):
        rec = sample_records[i]
        gt = str(rec["published"])
        test_set.append(
            {
                "id": f"eval_{len(test_set) + 1:03d}",
                "question_type": "date",
                "question": f"When was the paper '{rec['title']}' published?",
                "ground_truth": gt,
                "ground_truth_doc_ids": [rec["paper_id"]],
            }
        )

    # 2 cau hoi loai categories (sample 8, 9)
    for i in range(8, 10):
        rec = sample_records[i]
        gt = rec["categories_joined"]
        test_set.append(
            {
                "id": f"eval_{len(test_set) + 1:03d}",
                "question_type": "categories",
                "question": f"What are the research categories or subjects of the paper '{rec['title']}'?",
                "ground_truth": gt,
                "ground_truth_doc_ids": [rec["paper_id"]],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
