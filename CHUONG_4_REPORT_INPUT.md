# CHUONG_4_REPORT_INPUT.md

Tài liệu đầu vào cho **Chương 4. TRIỂN KHAI** — trích xuất từ **mã nguồn và cấu hình có trong repo**, không thay thế báo cáo hoàn chỉnh. Mọi chỗ không có chứng cứ được ghi **"Chưa tìm thấy trong mã nguồn"**.

---

## 1. Tổng quan triển khai hệ thống

Khi demo đầy đủ chức năng theo kiến trúc hiện tại, cần các thành phần sau (bổ sung tùy mô hình: chỉ MySQL local, hoặc **docker compose** cả stack).

| Thành phần | Công nghệ | Cổng/địa chỉ | Cách chạy (theo repo) | File/path chứng minh | Ghi chú |
|------------|-----------|--------------|-------------------------|------------------------|---------|
| Android app UNU Trip | Kotlin, Gradle | Client: gọi `BuildConfig.BASE_URL` (mặc định `http://10.0.2.2:3000/api/`) | Build/Run variant `devDebug` hoặc tương đương trong Android Studio; Gradle wrapper | `app/build.gradle`, `README.md` (§5 Android) | Flavor `dev`: `applicationId` suffix `.dev` |
| Backend Node.js/Express | Express 4, mysql2, JWT | **3000** (`BACKEND_PORT` / `PORT`), API: `http://<host>:3000/api` | `cd backend/nodejs && npm install && npm run dev` hoặc `npm start` | `backend/nodejs/package.json`, `backend/nodejs/src/index.js`, `README.md` | Log: `http://HOST:PORT/admin/dashboard` |
| MySQL | MySQL 8 (Docker) hoặc MySQL/MariaDB local (XAMPP) | **3306** (mặc định publish Docker) | Create DB + import SQL; hoặc `docker compose up` (service `mysql`) | `docker-compose.yml`, `backend/nodejs/database.sql` (ghi chú XAMPP), `.env.example` | DB mặc định env: **`unudata`** |
| FastAPI RAG | FastAPI + uvicorn | **8001** (compose + Dockerfile EXPOSE) | `cd backend/rag && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8001` hoặc Docker | `README.md`, `backend/rag/Dockerfile`, `docker-compose.yml` | Trước đó có thể cần build artifact/index (README: `jobs/build_rag_artifacts.py`, …) |
| Redis (tùy stack) | redis:7-alpine | 6379 nội bộ compose | `docker compose` service `redis` | `docker-compose.yml` | RAG compose set `REDIS_URL=redis://redis:6379/0` |
| Dashboard Admin | HTML trên Express | `http://<host>:3000/admin/...` | Mở trình duyệt sau khi backend chạy | `backend/nodejs/src/app.js`, `index.js` | Basic Auth tùy env (mục 7) |
| Open-Meteo | API HTTP công khai | `https://api.open-meteo.com/v1/forecast` | **Không cần chạy server** — app gọi trực tiếp | `app/src/main/java/com/smarttravel/utils/WeatherService.kt` | Không qua backend |
| OSMDroid / OSM tiles | OSMDroid, tile Mapnik | CDN OSM | Dùng trong app khi mở màn bản đồ | `app/src/main/java/com/smarttravel/ui/destination/MapFragment.kt` | Cần Internet |
| GPS / vị trí | Google Play Services Location | — | Quyền + `FusedLocationProviderClient` | `MapFragment.kt`, `app/src/main/AndroidManifest.xml` | Tuỳ thiết bị/emulator |

---

## 2. Môi trường cài đặt và công cụ sử dụng

### Ghi chú tổng hợp

- **Node.js:** `package.json` **không** có trường `engines` → phiên bản Node **Chưa tìm thấy trong mã nguồn**; Dockerfile backend dùng image **`node:20-bookworm-slim`** (`backend/nodejs/Dockerfile`).
- **npm:** **Chưa tìm thấy** pin phiên bản npm trong repo.
- **Python RAG:** `backend/rag/Dockerfile` — **`python:3.12-slim-bookworm`**. `requirements.txt` không ghi patch tối thiểu Python; `backend/nodejs/README.md` cũ nói Python **3.10+** cho hướng `server.py` (khác FastAPI RAG hiện tại) — khi viết báo cáo nên ưu tiên chứng cứ **Docker 3.12** + `requirements.txt`.
- **Android:** AGP **8.2.2**, Kotlin **1.9.23**, Gradle **8.4** (`build.gradle` root, `gradle-wrapper.properties`).
- **JDK:** **Chưa tìm thấy** file `jvm toolchain` cố định; với AGP 8.x, thông lệ là **JDK 17+** (ghi trong báo cáo như khuyến nghị, không khẳng định từ file repo).
- **MySQL / XAMPP:** `database.sql` ghi **"Manual Import for XAMPP / phpMyAdmin"** — đây là hướng thủ công, không có script tự động XAMPP trong repo.
- **Postman:** **Chưa tìm thấy** collection (`.postman` / tương đương) trong repo.
- **Docker:** `docker-compose.yml` ở thư mục gốc + `Dockerfile` `backend/nodejs`, `backend/rag`.
- **Trình duyệt Admin:** **Chưa chỉ định** trong code — mọi trình duyệt HTTP đều được (Express + HTML).

