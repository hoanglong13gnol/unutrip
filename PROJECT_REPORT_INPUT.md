# PROJECT_REPORT_INPUT.md

*(Tài liệu chỉ đọc và tóm tắt từ mã nguồn/kịch bản hiện có trong repo `E:/UNUtrip`. Không chỉnh sửa logic ứng dụng.)*

## 1. Tổng quan project

- **Tên project/app**: Gradle `rootProject.name` = `"SmartTravel"` (`settings.gradle`). Chuỗi hiển thị người dùng: `app_name` = **UNU Trip** (`app/src/main/res/values/strings.xml`). `applicationId` = `com.smarttravel`, flavors `dev`/`prod` với suffix `.dev` cho bản dev (`app/build.gradle`).
- **Mục tiêu hệ thống theo mã nguồn**: Ứng dụng Android đăng nhập, duyệt và tìm kiếm địa điểm (`app_places`), yêu thích, đánh giá, quản lý lịch trình; có luồng gợi ý/chỉnh lịch AI qua Backend Node và dịch vụ RAG (FastAPI) tích hợp truy xuất + sinh trả lời; có trợ lý chat (`ChatbotFragment` + `/api/ai/rag-chat`); thời tiết gọi API công khai Open-Meteo từ app (không qua backend).

- **Thành phần chính**:
  | Thành phần | Có trong code | File/cấu hình chứng minh |
  |------------|----------------|---------------------------|
  | Android app | Có | `app/`, `settings.gradle`, `AndroidManifest.xml` |
  | Backend API (Node/Express) | Có — **thành phần backend chạy qua npm** | `backend/nodejs/package.json`, `backend/nodejs/src/index.js`, `backend/nodejs/src/app.js` (`/api`, `/admin`) |
  | RAG / AI service (FastAPI Python) | Có — **backend RAG độc lập** | `backend/rag/app/main.py`, `backend/rag/Dockerfile` |
  | Database | MySQL được dùng từ Node (`mysql2` pool); tên DB mặc định `unudata` | `backend/nodejs/src/db.js` |
  | Docker cho RAG | Có Dockerfile | `backend/rag/Dockerfile` |
  | Docker Compose toàn stack | **Chưa tìm thấy** file `docker-compose.yml`/`docker-compose.yaml` ở gốc repo | chỉ có `deploy/redis-compose.yml` (Redis) |

- **Luồng tổng quát (theo kiến trúc được mã hóa)**:
  1. **Android** gọi HTTP REST tới `BASE_URL` (mặc định trong `build.gradle`: `http://10.0.2.2:3000/api/`) + header `Bearer` JWT (`ApiService.kt`, `RequestHeadersInterceptor`/session).
  2. **Node** (`express` trên port mặc định `3000` trong `backend/nodejs/src/index.js`) xử lý `/api/*`, truy vấn **MySQL** (`app_places`, `users`, …), proxy một số hành vi AI sang **FastAPI RAG** qua biến môi trường `RAG_BASE_URL` / `RAG_API_BASE` (mặc định `http://127.0.0.1:8001`, `backend/nodejs/src/config/env.js`, `backend/nodejs/src/lib/ragUpstream.js`).
  3. **FastAPI RAG** (`backend/rag`, cổng `8001` theo Dockerfile) nạp `RagPipeline` (HybridRetriever BM25 + tùy chọn Gemini theo env), Redis tùy chọn (`REDIS_URL` trong `deploy/redis-compose.yml` + `requirements.txt`).
  4. **AI không qua backend**: `WeatherService` gọi trực tiếp `api.open-meteo.com`.

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ/thư viện/framework | Phiên bản/ràng buộc (nếu có trong repo) | File chứng minh | Vai trò |
|-------------|-------------------------------|----------------------------------------|-----------------|--------|
| Android app module | Gradle Android Application, Kotlin, ViewBinding | AGP **8.2.2**, Kotlin **1.9.23** (`build.gradle` gốc); `compileSdk`/`targetSdk` **34**, `minSdk` **26** | `build.gradle`, `app/build.gradle` | Client chính |
| UI Android | Fragments + XML layout, Navigation fragment | Navigation **2.7.7** | `nav_graph.xml`, các `fragment_*.xml` | Điều hướng & màn hình |
| Jetpack Compose | `compose-bom` **2024.04.01**, Material3 | `build.gradle` app | Compose **bật** nhưng UI màn chính dùng XML; có theme Compose (`ui/theme/*.kt`) |
| Networking | Retrofit **2.9.0**, OkHttp **4.12.0**, Gson **2.10.1**, logging-interceptor | `app/build.gradle` | REST tới Backend Node |
| Bản đồ | OSMDroid **6.1.18**, Play Services Location **21.3.0** | `app/build.gradle`; manifest ghi "đã chuyển sang OSMDroid" | Bản đồ địa điểm (`MapFragment`) |
| Gemini client (dependency) | `com.google.ai.client.generativeai:generativeai` **0.2.2** | `app/build.gradle` | **Chưa tìm thấy trong mã Kotlin** chỗ khởi tạo `GenerativeModel` — chỉ thấy khai báo dependency |
| Bảo mật session cục bộ | `security-crypto` **1.0.0**, EncryptedSharedPreferences | `SessionManager.kt` | Lưu token/user |
| Coroutines | kotlinx-coroutines **1.7.3** | `app/build.gradle` | Bất đồng bộ |
| Glide | **4.16.0** | `app/build.gradle` | Ảnh |
| Room | **2.6.1** (+ kapt) | `app/build.gradle` | Dependency khai báo; **Không có** `@Database`/`@Entity` trong `app/src/main/java` (đã grep) |
| Backend Node | Express **4.21.x**, JWT `jsonwebtoken`, bcryptjs, zod validation, helmet, cors, morgan, multer, mysql2 **3.12.x**, dotenv **16.x** | `backend/nodejs/package.json` | REST `/api`, static `/uploads`, `/images` (`app.js`) |
| Backend Node test/lint | vitest **3.x**, eslint **9.x**, prettier, supertest | `backend/nodejs/package.json` | QA |
| RAG Python | FastAPI `<0.116`, uvicorn, pydantic v2, rank-bm25, scikit-learn **==1.7.1** (comment ghép pickle), google-genai, pymysql, redis | `backend/rag/requirements.txt`, `requirements-dev.txt` | API RAG, itinerary preview/options |
| RAG container | Python **3.12-slim-bookworm**, uvicorn cổng **8001** | `backend/rag/Dockerfile` | Deploy tùy chọn |
| Redis (ops) | `redis:7-alpine` | `deploy/redis-compose.yml` | Rate limit + cache Gemini (tuỳ cấu hình RAG) |
| CI | GitHub Actions Android | `.github/workflows/android-ci.yml` | Build/test Android |
| Dịch vụ Python lạ trong `nodejs/` | FastAPI + torch/transformers/peft/Qwen LoRA (**không** được `npm start` dùng) | `backend/nodejs/server.py`, comment `AI_MODEL_URL` trong `env.js` | **Tùy chọn**: endpoint `POST {AI_MODEL_URL}` với body `{ message }` → `{ answer }`; mặc định Node **không** gọi nếu biến trống |

