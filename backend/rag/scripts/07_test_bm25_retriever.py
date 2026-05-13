import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.bm25_retriever import BM25Retriever
from rag.text_utils import normalize_text


TEST_QUERIES = [
    "gợi ý địa điểm ở Đà Nẵng cho gia đình có trẻ nhỏ",
    "điểm miễn phí ở Hà Nội buổi tối",
    "lịch trình 1 ngày ở Phú Thọ cho người lớn tuổi",
    "địa điểm tâm linh ở An Giang",
    "đi biển ở Khánh Hòa",
]


def print_results(query: str, results: list[dict]) -> None:
    print("=" * 100)
    print("QUERY:", query)
    print("NORMALIZED:", normalize_text(query))
    print("-" * 100)

    for i, item in enumerate(results, start=1):
        meta = item["metadata"]

        print(f"{i}. [{item['doc_type']}] {item['title']}")
        print(f"   score: {item['score']}")
        print(f"   place_id: {item['place_id']}")
        print(f"   province: {meta.get('province')}")
        print(f"   category: {meta.get('category_main')} / {meta.get('category_sub')}")
        print(f"   budget: {meta.get('budget_level_norm')}")
        print(f"   walking: {meta.get('walking_level_norm')}")
        print(f"   kid: {meta.get('kid_friendly_norm')} | elderly: {meta.get('elderly_friendly_norm')}")
        print(f"   slot: {meta.get('slot_norm')} | recommended: {meta.get('recommended_use_norm')}")
        print(f"   realtime: {meta.get('requires_realtime_check')}")
        print()


def main() -> None:
    retriever = BM25Retriever()
    retriever.load()

    all_outputs = {}

    for query in TEST_QUERIES:
        results = retriever.search(query, top_k=8)
        print_results(query, results)
        all_outputs[query] = results

    output_path = ROOT / "reports" / "test_bm25_retriever_results.json"
    output_path.write_text(
        json.dumps(all_outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved test results: {output_path}")


if __name__ == "__main__":
    main()