| Công cụ | Phiên bản/cấu hình | Vai trò | File/path chứng minh |
|---------|-------------------|---------|----------------------|
| Node.js (Docker backend) | Image `node:20-bookworm-slim` | Chạy API trong container | `backend/nodejs/Dockerfile` |
| npm | — | Cài dependency backend (`npm install` / `npm ci`) | `backend/nodejs/package.json` |
| Python (Docker RAG) | `python:3.12-slim-bookworm` | Chạy FastAPI RAG | `backend/rag/Dockerfile` |
| pip / requirements | `requirements.txt` (khoảng phiên bản package) | Cài phụ thuộc RAG | `backend/rag/requirements.txt` |
| Android Gradle Plugin | `8.2.2` | Build Android | `build.gradle` (root) |
| Gradle | `8.4` | Wrapper | `gradle/wrapper/gradle-wrapper.properties` |
| Kotlin | `1.9.23` | Biên dịch app | `build.gradle` (root) |
| Docker / Compose | Compose file v4 services | Stack MySQL + Redis + RAG + Backend | `docker-compose.yml` |
| Android SDK (compile) | `compileSdk 34`, `minSdk 26`, `targetSdk 34` | Build app | `app/build.gradle` |
| OS môi trường dev | **Chưa tìm thấy** yêu cầu OS trong repo | — | — |

---

## 3. Quy trình cài đặt cơ sở dữ liệu MySQL / XAMPP

### Xác định từ code

- **Tên database (mặc định cấu hình):** `DB_NAME` mặc định **`unudata`** (`.env.example`, `docker-compose.yml`, `backend/nodejs/src/db.js`).
- **File SQL có trong repo:** `backend/nodejs/database.sql` — schema + comment nhập tay XAMPP/phpMyAdmin; tạo bảng **`users`, `destinations`, `favorites`, `reviews`, `itineraries`, …** (legacy).
- **Migration v2:** thư mục `database/migrations/` — **`001`–`010`** theo thứ tự trong `database/migrations/README.md`.

### Mâu thuẫn quan trọng cần nêu khi triển khai (chứng minh)

- API đọc địa điểm hiện tại dùng bảng **`app_places`** (`backend/nodejs/src/repositories/destinations.repository.js`).
- `backend/nodejs/database.sql` và `seed.js` thao tác bảng **`destinations`** (legacy).
- **Kết luận cho báo cáo triển khai:** team cần **một đường dữ liệu rõ ràng**: hoặc import/migrate sang **`app_places`** (pipeline `database/migrations`), hoặc đồng bộ DB với nhánh code đang chạy. **Không tự bịa** trạng thái DB thực tế trên máy demo.

### Các bước gợi ý (biên tập theo môi trường)

**Bước 1.** Cài MySQL (XAMPP hoặc MySQL độc lập hoặc Docker như `docker-compose.yml`).

**Bước 2.** Tạo database (vd. `unudata`) khớp `.env` (`DB_NAME`).

**Bước 3.** Import **`backend/nodejs/database.sql`** nếu dùng schema “SmartTravel” trong file đó (phpMyAdmin / `mysql` CLI).

**Bước 4.** (Tuỳ đề tài v2) Chạy lần lượt file **`database/migrations/001`…`010`** theo `database/migrations/README.md` (trên DB thử nghiệm trước).

**Bước 5.** Dữ liệu mẫu: script **`backend/nodejs/src/seed.js`** export hàm `seed()` nhưng **Chưa tìm thấy** trong mã nguồn chỗ gọi tự động khi `npm start` / `npm run dev`; **Chưa tìm thấy** script `npm run seed` trong `package.json`. Để chạy seed cần bổ sung lệnh gọi (ngoài phạm vi file báo cáo này không sửa code) — **ghi rõ trong báo cáo** nếu nhóm chưa wire CLI.

### Bảng file SQL / migration

| File SQL/migration | Mục đích | Bảng tạo / tác động | Có cần import khi demo không |
|--------------------|----------|---------------------|-------------------------------|
| `backend/nodejs/database.sql` | Schema legacy (comment XAMPP) | `users`, `destinations`, `favorites`, `reviews`, `itineraries`, … | **Cần** nếu dùng đúng file này làm nguồn schema legacy |
| `database/migrations/001_create_app_places.sql` | Tạo `app_places` | `app_places` | **Cần** nếu API dùng `app_places` như code hiện tại |
| `002_create_rag_knowledge_base.sql` | KB RAG trong MySQL | `rag_knowledge_base` | Tuỳ pipeline RAG DB-backed |
| `003_create_place_images.sql` | Ảnh runtime | `place_images` | Tuỳ |
| `004_create_place_id_map.sql` | Map id | `place_id_map` | Tuỳ AI/raw id |
| `005_create_v2_indexes.sql` | Index v2 | — | Tuỳ |
| `006`–`009` | Populate từ nguồn legacy | `app_places`, … | Tuỳ quy trình nhóm |
| `010_v2_validation_queries.sql` | Validation (read-only) | — | Kiểm tra sau migrate |

