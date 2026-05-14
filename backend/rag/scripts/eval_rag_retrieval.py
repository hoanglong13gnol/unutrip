"""
Offline retrieval evaluation: hit@k on place_id labels + MRR + optional intent/province checks.

Usage:
  python scripts/eval_rag_retrieval.py
  python scripts/eval_rag_retrieval.py --golden eval/custom.json
  python scripts/eval_rag_retrieval.py --ci   # exit 0 if index missing; else run checks
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.hybrid_retriever import HybridRetriever


def hit_at_k(relevant: set[str], ranked_ids: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = ranked_ids[:k]
    return 1.0 if any(rid in relevant for rid in top) else 0.0


def mrr(relevant: set[str], ranked_ids: list[str]) -> float:
    if not relevant:
        return 0.0
    for i, rid in enumerate(ranked_ids, start=1):
        if rid in relevant:
            return 1.0 / float(i)
    return 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=Path, default=ROOT / "eval" / "golden_queries.json")
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    bm25 = ROOT / "data" / "indexes" / "bm25_index.pkl"
    if not bm25.exists():
        print("SKIP: no BM25 index (build artifacts first)")
        sys.exit(0 if args.ci else 1)

    cases = json.loads(args.golden.read_text(encoding="utf-8"))
    retriever = HybridRetriever()

    hit_scores: list[float] = []
    mrr_scores: list[float] = []
    prov_hits = 0
    prov_total = 0

    for row in cases:
        q = row["query"]
        rel = {str(x) for x in (row.get("relevant_place_ids") or []) if x}
        top_k = int(row.get("top_k", 8))
        out = retriever.retrieve(q, top_k=top_k)
        ranked = [str(x.get("place_id")) for x in out.get("results", []) if x.get("place_id")]

        if rel:
            hit_scores.append(hit_at_k(rel, ranked, min(5, top_k)))
            mrr_scores.append(mrr(rel, ranked))

        exp = row.get("expect_province_norm")
        if exp:
            prov_total += 1
            intent = (out.get("intent") or {}).get("province_norm")
            if intent == exp:
                prov_hits += 1

    if hit_scores:
        print(f"mean_hit@5: {sum(hit_scores) / len(hit_scores):.4f} (n={len(hit_scores)})")
    else:
        print("mean_hit@5: n/a (no labeled relevant_place_ids in golden set)")

    if mrr_scores:
        print(f"mean_mrr: {sum(mrr_scores) / len(mrr_scores):.4f} (n={len(mrr_scores)})")
    else:
        print("mean_mrr: n/a (no labeled relevant_place_ids in golden set)")

    if prov_total:
        acc = prov_hits / prov_total
        print(f"province_norm_accuracy: {acc:.4f} ({prov_hits}/{prov_total})")
        if args.ci and acc < 0.5:
            print("CI FAIL: province_norm_accuracy below 0.5")
            sys.exit(1)

    print("eval_ok")


if __name__ == "__main__":
    main()
