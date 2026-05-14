"""
Export `rag_knowledge_base` rows to the RAG corpus JSONL consumed by BM25 build.

Requires: pip install pymysql (see requirements.txt)
Env: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (same as Node .env)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.text_utils import normalize_text


def norm_key(value) -> str | None:
    text = normalize_text(str(value or "")).strip()
    if not text:
        return None
    return text.replace(" ", "_")


def row_to_doc(row: dict) -> dict:
    kt = (row.get("knowledge_type") or "place").strip()
    if kt not in {"place", "constraint", "itinerary", "realtime"}:
        kt = "place"

    place_key = row.get("place_key") or row.get("knowledge_key") or ""
    pk = str(place_key).strip()
    kid = str(row.get("knowledge_key") or pk).strip()

    meta = {
        "place_id": pk,
        "name": row.get("title") or pk,
        "province": row.get("province"),
        "province_norm": norm_key(row.get("province")),
        "city": row.get("city"),
        "city_norm": norm_key(row.get("city")),
        "area": row.get("area"),
        "area_norm": norm_key(row.get("area")),
        "destination_group": row.get("destination_group"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "category_main": row.get("category_main"),
        "category_sub": row.get("category_sub"),
        "category_main_norm": row.get("category_main_norm"),
        "category_sub_norm": row.get("category_sub_norm"),
        "slot_norm": row.get("slot_norm"),
        "budget_level_norm": row.get("budget_level_norm"),
        "walking_level_norm": row.get("walking_level_norm"),
        "activity_level_norm": row.get("activity_level_norm"),
        "kid_friendly_norm": bool(row.get("kid_friendly_norm"))
        if row.get("kid_friendly_norm") is not None
        else None,
        "elderly_friendly_norm": bool(row.get("elderly_friendly_norm"))
        if row.get("elderly_friendly_norm") is not None
        else None,
        "quality_score": row.get("quality_score"),
        "recommended_use_norm": row.get("recommended_use_norm"),
        "must_not_schedule_as_main": bool(row.get("must_not_schedule_as_main")),
        "requires_realtime_check": bool(row.get("requires_realtime_check")),
        "is_active": bool(row.get("is_active", 1)),
        "doc_type": kt,
    }

    parts = [row.get("summary"), row.get("content"), row.get("search_text")]
    body = "\n".join(str(p).strip() for p in parts if p)

    return {
        "doc_id": f"{kt}::{kid}",
        "doc_type": kt,
        "place_id": pk or kid,
        "title": (row.get("title") or pk or kid).strip(),
        "text": body,
        "metadata": meta,
    }


def main() -> None:
    try:
        import pymysql
    except ImportError as exc:
        raise SystemExit("Install pymysql: pip install pymysql") from exc

    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "unudata")

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    sql = """
    SELECT
      knowledge_key, place_key, title, knowledge_type,
      content, summary, search_text,
      province, city, area, destination_group, latitude, longitude,
      category_main, category_sub, category_main_norm, category_sub_norm,
      slot_norm, budget_level_norm, walking_level_norm, activity_level_norm,
      kid_friendly_norm, elderly_friendly_norm,
      quality_score, recommended_use_norm,
      must_not_schedule_as_main, requires_realtime_check, is_active
    FROM rag_knowledge_base
    WHERE is_active = 1
    """

    settings.rag_documents_file.parent.mkdir(parents=True, exist_ok=True)

    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    conn.close()

    out_path = settings.rag_documents_file
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            doc = row_to_doc(row)
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    report = {
        "output_file": str(out_path),
        "row_count": len(rows),
    }
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    (settings.reports_dir / "export_rag_knowledge_base_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Exported {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
