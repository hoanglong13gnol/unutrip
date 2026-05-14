# UnuTrip — RAG v2: các cải tiến đã triển khai

Tài liệu này tóm tắt **những gì đã làm** trên nhánh hướng “RAG / backend chuyên nghiệp hơn”: bảo mật biên Node, quan sát theo request, CI, và Redis cho rate limit + cache Gemini (FastAPI RAG).

---

## 1. Backend Node (`backend/nodejs`)

### 1.1 Bảo mật & hợp đồng API

- **`POST /api/ai/rag-chat`**  
  - Gắn **`authMiddleware`** (JWT), khớp với Android (`ApiService.chat` đã gửi `Authorization: Bearer …`).  
  - Validate body bằng **Zod**: `message` (1–8000 ký tự), `top_k` (1–10, coerce số), `mode`, `targetProvince`, `targetCity`.

- **`db.js`**  
  - **Production** (`NODE_ENV=production`): không log đường dẫn `.env`, không in danh sách tên biến môi trường; chỉ log pool (database).  
  - **Development**: log có/không file env và **số lượng** biến đã load (không dump tên key).

- **`config/env.js`**  
  - Khi `NODE_ENV=production`, **cảnh báo** nếu chưa đặt `RAG_INTERNAL_API_KEY` (không throw để tránh phá deploy cũ).

### 1.2 Trace request (`X-Request-ID`)

- **`utils.js`**: hàm **`resolveRequestTrace(headers)`** — đọc `x-request-id` (hỗ trợ giá trị dạng mảng), tạo UUID nếu thiếu; trả về `{ requestId, traceHeaders }`.

- **`routes/ai.routes.js`**: các route sau đều **`res.setHeader("X-Request-ID", …)`** và gửi **`traceHeaders`** khi gọi FastAPI qua `ai.service.js`:  
  - `/ai/suggest-itinerary`  
  - `/ai/rag-chat`  
  - `/ai/chat` (fallback RAG)  
  - `/ai/itinerary-preview`  
  - `/ai/itinerary-options`

- **`services/ai.service.js`**:  
  - `requestRagChatSimple(payload, traceHeaders?)`  
  - `requestRagChatFallbackForAiChat({ message, traceHeaders? })`  
  - `requestItineraryPreview`, `requestItineraryOptions` nhận `traceHeaders`  
  - `generateSuggestItineraryAiResult` nhận `traceHeaders` cho lần gọi RAG `/rag/chat` fallback.

---

## 2. FastAPI RAG (`backend/rag`)

### 2.1 Rate limit

- Áp dụng cho **`/rag/*`**, **`/v1/rag/*`**, **`/ai/*`**, **`/v1/ai/*`** (trước đây chỉ `/rag/*`).
- **Có `REDIS_URL`**: giới hạn theo IP bằng **Redis** — cửa sổ cố định **60 giây** (`INCR` + `EXPIRE`), dùng chung nhiều replica.  
- **Không Redis**: giữ cơ chế **in-memory** (deque sliding) như trước, theo từng process.
- Cấu hình: `RAG_RATE_LIMIT_PER_MINUTE` (0 = tắt). Thông báo 429: *Too many AI/RAG requests*.

### 2.2 Cache câu trả lời Gemini

- **Có `REDIS_URL`**: lưu/ghi cache bằng **`SETEX` / `GET`** (JSON), key có tiền tố `REDIS_KEY_PREFIX` + `gem:v1:` + hash.  
- **Không Redis**: giữ **`data/cache/gemini_response_cache.jsonl`** + bộ nhớ trong process.  
- TTL: **`GEMINI_CACHE_TTL_SECONDS`** (mặc định 86400).  
- Admin **`/admin/cache/status`** và **`/admin/cache/clear`**: trả về `backend: redis` hoặc `local_jsonl`; clear Redis dùng `SCAN` + `DELETE` theo pattern cache Gemini.

### 2.3 Vòng đời ứng dụng & Redis client