**Database**

- Driver: **MySQL** qua `mysql2/promise` (`backend/nodejs/src/db.js`).
- Biến: `DB_NAME` mặc định **`unudata`**, host `127.0.0.1`, port `3306` (`backend/nodejs/src/db.js`).
- **Không có** Postgres/Mongo/`SQLite` làm DB chạy trong app (Room không dùng thực tế trong code Kotlin).

**API ngoài (theo URL hardcode)**

- Open-Meteo: `https://api.open-meteo.com/v1/forecast` (`WeatherService.kt`).
- **Chưa tìm thấy** trong mã Kotlin chỗ gọi Nominatim dù có gợi ý trong comment class docstring — triển khai đang map tên thành phố qua `cityCoords`.

**Gemini/model AI**

- FastAPI RAG: `GEMINI_MODEL` mặc định **`gemini-2.5-flash`**, `ENABLE_GEMINI` mặc định **false**, `AI_RUNTIME_MODE` mặc định **`mock`** (`backend/rag/core/config.py`).
- Không chứng minh từ mã được “model đang chạy trên môi trường thật của chủ đồ án” — chỉ biết mặc định và biến môi trường.

## 3. Cấu trúc thư mục (cấp cao)

```
E:/UNUtrip/
├── app/                    # Module Android UNUTrip/SmartTravel
├── backend/
│   ├── nodejs/             # Backend REST chính (Express): /api + /admin
│   └── rag/                # Dịch vụ FastAPI RAG + pipeline + scripts + data
├── database/
│   ├── migrations/       # SQL tạo bảng v2 (app_places, rag_knowledge_base, place_images, place_id_map) + populate
│   └── docs/               # Tài liệu quyết định schema
├── docs/                   # Audit DB hiện tại, v.v.
├── deploy/
│   └── redis-compose.yml   # Redis standalone (Compose)
├── .github/workflows/       # CI
└── PROJECT_REPORT_INPUT.md # (file này)
```

**Vai trò ngắn gọn**

- **`app/`**: mã nguồn APK, fragments, Retrofit models, WeatherService OSMDroid, session.
- **`backend/nodejs/`**: API cho app, JWT, proxy RAG (`ragPostJson`), phục vụ upload ảnh review/avatar (`app.js`).
- **`backend/rag/`**: ingestion/index scripts, BM25 pickle, Gemini (nếu bật), route `/rag/*`, `/ai/itinerary-*`, `/admin/*`.
- **`database/`**: migrations v2 và tài liệu; **migrate() runtime Node bị skip** (`db.js`).
- **`deploy/`**: Redis Compose, không bọc Node/RAG/App.

## 4. Backend API (Express, prefix `/api` + global middleware)

Mount: `app.use("/api", buildRouter())` (`backend/nodejs/src/app.js`). JWT: `Authorization: Bearer` (`backend/nodejs/src/auth.js`).

*(Admin HTML/JSON dưới `/admin/**` không nằm trong prefix `/api`; bảo vệ Basic Auth tùy env — bảng riêng dưới.)*

### 4a. REST `/api/*` (Mobile)

Phân nhóm theo đăng ký router (`backend/nodejs/src/routes/index.js`) + các file `*.routes.js`, `*.controller.js`.

#### Nhóm: Health

