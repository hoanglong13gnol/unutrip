import json
import sys
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.intent_parser import IntentParser


TEST_QUERIES = [
    "gợi ý địa điểm ở Đà Nẵng cho gia đình có trẻ nhỏ",
    "điểm miễn phí ở Hà Nội buổi tối",
    "lịch trình 1 ngày ở Phú Thọ cho người lớn tuổi",
    "địa điểm tâm linh ở An Giang",
    "đi biển ở Khánh Hòa",
    "lập lịch trình 2 ngày ở Nha Trang cho gia đình, ngân sách thấp",
    "đi Huế với bố mẹ lớn tuổi, ít đi bộ",
]


def main() -> None:
    parser = IntentParser()
    outputs = {}

    for query in TEST_QUERIES:
        intent = parser.parse(query)
        data = asdict(intent)
        outputs[query] = data

        print("=" * 100)
        print("QUERY:", query)
        print(json.dumps(data, ensure_ascii=False, indent=2))

    output_path = ROOT / "reports" / "test_intent_parser_results.json"
    output_path.write_text(
        json.dumps(outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()