"""Build app/routers/admin.py from _admin_extracted.txt."""

from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "app/routers/_admin_extracted.txt").read_text(encoding="utf-8")
lines = src.splitlines()
out: list[str] = []
header = '''"""Admin routes (monitoring, RAG debug, data quality)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import PipelineDep
from app.schemas import AdminAiDebugQueryRequest, AdminRagRetrieveDebugRequest
from core.artifacts import manifest_status_block
from core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])
'''
out.append(header.strip())

skip = {"admin_ai_logs", "admin_ai_metrics", "admin_data_quality_status", "admin_data_quality_issues",
        "admin_data_quality_autofix_changes", "admin_data_quality_summary_by_province", "admin_rag_status"}

for line in lines:
    stripped = line.strip()
    if stripped.startswith("def admin_") and "(" in line:
        name = stripped.split("(")[0].replace("def ", "").strip()
        idx = line.index("(")
        rest = line[idx + 1 :]
        if name in skip:
            out.append(line)
        else:
            if rest.startswith(")"):
                new_rest = "pipeline: PipelineDep" + rest
            else:
                new_rest = "pipeline: PipelineDep, " + rest
            out.append(line[: idx + 1] + new_rest)
        continue
    if stripped == "if pipeline is None:":
        continue
    if stripped == 'raise RuntimeError("RAG pipeline is not initialized")':
        continue
    out.append(line)

text = "\n".join(out)
# admin_rag_status: inject artifacts into return dict — append before return ready
needle = '    return {\n        "service": "UnuTrip RAG v2",\n        "ready": ready,\n        "files": files,\n    }'
replacement = '''    return {
        "service": "UnuTrip RAG v2",
        "ready": ready,
        "files": files,
        "artifacts": manifest_status_block(),
    }'''
if needle in text:
    text = text.replace(needle, replacement, 1)

# admin_system_overview rag section add artifacts
needle2 = '''        "rag": {
            "ready": rag_ready,
            "using_reviewed": pipeline.place_store.status().get("using_reviewed"),
            "place_store": pipeline.place_store.status(),
            "files": rag_files,
        },'''
replacement2 = '''        "rag": {
            "ready": rag_ready,
            "using_reviewed": pipeline.place_store.status().get("using_reviewed"),
            "place_store": pipeline.place_store.status(),
            "files": rag_files,
            "artifacts": manifest_status_block(),
        },'''
if needle2 in text:
    text = text.replace(needle2, replacement2, 1)

(root / "app/routers/admin.py").write_text(text + "\n", encoding="utf-8")
print("wrote admin.py")