| Method | Endpoint | File route | Middleware | Request | Response / lỗi | Chức năng |
|--------|----------|------------|------------|---------|----------------|-----------|
| GET | `/api/health` | `backend/nodejs/src/modules/health/health.routes.js` → `health.controller.js` | Không JWT | — | `{ ok, service, uptime_s }` | Liveness đơn giản |
| GET | `/api/health/ready` | idem | Không JWT | — | `{ ok, checks }` hoặc 503 — kiểm tra MySQL; gọi RAG `/health` trừ khi `HEALTHCHECK_SKIP_RAG` | Readiness |

#### Nhóm: Auth/user

| Method | Endpoint | File | Middleware | Body / query | Response chính | Chức năng |
|--------|---------|------|------------|---------------|----------------|-----------|
| POST | `/api/auth/register` | `modules/auth/` | Không | `fullName`, `email`, `password`, `phone?` — zod | `token`, `user` hoặc 400 | Đăng ký |
| POST | `/api/auth/login` | idem | Không | `email`, `password` | `token`, `user` hoặc 401 | Đăng nhập |
| POST | `/api/auth/logout` | idem | `authMiddleware` | — | `{ success, … }` (apiOk) | Logout (phiên không state server-side) |
| GET | `/api/users/profile` | `modules/users/` | JWT | — | ApiResponse User | Hồ sơ |
| GET | `/api/users/stats` | idem | JWT | — | `{ itineraryCount, favoriteCount, reviewCount }` | Thống kê |
| PUT | `/api/users/profile` | idem | JWT | fullName, email, phone?, avatar?, preferences? | User DTO | Cập nhật hồ sơ |
| PUT | `/api/users/preferences` | idem | JWT | body array `preferences` hoặc tương đương | User DTO | Sở thích |
| POST | `/api/users/avatar` | idem | JWT + multer single `avatar` | multipart | User DTO + URL `/uploads/avatars/` | Avatar |

#### Nhóm: Destinations / places

| Method | Endpoint | File | Middleware | Params | Response | Chức năng |
|--------|----------|------|------------|---------|----------|-----------|
| GET | `/api/destinations` | `modules/destinations/` | JWT | Query: `page`, `limit`, `category`, `province`, `search` | `{ success, data, total, page, limit }` | Danh sách có phân trang |
| GET | `/api/destinations/featured` | idem | JWT | — | 5 điểm nổi bật cố định service | Featured |
| GET | `/api/destinations/nearby` | idem | JWT | `lat`, `lng`, `radiusKm`/`radius`, `limit` | `data`, `center`, `radiusKm` hoặc 400 | Lân cận (Haversine SQL) |
| GET | `/api/destinations/:id` | idem | JWT | path id | Detail hoặc 404 | Chi tiết |

#### Nhóm: Favorites

| GET | `/api/users/favorites` | `modules/favorites/` | JWT | — | `{ success, data, total… }` | Danh sách yêu thích |
| POST | `/api/users/favorites` | idem | JWT | `{ destinationId: number }` | apiOk hoặc 404 | Thêm |
| DELETE | `/api/users/favorites/:destinationId` | idem | JWT | path id | apiOk | Xóa |

#### Nhóm: Reviews

| GET | `/api/destinations/:id/reviews` | `modules/reviews/` | JWT | — | ApiResponse list Review | DS review |
| POST | `/api/reviews` | idem | JWT + multer up to **3** `images` | form: `destinationId`, `rating`, `comment`; files | ApiResponse Review | Tạo + ảnh `/uploads/reviews/` |

#### Nhóm: Itinerary (CRUD)

| GET | `/api/itineraries` | `modules/itineraries/` | JWT | — | List itineraries | DS |
| GET | `/api/itineraries/:id` | idem | JWT | path id | ApiResponse itinerary tree | Chi tiết |
| POST | `/api/itineraries` | idem | JWT | body schema zod (`title`, `startDate`, `endDate`, `description?`, `destinationIds?`, …) | apiOk itinerary | Tạo + ngày + item seed theo days |
| POST | `/api/itineraries/:id/items` | idem | JWT | `{ destinationId, dayId?, startTime?, endTime?, note? }` | success message | Thêm điểm |
| PUT | `/api/itineraries/:id` | idem | JWT | itinerary fields zod | updated DTO | Sửa |
| DELETE | `/api/itineraries/:id` | idem | JWT | — | apiOk | Xóa |

#### Nhóm: AI / RAG itinerary (qua Node)

*(Controller `modules/ai/ai.controller.js`; proxy RAG trong `services/ai.service.js`)*