---

## 4. Quy trình cấu hình và chạy Backend Node.js/Express

| Mục | Chi tiết | Chứng minh |
|-----|----------|------------|
| Cài thư viện | `npm install` (trong `backend/nodejs`) | `README.md`, `package.json` |
| Chạy dev | `npm run dev` → `node --watch src/index.js` | `package.json` |
| Chạy “production” kiểu process | `npm start` → `node src/index.js` | `package.json` |
| Port mặc định | `Number(process.env.BACKEND_PORT \|\| process.env.PORT \|\| 3000)` | `backend/nodejs/src/index.js` |
| Base API | Prefix **`/api`** | `backend/nodejs/src/app.js` |
| Admin | **`/admin`** (sau `adminAuthMiddleware`) | `backend/nodejs/src/app.js` |
| Env | Load `.env` từ **thư mục gốc repo** trong `config/env.js` và `db.js` | `backend/nodejs/src/config/env.js`, `backend/nodejs/src/db.js` |
| MySQL | Pool `mysql.createPool` với `DB_*` | `backend/nodejs/src/db.js` |
| Gọi RAG | `RAG_BASE_URL` + client `ragPostJson` / `ragUrl` | `backend/nodejs/src/config/env.js`, `backend/nodejs/src/lib/ragUpstream.js`, `backend/nodejs/src/config/ragClient.js` |

### Bảng biến môi trường (chọn lọc — đầy đủ xem `.env.example`)

| Biến môi trường | Ý nghĩa | Mặc định nếu có | Bắt buộc khi demo | File/path |
|-----------------|---------|-------------------|-------------------|-----------|
| `NODE_ENV` | Chế độ Node | `development` trong `.env.example` | Không (nhưng `production` kích hoạt check JWT) | `.env.example`, `backend/nodejs/src/config/env.js` |
| `BACKEND_HOST` / `HOST` | Bind address | `0.0.0.0` | Không | `index.js` |
| `BACKEND_PORT` / `PORT` | Cổng lắng nghe | **3000** | Không (có default) | `index.js` |
| `JWT_SECRET` | Ký JWT | Ví dụ placeholder trong `.env.example`; code có default dev | **Bắt buộc** nếu `NODE_ENV=production` (assert) | `auth.js`, `config/env.js` |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL | `127.0.0.1`, `3306`, `root`, `""`, `unudata` trong example | **Cần** khớp máy chủ DB thật | `db.js`, `.env.example` |
| `RAG_BASE_URL` | URL FastAPI | `http://127.0.0.1:8001` | **Cần** khi demo AI/RAG qua Node | `config/env.js`, `.env.example` |
| `RAG_INTERNAL_API_KEY` | Key gửi sang RAG (header) | Rỗng trong example | Tùy cấu hình bảo mật RAG | `ragClient.js`, `.env.example` |
| `HEALTHCHECK_SKIP_RAG` | Bỏ probe RAG trong readiness API | `false` | Tùy | `config/env.js` |

### Bảng lệnh

| Bước | Lệnh | Mục đích |
|------|------|----------|
| 1 | `cp .env.example .env` rồi chỉnh (tại thư mục gốc repo) | Tạo cấu hình | `.env.example`, `README.md` |
| 2 | `cd backend/nodejs` | Vào thư mục backend | `README.md` |
| 3 | `npm install` | Cài dependency | `package.json` |
| 4 | `npm run dev` | Chạy dev có `--watch` | `package.json` |
| 5 | (Tuỳ) `npm test` | Vitest | `package.json` |

---

## 5. Quy trình cấu hình và chạy FastAPI RAG Service

| Mục | Chi tiết | Chứng minh |
|-----|----------|------------|
| Entry FastAPI | `app = FastAPI(...)` trong `app/main.py`, uvicorn target `app.main:app` | `backend/rag/app/main.py`, `Dockerfile` |
| Cài dependency | `pip install -r requirements.txt` | `README.md`, `requirements.txt` |
| Chạy local | `uvicorn app.main:app --host 0.0.0.0 --port 8001` | `README.md` |
| Port | **8001** (Docker CMD + README) | `Dockerfile`, `README.md` |
| Build artifact / index | `python jobs/build_rag_artifacts.py` hoặc `python scripts/06_build_bm25_index.py` | `README.md` |
| AI runtime | `Settings` trong `core/config.py`: **`AI_RUNTIME_MODE` default `"mock"`**, **`ENABLE_GEMINI` default `False`**, `GEMINI_API_KEY` từ env | `backend/rag/core/config.py` |
| Khi nào “thật” | Khi bật cấu hình env (ví dụ **`ENABLE_GEMINI=true`** + có **`GEMINI_API_KEY`**) — **không** suy diễn máy demo của nhóm | `.env.example`, `core/config.py`, `app/routers/health.py` (`runtime_status` báo `enable_gemini`, `gemini_configured`) |
| Mock / fallback | Default code: **`mock`** + **`enable_gemini` false**; logic chi tiết trong pipeline/service (báo cáo nên trích thêm khi đọc `services/` nếu cần độ sâu) | `core/config.py` |

### Bảng biến cấu hình RAG (trích chính)

