import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.pipeline import RagPipeline


TEST_QUERIES = [
    "điểm miễn phí ở Hà Nội buổi tối",
    "lịch trình 1 ngày ở Phú Thọ cho người lớn tuổi",
    "đi Huế với bố mẹ lớn tuổi, ít đi bộ",
    "đi biển ở Khánh Hòa",
]


def main() -> None:
    pipeline = RagPipeline()

    outputs = {}

    for query in TEST_QUERIES:
        result = pipeline.run(
            query=query,
            top_k=6,
            mode="balanced",
            include_prompt=False,
        )

        outputs[query] = result

        debug = result.get("debug", {})
        latency = result.get("latency_ms", {})

        print("=" * 110)
        print("QUERY:", query)
        print("RUNTIME MODE:", result.get("runtime_mode"))
        print("MODEL USED:", result.get("model_used"))
        print("FALLBACK USED:", result.get("fallback_used"))
        print("LATENCY:", latency)
        print("GENERATION ERROR:", debug.get("generation_error"))
        print("GENERATION ERROR TYPE:", debug.get("generation_error_type"))
        print("RETRY AFTER SECONDS:", debug.get("retry_after_seconds"))
        print("GEMINI TIMEOUT:", debug.get("gemini_timeout"))
        print("CACHE HIT:", debug.get("cache_hit"))
        print("-" * 110)
        print("ANSWER:")
        print(result.get("answer"))
        print("-" * 110)
        print("PLACES:")

        for i, place in enumerate(result.get("places", []), start=1):
            print(
                f"{i}. {place.get('name')} | {place.get('province')} | "
                f"{place.get('category_main')} / {place.get('category_sub')} | "
                f"score={place.get('score')} | realtime={place.get('requires_realtime_check')}"
            )

        print("WARNINGS:")
        for warning in result.get("warnings", [])[:3]:
            print("-", warning)

    output_path = ROOT / "reports" / "test_rag_pipeline_results.json"
    output_path.write_text(
        json.dumps(outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()