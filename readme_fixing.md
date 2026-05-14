# readme_fixing — Nâng cấp backend Node & RAG (UnuTrip)

Tài liệu này gom **những gì đã thay đổi** trong repo (đợt “professionalize” gần nhất) và **việc còn nên làm** để đưa **backend Node.js** và **dịch vụ RAG (FastAPI)** lên mức vận hành/chất lượng chuyên nghiệp.

---

## Phần 1 — Đã thay đổi (tóm tắt theo hạng mục)

### 1.1 Backend Node.js (`backend/nodejs/`)

| Hạng mục | Mô tả |
|----------|--------|
| **Tách ứng dụng Express** | `src/app.js` export `createApp()` (middleware + route); `src/index.js` chỉ khởi động server (`assertSafeProductionConfig`, `listen`). Phục vụ test (Supertest) không cần mở port. |
| **Health API** | `src/routes/health.routes.js`: `GET /api/health` (liveness), `GET /api/health/ready` (MySQL `SELECT 1` + probe `GET {RAG_BASE_URL}/health`). Đăng ký đầu `buildRouter()` trong `src/routes/index.js`. Route cũ `GET /api/health` trong `auth.routes.js` đã bỏ để tránh trùng. |
| **Gọi RAG có timeout & retry** | `src/lib/ragUpstream.js`: `ragPostJson()` — timeout mỗi request (`RAG_FETCH_TIMEOUT_MS`), retry khi lỗi mạng hoặc HTTP 429/502/503/504 (`RAG_FETCH_MAX_ATTEMPTS`). |
| **Local AI có timeout** | `src/lib/httpFetch.js`: `fetchWithTimeout()`; `AI_MODEL_FETCH_TIMEOUT_MS` dùng cho `AI_MODEL_URL` / local chat trong `ai.service.js`. |
| **Chuẩn hóa phản hồi RAG chat đơn** | `src/schemas/ragContract.js` (Zod) + `normalizeRagChatSimpleResponse()`; `src/services/ai.service.js` dùng sau `/rag/chat/simple` (và fallback `/ai/chat`). Log cảnh báo `[rag-contract]` khi body lệch schema. |
| **Sửa lỗi nhỏ** | `src/seed.js`: import `jsonOrNull` từ `db.js`. `src/routes/helpers.js`: bỏ import `db` không dùng. |
| **Cấu hình** | `src/config/env.js`: thêm `RAG_FETCH_TIMEOUT_MS`, `RAG_FETCH_MAX_ATTEMPTS`, `HEALTHCHECK_SKIP_RAG`, `AI_MODEL_FETCH_TIMEOUT_MS`. |
| **Chất lượng code** | ESLint 9 (`eslint.config.js`), Prettier (`.prettierrc.json`), Vitest (`vitest.config.js`). `package.json`: script `lint`, `lint:fix`, `format`, `format:check` (scoped), `test`, `test:watch`. |
| **Test** | `tests/health.test.js` (mock `db` + `fetch`), `tests/ragUpstream.test.js` (retry 502), `tests/ragContract.test.js`, `tests/ai-rag-chat.route.test.js` (JWT + mock RAG). |
| **CI** | `.github/workflows/backend-ci.yml` (job `node-check`): `npm run lint`, `npm run format:check`, `npm test`, `node --check`. |
| **Môi trường mẫu** | `.env.example`: ghi chú biến Node→RAG và health (xem phần 2). |

### 1.2 RAG FastAPI (`backend/rag/`)

**Trong các đợt chỉnh sửa ghi trong file này, không có thay đổi mã nguồn RAG trực tiếp** — mọi cải tiến liên quan RAG ở đây là **tích hợt phía Node** (timeout, retry, readiness gọi `/health`, contract JSON `/rag/chat/simple`). Các hạng mục RAG “cần làm” nằm ở **Phần 3**.

### 1.3 File đường dẫn nhanh (đã đụng tới)

```
backend/nodejs/src/app.js
backend/nodejs/src/index.js
backend/nodejs/src/config/env.js
backend/nodejs/src/lib/httpFetch.js
backend/nodejs/src/lib/ragUpstream.js
backend/nodejs/src/schemas/ragContract.js
backend/nodejs/src/services/ai.service.js
backend/nodejs/src/routes/health.routes.js
backend/nodejs/src/routes/index.js
backend/nodejs/src/routes/auth.routes.js   (bỏ GET /health cũ)
backend/nodejs/src/routes/helpers.js
backend/nodejs/src/seed.js
backend/nodejs/package.json
backend/nodejs/package-lock.json
backend/nodejs/eslint.config.js
backend/nodejs/vitest.config.js
backend/nodejs/.prettierrc.json
backend/nodejs/tests/*.test.js
.github/workflows/backend-ci.yml
.env.example
readme_fixing.md                    (file này)
```

---

## Phần 2 — Biến môi trường & lệnh hữu ích

### 2.1 Biến mới / đáng chú ý (Node)

| Biến | Mặc định (gần đúng) | Ý nghĩa |
|------|---------------------|---------|
| `RAG_FETCH_TIMEOUT_MS` | `90000` | Timeout một lần gọi HTTP tới FastAPI RAG. |
| `RAG_FETCH_MAX_ATTEMPTS` | `3` | Số lần thử tối đa khi lỗi tạm (mạng / 429 / 502 / 503 / 504). |
| `HEALTHCHECK_SKIP_RAG` | `false` | `true`: `/api/health/ready` không probe RAG (RAG tùy chọn trong môi trường). |
| `AI_MODEL_FETCH_TIMEOUT_MS` | `120000` | Timeout gọi `AI_MODEL_URL` (local AI). |