| Biến | Ý nghĩa | Mặc định (code Python) | Ghi chú demo |
|------|---------|--------------------------|--------------|
| `AI_RUNTIME_MODE` | Chế độ chạy AI | **`mock`** | `.env.example` ghi ví dụ `demo` — khác default code |
| `ENABLE_GEMINI` | Bật Gemini | **`false`** | `.env.example` = `true` là mẫu triển khai |
| `GEMINI_API_KEY` | Key API | `None` nếu không set | Chỉ RAG đọc trực tiếp (ghi trong `.env.example`) |
| `GEMINI_MODEL` | Model | `gemini-2.5-flash` | `core/config.py` |
| `REDIS_URL` | Redis tùy chọn | `None` | Compose set trong `docker-compose.yml` |
| `RAG_INTERNAL_API_KEY` | Bảo vệ route | Không set → middleware có đường “mở” | `app/middleware.py` |

### Bảng endpoint RAG (đại diện — không liệt kê hết `/admin/*`)

| Endpoint RAG | Method | Mục đích | Dùng ở đâu (theo repo) |
|----------------|--------|----------|-------------------------|
| `/health` | GET | Trạng thái | Docker healthcheck, README |
| `/health/ready` | GET | Readiness (503 nếu chưa sẵn sàng) | `README.md`, `health.py` |
| `/runtime/status` | GET | Metadata runtime, gemini flag | `health.py` |
| `/rag/chat` | POST | Chat RAG đầy đủ | `rag.py`, Node proxy qua `ai.service.js` |
| `/rag/chat/simple` | POST | Chat đơn giản | `rag.py`, Node `/api/ai/rag-chat` |
| `/rag/retrieve` | POST | Retrieve | `rag.py` |
| `/chat` | GET/POST | Legacy / tương thích | `rag.py`, README “legacy paths” |
| `/admin/*` | GET/POST | Metrics, logs, debug-query, data-quality, … | `admin.py`, Node admin `ragAi.admin.routes.js` |
| `/docs` | GET | Swagger | `middleware.py` exempt API key cho docs |

*(Prefix `/v1` cho một số route — xem `README.md` mục “Phiên bản API”.)*

---

## 6. Quy trình cấu hình và chạy Android App

### Bảng thông tin

| Thông tin | Giá trị | File/path chứng minh |
|-----------|---------|----------------------|
| `applicationId` | `com.smarttravel` (prod flavor); dev: suffix **`.dev`** | `app/build.gradle` |
| App name | `UNU Trip` | `app/src/main/res/values/strings.xml` — `app_name` |
| `minSdk` / `targetSdk` / `compileSdk` | **26** / **34** / **34** | `app/build.gradle` |
| Base URL mặc định (không có `local.properties`) | `http://10.0.2.2:3000/api/` | `app/build.gradle` |
| `local.properties` | Gitignored; mẫu keys trong `README.md` & comment `.env.example` | `README.md`, `.env.example` |
| Emulator → máy host | **`10.0.2.2`** maps tới localhost máy dev | `app/build.gradle`, `README.md` |
| Thiết bị thật | Cần **`API_BASE_URL=http://<IP_LAN_máy_chạy_backend>:3000/api/`** trong `local.properties` | `app/build.gradle`, `README.md` |
| Network cleartext | Main manifest: **`usesCleartextTraffic="false"`**; flavor **dev** replace `true` + `network_security_config` cleartext | `app/src/main/AndroidManifest.xml`, `app/src/dev/AndroidManifest.xml`, `app/src/dev/res/xml/network_security_config.xml` |
| Build / test (ví dụ) | `./gradlew testDevDebugUnitTest lintDevDebug` | `README.md` |

#### APK / AAB

- **Chưa tìm thấy** script release tùy chỉnh trong repo ngoài chuẩn Android Gradle. Thông lệ: `./gradlew assembleDevDebug` / `assembleRelease` (không có wrapper path cố định trong tài liệu riêng — dùng Gradle project root).

### Bảng permission (trích `AndroidManifest.xml`)

| Permission | Mục đích | File/path |
|------------|----------|-----------|
| `INTERNET` | Gọi API / OSM / Open-Meteo | `app/src/main/AndroidManifest.xml` |
| `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` | Bản đồ / GPS | idem |
| `CAMERA` | (Khai báo; `required=false`) — **mục đích chi tiết trong code** không liệt kê hết tại manifest | idem |
| `READ_EXTERNAL_STORAGE` (maxSdk 32) | Đọc media (max API 32) | idem |
| `WRITE_EXTERNAL_STORAGE` (maxSdk 29) | Cache OSMDroid (comment manifest) | idem |

---

## 7. Quy trình truy cập Dashboard Admin

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| URL gốc | **`http://<BACKEND_HOST>:<PORT>/admin/...`** — ví dụ log: `http://${HOST}:${PORT}/admin/dashboard` | `backend/nodejs/src/index.js` |
| Basic Auth | Chỉ áp dụng khi **đồng thời** có `ADMIN_BASIC_USER` **và** `ADMIN_BASIC_PASS`; thiếu → **cho qua** + `console.warn` | `backend/nodejs/src/middlewares/adminAuth.middleware.js` |
| RAG AI page gọi API | `GET /admin/rag-ai` fetch song song các path FastAPI `/admin/...` | `backend/nodejs/src/admin/ragAi.admin.routes.js` |