| POST | `/api/ai/suggest-itinerary` | `modules/ai/ai.routes.js` | JWT | `preferences[]`, `startDate`, `endDate`, `budget?`, `startLocation?` | `{ success, itinerary, message }` hoặc 500 parse AI | Prompt catalog `app_places` → AI_MODEL_URL hoặc RAG `/rag/chat` → persist |
| POST | `/api/ai/rag-chat` | idem | JWT | `message`, `top_k?`, `mode?`, `targetProvince?`, `targetCity?` | `answer`, `places`, diagnostics… hoặc 502 | Chat RAG qua `/rag/chat/simple` |
| POST | `/api/ai/chat` | idem | JWT | `{ message }` trong body đọc lỏng | `{ success, answer }` | Ưu tiên `AI_MODEL_URL`, fallback `/rag/chat/simple` |
| POST | `/api/ai/itinerary-preview` | idem | JWT | body chứa `title`, `description`, `startDate`, `endDate`, `budget`, `preferences`, `province` (pass-through `req.body`) | JSON upstream hoặc 502 | Proxy FastAPI `/ai/itinerary-preview` |
| POST | `/api/ai/itinerary-options` | idem | JWT | như preview; backend yêu cầu có `startDate`/`endDate` | upstream JSON | Proxy FastAPI `/ai/itinerary-options` |
| POST | `/api/itineraries/create-from-option` | idem *(note route comments)* | JWT | `{ title`, `startDate`, `endDate`, `days` array … } validation trong controller | `data` itinerary hoặc 400 mapping | Persist tour từ option AI |
| POST | `/api/itineraries/create-from-selection` | idem | JWT | `title`, dates, `selectedDestinations`… | Hoặc 400 không map được place | Persist từ chọn điểm preview |
| POST | `/api/itineraries/save-ai` | `modules/itineraries/itineraries.routes.js` | JWT | `{ title, description?, startDate, endDate, budget?, days[] }` | `{ success, message }` | Lưu cấu trúc AI thủ công (`saveAiItinerary` service) |

### 4b. `/admin/*` (Express, không dùng prefix `/api`)

Router: `app.use("/admin", adminAuthMiddleware, buildAdminRouter());` (`app.js`).

- **Auth**: Basic optional — nếu thiếu `ADMIN_BASIC_USER`/`ADMIN_BASIC_PASS` thì middleware cho qua và cảnh báo console (`middlewares/adminAuth.middleware.js`).

Đăng ký (`backend/nodejs/src/admin/index.js`):

- `dashboard.admin.routes.js` — `GET /dashboard`
- `users.admin.routes.js` — `GET /users`, `GET /users/api/:id`, `POST /users/save`, `POST /users/delete/:id`
- `destinations.admin.routes.js` — `GET /destinations`, `GET /destinations/api/:id`, `POST /destinations/save`, `POST /destinations/delete/:id`
- `system.admin.routes.js` — `GET /system`
- `ragAi.admin.routes.js` — `GET /rag-ai`, POST reload/cache, GET metrics/logs, POST debug-query, … *(chi tiết trong file; proxy FastAPI admin)*
- `aiReport.admin.routes.js` — `GET /ai-report`

Chi tiết từng body/query của admin: **đọc từng file `*.admin.routes.js`** nếu cần verbatim cho báo cáo — tài liệu này không liệt kê hết từng form field HTML.

---

## FastAPI RAG (cổng mặc định Dockerfile `8001`, không có `/api` prefix trong app router gốc)

Base URL được Node ghép vào ví dụ `http://127.0.0.1:8001/rag/chat/simple`.

| Method | Endpoint (ghi trong codebase) | File | Middleware | Payload (schema chính) | Vai trò |
|--------|-------------------------------|------|-------------|-------------------------|---------|
| GET | `/health`, `/health/ready`, `/runtime/status` | `app/routers/health.py` | Public / status | — | Ops |
| GET | `/v1/health`, `/v1/health/ready` | `main.py` duplicate include | như trên | versioned alias | — |
| POST | `/chat`, GET `/chat` Help | `app/routers/rag.py` | Internal key middleware nếu set | `{ message }` | Tương thích `AI_MODEL_URL`/`server.py` cũ — trả `{ answer }` |
| POST | `/rag/chat`, `/rag/retrieve`, `/rag/chat/simple` | `rag.py` | optional key | `RagChatRequest`, `RagRetrieveRequest`, `RagChatSimpleRequest` trong `schemas` | Retrieval + chat |
| POST | `/ai/itinerary-preview`, `/ai/itinerary-options` | `ai_itinerary.py` (+ duplicate prefix `/v1` trong main) | optional key | `ItineraryPreviewRequest` pydantic | Gợi ý địa điểm / options tour |
| Nhiều route | `/admin/**` | `app/routers/admin.py` | Admin key khác Internal nếu cấu hình (`middleware.py`) | — | Logs, metrics, debug RAG |

## 5. Android app — màn hình / chức năng (theo Navigation + lớp Kotlin)

*Nguồn định danh Fragment: `app/src/main/res/navigation/nav_graph.xml` và file `.kt` tương ứng.*

