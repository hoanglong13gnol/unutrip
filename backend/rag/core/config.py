import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(PROJECT_ROOT / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except Exception:
        return default


class Settings(BaseModel):
    project_name: str = "UnuTrip RAG v2"
    api_version: str = "0.2.0"

    root_dir: Path = RAG_DIR
    project_root: Path = PROJECT_ROOT

    raw_data_dir: Path = root_dir / "data" / "raw"
    processed_data_dir: Path = root_dir / "data" / "processed"
    indexes_dir: Path = root_dir / "data" / "indexes"
    reports_dir: Path = root_dir / "reports"

    dataset_file: Path = raw_data_dir / "dataset_vip_fixed.xlsx"
    dataset_sheet: str = "places_core_dedup_by_id"

    places_master_file: Path = processed_data_dir / "places_master.parquet"
    places_app_file: Path = processed_data_dir / "places_app.json"
    places_itinerary_file: Path = processed_data_dir / "places_itinerary.json"
    rag_documents_file: Path = processed_data_dir / "places_rag_documents.jsonl"

    ai_runtime_mode: str = os.getenv("AI_RUNTIME_MODE", "mock")
    enable_gemini: bool = env_bool("ENABLE_GEMINI", False)
    enable_lora: bool = env_bool("ENABLE_LORA", False)
    enable_validator: bool = env_bool("ENABLE_VALIDATOR", False)

    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_timeout_seconds: int = env_int("GEMINI_TIMEOUT_SECONDS", 12)


settings = Settings()


def get_log_level() -> str:
    return os.getenv("RAG_LOG_LEVEL", "INFO").strip().upper() or "INFO"