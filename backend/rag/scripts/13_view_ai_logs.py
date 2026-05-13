import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings


def main() -> None:
    log_file = settings.reports_dir / "ai_request_logs.jsonl"

    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return

    lines = log_file.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]

    print(f"Total logs: {len(records)}")
    print("=" * 100)

    for record in records[-10:]:
        latency = record.get("latency_ms", {})

        print("created_at:", record.get("created_at"))
        print("query:", record.get("query"))
        print("runtime_mode:", record.get("runtime_mode"))
        print("rag_mode:", record.get("rag_mode"))
        print("model_used:", record.get("model_used"))
        print("fallback_used:", record.get("fallback_used"))
        print("gemini_timeout:", record.get("gemini_timeout"))
        print("cache_hit:", record.get("cache_hit"))
        print("generation_error:", record.get("generation_error"))
        print("generation_error_type:", record.get("generation_error_type"))
        print("retry_after_seconds:", record.get("retry_after_seconds"))
        print("total_latency:", latency.get("total"))
        print("gemini_latency:", latency.get("gemini"))
        print("top_places:", ", ".join(record.get("top_place_names", [])[:5]))
        print("-" * 100)


if __name__ == "__main__":
    main()