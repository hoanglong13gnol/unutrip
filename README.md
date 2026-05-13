# UnuTrip / SmartTravel

Ứng dụng du lịch kết hợp **Android**, **backend Node.js**, **dịch vụ RAG (Python / FastAPI)** và **MySQL**. Người dùng xem địa điểm, lịch trình, đánh giá, chatbot/RAG gợi ý và tạo lịch trình với AI.

---

## Kiến trúc tổng quan

| Thành phần | Công nghệ | Vai trò |
|------------|-----------|---------|
| **Android app** | Kotlin, Retrofit, Navigation, Room, OSMDroid | Client chính; gọi API Node (`/api/...`) |
| **Backend API** | Node.js, Express, MySQL2, JWT, Zod | Auth, CRUD địa điểm / lịch trình / review; proxy sang RAG |
| **RAG service** | Python, FastAPI, BM25 + hybrid retriever, Gemini (google-genai) | Chat RAG, gợi ý lịch trình, admin/debug |
| **Cơ sở dữ liệu** | MySQL (`unudata` mặc định) | `users`, `destinations`, `itineraries`, `rag_places`, … |

Luồng điển hình:

```
Android → http(s)://<host>:3000/api/* → Node → MySQL
                              ↓
                    RAG_BASE_URL (vd. :8001) → FastAPI RAG
```

---

## Cấu trúc thư mục (quan trọng)

```
UNUtrip/
├── .env                    # Cấu hình chung (backend Node, RAG đọc từ đây qua PROJECT_ROOT)
├── .env.example            # Mẫu biến môi trường
├── app/                    # Module Android duy nhất (Gradle root include ':app')
├── backend/
│   ├── nodejs/             # API Express
│   │   └── src/
│   │       ├── config/env.js, config/ragClient.js
│   │       ├── routes.js           # Re-export buildRouter
│   │       └── routes/             # Router tách module (xem mục “Thay đổi đã làm”)
│   └── rag/                # FastAPI RAG
│       ├── app/main.py
│       ├── core/
│       ├── rag/
│       ├── Dockerfile
│       └── requirements.txt
└── README.md               # File này
```

---

## Thiết lập nhanh

### 1. MySQL

- Tạo database (mặc định tên `unudata` trong `.env.example`).
- Import schema / dữ liệu theo script dự án (`backend/nodejs/database.sql` hoặc pipeline RAG/scripts tùy môi trường).

### 2. Biến môi trường (root `.env`)

Xem **`.env.example** đầy đủ. Các nhóm chính:

- **Node**: `BACKEND_HOST`, `BACKEND_PORT`, `JWT_SECRET`, `DB_*`, `RAG_BASE_URL`
- **RAG / AI**: `AI_RUNTIME_MODE`, `ENABLE_GEMINI`, `GEMINI_API_KEY`, `GEMINI_MODEL`, …
- **RAG hardening (mới)**: `RAG_LOG_LEVEL`, `RAG_DEBUG`, `RAG_INTERNAL_API_KEY`, `RAG_CORS_ORIGINS`

### 3. Chạy backend Node

```bash
cd backend/nodejs
npm install
npm run dev
# hoặc: npm start
```

Mặc định load `.env` từ thư mục gốc repo (`../../../.env` từ `src/`).

### 4. Chạy RAG (Python)

```bash
cd backend/rag
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### 5. Android

- Tạo **`local.properties`** (đã gitignore) ở root repo Gradle:

```properties
GEMINI_API_KEY=<key nếu app gọi Gemini trực tiếp>
API_BASE_URL=http://10.0.2.2:3000/api/
```

- **Product flavors**: `dev` (suffix `com.smarttravel.dev`) và `prod`.
- Build ví dụ: variant **`devDebug`** trong Android Studio.

`BASE_URL` và `GEMINI_API_KEY` trong `BuildConfig` lấy từ `local.properties` (không hard-code key trong `build.gradle`).

### 6. Docker (RAG)

Từ thư mục gốc repo:

```bash
docker build -f backend/rag/Dockerfile -t unutrip-rag backend/rag
docker run -p 8001:8001 --env-file .env unutrip-rag
```

---

## API & phiên bản

### Node (`/api`)

- Health: `GET /api/health`
- Auth, users, destinations, reviews, itineraries, proxy AI/RAG — giữ contract cũ cho app.
- `RAG_BASE_URL` trỏ tới service Python (mặc định `http://127.0.0.1:8001`).

### RAG (FastAPI)

- **Legacy paths** (không đổi): `/health`, `/rag/chat`, `/rag/chat/simple`, `/rag/retrieve`, `/ai/...`, `/admin/...`
- **Phiên bản API**: metadata `settings.api_version` (hiện **0.2.0**).
- **Prefix `/v1`**:  
  - Toàn bộ **AI itinerary** có thêm bản tại `/v1/ai/...`  
  - Thêm alias: `/v1/health`, `/v1/health/ready`, `/v1/runtime/status`, `/v1/rag/chat`, `/v1/rag/retrieve`, `/v1/rag/chat/simple`