### Bảng màn hình Admin

| Màn hình Admin | Route (prefix `/admin`) | Chức năng (đăng ký route) | File/path |
|------------------|---------------------------|-----------------------------|-----------|
| Dashboard | `GET /dashboard` | Thống kê users / `app_places` / itineraries | `dashboard.admin.routes.js` |
| Người dùng | `GET /users`, `GET /users/api/:id`, `POST /users/save`, `POST /users/delete/:id` | CRUD user | `users.admin.routes.js` |
| Địa điểm | `GET /destinations`, … | CRUD địa điểm | `destinations.admin.routes.js` |
| Hệ thống | `GET /system` | Thống kê hệ thống | `system.admin.routes.js` |
| RAG AI Monitor | `GET /rag-ai` + POST/GET action phụ | Giám sát + reload store, clear cache, metrics, logs, debug query | `ragAi.admin.routes.js` |
| AI Report | `GET /ai-report` | Báo cáo AI | `aiReport.admin.routes.js` |

---

## 8. Giao diện chương trình cần chụp ảnh cho Chương 4

### Android (theo Fragment/Activity có trong mã)

| Số hình đề xuất | Tên giao diện | File màn hình/Fragment | Gợi ý nội dung mô tả |
|-----------------|----------------|-------------------------|------------------------|
| 1 | Đăng nhập / Đăng ký | `ui/auth/AuthActivity.kt` + layout `activity_auth` | Form đăng nhập vs toggle đăng ký |
| 2 | Trang chủ | `HomeFragment.kt` | Featured, nearby, tìm kiếm |
| 3 | Danh sách địa điểm | `DestinationListFragment.kt` | Grid/list + filter category |
| 4 | Chi tiết địa điểm | `DestinationDetailFragment.kt` | Ảnh, mô tả, weather card, reviews, nút yêu thích / thêm itinerary |
| 5 | Bản đồ OSM | `MapFragment.kt` | Marker đích + (nếu có) vị trí hiện tại |
| 6 | Thời tiết (embedded) | Chi tiết địa điểm + `WeatherService.kt` | Nhiệt độ, 5 ngày |
| 7 | Lịch trình — danh sách | `ItineraryFragment.kt` | Danh sách trip + FAB/nút tạo |
| 8 | Chi tiết lịch trình | `ItineraryDetailFragment.kt` (và adapter trong file) | Ngày / điểm |
| 9 | AI tour — request/options/editor | `AIItineraryRequestFragment.kt`, `AIItineraryOptionsFragment.kt`, `AIItineraryEditorFragment.kt` | Luồng AI multi-step |
| 10 | AI gợi ý lịch trình (AISuggest) | Class `AISuggestFragment` trong `ItineraryDetailFragment.kt` | Form preferences + generate |
| 11 | Chatbot | `ChatbotFragment.kt` | Hội thoại + chip gợi ý |
| 12 | Hồ sơ | `ProfileFragment.kt` | Avatar, menu, stats |
| 13 | Yêu thích | `DestinationListFragment` với `isFavoriteOnly=true` từ `ProfileFragment` | Danh sách chỉ favorite |
| 14 | Đánh giá / viết review | Trong `DestinationDetailFragment` + dialog (nếu tách file dialog review) | RV reviews + nhập review |
| 15 | Cài đặt | `SettingsFragment.kt` | Menu placeholder “đang phát triển” |
| 16 | Main shell | `MainActivity.kt` + `activity_main.xml` | Bottom navigation |

### Dashboard Admin

| Số hình đề xuất | Tên giao diện | Route | Gợi ý mô tả |
|-----------------|---------------|-------|-------------|
| A1 | Dashboard tổng quan | `/admin/dashboard` | Số liệu tổng hợp |
| A2 | Quản lý người dùng | `/admin/users` | Bảng user |
| A3 | Quản lý địa điểm | `/admin/destinations` | Bảng địa điểm |
| A4 | Hệ thống | `/admin/system` | Thống kê hệ thống |
| A5 | RAG AI Monitor | `/admin/rag-ai` | KPI + JSON boxes |

---

## 9. Biện pháp bảo vệ hệ thống

| Nội dung bảo mật | Cách triển khai hiện tại | File/path | Ghi chú/hạn chế |
|------------------|-------------------------|-----------|-------------------|
| Hash mật khẩu | bcrypt `hashSync` / `compareSync` | `backend/nodejs/src/modules/auth/auth.controller.js` | |
| JWT | `jsonwebtoken`; middleware bearer | `backend/nodejs/src/auth.js` | Default secret dev trong code — không dùng prod |
| Lưu token Android | `EncryptedSharedPreferences` | `app/.../SessionManager.kt` | |
| Auth API | `authMiddleware` | `backend/nodejs/src/auth.js` + các `*.routes.js` |
| Admin Basic Auth | Optional — thiếu env thì mở | `adminAuth.middleware.js` | Rủi ro demo |
| Env | `.env` gốc repo; dotenv trong Node/RAG | `.env.example`, `db.js`, `rag/core/config.py` |
| CORS | `cors()` toàn app | `app.js` | Mặc định mở theo chính sách thư viện |
| Helmet / CSP | `helmet` + nonce admin | `app.js` | |
| Network Android | cleartext chỉ dev flavor | `app/src/dev/...`, manifest main | Prod cần HTTPS hoặc cấu hình phù hợp |
| Gemini key | RAG đọc `GEMINI_*`; Node không gọi SDK Gemini (comment `.env.example`) | `.env.example` | |
| Logout | `ProfileFragment` **xóa session local**, **không** gọi `POST auth/logout` đã định nghĩa trong `ApiService.kt` | `ProfileFragment.kt`, `ApiService.kt` |