- **`app/main.py` (lifespan)**  
  - Gọi **`init_redis(settings.redis_url)`** **trước** khi tạo `RagPipeline()`.  
  - Gán **`app.state.redis_client`** cho middleware.  
  - Shutdown: **`close_redis()`**, `app.state.redis_client = None`.

- **`core/redis_client.py`**: kết nối, `ping`, xử lý lỗi (fallback), `close`.

- **`core/rate_limit_redis.py`**: **`fixed_window_allow`** — không dùng Lua (tương thích fakeredis và Redis thật).

- **`core/config.py`**: thêm `redis_url`, `redis_key_prefix`, `gemini_response_cache_ttl_seconds` (+ helper đọc env).

### 2.4 Phụ thuộc Python

- **`requirements.txt`**: thêm **`redis>=5,<6`**.  
- **`requirements-dev.txt`**: **`pytest`**, **`fakeredis`**.

### 2.5 Kiểm thử tự động

- **`tests/test_schemas.py`**: Pydantic schema RAG (giới hạn `top_k`, v.v.).  
- **`tests/test_fusion.py`**: **`reciprocal_rank_fusion`** (BM25/TF-IDF RRF).  
- **`tests/test_redis_rate_limit.py`**: rate limit Redis bằng fakeredis.

---

## 3. CI GitHub Actions

- **`.github/workflows/backend-ci.yml`**  
  - Job **`rag-tests`**: Python 3.12, cài `requirements.txt` + `requirements-dev.txt`, chạy **`pytest tests/`**.  
  - Job **`node-check`**: `npm ci`, **`node --check src/index.js`**.  
  - Trigger khi thay đổi `backend/rag/**`, `backend/nodejs/**`, hoặc file workflow.  
  - Cache pip: cả `requirements.txt` và `requirements-dev.txt`.

---

## 4. Docker Redis (tùy chọn)

- **`deploy/redis-compose.yml`**: Redis 7 Alpine, port 6379, AOF, volume `unutrip_redis_data`.  
- Chạy: `docker compose -f deploy/redis-compose.yml up -d`  
- Trong **`.env`** (root repo): ví dụ `REDIS_URL=redis://127.0.0.1:6379/0` (và tùy chọn `REDIS_KEY_PREFIX`, `GEMINI_CACHE_TTL_SECONDS` — mô tả trong **`.env.example`**).

---

## 5. Biến môi trường liên quan (tham chiếu nhanh)

| Biến | Vai trò |
|------|--------|
| `REDIS_URL` | Bật Redis cho rate limit + cache Gemini trên service RAG |
| `REDIS_KEY_PREFIX` | Tiền tố key Redis (mặc định `unutrip:rag:`) |
| `GEMINI_CACHE_TTL_SECONDS` | TTL entry cache Gemini (giây) |
| `RAG_RATE_LIMIT_PER_MINUTE` | Giới hạn request/phút/IP cho `/rag/*` và `/ai/*` |
| `RAG_INTERNAL_API_KEY` | Khóa nội bộ FastAPI + header từ Node khi gọi RAG |

---

## 6. Hành vi cần lưu ý

- **Chatbot RAG**: sau khi bảo vệ route, cần **đăng nhập** (JWT hợp lệ); không token → 401.  
- **Rate limit Redis**: cửa sổ **cố định 60s** có thể cho phép nhẹ ở ranh giới phút so với sliding thuần in-memory.  
- **Không Redis**: scale nhiều replica RAG → rate limit và cache Gemini **không** đồng bộ giữa các instance (như thiết kế cũ).

---

## 7. Tài liệu kiến trúc có sẵn (chưa triển khai hết trong code)

- `docs/v2/RAG_ARCHITECTURE.md` — mục tiêu tách layer, `rag_knowledge_base`, vector/BM25 là artifact.  
- `database/docs/RAG_SYNC_FLOW.md` — luồng đồng bộ DB ↔ corpus ↔ index.

Các mục trên là **hướng dài hạn**; nội dung file `README_fixed_rag_v2.md` này chỉ mô tả **phần đã code / đã cấu hình** trong repo.

---

*Tạo theo yêu cầu: một README cố định ghi lại “những gì đã làm” cho RAG v2 / backend.*