| Nhóm | Tên UI (class XML label / Fragment) | File | Chức năng chính | API / utils |
|------|-------------------------------------|------|-----------------|-------------|
| Đăng nhập | `AuthActivity` | `ui/auth/AuthActivity.kt` | Launcher, login/register flows | Retrofit auth (`ApiService.kt`) |
| Shell | `MainActivity` | `ui/home/MainActivity.kt` | Host bottom nav | — |
| Trang chủ / featured / nearby | `HomeFragment` | `ui/home/HomeFragment.kt`, `HomeViewModel.kt`, `DestinationViewModel.kt` | Danh sách địa điểm, tìm kiếm UX | `/destinations`, `/featured`, `/nearby`, profile token |
| Danh sách địa điểm / yêu thích | `DestinationListFragment` (+ args category / favorites) | `ui/destination/DestinationListFragment.kt` | Lọc, favorites mode | như destinations + favorites endpoints |
| Chi tiết + review + weather strip | `DestinationDetailFragment` | `DestinationDetailFragment.kt` | Chi tiết, reviews, có `WeatherService.getWeather(city)` | `/destinations/{id}`, `/reviews`; Open-Meteo |
| Bản đồ | `MapFragment` | `ui/destination/MapFragment.kt` | OSMDroid + `MapIntentHelper` | Không Retrofit maps — tile OSM |
| Lịch trình | `ItineraryFragment`, `ItineraryDetailFragment` | `ItineraryFragment.kt`, `ItineraryDetailFragment.kt`, `ItineraryViewModel.kt` | CRUD + danh mục | `/itineraries`… |
| AI tour (preview → options → editor) | `AIItineraryRequestFragment`, `AIItineraryOptionsFragment`, `AIItineraryEditorFragment` | các file trong `ui/itinerary/` | Wizard AI tour | `/ai/itinerary-preview`, `/ai/itinerary-options`, `/itineraries/create-from-option`, … |
| AI gợi ý (flow “AISuggest”) | `AISuggestFragment` (**cùng file** `ItineraryDetailFragment.kt`) | Binding `fragment_ai_suggest.xml` | Gọi `suggestItinerary` + liên quan ViewModel | `POST /api/ai/suggest-itinerary`, `AISuggest*` models |
| Chatbot | `ChatbotFragment` | `ChatbotFragment.kt`, `ChatbotViewModel.kt` | Chuẩn hóa query + RAG + sửa câu trả lời | `/api/ai/rag-chat`, `/api/ai/chat` qua `RagService`/`GeminiService` |
| Hồ sơ / cài đặt | `ProfileFragment`, `SettingsFragment` | `ProfileFragment.kt`, `SettingsFragment.kt` | Avatar, logout, prefs | `/users/*`, upload avatar |

**Điểm nhấn Retrofit**: `RetrofitClient.kt` + `ApiService.kt` (đầy đủ đường dẫn relative sau `BASE_URL`).  
**Điểm nhấn thời tiết**: chỉ trong `WeatherService.kt` — không có endpoint backend `/weather`.

---

## 6. Database / schema / entity

### 6.1. Bảng Node runtime trích từ SQL trong repository/service

*(DDL đầy đủ không nằm trong migrations của repo cho các bảng `users/itineraries/...`; `migrate()` bị disable — `backend/nodejs/src/db.js`).*

| Bảng / artifact | Định nghĩa trong repo | Trường / ý chính | PK / FK (theo nhận định code) |
|-----------------|------------------------|-----------------|--------------------------------|
| `app_places` | `database/migrations/001_create_app_places.sql` + query `FROM app_places` | id, place_key, name, description, geo, category enum…, tags_json, rating, review_count, … | PK `id` |
| `favorites` | SQL join trong `destinations.repository.js`, `favorites.repository.js` | `user_id`, `destination_id` (trỏ tới **id địa điểm**), `created_at`? | FK logic tới user + place/app place id *(DDL đầy đủ: Chưa tìm thấy migration SQL trong `database/migrations` cho favorites — chỉ thấy cột được dùng qua các file repository).* |
| `users` | `users.repository.js` insert/select (`full_name`, `email`, `password_hash`, `phone`, `avatar`, `preferences_json`) | Theo usage | PK assumed `id` |
| `reviews` | `reviews.repository.js` | `destination_id`, `user_id`, `rating`, `comment`, `images_json`, `created_at` | FK kiểu user + destination/app place id *(DDL đầy đủ: Chưa tìm thấy migration trong `database/migrations` — chỉ thấy cột được dùng trong repository).* |
| `itineraries` | `itineraries.repository.js` | `user_id`, `title`, dates, `total_days`, `status`, budget | FK user |
| `itinerary_days` | idem | `itinerary_id`, `day_number`, `date` | FK itinerary |
| `itinerary_items` | idem | `day_id`, `destination_id`, time window, note, `order_index` | FK |
| `place_images` | `003_create_place_images.sql`, repo `destinationImages.repository.js` | `app_place_id`, `image_url`, sort, status… | FK tới `app_places.id` |
| `place_id_map` | `004_create_place_id_map.sql`, `placeIdMap.repository.js` | Map legacy rag id → `new_app_place_id` | FK `new_app_place_id` → app_places |
| `rag_knowledge_base` | `002_create_rag_knowledge_base.sql` | Cột chi tiết trong file SQL | FK `app_place_id` optional |
| **`destinations` (legacy seed)** | `backend/nodejs/src/seed.js` INSERT + UPDATE | seed dùng bảng `destinations`; **repository API đọc `app_places`** | Seed & runtime **lệch tên bảng** trong cùng repo — chủ đồ án cần giải thích quy trình DB thực tế |

**Seeds trong code**

- File `backend/nodejs/src/seed.js`: mục tiêu tối đa ~50 users, seed mass `DESTINATIONS_DATA` vào **`destinations`**, ~100 itineraries, 50 reviews, cập nhật **`destinations`** rating.
- Không chứng minh từ mã được lượng bản ghi trên máy chủ của chủ đồ án (chỉ logic seed).

---

## 7. AI / RAG

### 7.1. Entry và version