---

## 10. Xử lý lỗi và fallback

| Tình huống lỗi | Cách xử lý trong code | File/path | Gợi ý cách viết báo cáo |
|----------------|----------------------|-----------|---------------------------|
| HTTP API lỗi (Android) | Repositories trả `Resource.Error`; Retrofit log body lỗi khi !success | `Repositories.kt`, `RetrofitClient.kt` | Mô tả lớp repository + log |
| 404/500 Express | `notFoundMiddleware` → `HttpError`; `errorHandlerMiddleware` JSON `success: false` | `notFound.middleware.js`, `errorHandler.middleware.js` | |
| RAG không gọi được (Node) | `ragPostJson` retry transient; AI routes trả 502 / message | `ragUpstream.js`, `ai.controller.js` | |
| Chatbot RAG fail | `ChatbotViewModel` fallback `GeminiService` qua `/ai/chat` | `ChatbotViewModel.kt` | Chuỗi fallback nhiều lớp |
| Weather | Không map được city → tọa độ **Hà Nội**; lỗi → `Resource.Error` | `WeatherService.kt` | Ghi rõ heuristic + rủi ro |
| Map / GPS | Toast khi từ chối quyền / `lastLocation` null | `MapFragment.kt` | |
| Admin RAG down | `fetchRagJson` không ok → biểu tượng/HTTP đỏ trong template (chi tiết HTML) | `ragAi.admin.routes.js` | Diễn giải “quan sát dashboard” khi demo |

---

## 11. Dữ liệu thử nghiệm

**Không thể suy ra số lượng bản ghi thực tế trên DB chỉ từ static code** — chỉ có quy ước trong `seed.js` và nội dung file seed.

| Loại dữ liệu | Số lượng tìm thấy trong **logic seed** (không phải DB thực) | Bảng/file nguồn | Mục đích thử nghiệm |
|--------------|----------------------------------------------------------|-----------------|---------------------|
| Users | Mục tiêu ~**50** user nếu chạy `seedUsers` (có user demo `demo@smarttravel.local`) | `users` | `seed.js` |
| Destinations | Vòng lặp seed từ ~**50** mục hardcode + có thể mở rộng từ JSON | `destinations` | `DESTINATIONS_DATA` trong `seed.js` |
| Reviews | Mục tiêu ~**50** reviews trong `seedReviews` | `reviews` | `seed.js` |
| Itineraries / items | Mục tiêu ~**100** itineraries (logic vòng lặp) | `itineraries`, `itinerary_days`, `itinerary_items` | `seed.js` |
| RAG knowledge base (DB) | **Chưa đếm** — tuỳ import migration `009` + DB thực | `rag_knowledge_base` | `database/migrations/009_populate_rag_knowledge_base.sql` |

**Ghi chú:** `seed.js` dùng bảng **`destinations`** trong khi runtime API list destination đọc **`app_places`**. Số lượng sau khi import/migrate **phải đối chiếu trên MySQL** — báo cáo nên ghi: *"Chưa xác định, cần kiểm tra database sau import"* nếu chưa đo trực tiếp.

---

## 12. Kết quả thử nghiệm chức năng (bảng test case đề xuất)

Cột **Trạng thái khi demo** để chủ project điền — không suy ra từ code.

