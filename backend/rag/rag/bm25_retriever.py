import pickle
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from core.config import settings
from rag.text_utils import tokenize_vi

BM25_INDEX_FILE = settings.indexes_dir / "bm25_index.pkl"


class BM25Retriever:
    def __init__(self, index_file: Path = BM25_INDEX_FILE):
        self.index_file = index_file
        self.docs: list[dict[str, Any]] = []
        self.bm25 = None
        self.tokenized_corpus: list[list[str]] = []
        self.tfidf_vectorizer = None
        self.tfidf_X_norm = None

    def load(self) -> None:
        if not self.index_file.exists():
            raise FileNotFoundError(
                f"BM25 index not found: {self.index_file}. "
                "Run scripts\\06_build_bm25_index.py or jobs\\build_rag_artifacts.py first."
            )

        with self.index_file.open("rb") as f:
            # Artifact thường được pickle với sklearn cũ hơn runtime — tránh spam log (vẫn nên cài đúng scikit-learn==1.7.1).
            with warnings.catch_warnings():
                try:
                    from sklearn.exceptions import InconsistentVersionWarning

                    warnings.simplefilter("ignore", InconsistentVersionWarning)
                except ImportError:
                    warnings.filterwarnings(
                        "ignore",
                        message=r"Trying to unpickle estimator",
                        category=UserWarning,
                    )
                payload = pickle.load(f)

        self.docs = payload["docs"]
        self.bm25 = payload["bm25"]
        self.tokenized_corpus = payload["tokenized_corpus"]
        self.tfidf_vectorizer = payload.get("tfidf_vectorizer")
        self.tfidf_X_norm = payload.get("tfidf_X_norm")

    def has_tfidf(self) -> bool:
        return self.tfidf_vectorizer is not None and self.tfidf_X_norm is not None

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_types: list[str] | None = None,
        province_norm: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.bm25 is None:
            self.load()

        query_tokens = tokenize_vi(query)
        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                break

            doc = self.docs[int(idx)]
            metadata = doc.get("metadata") or {}

            if doc_types and doc.get("doc_type") not in doc_types:
                continue

            if province_norm and metadata.get("province_norm") != province_norm:
                continue

            item = {
                "score": round(score, 4),
                "doc_id": doc.get("doc_id"),
                "doc_type": doc.get("doc_type"),
                "place_id": doc.get("place_id"),
                "title": doc.get("title"),
                "text": doc.get("text"),
                "metadata": metadata,
            }
            results.append(item)

            if len(results) >= top_k:
                break

        return results

    def search_tfidf(
        self,
        query: str,
        top_k: int = 10,
        doc_types: list[str] | None = None,
        province_norm: str | None = None,
    ) -> list[dict[str, Any]]:
        """Char n-gram TF–IDF cosine (built next to BM25). Optional."""
        if self.bm25 is None:
            self.load()

        if not self.has_tfidf():
            return []

        q = self.tfidf_vectorizer.transform([query])
        # sklearn normalizes sparse in-place copy
        from sklearn.preprocessing import normalize

        q = normalize(q)
        sims = (self.tfidf_X_norm @ q.T).toarray().ravel()
        ranked_indices = np.argsort(sims)[::-1]

        results: list[dict[str, Any]] = []
        for idx in ranked_indices:
            score = float(sims[idx])
            if score <= 0:
                break

            doc = self.docs[int(idx)]
            metadata = doc.get("metadata") or {}

            if doc_types and doc.get("doc_type") not in doc_types:
                continue

            if province_norm and metadata.get("province_norm") != province_norm:
                continue

            item = {
                "score": round(score, 6),
                "doc_id": doc.get("doc_id"),
                "doc_type": doc.get("doc_type"),
                "place_id": doc.get("place_id"),
                "title": doc.get("title"),
                "text": doc.get("text"),
                "metadata": metadata,
            }
            results.append(item)

            if len(results) >= top_k:
                break

        return results
