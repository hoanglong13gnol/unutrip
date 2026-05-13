import json
import pickle
import sys
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.text_utils import tokenize_vi


BM25_INDEX_FILE = settings.indexes_dir / "bm25_index.pkl"


def load_jsonl(path: Path) -> list[dict]:
    docs = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def main() -> None:
    if not settings.rag_documents_file.exists():
        raise FileNotFoundError(
            f"RAG documents file not found: {settings.rag_documents_file}. "
            "Run scripts\\05_build_rag_documents.py first."
        )

    settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    docs = load_jsonl(settings.rag_documents_file)
    print(f"Loaded documents: {len(docs)}")

    tokenized_corpus = []
    for doc in docs:
        title = doc.get("title") or ""
        text = doc.get("text") or ""
        doc_type = doc.get("doc_type") or ""
        metadata = doc.get("metadata") or {}

        # Gộp thêm metadata quan trọng vào corpus để search dễ hơn
        metadata_text = " ".join([
            str(metadata.get("province") or ""),
            str(metadata.get("city") or ""),
            str(metadata.get("area") or ""),
            str(metadata.get("category_main") or ""),
            str(metadata.get("category_sub") or ""),
            str(metadata.get("budget_level_norm") or ""),
            str(metadata.get("walking_level_norm") or ""),
            str(metadata.get("slot_norm") or ""),
            str(metadata.get("recommended_use_norm") or ""),
            str(doc_type),
        ])

        full_text = f"{title}\n{text}\n{metadata_text}"
        tokenized_corpus.append(tokenize_vi(full_text))

    bm25 = BM25Okapi(tokenized_corpus)

    payload = {
        "docs": docs,
        "tokenized_corpus": tokenized_corpus,
        "bm25": bm25,
    }

    with BM25_INDEX_FILE.open("wb") as f:
        pickle.dump(payload, f)

    report = {
        "index_file": str(BM25_INDEX_FILE),
        "document_count": len(docs),
        "avg_tokens": round(
            sum(len(tokens) for tokens in tokenized_corpus) / max(len(tokenized_corpus), 1),
            2,
        ),
        "sample_tokens": tokenized_corpus[:3],
    }

    report_path = settings.reports_dir / "build_bm25_index_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved BM25 index: {BM25_INDEX_FILE}")
    print(f"Saved report: {report_path}")
    print(f"Average tokens/doc: {report['avg_tokens']}")


if __name__ == "__main__":
    main()