- **FastAPI**: `backend/rag/app/main.py` khởi tạo `RagPipeline`, mount routers, middleware rate limit + API key nội bộ (`InternalApiKeyMiddleware`), optional OpenTelemetry.
- **Node proxy**: `generateSuggestItineraryAiResult` và các `request*` trong `backend/nodejs/src/services/ai.service.js`; header `X-RAG-Internal-Key`/`X-Request-ID` qua `ragClient.js`.

### 7.2. Model AI được gọi (theo điều kiện mã)

1. **`AI_MODEL_URL` (Node)** — POST JSON `{ message }` nhận `{ answer }`; nếu env trống, `getResolvedAiModelUrl()` **null**, Node **không** gọi local model default (`backend/nodejs/src/config/env.js`).
2. **RAG pipeline** — retrieval BM25/sklearn pickled index + rule score (`backend/rag/rag/hybrid_retriever.py`).
3. **Gemini (Python)** — khi `ENABLE_GEMINI` true và `AI_RUNTIME_MODE` trong tập `{demo,gemini_only,hybrid}` (`backend/rag/rag/pipeline.py` khởi tạo `GeminiGenerator`); model string từ env `GEMINI_MODEL` default `gemini-2.5-flash` (`backend/rag/core/config.py`).
4. **Android** — không gọi trực tiếp Gemini SDK trong code Kotlin đã grep; “GeminiService” chủ yếu gọi **`/api/ai/chat`** qua Retrofit như một **client tên Gemini** nhưng thực hiện qua backend.

### 7.3. Dữ liệu địa điểm cho các luồng

| Luồng | Nguồn trong code |
|-------|-------------------|
| `/api/ai/suggest-itinerary` catalog | Query MySQL **`app_places`** tối đa 50 bản đầu khi prompt (`backend/nodejs/src/repositories/ai.repository.js`, `services/ai.service.js`) |
| Preview/options FastAPI | `load_places()` đọc JSON `processed/places_app_reviewed.json` ưu tiên, không thì `places_app.json` (`backend/rag/app/ai_itinerary.py`) |
| RAG chat | chỉ mục local/bm25 từ artifacts trong `backend/rag/data/indexes/` + pipeline files *(chi tiết file index: đọc HybridRetriever BM25Retriever)* |

### 7.4. “Có dùng RAG không?”

- **Có** cho chat và fallback suggest-itinerary: Node gọi `POST ${RAG_BASE_URL}/rag/chat` hoặc `/rag/chat/simple` (`services/ai.service.js`).
- Retrieval: có class `HybridRetriever`, `Fusion`, intent parser (`backend/rag/rag/`).

### 7.5. Mapping ID & place store

- `place_id_map` repository map `rag_place_id` / legacy keys sang `new_app_place_id` (FK app_places) — được dùng khi ghép itinerary từ rawPlaceId (theo pipeline Node service itineraries — chứng minh qua repositories imports trong `itineraries.service.js`/`placeIdMap.repository.js`; chi tiết từng hàm: đọc file service nếu cần verbatim).

### 7.6. AI suggest itinerary (`/api/ai/suggest-itinerary`)

- **Input validated**: `preferences` array, dates, optional `budget`, optional `startLocation` (accepted in Zod nhưng `ai.controller.js` chỉ destructuring preferences/dates/budget khi compute days — `startLocation` parsed but not passed to generator in excerpt read).
- **Output JSON app**: Backend trả `itinerary` entity sau persist (`persistAiSuggestedItinerary`) + message (`ai.controller.js`); Android maps `AISuggestResponse` trong `Models.kt`.

### 7.7. Chatbot hoạt động (`ChatbotViewModel.kt`)

Hiện có pipeline nhiều bước (trích luận có thực):

1. `GeminiService.prepareRagQuery` — gửi prompt dài vào **`/api/ai/chat`** (thực tế backend+RAG fallback) và parse JSON `GeminiPreparedQuery`.
2. `RagService.chat` → **`/api/ai/rag-chat`** với targetProvince/City/query.
3. Nếu lệch tỉnh / lỗi RAG có nhánh mismatch + retry strict query và validate `validateRagOutputFull`.
4. Nếu validation fail không có correctedQuery → trả tin nhắn lỗi “chưa tìm được địa điểm phù hợp…”
5. Nếu RAG fail → **`GeminiService.fallbackChat`** (lại **`/api/ai/chat`**)
6. Nếu OK → **`repairRagAnswer`** (**`/api/ai/chat`**) chỉnh văn bản theo RULE + places.

### 7.8. Exceptions / fallback (liệt kê có thực chứng minh ngắn)

- FastAPI middleware bắt `HTTPException`, `ValidationError`, generic (`main.py`).
- Node `ragPostJson` retries transient network/429/502/504 (`ragUpstream.js`).
- AI suggest: local AI fails → fallback RAG (`ai.service.js` log); parse JSON fails → `{ success:false, invalid message }`; RAG upstream throws → handler 500.
- Android `GeminiService`/`RagService` bọc try/catch trả plain text errors.

---

## 8. Use case thực tế (mã chứng minh)