| STT | Chức năng | Dữ liệu đầu vào | Kết quả mong đợi (theo contract code) | Cách kiểm tra | Trạng thái cần điền khi demo |
|-----|-----------|-----------------|----------------------------------------|---------------|------------------------------|
| 1 | Đăng ký | email, password, fullName, phone? | `201/200` JSON `success`, có `token` + `user` | App form hoặc `POST /api/auth/register` | |
| 2 | Đăng nhập | email, password | JSON có JWT | App hoặc `POST /api/auth/login` | |
| 3 | Danh sách địa điểm | header Bearer | `GET /api/destinations` trả `DestinationResponse` | Tab Khám phá / list | |
| 4 | Tìm kiếm | query `search` | Lọc theo backend `name/description/city/province` | Ô tìm trên Home/List | |
| 5 | Chi tiết địa điểm | `id` | `GET /api/destinations/:id` | Màn detail | |
| 6 | Bản đồ | lat, lng, tên | OSMDroid hiển thị marker | Nút xem bản đồ | |
| 7 | Thời tiết | city name string | Open-Meteo JSON → UI card hoặc ẩn khi lỗi | Màn detail | |
| 8 | Tạo lịch trình | title, date… | `POST /api/itineraries` | Dialog tạo / flow itinerary | |
| 9 | Xóa lịch trình | itinerary id | `DELETE /api/itineraries/:id` | Nút xóa list | |
| 10 | Thêm địa điểm vào lịch trình | itineraryId, destinationId | `POST /api/itineraries/:id/items` | Chi tiết địa điểm → chọn itinerary | |
| 11 | Đánh giá | rating, comment, optional images | `POST /api/reviews` (multipart hoặc JSON) | Màn detail | |
| 12 | Yêu thích | destination id | POST/DELETE favorites | FAB favorite | |
| 13 | Chatbot AI | message | Android → `POST /api/ai/rag-chat` (RAG); fallback `/api/ai/chat` trong `ChatbotViewModel` | Tab Trợ lý | |
| 14 | Gợi ý lịch AI | preferences, date range | `POST /api/ai/suggest-itinerary` + lưu `save-ai` trong flow AISuggest | `AISuggestFragment` | |
| 15 | Dashboard Admin | truy cập browser | Trang `/admin/dashboard` tải được | Chrome/Edge… | |
| 16 | RAG AI Monitor | mở `/admin/rag-ai` | Fetch các `/admin/*` RAG hiển thị KPI/JSON | Browser | |
| 17 | Debug query RAG | POST body message | `POST /admin/rag-ai/debug-query` → FastAPI `/admin/ai/debug-query` | Form debug (nếu có trong trang) | |

---

## 13. Các lệnh chạy demo tổng hợp

### Checklist dạng danh sách

1. **MySQL** chạy (XAMPP hoặc Docker `mysql` hoặc instance riêng).
2. **Import schema/dữ liệu** (`database.sql` và/hoặc `database/migrations` — thống nhất với nhánh `app_places`).
3. **Copy `.env`** từ `.env.example`, chỉnh `DB_*`, `JWT_SECRET`, `RAG_BASE_URL`, `GEMINI_*` nếu cần.
4. **Chạy RAG:** `pip install …` + `uvicorn … :8001` *hoặc* `docker compose up rag` (kèm Redis nếu dùng compose).
5. **Chạy backend:** `cd backend/nodejs && npm install && npm run dev`.
6. **Kiểm tra** `GET http://localhost:3000/api/health` và (tuỳ) `/api/health/ready`.
7. **Mở Admin:** `http://localhost:3000/admin/dashboard`.
8. **Android:** tạo `local.properties` với `API_BASE_URL`; chạy app trỏ tới backend.
9. **Postman:** không bắt buộc — **Chưa có** collection trong repo; có thể gọi thủ công các REST như `README.md`.

### Bảng

| Thứ tự | Thành phần | Lệnh/thao tác | Kết quả cần thấy |
|--------|------------|---------------|------------------|
| 1 | MySQL | Bật service / `docker compose up -d mysql` | Port 3306 listening / container healthy |
| 2 | Import DB | Import `database.sql` + (tuỳ) migrations `001`–`010` | Bảng tồn tại khi `SHOW TABLES` |
| 3 | Env | `cp .env.example .env` và sửa | Backend đọc đúng `DB_NAME` |
| 4 | RAG | `uvicorn app.main:app --port 8001` hoặc compose | `GET /health` trả JSON ok |
| 5 | Backend | `npm run dev` trong `backend/nodejs` | Log “running on http://…” |
| 6 | Kiểm tra API | Trình duyệt/curl `GET /api/health` | `ok: true` trong body hiện tại |
| 7 | Admin | Mở `/admin/dashboard` | HTML dashboard |
| 8 | Android | Run **devDebug** với `API_BASE_URL` | App tải danh sách khi backend + DB đúng |

---

## 14. Hạn chế triển khai hiện tại (theo chứng cứ code)

- **AI RAG default** trong Python: **`AI_RUNTIME_MODE=mock`**, **`ENABLE_GEMINI=false`** mặc định — `.env.example` lại ghi ví dụ khác → **phải thống nhất khi demo** (`backend/rag/core/config.py`, `.env.example`).
- **UI itinerary:** codebase `ItineraryFragment` lớn, có nhiều luồng AI — **Chưa tìm thấy** chứng cứ “đầy đủ mọi nút đều hoàn thiện” ngoài việc file tồn tại (đánh giá chức năng là việc của nhóm khi chạy thực tế).
- **Logout server-side:** endpoint `POST /api/auth/logout` có trong `ApiService.kt` nhưng UI logout **chưa gọi** — chỉ xóa local session (`ProfileFragment.kt`).
- **Admin Basic Auth:** thiếu env → **không khóa** (`adminAuth.middleware.js`).
- **Schema `destinations` vs `app_places`:** xung đột tiềm ẩn giữa `database.sql`/`seed.js` và repository runtime — **rất quan trọng** khi mô tả triển khai DB.
- **Deploy production:** có Docker nhưng **Chưa tìm thấy** pipeline CI/CD hay K8s manifest trong repo (ngoài compose).
- **Docker Compose:** có **đủ** MySQL + Redis + RAG + Backend trong `docker-compose.yml`, kèm note **“không tự migrate đầy đủ”** — vẫn cần import SQL thủ công.
- **Weather:** fallback **Hà Nội** khi không map được tên thành (`WeatherService.kt`).
- **Seed tự động:** `seed()` **không** được gọi từ `index.js` và **không** có npm script — dễ dẫn tới DB trống nếu không import/`seed` thủ công.