- **Readiness**: `GET /health/ready` — trả **503** nếu pipeline chưa sẵn sàng hoặc thiếu `data/indexes/bm25_index.pkl` (dùng cho orchestrator / K8s).
- **Bảo vệ tùy chọn**: đặt `RAG_INTERNAL_API_KEY` → mọi route (trừ health/docs/openapi) cần header `X-RAG-Internal-Key` hoặc `Authorization: Bearer <key>`.
- **CORS**: bật khi `RAG_CORS_ORIGINS` là danh sách origin cách nhau bằng dấu phẩy.
- **Request ID**: middleware gắn `X-Request-ID` (vào response).

---

## Nhật ký thay đổi (đã triển khai trong repo)

### A. Backend Node (`backend/nodejs`)

1. **Tách router**  
   - `src/routes.js` chỉ re-export `buildRouter` từ `src/routes/index.js`.  
   - Module: `auth.routes.js`, `users.routes.js`, `favorites.routes.js`, `destinations.routes.js`, `reviews.routes.js`, `itineraries.routes.js`, `ai.routes.js`, cùng `helpers.js`, `upload.js`.

2. **Cấu hình & bảo mật**  
   - `src/config/env.js`: `RAG_BASE_URL`, `getJwtSecret()`, `assertSafeProductionConfig()`.  
   - Khi `NODE_ENV=production`, **bắt buộc** `JWT_SECRET` khác giá trị mặc định dev — nếu không server thoát.

3. **Database**  
   - `db.js`: không còn throw cứng khi `DB_NAME` ≠ `unudata`; chỉ **cảnh báo** (thuận tiện staging).

4. **Auth**  
   - `auth.js` dùng `getJwtSecret()` thống nhất.

5. **AI routes**  
   - `/ai/chat` an toàn hơn khi thiếu `message` trong body.  
   - Fallback không còn Gemini SDK trên Node; gọi RAG qua `config/ragClient.js`.

### B. Android (`app/build.gradle`)

1. **Secrets & base URL** từ `local.properties`: `GEMINI_API_KEY`, `API_BASE_URL` (tự thêm `/` nếu thiếu).  
2. **Product flavors**: `dev` (`applicationIdSuffix ".dev"`), `prod`.  
3. **`.env.example`**: ghi chú thêm biến Android trong `local.properties`.

### C. RAG (`backend/rag`)

1. **`core/logging_config.py`**: logging có cấu trúc ra stdout.  
2. **`core/security.py`**: `RAG_INTERNAL_API_KEY`, `RAG_CORS_ORIGINS`, `RAG_DEBUG`.  
3. **`app/middleware.py`**: Request ID, internal API key (optional), CORS optional.  
4. **`app/main.py`**: `lifespan` thay `on_event("startup")`, exception handlers JSON, `/health/ready`, mount `/v1` cho AI itinerary + alias RAG/health/runtime.  
5. **`core/config.py`**: thêm `api_version`.  
6. **`rag/pipeline.py`**: `print` → `logging`.  
7. **`requirements.txt`**: khoảng phiên bản rõ ràng hơn.  
8. **`Dockerfile`**: image chạy uvicorn cổng 8001.  
9. **`.env.example`**: biến RAG mới.

---

## Gợi ý tiếp theo (chưa làm)

- Docker Compose một lệnh: MySQL + Node + RAG.  
- Migration SQL có phiên bản (`migrations/`) thay vì chỉ một file dump lớn.

### Đã xử lý gần đây (refactor nợ kỹ thuật)

- **Android**: gỡ bỏ thư mục `android/` trùng lặp; chỉ dùng module `app/` ở root Gradle.  
- **Git**: `.gitignore` bỏ qua `**/build/`, venv Python, thư mục `/backups/`.  
- **Node ↔ RAG**: không còn `@google/generative-ai` trên Node; fallback AI dùng RAG (`/rag/chat`, `/rag/chat/simple`). Header `X-RAG-Internal-Key` được gắn tự động khi đặt `RAG_INTERNAL_API_KEY` trong `.env`.  
- **Repo**: xóa snapshot backup (`backups/`, `backend/rag_backup_*`, file `routes.backup*.js` trong Node).

---

## License / tác giả

Theo quyết định của team dự án (chưa ghi trong repo nếu bạn chưa thêm).

---

*Tài liệu này mô tả trạng thái dự án và các thay đổi đã merge vào codebase theo các phiên làm việc refactor backend, Android và nâng cấp RAG.*
