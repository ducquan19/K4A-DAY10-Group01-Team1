from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.qa import _extract_answer, answer_question


class FakeEmbeddings:
    def __init__(self, _model_name: str):
        pass

    @staticmethod
    def _vector(text: str) -> list[float]:
        return [0.0, 1.0] if "quality" in text.casefold() else [1.0, 0.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeCollection:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, *, ids, embeddings, documents, metadatas) -> None:
        self.rows = [
            {"id": row_id, "embedding": embedding, "document": document, "metadata": metadata}
            for row_id, embedding, document, metadata in zip(ids, embeddings, documents, metadatas, strict=True)
        ]

    def count(self) -> int:
        return len(self.rows)

    def get(self, *, include):
        del include
        return {"ids": [row["id"] for row in self.rows]}

    def delete(self, *, ids) -> None:
        id_set = set(ids)
        self.rows = [row for row in self.rows if row["id"] not in id_set]

    def query(self, *, query_embeddings, n_results, include):
        del include
        query = query_embeddings[0]
        ranked = sorted(
            self.rows,
            key=lambda row: sum(left * right for left, right in zip(row["embedding"], query, strict=True)),
            reverse=True,
        )[:n_results]
        similarities = [
            sum(left * right for left, right in zip(row["embedding"], query, strict=True)) for row in ranked
        ]
        return {
            "ids": [[row["id"] for row in ranked]],
            "documents": [[row["document"] for row in ranked]],
            "metadatas": [[row["metadata"] for row in ranked]],
            "distances": [[1.0 - similarity for similarity in similarities]],
        }


class FakePersistentClient:
    collections: dict[str, FakeCollection] = {}

    def __init__(self, *, path: str) -> None:
        del path

    def delete_collection(self, *, name: str) -> None:
        if name not in self.collections:
            raise ValueError(name)
        del self.collections[name]

    def create_collection(self, *, name: str, configuration) -> FakeCollection:
        del configuration
        collection = FakeCollection()
        self.collections[name] = collection
        return collection

    def get_collection(self, *, name: str) -> FakeCollection:
        return self.collections[name]


def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "paper_id": "10.1/rag",
                "title": "Retrieval Augmented Generation",
                "text_for_embedding": "Title: Retrieval Augmented Generation",
                "published": "2026-01-01",
                "authors_joined": "Alice",
                "categories_joined": "Artificial Intelligence",
                "summary": "Retrieval improves factual answers. Extra detail.",
                "abs_url": "https://example.test/rag",
                "pdf_url": "",
            },
            {
                "paper_id": "10.1/quality",
                "title": "Data Quality Monitoring",
                "text_for_embedding": "Title: Data Quality Monitoring",
                "published": "2026-02-01",
                "authors_joined": "Bob",
                "categories_joined": "Data Engineering",
                "summary": "Quality gates detect broken records. Extra detail.",
                "abs_url": "https://example.test/quality",
                "pdf_url": "",
            },
        ]
    )


class RetrievalUnitTests(unittest.TestCase):
    def test_schema_validation_reports_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing columns"):
            LocalEmbeddingIndex._build_documents(pd.DataFrame([{"paper_id": "10.1/x"}]))

    def test_manifest_path_is_portable_inside_project(self) -> None:
        settings = load_settings()
        value = LocalEmbeddingIndex._manifest_persist_path(settings, settings.paths.chroma_dir)
        self.assertEqual(value, "data/chroma")
        self.assertEqual(
            LocalEmbeddingIndex._resolve_persist_path(settings, value),
            settings.paths.chroma_dir.resolve(),
        )

    def test_answer_extraction_supports_all_benchmark_types(self) -> None:
        result = SearchResult(
            paper_id="10.1/rag",
            title="Retrieval Augmented Generation",
            score=1.0,
            content="context",
            metadata={
                "authors_joined": "Alice",
                "published": "2026-01-01",
                "categories_joined": "Artificial Intelligence",
                "summary": "Retrieval improves factual answers. Extra detail.",
            },
        )
        self.assertEqual(_extract_answer("Who are the authors of this paper?", result), "Alice")
        self.assertEqual(_extract_answer("What is its publication date?", result), "2026-01-01")
        self.assertEqual(_extract_answer("Which field covers this paper?", result), "Artificial Intelligence")
        self.assertEqual(_extract_answer("Summarize this paper.", result), "Retrieval improves factual answers.")


class RetrievalIntegrationTests(unittest.TestCase):
    def test_build_search_lookup_and_exact_title_qa(self) -> None:
        settings = load_settings()
        paths = replace(
            settings.paths,
            chroma_dir=Path.cwd(),
            embeddings_json=Path("unused-manifest.json"),
        )
        settings = replace(settings, paths=paths, top_k=2)
        FakePersistentClient.collections.clear()

        with (
            patch("retrieval.index.MiniLMEmbeddings", FakeEmbeddings),
            patch("retrieval.index.chromadb.PersistentClient", FakePersistentClient),
            patch("retrieval.index.write_json"),
        ):
            index = LocalEmbeddingIndex.build(sample_dataframe(), settings)
            self.assertEqual(index.collection.count(), 2)
            self.assertEqual(index.search("quality monitoring", top_k=1)[0].paper_id, "10.1/quality")
            self.assertEqual(index.lookup("10.1/RAG")["title"], "Retrieval Augmented Generation")

            answer = answer_question(
                'Who are the authors of "Retrieval Augmented Generation"?',
                settings,
                index,
            )
            self.assertEqual(answer.answer, "Alice")
            self.assertEqual(answer.retrieved_doc_ids[0], "10.1/rag")

            rebuilt = LocalEmbeddingIndex.build(sample_dataframe(), settings)
            self.assertIs(rebuilt.collection, index.collection)
            self.assertEqual(rebuilt.collection.count(), 2)


if __name__ == "__main__":
    unittest.main()