| Mã | Tên | Tác nhân | Mô tả ngắn | API/Màn | Trạng thái |
|----|-----|----------|------------|---------|-----------|
| UC-A1 | Đăng ký / đăng nhập | User | bcrypt + JWT, lưu session encrypted | `/api/auth/*`, `AuthActivity` | **Đã có** |
| UC-A2 | Xem/Sửa profile, avatar | User | update info + multipart avatar | `/api/users/*`, `ProfileFragment`, `dialog_edit_profile` | **Đã có** *(UI files present)* |
| UC-D1 | Tìm & xem địa điểm | User | paging, filters, chi tiết | `/api/destinations*`, các Fragment | **Đã có** |
| UC-D2 | Địa điểm gần bạn | User | geo query radius | `/api/destinations/nearby`, `HomeFragment`/VM | **Đã có** |
| UC-I1 | CRUD lịch trình | User | itineraries API | Fragments itinerary | **Đã có** |
| UC-I2 | Gợi ý lịch legacy “AISuggest” | User | Prompt + persist suggest | `/api/ai/suggest-itinerary`, `AISuggestFragment` | **Đã có** |
| UC-I3 | AI tour wizard (preview/options) | User | RAG-weighted grouping | `/api/ai/itinerary-*`, các `AIItinerary*Fragment` | **Đã có** |
| UC-C1 | Chatbot tư vấn | User | RAG + repair/fallback loops | `/api/ai/rag-chat`, `/api/ai/chat`, `ChatbotViewModel` | **Đã có** |
| UC-R1 | Đánh giá địa điểm | User | list + multipart images | `/api/reviews`, `DestinationDetailFragment` | **Đã có** |
| UC-R2 | Danh mục yêu thích | User | favorites API | Fragments favorites | **Đã có** |
| UC-M1 | Bản đồ định vị | User | OSMDroid + fused location manifest | `MapFragment` | **Đã có** |
| UC-W1 | Dự báo thời tiết | User | REST Open-Meteo public | `DestinationDetailFragment` + `WeatherService` | **Đã có** |
| UC-AD | Quản trị web | Admin (HTTP Basic tuỳ chọn) | HTML dashboard + CRUD-ish | `/admin/*` routers | **Đã có backend** *(client không phải Android)* |

**Chưa thấy / có một phần**

- **UC “Admin mobile”**: Chưa tìm thấy màn admin trong module Android.
- **“Generative AI trực tiếp trên thiết bị qua SDK”**: dependency có nhưng **không** thấy sử dụng → coi là **Chưa tìm thấy trong mã Kotlin**.

---

## 9. Luồng nghiệp vụ đề xuất cho báo cáo *(chỉ theo các bước thực sự trong code)*

### 9.1. Tìm kiếm và xem địa điểm

1. User mở `HomeFragment` hoặc `DestinationListFragment`.
2. App gửi JWT tới `/api/destinations` (+ query) hoặc `/featured`, `/nearby`.
3. Node đọc `app_places` + join favorites.
4. User chọn một địa điểm → `DestinationDetailFragment` gọi `/api/destinations/{id}`, `/reviews`; đồng thời `WeatherService` gọi Open-Meteo theo tên TP.
5. User có thể chuyển `MapFragment` với lat/lng truyền arguments.

### 9.2. Tạo lịch trình (thủ công)

1. `ItineraryFragment`/`ItineraryViewModel` POST `/api/itineraries` với khung dates + điểm.
2. User mở `ItineraryDetailFragment`, có thể thêm item `/api/itineraries/{id}/items`.
3. Cập nhật `/api/itineraries/{id}`, xóa `/api/itineraries/{id}` theo chức năng có trong `ApiService`.

### 9.3. Gợi ý lịch trình AI (AISuggest Fragment)

1. User mở `AISuggestFragment` (wizard riêng) nhập prefs + dates.
2. POST `/api/ai/suggest-itinerary` → Node build prompt catalog `app_places` → AI_MODEL_URL hoặc RAG → parse JSON plan → persist.
3. Thông báo thành công/message trả UI.

*(Luồng song song khác)*

### 9.4. Gợi ý AI tour kiểu “preview/options” **(Fragments AIItinerary*)**

1. User điền form `AIItineraryRequestFragment` → POST `/api/ai/itinerary-preview` (Node→FastAPI) để có `suggestedDestinations` trong response.
2. User chọn lọc và POST `/api/ai/itinerary-options` nhận nhiều `options`. 
3. Chọn option → có thể tạo hành trình persisted qua `/api/itineraries/create-from-option`. 
4. `AIItineraryEditorFragment` + `/api/itineraries/save-ai` cho chỉnh trước khi save hoặc theo UX fragment.

### 9.5. Chatbot

1. `ChatbotViewModel.sendMessage` → pipeline `GeminiService.prepareRagQuery` (**gọi** `/api/ai/chat`). 
2. Gọi RAG (**`/api/ai/rag-chat`**) + logic mismatch/validate/repair.
3. Hiển thị `answer` và `places` trong chat bubble adapter.

### 9.6. Đánh giá địa điểm

1. `DestinationDetailFragment` load reviews `/api/destinations/{id}/reviews`.
2. User POST `/api/reviews` multipart nếu có ảnh (`postReviewWithImages`).

### 9.7. Đăng nhập / đăng ký

1. `AuthActivity` submit → `/api/auth/login|register`.
2. Success → SessionManager encrypt lưu `token`, `User` (`SessionManager.kt`).
3. Các Retrofit sau tự Bearer (`ApiService`/interceptor được cấu hình trong Retrofit setup — chứng minh `ApiService.kt` headers). 

---

## 10. Yêu cầu chức năng (FR) & phi chức năng (NFR) — rút ra từ mã có thật