Các biến đã có từ trước: `RAG_BASE_URL`, `RAG_INTERNAL_API_KEY`, `JWT_SECRET`, `DB_*`, v.v. — xem `.env.example`.

### 2.2 Lệnh (trong `backend/nodejs/`)

```bash
npm ci
npm run lint
npm run format:check
npm test
npm run dev
```

---

## Phần 3 — Việc cần làm để “lên chuyên nghiệp” (backlog gợi ý)

### 3.1 Backend Node.js (ưu tiên gợi ý)

| Ưu tiên | Việc làm |
|---------|----------|
| **P0** | **Schema Zod** cho body/response các endpoint proxy RAG còn lại (`/ai/itinerary-preview`, `/ai/itinerary-options`) và cho pipeline suggest-itinerary (JSON AI). |
| **P0** | **Test route** thêm: `/api/ai/chat` (mock local AI fail → RAG), các route itinerary proxy với mock `fetch`. |
| **P1** | **OpenAPI / contract-first**: export spec từ FastAPI RAG, generate client TypeScript hoặc giữ Zod đồng bộ tay — giảm vỡ field khi RAG đổi version. |
| **P1** | **Resilience phía Node**: circuit breaker độc lập (không chỉ retry), phân loại lỗi rõ (timeout vs 4xx vs 5xx), timeout riêng cho từng loại endpoint (chat ngắn vs itinerary dài). |
| **P1** | **Structured logging** (JSON), correlation id đã có `X-Request-ID` — đảm bảo mọi route AI/RAG đều forward và log cùng id. |
| **P2** | **Tách prompt lớn** trong `generateSuggestItineraryAiResult` ra module template + giới hạn catalog/token có chủ đích. |
| **P2** | **npm audit** / thay dependency có CVE (ví dụ xlsx); rà soát `multer`/upload. |
| **P2** | **Prettier full `src/`** (gồm `admin.js`) hoặc tách admin ra build riêng — hiện `format:check` chỉ scoped để CI không nổ hàng loạt diff cũ. |
| **P3** | **Docker Compose** một stack: Node + MySQL + Redis + RAG cho dev/prod parity. |

### 3.2 RAG FastAPI & pipeline retrieval

| Ưu tiên | Việc làm |
|---------|----------|
| **P0** | **CI eval có gate**: commit/cache artifact BM25 nhỏ hoặc golden tối thiểu để `eval_rag_retrieval.py` luôn chạy trên PR (hiện có thể skip khi thiếu index). |
| **P1** | **Vector retrieval** (embedding + Qdrant/Milvus/pgvector) + hybrid BM25+vector+RRF; cập nhật `rag_artifacts_manifest` (model embedding, dim). |
| **P1** | **Cross-encoder / API rerank** trên top-k trước khi đưa vào context (thay/thích hợp với rule-score hiện tại). |
| **P1** | **Provider interface**: Gemini/template sau interface chung; circuit breaker quota **theo Redis** (đa worker), không chỉ biến class-level. |
| **P2** | **Hoàn thiện layout module** theo `docs/v2/RAG_ARCHITECTURE.md` (`pipelines/`, `providers/`, `repositories/`). |
| **P2** | **Grounding / citation**: kiểm tra `place_id` trong câu trả lời ⊆ tập đã retrieve; JSON mode cho itinerary. |
| **P2** | **Dọn artifact**: xóa hoặc đưa ra khỏi deploy file kiểu `pipeline.backup_broken.py` nếu còn. |
| **P3** | **Observability**: OTEL end-to-end (Node → RAG), metric latency theo từng bước retrieval/generation. |

### 3.3 Liên kết Node ↔ RAG & vận hành

| Ưu tiên | Việc làm |
|---------|----------|
| **P1** | **Version API** rõ (`/v1` RAG đã có); Node và Android thống nhất contract version. |
| **P1** | **Readiness chặt**: tùy chọn probe `GET …/health/ready` của RAG thay vì chỉ `/health` nếu cần đảm bảo BM25 đã load. |
| **P2** | **Runbook**: cách build artifact RAG (`jobs/build_rag_artifacts.py`, export corpus), rotate key, rollback. |

---

## Phần 4 — Tài liệu kiến trúc có sẵn (nên đọc khi triển khai backlog)

- `docs/v2/RAG_ARCHITECTURE.md` — kiến trúc RAG mục tiêu.
- `docs/v2/BACKEND_RAG_BOUNDARY.md` — ranh giới Node vs RAG.
- `README.md`, `README_cleaner_v1.md` — tổng quan dự án và lịch sử nâng RAG v1.
- `database/docs/RAG_SYNC_FLOW.md` — luồng đồng bộ dữ liệu RAG.

---

## Phần 5 — Ghi chú bảo trì file này

- Khi hoàn thành một hạng mục trong Phần 3, có thể **chuyển sang Phần 1** (đã làm) và ghi rõ ngày / PR.
- Tránh để `readme_fixing.md` phình quá lâu: có thể tách backlog sang `docs/BACKLOG.md` sau khi ổn định quy trình.

---

*Cập nhật theo trạng thái repo tại thời điểm tạo file: ghi nhận đầy đủ đợt Node (app factory, health, RAG client, Zod contract, lint/test/format CI) và backlog chung Node + RAG.*
