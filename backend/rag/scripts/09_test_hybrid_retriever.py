import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.hybrid_retriever import HybridRetriever


TEST_QUERIES = [
    "gợi ý địa điểm ở Đà Nẵng cho gia đình có trẻ nhỏ",
    "điểm miễn phí ở Hà Nội buổi tối",
    "lịch trình 1 ngày ở Phú Thọ cho người lớn tuổi",
    "địa điểm tâm linh ở An Giang",
    "đi biển ở Khánh Hòa",
    "đi Huế với bố mẹ lớn tuổi, ít đi bộ",
]


def print_results(payload: dict) -> None:
    print("=" * 110)
    print("QUERY:", payload["query"])
    print("INTENT:", json.dumps(payload["intent"], ensure_ascii=False))
    print("DEBUG:", payload["debug"])
    print("-" * 110)

    for i, item in enumerate(payload["results"], start=1):
        meta = item["metadata"]

        print(f"{i}. [{item['doc_type']}] {item['title']}")
        print(f"   place_id: {item['place_id']}")
        print(f"   province: {meta.get('province')}")
        print(f"   category: {meta.get('category_main')} / {meta.get('category_sub')}")
        print(f"   bm25: {item['bm25_score']} | rule: {item['rule_score']} | final: {item['final_score']}")
        print(f"   budget: {meta.get('budget_level_norm')} | walking: {meta.get('walking_level_norm')}")
        print(f"   kid: {meta.get('kid_friendly_norm')} | elderly: {meta.get('elderly_friendly_norm')}")
        print(f"   slot: {meta.get('slot_norm')} | recommended: {meta.get('recommended_use_norm')}")
        print(f"   realtime: {meta.get('requires_realtime_check')}")
        print(f"   reasons: {', '.join(item['reasons'])}")
        print()


def main() -> None:
    retriever = HybridRetriever()

    outputs = {}

    for query in TEST_QUERIES:
        payload = retriever.retrieve(query, top_k=8)
        print_results(payload)
        outputs[query] = payload

    output_path = ROOT / "reports" / "test_hybrid_retriever_results.json"
    output_path.write_text(
        json.dumps(outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()