---

## 15. Hướng phát triển

Gợi ý phù hợp với gaps đã liệt kê (không bịa roadmap sản phẩm):

- Chuẩn hóa **một** schema DB (`app_places` + migrate) và tài liệu import rõ ràng.
- Triển khai **cloud** (VPS + HTTPS) và domain cho Android prod (cleartext off).
- Bật **Gemini/RAG thật** có kiểm soát (key, quota, logging).
- Hoàn thiện **logout** (optional denylist JWT hoặc gọi endpoint revoke nếu có thiết kế).
- **Bắt buộc** Basic Auth admin khi public.
- Mở rộng **dữ liệu** + test tự động (đã có Vitest backend).
- Tối ưu UI Android (Compose hoặc polish XML).
- Analytics/thống kê — **Chưa có** module analytics trong code đã grep; thêm sau nếu cần.

---

## 16. Đoạn gợi ý viết vào báo cáo Chương 4

**(4.1) Môi trường cài đặt:** Hệ thống được triển khai trên máy trạm phát triển với Android Studio, môi trường Node.js để chạy máy chủ API, cơ sở dữ liệu MySQL lưu trữ người dùng và địa điểm, dịch vụ Python FastAPI cho tầng truy xuất và sinh nội dung AI, cùng tùy chọn Docker để gói các thành phần phụ thuộc. Trình duyệt web dùng để truy cập giao diện quản trị đi kèm backend.

**(4.2) Quy trình cài đặt:** Quy trình bắt đầu từ khởi động MySQL và nạp schema phù hợp, sau đó cấu hình biến môi trường ở tệp `.env` ở thư mục dự án. Tiếp theo, cài đặt thư viện backend bằng trình quản lý gói, chạy dịch vụ RAG trên cổng đã thống nhất, khởi động máy chủ Node và kiểm tra điểm sức khỏe API. Ứng dụng Android được cấu hình địa chỉ máy chủ phù hợp môi trường giả lập hoặc thiết bị thật.

**(4.3) Các giao diện:** Phần client bao gồm các màn hình xác thực, trang chủ, tra cứu và xem chi tiết địa điểm, bản đồ nhúng, lịch trình, chatbot, hồ sơ người dùng. Phần quản trị cung cấp các trang thống kê và vận hành, trong đó có trang giám sát phân hệ RAG.

**(4.4) Bảo vệ hệ thống:** Mật khẩu được băm an toàn trước khi lưu, phiên đăng nhập dùng JSON Web Token cho các API. Thiết bị di động lưu token trong bộ nhớ mã hóa. Kênh quản trị có thể bật xác thực Basic khi cấu hình đủ thông tin biến môi trường. Giao tiếp có giới hạn cleartext trên bản dựng phát triển nhưng nên chuyển sang HTTPS khi triển khai thực tế.

**(4.5) Thử nghiệm và đánh giá:** Thử nghiệm chức năng được thiết kế theo kịch bản đi từ đăng ký, duyệt dữ liệu đến các thao tác lịch trình, đánh giá, yêu thích và các luồng AI. Kết quả cần được ghi nhận trên môi trường demo thực tế của nhóm.

**(4.5.6) Hạn chế và hướng phát triển:** Còn tồn tại điểm cần thống nhất giữa lược đồ cơ sở dữ liệu và mã nguồn ở các phiên bản bảng địa điểm; tầng AI phụ thuộc cấu hình chế độ chạy và khóa dịch vụ; một số cơ chế bảo mật quản trị và phiên bản chạy thật của Gemini chỉ phát huy khi được cấu hình đầy đủ. Hướng phát triển tiếp theo gồm chuẩn hóa triển khai, tăng cường bảo mật và hoàn thiện trải nghiệm người dùng.

---

## 17. Các thông tin cần xác nhận thêm với chủ project

- Môi trường máy demo thực tế (Windows/Linux/macOS) và phiên bản công cụ đã cài.
- Có demo trên **emulator** hay **điện thoại thật**; IP/LAN và `API_BASE_URL`.
- Tên database cuối cùng đang dùng (**`unudata`** hay tên khác).
- Đã import **`database.sql`**, **`migrations`**, hay cả hai; đã chạy **`seed`** hay chưa.
- Có bật **Gemini thật** trên RAG khi quay video/bảo vệ không.
- Số lượng bản ghi thực tế sau import (users, places, reviews, itineraries).
- Ảnh minh họa nào đã chụp sẵn.
- Tài khoản demo (`demo@smarttravel.local` / `123456` trong seed — **chỉ đúng nếu seed đã chạy và DB trùng schema seed**).
- Tài khoản admin dashboard (Basic Auth) có đặt hay đang để mở.
- Chức năng nào đã test pass; chức năng AI/RAG nào chỉ hoạt động khi đủ artifact BM25/Gemini.

---

*Kết thúc tệp đầu vào Chương 4.*
