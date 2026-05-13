import json
from datetime import datetime
from typing import Any

from core.config import settings


class AiRequestLogger:
    def __init__(self) -> None:
        settings.reports_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = settings.reports_dir / "ai_request_logs.jsonl"

    def log(self, record: dict[str, Any]) -> None:
        record = dict(record)
        record["created_at"] = datetime.now().isoformat(timespec="seconds")

        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")