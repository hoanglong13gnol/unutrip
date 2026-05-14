# README_cleaner_v1 — Nâng cấp RAG & backend FastAPI (v1)

Tài liệu tóm tắt **những gì đã làm** trong đợt nâng cấp RAG (kiến trúc, pipeline, hybrid retrieval, eval, vận hành). Phiên bản API RAG: **0.3.0** (`core/config.py`).

---

## 1. Kiến trúc FastAPI (tách `main.py`)

| Trước | Sau |
|--------|-----|
| Toàn bộ route + admin + health trong một `main.py` rất dài | `app/main.py` chỉ còn: lifespan, middleware, `include_router`, exception handlers, OTEL tùy chọn |

**File chính**

- `app/main.py` — khởi tạo app, gắn router, OTEL (nếu có biến môi trường + package).
- `app/routers/health.py` — `/health`, `/health/ready`, `/runtime/status`.
- `app/routers/rag.py` — `/rag/chat`, `/rag/retrieve`, `/rag/chat/simple` (và mount lại dưới `/v1/...`).
- `app/routers/admin.py` — toàn bộ `/admin/*` (monitor, RAG debug, data quality, system overview/self-test).
- `services/rag_service.py` — lớp service gọi `RagPipeline` (route không gọi pipeline trực tiếp).
- `app/deps.py` — `PipelineDep`, `RagServiceDep` (FastAPI `Depends`).
- `app/schemas.py` — Pydantic models dùng chung cho HTTP.

**Hành vi HTTP**

- Route RAG dùng **`async def`** + `starlette.concurrency.run_in_threadpool` để không chặn event loop khi chạy BM25 / pipeline (CPU-bound).

---

## 2. Pipeline dữ liệu có thể lặp lại (reproducible)

1. **Export từ DB (tùy chọn)**  
   - `scripts/export_rag_knowledge_base_to_corpus.py`  
   - Đọc bảng `rag_knowledge_base` qua **pymysql**, ghi `data/processed/places_rag_documents.jsonl`.  
   - Cần biến `DB_*` giống Node trong `.env`.

2. **Build index**  
   - `scripts/06_build_bm25_index.py` — BM25 + **TF–IDF** (sklearn, char n-gram), pickle tại `data/indexes/bm25_index.pkl`.

3. **Manifest phiên bản artifact**  
   - `core/artifacts.py` — `sha256_file`, `write_manifest`, `load_manifest`, `manifest_status_block`.  
   - File: `data/indexes/rag_artifacts_manifest.json` (checksum corpus + index, số document, cờ TF‑IDF).

4. **Một lệnh build**  
   - `jobs/build_rag_artifacts.py` — ví dụ: `python jobs/build_rag_artifacts.py --from-db` (export + build) hoặc không flag (chỉ build từ JSONL hiện có).

5. **CI / kiểm tra**  
   - `scripts/verify_rag_artifacts.py` — so khớp SHA256 manifest với file thật (`--allow-missing` khi chưa có manifest).

---

## 3. Hybrid retrieval (BM25 + TF–IDF + RRF)

- `rag/fusion.py` — **RRF** (Reciprocal Rank Fusion).
- `rag/bm25_retriever.py` — tải thêm `tfidf_vectorizer` + `tfidf_X_norm` nếu có trong pickle; thêm `search_tfidf()`.
- `rag/hybrid_retriever.py` — khi `RAG_ENABLE_RRF=true` (mặc định) **và** index có TF‑IDF: trộn thứ hạng BM25 + TF–IDF bằng RRF, rồi vẫn qua lớp rule score + dedup như cũ.  
- `debug` của retrieval có thêm khóa `fusion` (`mode`, số hit, v.v.).

**Tương thích ngược**: pickle cũ không có TF‑IDF → chỉ BM25 (fusion tự tắt).

---

## 4. Đánh giá offline (golden set)

- `eval/golden_queries.json` — ví dụ câu hỏi + `expect_province_norm` (và chỗ trống `relevant_place_ids` để sau này gắn `place_id` cho hit@k / MRR).
- `scripts/eval_rag_retrieval.py` — hit@5, MRR (khi có label), độ chính xác `province_norm`; `--ci` fail nếu accuracy tỉnh < 0.5 khi có đủ case.

---

## 5. Vận hành & an toàn

| Tính năng | Chi tiết |
|-----------|-----------|
| Rate limit | `app/rate_limit_middleware.py` — giới hạn `/rag/*`, `/v1/rag/*` theo IP; `RAG_RATE_LIMIT_PER_MINUTE` (0 = tắt); bỏ qua `OPTIONS`. |
| Admin key tách | `RAG_ADMIN_API_KEY`: nếu set, **`/admin/*`** yêu cầu key này, không dùng `RAG_INTERNAL_API_KEY` cho admin. **Node admin** hiện proxy bằng internal key — nếu bật admin key trên RAG cần chỉnh proxy Node. |
| Gemini circuit breaker | `llm/gemini_generator.py` — sau nhiều lỗi quota liên tiếp mở circuit theo `RAG_GEMINI_CIRCUIT_*`. |
| Log JSON | `RAG_LOG_JSON=true` → `core/logging_config.py` ghi log dòng JSON. |
| OpenTelemetry | Nếu set `OTEL_EXPORTER_OTLP_ENDPOINT` và cài package instrumentation → `FastAPIInstrumentor.instrument_app(app)` sau khi mount router. |

---

## 6. Stub / mở rộng sau

- `rag/rerank_stub.py` — `maybe_cross_encoder_rerank()` (pass-through) để sau nối cross-encoder hoặc API rerank.

---

## 7. Phụ thuộc & cấu hình

- `requirements.txt` — thêm **scipy**, **pymysql**.
- `.env.example` — mô tả `RAG_ADMIN_API_KEY`, `RAG_RATE_LIMIT_PER_MINUTE`, `RAG_ENABLE_RRF`, `RAG_GEMINI_CIRCUIT_*`, `RAG_LOG_JSON`, `OTEL_EXPORTER_OTLP_ENDPOINT`, v.v.

---

## 8. CI

- `.github/workflows/rag-ci.yml` — khi đổi `backend/rag/**`: cài deps, import `app.main`, verify manifest (cho phép missing), chạy eval `--ci`.

---

## 9. Dọn code khác

- `rag/pipeline.py` — xóa khối comment trùng lặp phía cuối file.

---

## 10. Lệnh tham chiếu nhanh

```bash
cd backend/rag
pip install -r requirements.txt
python jobs/build_rag_artifacts.py
python scripts/verify_rag_artifacts.py
python scripts/eval_rag_retrieval.py --ci
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

*Tài liệu này là bản “clean” v1; khi có thay đổi lớn tiếp theo có thể tách `README_cleaner_v2.md` hoặc gộp vào `docs/v2/` theo quy ước repo.*
