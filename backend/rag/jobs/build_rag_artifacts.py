"""
One-shot RAG artifact build: optional DB corpus export + BM25/TF-IDF index + manifest.

Usage (from repo root .env with DB_* if using --from-db):
  python jobs/build_rag_artifacts.py
  python jobs/build_rag_artifacts.py --from-db
  python jobs/build_rag_artifacts.py --skip-export
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-db", action="store_true", help="Run export_rag_knowledge_base_to_corpus.py first")
    ap.add_argument("--skip-export", action="store_true", help="Skip DB export (use existing JSONL)")
    args = ap.parse_args()

    py = sys.executable

    if args.from_db and not args.skip_export:
        run([py, str(ROOT / "scripts" / "export_rag_knowledge_base_to_corpus.py")])

    run([py, str(ROOT / "scripts" / "06_build_bm25_index.py")])


if __name__ == "__main__":
    main()
