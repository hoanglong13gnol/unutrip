import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.hybrid_retriever import HybridRetriever
from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder


TEST_QUERIES = [
    "điểm miễn phí ở Hà Nội buổi tối",
    "lịch trình 1 ngày ở Phú Thọ cho người lớn tuổi",
    "đi Huế với bố mẹ lớn tuổi, ít đi bộ",
]


def main() -> None:
    retriever = HybridRetriever()
    context_builder = ContextBuilder()
    prompt_builder = PromptBuilder()

    outputs = {}

    for query in TEST_QUERIES:
        retrieved = retriever.retrieve(query, top_k=6)
        context = context_builder.build_context(retrieved, max_places=6)
        prompt = prompt_builder.build_prompt(retrieved, context)

        outputs[query] = {
            "intent": retrieved["intent"],
            "debug": retrieved["debug"],
            "context": context,
            "prompt": prompt,
            "prompt_chars": len(prompt),
        }

        print("=" * 110)
        print("QUERY:", query)
        print("PROMPT CHARS:", len(prompt))
        print("-" * 110)
        print(prompt[:3000])
        print("\n...[TRUNCATED PREVIEW]...\n")

    output_path = ROOT / "reports" / "test_prompt_builder_results.json"
    output_path.write_text(
        json.dumps(outputs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()