### 10.1. FR *(tập trung, không exhaustive từng widget)* 

| FR-ID | Diễn giải (chứng minh) |
|-------|-------------------------|
| FR-001 | Người dùng có thể đăng ký/đăng nhập và nhận JWT (`auth.routes.js`, Android `AuthActivity`). |
| FR-002 | Xem và tìm danh sách địa điểm, featured, nearby với paging/lọc (`destinations.*`). |
| FR-003 | Xem chi tiết địa điểm + reviews (`DestinationDetailFragment`, routes reviews). |
| FR-004 | Thêm/Xóa yêu thích (`favorites.routes.js`). |
| FR-005 | Tạo/sửa/xóa itinerary & item (`itineraries.*`). |
| FR-006 | Gợi ý itinerary bằng AI (prompt server + có RAG fallback) (`/api/ai/suggest-itinerary`). |
| FR-007 | Chuỗi AI preview/options cho tour (`Ai itinerary fragments`, FastAPI endpoints). |
| FR-008 | Chatbot có chuẩn hóa query + RAG (`ChatbotViewModel`). |
| FR-009 | Đánh giá có multipart ảnh (`reviews.routes.js`, `DestinationDetail`). |
| FR-010 | Hiển thị thời tiết trong chi tiết (Open-Meteo). |
| FR-011 | Hiển thị địa điểm trên OSMDroid (`MapFragment`). |
| FR-012 | Admin dashboard/backend web (`/admin` router). |
| FR-013 | Health checks cho deploy (`/api/health`). |

### 10.2. NFR

| NFR-ID | Yếu tố | Chứng minh từ mã |
|--------|--------|------------------|
| NFR-S1 | Bảo vệ JWT + HTTPS cleartext tắt | `AndroidManifest.xml` cleartext false; Bearer auth middleware |
| NFR-S2 | Helmet CSP + uploads static | `app.js` |
| NFR-S3 | Mật khẩu hash bcrypt sync | `auth.controller.js` |
| NFR-S4 | Rate limit middleware RAG | `RagRateLimitMiddleware`, config `rate_limit_per_minute` |
| NFR-S5 | Redis cache optional | `requirements.txt redis`, Compose file |
| NFR-O1 | Timeouts và retry upstream RAG | `ragUpstream.js`, env `RAG_FETCH_TIMEOUT_MS` |
| NFR-O2 | Graceful degraded health | `health/ready` skips RAG nếu flag |
| NFR-I1 | ProGuard minify bật trên release | `app/build.gradle` `minifyEnabled true` |
| NFR-I2 | LeakCanary debug | dependency debug |
| NFR-C1 | Product flavors dev/prod | `app/build.gradle` |
| NFR-X1 | Mở rộng Redis + horizontal note | Code comments + optional Redis |
| NFR-X2 | Mở rộng versioning API RAG `/v1` duplication | `main.py` |
| NFR-X3 | Chuẩn hóa lỗi JSON FastAPI `{ success:false, … }` | `main.py` handlers |

**Chưa chứng minh tới mức vận hành trong code**: mã hóa payload bổ sung ngoài TLS, SLA cụ thể (chỉ thấy timeout configurable), chứng nhận bảo mật store Play.

---

## 11. Những điểm chưa chắc chắn cần hỏi lại chủ project

*(Trả lời triển khai thực tế không nằm trong repo một cách rõ ràng.)* 

1. **DB “nguồn sự thật” trong môi trường chạy thật** là phiên bản nào: đã migrate `destinations` → `app_places` chưa? Vì **`seed.js` ghi vào `destinations` trong khi API đọc `app_places`.**
2. **RAG và Node đang được host URL/cổng nào** trên staging/prod và giá trị `RAG_BASE_URL`, `AI_MODEL_URL`, `ENABLE_GEMINI`, `GEMINI_API_KEY` thực tế?
3. **APK/phát hành**: repo **Không chứa** file `.apk`/bundle build output — APK đã build sẵn được lưu ở đâu?
4. **Gradle Generative SDK** có dự định sử dụng hay chỉ sót dependency?
5. **Room** được khai báo nhưng không entity — chủ có kế hoạch offline caching không?
6. **docker-compose một lệnh** cho full stack (**Node + MySQL + RAG**) — không có trong repo; triển khai thực tế?
7. **Tài khoản admin** và Bảo vệ `/admin`: hiện tại Basic auth optional — production setup?
8. **Dữ liệu chỗ chứa BM25 và JSON places** trong `backend/rag/data/` — được commit đầy đủ trong git hay build pipeline sinh?
9. **`backend/nodejs/server.py` Qwen/LoRA** có còn dùng cho `AI_MODEL_URL` không hay đã obsolete?
10. **Google Play policy** cho `GEMINI_API_KEY`/`API_BASE_URL` qua `local.properties`/`BuildConfig` — phương án không commit key (project đã có pattern local.properties).
11. **`sort` query** trong Android `ApiService.getDestinations` — backend **Không đọc** `sort` trong `listDestinations` controller → tham số hiện **không có tác dụng** trong Node (ghi rõ trong Q&A chủ có biết không).

---
**Ghi nhớ báo cáo**: luôn trích đường dẫn file khi làm báo cáo chính quy; không phóng đại tính năng ngoài bảng trên.

