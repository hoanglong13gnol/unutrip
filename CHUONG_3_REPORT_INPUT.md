# CHUONG_3_REPORT_INPUT.md

Tài liệu này tổng hợp **chứng cứ trong mã nguồn** (đường dẫn file, endpoint) cho đề tài *“Xây dựng ứng dụng du lịch thông minh trên nền tảng Android tích hợp trí tuệ nhân tạo”*. Không phải bản báo cáo Chương 3 hoàn chỉnh. Nơi không có chứng cứ trong repo được ghi rõ.

---

## 1. Tổng quan thiết kế hệ thống

### Mô tả theo code

| Hạng mục | Nội dung | Chứng minh |
|-----------|-----------|-------------|
| Tên hiển thị Android | `UNU Trip` | `app/src/main/res/values/strings.xml` — `app_name` |
| `applicationId` (prod) | `com.smarttravel` | `app/build.gradle` — `defaultConfig.applicationId` |
| `applicationId` (dev flavor) | `com.smarttravel.dev` (suffix `.dev`) | `app/build.gradle` — `productFlavors.dev.applicationIdSuffix` |
| Backend | Node.js / Express — mount API tại `/api`, static uploads/images, Admin tại `/admin` | `backend/nodejs/src/app.js` |
| Cơ sở dữ liệu | MySQL qua pool `mysql2/promise`; cấu hình `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (mặc định DB `unudata`) | `backend/nodejs/src/db.js`, `.env.example` |
| RAG / AI HTTP | FastAPI (`UnuTrip RAG`), cổng publish mặc định **8001** trong Docker/.env | `backend/rag/app/main.py`, `docker-compose.yml`, `backend/nodejs/src/config/env.js` — `RAG_BASE_URL` mặc định `http://127.0.0.1:8001` |
| Redis | Dùng trong stack Docker cho RAG (rate limit/cache theo comment env) | `docker-compose.yml`, `.env.example` |
| Dashboard Admin | Web HTML render từ Express, route con dưới `/admin/...` | `backend/nodejs/src/app.js` (`/admin`), `backend/nodejs/src/admin/index.js` |
| Bản đồ Android | OSMDroid (`MapView`, `TileSourceFactory.MAPNIK`); **không** còn meta-data Google Maps trong manifest chính | `app/build.gradle`, `app/src/main/AndroidManifest.xml`, `app/src/main/java/.../MapFragment.kt` |
| Định vị | Google Play Services Location — `FusedLocationProviderClient.lastLocation` | `app/build.gradle`, `MapFragment.kt` |
| Thời tiết | Android gọi trực tiếp **Open-Meteo** (`https://api.open-meteo.com/v1/forecast`) | `app/src/main/java/com/smarttravel/utils/WeatherService.kt` |
| Thành phần chính vs hỗ trợ | **Chính:** Android client + Node API + MySQL (`app_places`, users, itineraries…). **Hỗ trợ/vận hành:** FastAPI RAG, Redis (trong compose), Admin web, dịch vụ ngoài Open-Meteo / intent Google Maps | Các file trên |

### Luồng tổng quát (theo integration thực tế)

1. Người dùng mở app → **AuthActivity** (launcher) → JWT lưu **EncryptedSharedPreferences** → **MainActivity** + **NavHost** Fragment.
2. Android gọi REST **BASE_URL** (mặc định build: `http://10.0.2.2:3000/api/`) — xem **Retrofit `BuildConfig.BASE_URL`** trong `app/build.gradle`.
3. Node xử lý CRUD/MySQL; các luồng AI được proxy sang FastAPI (**`ragPostJson`** tới các path như `/rag/chat/simple`, `/ai/itinerary-preview`, …).
4. Thời tiết: Android **không** qua Node — gọi Open-Meteo.
5. Admin: duyệt web `http://<host>:<port>/admin/...`; Node có thể gọi tiếp FastAPI `/admin/*` với header key nội bộ.

### Môi trường mặc định trong code/config

| Mục | Giá trị / ghi chú | Chứng minh |
|-----|-------------------|-------------|
| Backend port | Ưu tiên `BACKEND_PORT` hoặc `PORT`, mặc định **3000** | `backend/nodejs/src/index.js` |
| Backend host bind | `0.0.0.0` mặc định trong log startup / compose | `index.js`, `docker-compose.yml` |
| RAG URL (Node → RAG) | `process.env.RAG_BASE_URL || RAG_API_BASE || http://127.0.0.1:8001` | `backend/nodejs/src/config/env.js` |
| RAG publish port (Docker) | **8001** (map `${RAG_PUBLISH_PORT:-8001}:8001`) | `docker-compose.yml` |
| MySQL (Docker / .env) | Host trong compose: service `mysql`, port nội bộ 3306; publish `3306` mặc định | `docker-compose.yml`, `.env.example` |
| Android emulator → backend | Mặc định `http://10.0.2.2:3000/api/` | `app/build.gradle` — `API_BASE_URL` default trong `local.properties` comment |
| XAMPP | **Chưa tìm thấy trong mã nguồn** — chỉ thấy MySQL qua biến `DB_*` | — |

### Bảng thành phần

| Thành phần | Công nghệ | File/path chứng minh | Vai trò |
|------------|-----------|----------------------|---------|
| Ứng dụng Android | Kotlin, Android SDK 26–34, ViewBinding, Navigation, Retrofit, OkHttp, Room (dependency) | `app/build.gradle`, `app/src/main/AndroidManifest.xml` | Client chính |
| UI Android | Chủ yếu **Fragment + XML**; Compose bật nhưng `@Composable` chỉ thấy trong theme | `app/build.gradle` (`viewBinding`, `compose true`), `app/src/main/java/.../ui/theme/*.kt` | Giao diện người dùng |
| Backend API | Express, helmet, cors, morgan, JWT | `backend/nodejs/src/app.js`, `backend/nodejs/src/auth.js` | REST + static + admin |
| MySQL | `mysql2` pool | `backend/nodejs/src/db.js` | Lưu trữ |
| RAG service | FastAPI, routers health/rag/admin, pipeline BM25… | `backend/rag/app/main.py`, `backend/rag/app/routers/*.py` | Truy vấn + sinh câu trả lời AI |
| Redis | `redis:7-alpine` trong compose | `docker-compose.yml` | Hạ tầng RAG (theo stack) |
| Admin dashboard | HTML template Express | `backend/nodejs/src/admin/**/*.js`, `backend/nodejs/src/admin/templates/` | Vận hành / giám sát |
| Bản đồ | OSMDroid + tile OSM | `MapFragment.kt` | Hiển thị bản đồ trong app |
| Chỉ đường ngoài app | Intent tới Google Maps (web / app) | `MapIntentHelper.kt` | Mở chỉ đường bên ngoài |
| Thời tiết | Open-Meteo | `WeatherService.kt` | Dự báo không qua backend |

---

## 2. Thiết kế kiến trúc hệ thống

### Trả lời ngắn (có chứng minh)

| Câu hỏi | Kết luận | Chứng minh |
|---------|-----------|------------|
| Client–server? | **Có** — Android REST tới Node `/api/*` | `ApiService.kt`, `app.js` |
| Android giao tiếp backend? | **HTTPS/HTTP + JSON** qua **Retrofit 2 + Gson** | `RetrofitClient.kt`, `ApiService.kt` |
| Tổ chức backend | Module theo domain: `routes/index.js` đăng ký `register*Routes` | `backend/nodejs/src/routes/index.js`, `backend/nodejs/src/modules/*/*.routes.js` |
| MySQL kết nối? | Pool tại `db.js`, import `db` trong repositories | `backend/nodejs/src/db.js`, ví dụ `destinations.repository.js` |
| FastAPI RAG endpoint phía Node | Node gọi URL ghép từ `RAG_BASE_URL` + path (vd. `POST /rag/chat/simple`) | `backend/nodejs/src/lib/ragUpstream.js`, `backend/nodejs/src/services/ai.service.js` |
| Admin mount | **`/admin`** + `buildAdminRouter()` | `app.js` |
| Weather? | **Android trực tiếp Open-Meteo** | `WeatherService.kt` |
| Map trong app? | **OSMDroid** (tile Mapnik) | `MapFragment.kt` |
| Map ngoài app (chỉ đường)? | **Intent Google Maps** | `MapIntentHelper.kt` |
| Triển khai dev local | Node + (optional) Docker compose: MySQL, Redis, RAG, Backend | `docker-compose.yml`, `.env.example` |

### 2.1. Sơ đồ tổng quan kiến trúc — node cần vẽ

- **Android App (UNU Trip / package `com.smarttravel[.dev]`)**
- **Node.js / Express Backend** — `/api`, `/admin`, `/uploads`, `/images`
- **MySQL** — `unudata` (theo default `DB_NAME`)
- **FastAPI RAG Service** — port **8001** (compose mặc định)
- **Redis** (trong docker-compose)
- **Dashboard Admin (trình duyệt)** — HTTP tới `/admin/*`
- **Open-Meteo API** — `api.open-meteo.com` (gọi từ Android)
- **OSMDroid / OSM tile** — tile Mapnik
- **GPS / FusedLocationProvider** — lấy vị trí “Bạn đang ở đây” trên bản đồ
- **Google Maps (ứng dụng hoặc web)** — qua **Intent** khi chỉ đường / tìm địa điểm (không dùng Maps SDK trong app)

### 2.2. Sơ đồ triển khai (localhost/dev)

| Hạng mục | Giá trị trong dự án | Chứng minh |
|----------|---------------------|------------|
| Thành phần trên máy dev | Android Studio/emulator; Node backend; MySQL (local hoặc Docker); FastAPI RAG; (optional) Redis | `docker-compose.yml`, `.env.example` |
| Port backend | **3000** (mặc định) | `index.js`, `docker-compose.yml` |
| Port RAG | **8001** (publish compose) | `docker-compose.yml` |
| DB host/name | `.env`: `DB_HOST=127.0.0.1`, `DB_NAME=unudata`; Docker: host `mysql` | `.env.example`, `db.js`, `docker-compose.yml` |
| Emulator → API | `10.0.2.2:3000` (default `API_BASE_URL` comment / build) | `app/build.gradle` |
| Thiết bị thật | Cần **IP LAN máy chạy backend** trong `local.properties` → `API_BASE_URL` (và prod flavor: **cleartext tắt** — cần HTTPS hoặc cấu hình network phù hợp) | `app/build.gradle`, `app/src/main/AndroidManifest.xml` (`usesCleartextTraffic="false"`), `app/src/dev/AndroidManifest.xml` + `app/src/dev/res/xml/network_security_config.xml` |

---

## 3. Thiết kế ứng dụng Android

### Ghi chú chung

- **Launcher:** `AuthActivity` — `app/src/main/AndroidManifest.xml`
- **Shell chính:** `MainActivity` + `NavHostFragment` + bottom navigation — `activity_main.xml`, `MainActivity.kt`
- **Navigation graph:** `app/src/main/res/navigation/nav_graph.xml`
- **Admin:** **không** có trên Android — Admin là **web** Express (`/admin`).

### Bảng màn hình

| STT | Màn hình/Fragment/Activity | File/path | Chức năng (theo code) | API / dịch vụ gọi | ViewModel/Repository | Ghi chú |
|-----|----------------------------|-----------|------------------------|-------------------|----------------------|---------|
| 1 | **AuthActivity** (Login/Register) | `app/src/main/java/.../ui/auth/AuthActivity.kt` | Đăng nhập/đăng ký, lưu session | `POST auth/login`, `POST auth/register` | `AuthViewModel`, `AuthRepository` | Đã đăng nhập thì vào Main |
| 2 | **MainActivity** | `.../ui/home/MainActivity.kt` | Host NavHost + BottomNav | — | — | Ẩn bottom nav một số destination |
| 3 | **HomeFragment** | `.../ui/home/HomeFragment.kt` | Trang chủ: featured, nearby, tìm kiếm | `destinations` (repo) | `HomeViewModel`, `DestinationRepository` | Điều hướng tới list/detail |
| 4 | **DestinationListFragment** | `.../ui/destination/DestinationListFragment.kt` | Danh sách địa điểm / yêu thích-only | `GET destinations`, `GET users/favorites` | `DestinationViewModel`, `DestinationRepository` | Args `category`, `isFavoriteOnly` |
| 5 | **DestinationDetailFragment** | `.../ui/destination/DestinationDetailFragment.kt` | Chi tiết, ảnh, tag, yêu thích, thêm vào itinerary, đánh giá, thời tiết | `GET destinations/{id}`, reviews, favorites, itineraries + items; **Weather:** Open-Meteo | `DestinationViewModel`, repos | Map: navigate `MapFragment` |
| 6 | **MapFragment** | `.../ui/destination/MapFragment.kt` | OSMDroid, marker đích, GPS nếu có quyền | OSM tiles; **Intent** Google Maps | — | Fallback tọa độ nếu thiếu args (code có default) |
| 7 | **ItineraryFragment** | `.../ui/itinerary/ItineraryFragment.kt` | Danh sách lịch trình, tạo/xóa, luồng AI (theo nút) | `GET/POST/DELETE itineraries`, AI endpoints qua `ItineraryViewModel` | `ItineraryViewModel` | File dài — UI AI tour |
| 8 | **ItineraryDetailFragment** | `.../ui/itinerary/ItineraryDetailFragment.kt` | Chi tiết ngày/items, điều hướng sang detail địa điểm | `GET itineraries/{id}` | `ItineraryViewModel` | Cùng file Kotlin chứa thêm **AISuggestFragment** |
| 9 | **AISuggestFragment** | Cùng file: `.../ItineraryDetailFragment.kt` (class riêng) | “AI Gợi ý” form → gọi suggest + save AI | `POST ai/suggest-itinerary`, `POST itineraries/save-ai` | `ItineraryViewModel`, `GeminiService` | Tên class `AISuggestFragment` |
| 10 | **AIItineraryRequestFragment** | `.../AIItineraryRequestFragment.kt` | Bước 1 flow AI tour | Qua `ItineraryRepository` / `DestinationRepository` | `ItineraryViewModel` | nav từ `ItineraryFragment` |
| 11 | **AIItineraryOptionsFragment** | `.../AIItineraryOptionsFragment.kt` | Chọn tour AI | `POST ai/itinerary-options`, `POST itineraries/create-from-option` | `ItineraryViewModel` | |
| 12 | **AIItineraryEditorFragment** | `.../AIItineraryEditorFragment.kt` | Chỉnh sửa tour AI | `POST ai/itinerary-preview`, `POST itineraries/create-from-selection`, v.v. | `ItineraryViewModel` | |
| 13 | **ChatbotFragment** | `.../ui/chatbot/ChatbotFragment.kt` | Chat trợ lý | `POST ai/rag-chat` (qua `RagService.chat`); `POST ai/chat` (qua `GeminiService` các bước) | `ChatbotViewModel` | Token init `getToken()` |
| 14 | **ProfileFragment** | `.../ui/profile/ProfileFragment.kt` | Hồ sơ, stats, yêu thích, lịch trình, settings, avatar | `GET users/stats`, `PUT users/profile`, `POST users/avatar` | (trực tiếp `apiService` một phần) | **Đăng xuất:** xóa session local, **không** gọi `POST auth/logout` |
| 15 | **SettingsFragment** | `.../ui/profile/SettingsFragment.kt` | Menu cài đặt (placeholder “đang phát triển”) | — | — | Toast placeholder |
| 16 | **SelectItineraryDialog** / **CreateItineraryDialog** | `SelectItineraryDialog.kt`, `CreateItineraryDialog.kt` | Chọn lịch trình / tạo lịch trình | `GET itineraries`, `POST itineraries`, `POST .../items` | `ItineraryRepository` | |

---

## 4. Thiết kế điều hướng Android

| Câu hỏi | Kết luận | Chứng minh |
|---------|-----------|------------|
| Fragment + XML hay Compose? | **Chủ đạo Fragment + XML + ViewBinding**. Compose có trong `buildFeatures` và file theme Compose, **không** thấy màn `@Composable` chính ngoài `ui/theme/` | `app/build.gradle`, grep `@Composable` |
| Navigation Component? | **Có** — `NavHostFragment` + `nav_graph.xml` | `activity_main.xml`, `nav_graph.xml` |
| Auth → Main | `AuthActivity` → `MainActivity` sau khi `saveSession` | `AuthActivity.kt` |
| List → Detail | Actions `..._to_destinationDetailFragment` với arg `destinationId` | `nav_graph.xml` |
| Detail → Map / weather / reviews / favorite / itinerary | Map: `action_destinationDetailFragment_to_mapFragment`. Weather: gọi trong `DestinationDetailFragment`. Reviews/favorite/itinerary: cùng fragment + `DestinationViewModel` / repo | `DestinationDetailFragment.kt`, `nav_graph.xml` |
| Home / tab → AI / Chat / Profile | Bottom menu id trùng destination id (`homeFragment`, `destinationListFragment`, `itineraryFragment`, `chatbotFragment`, `profileFragment`) | `bottom_nav_menu.xml`, `MainActivity.kt` |
| Đăng xuất | `SessionManager.clearSession()` + mở `AuthActivity` (clear task) | `ProfileFragment.kt` |

### Mô tả cho sơ đồ navigation (gợi ý)

Người dùng mở app → **AuthActivity** (login/register) → **MainActivity** → **NavHost** mặc định **HomeFragment** → từ đây điều hướng tới **DestinationListFragment** / **DestinationDetailFragment** / **MapFragment**; thanh dưới chuyển tab tới **ItineraryFragment** (và các màn AI con), **ChatbotFragment**, **ProfileFragment** (và **Settings**, list yêu thích, list itinerary profile) → **Đăng xuất** quay về **AuthActivity**.

### File navigation graph

- `app/src/main/res/navigation/nav_graph.xml`

---

## 5. Thiết kế giao tiếp API trong Android

### Base URL & client

| Mục | Giá trị | Chứng minh |
|-----|---------|------------|
| Base URL build | `BuildConfig.BASE_URL` từ `local.properties` `API_BASE_URL`, default `http://10.0.2.2:3000/api/` (bắt buộc kết thúc `/`) | `app/build.gradle`, `RetrofitClient.kt` |
| Converter | Gson | `RetrofitClient.kt` |
| Interceptor | `RequestHeadersInterceptor` ( `X-Request-ID`, `X-Client-Version` ), logging, error logging | `RetrofitClient.kt`, `RequestHeadersInterceptor.kt` |
| Token | Mỗi endpoint (trừ login/register) truyền `@Header("Authorization")` — app dùng `Bearer <jwt>` | `ApiService.kt`, `SessionManager.getBearerToken()` |
| Lỗi response | `HttpErrorBodies.parseErrorMessageOrNull`; repo trả `Resource.Error` | `HttpErrorBodies.kt`, `Repositories.kt` |

### Bảng API Android (Retrofit `ApiService`)

*Nhóm Auth — base path theo `BuildConfig.BASE_URL` (đã có `/api/`).*

| Nhóm | Method | Endpoint (relative) | Hàm Retrofit | File/path | Request | Response/model | Màn hình / luồng |
|------|--------|----------------------|--------------|-----------|---------|----------------|-----------------|
| Auth | POST | `auth/login` | `login` | `ApiService.kt` | `LoginRequest` | `AuthResponse` | `AuthActivity` |
| Auth | POST | `auth/register` | `register` | idem | `RegisterRequest` | `AuthResponse` | `AuthActivity` |
| Auth | POST | `auth/logout` | `logout` | idem | Header Authorization | `ApiResponse<Unit>` | **Chưa thấy chỗ gọi trong UI** (logout hiện xóa local) |
| User | GET | `users/profile` | `getProfile` | idem | — | `ApiResponse<User>` | Chưa liệt kê hết — có model |
| User | GET | `users/stats` | `getUserStats` | idem | — | `ApiResponse<UserStats>` | `ProfileFragment` |
| User | PUT | `users/profile` | `updateProfile` | idem | `User` | `ApiResponse<User>` | `ProfileFragment` |
| User | PUT | `users/preferences` | `updatePreferences` | idem | `Map<String, List<String>>` | `ApiResponse<User>` | Chưa grep usage — endpoint tồn tại |
| User | POST | `users/avatar` | `uploadAvatar` | idem | multipart | `ApiResponse<User>` | `ProfileFragment` |
| Destinations | GET | `destinations` | `getDestinations` | idem | query page, limit, category, province, search, sort | `DestinationResponse` | `DestinationListFragment`, `HomeFragment` |
| Destinations | GET | `destinations/{id}` | `getDestinationDetail` | idem | path id | `DestinationDetailResponse` | `DestinationDetailFragment` |
| Destinations | GET | `destinations/featured` | `getFeaturedDestinations` | idem | — | `DestinationResponse` | `HomeFragment` |
| Destinations | GET | `destinations/nearby` | `getNearbyDestinations` | idem | lat,lng,radiusKm,limit | `DestinationResponse` | `HomeFragment` |
| Favorites | GET | `users/favorites` | `getFavorites` | idem | — | `DestinationResponse` | List yêu thích |
| Favorites | POST | `users/favorites` | `addFavorite` | idem | `FavoriteRequest` | `ApiResponse<Unit>` | Detail |
| Favorites | DELETE | `users/favorites/{destinationId}` | `removeFavorite` | idem | path | `ApiResponse<Unit>` | Detail |
| Reviews | GET | `destinations/{id}/reviews` | `getReviews` | idem | — | `ApiResponse<List<Review>>` | `DestinationDetailFragment` |
| Reviews | POST | `reviews` | `postReview` / `postReviewWithImages` | idem | JSON hoặc multipart | `ApiResponse<Review>` | `DestinationDetailFragment` |
| Itinerary | GET | `itineraries` | `getItineraries` | idem | — | `ItineraryResponse` | `ItineraryFragment`, dialog |
| Itinerary | GET | `itineraries/{id}` | `getItineraryDetail` | idem | — | `ApiResponse<Itinerary>` | `ItineraryDetailFragment` |
| Itinerary | POST | `itineraries` | `createItinerary` | idem | `CreateItineraryRequest` | `ApiResponse<Itinerary>` | Dialog tạo |
| Itinerary | PUT | `itineraries/{id}` | `updateItinerary` | idem | `Itinerary` | `ApiResponse<Itinerary>` | **Cần grep nếu dùng** |
| Itinerary | DELETE | `itineraries/{id}` | `deleteItinerary` | idem | — | `ApiResponse<Unit>` | List |
| Itinerary | POST | `itineraries/{id}/items` | `addDestinationToItinerary` | idem | `AddItineraryItemRequest` | `ApiResponse<Unit>` | `DestinationDetailFragment` |
| Itinerary | POST | `itineraries/create-from-selection` | `createItineraryFromSelection` | idem | `CreateItineraryFromSelectionRequest` | `ApiResponse<CreateItineraryFromSelectionResult>` | Flow AI editor |
| Itinerary | POST | `itineraries/save-ai` | `saveAIItinerary` | idem | `SaveAIItineraryRequest` | `ApiResponse<Unit>` | `AISuggestFragment` / `GeminiService` |
| Itinerary | POST | `itineraries/create-from-option` | `createItineraryFromOption` | idem | `CreateItineraryFromOptionRequest` | `ApiResponse<CreateItineraryFromOptionResult>` | AI options |
| AI | POST | `ai/itinerary-preview` | `previewAIItinerary` | idem | `AIItineraryPreviewRequest` | `AIItineraryPreviewResponse` | `ItineraryViewModel` |
| AI | POST | `ai/itinerary-options` | `getAIItineraryOptions` | idem | `AIItineraryPreviewRequest` | `AIItineraryOptionsResponse` | idem |
| AI | POST | `ai/suggest-itinerary` | `suggestItinerary` | idem | `AISuggestRequest` | `AISuggestResponse` | `GeminiService.suggestItinerary` |
| AI | POST | `ai/rag-chat` | `chat` | idem | `ChatRequest` | `ChatResponse` | `RagService` — **Lưu ý:** `RagService` gọi method Retrofit tên `chat` → map `ai/rag-chat` |
| AI | POST | `ai/chat` | `chatFallback` | idem | `Map<String,String>` | `ChatResponse` | `GeminiService` (prompt/validation/repair/fallback) |
| Weather | — | — | — | `ApiService.kt` comment | **Không** có endpoint Retrofit weather | Open-Meteo trực tiếp | `WeatherService.kt` |

---

## 6. Thiết kế Backend Server

### `createApp` — mount route

- `app.use("/api", buildRouter());`
- `app.use("/admin", adminAuthMiddleware, buildAdminRouter());`
- Static: `/uploads`, `/images`
- Cuối cùng: `notFoundMiddleware`, `errorHandlerMiddleware`

**Chứng minh:** `backend/nodejs/src/app.js`, `routes/index.js`, `admin/index.js`.

### Bảng route API chính (`/api` prefix)

| Nhóm | Method | Endpoint | File route | Middleware / ghi chú | Service layer (ví dụ) | Chức năng |
|------|--------|----------|------------|------------------------|------------------------|-----------|
| Health | GET | `/health` | `modules/health/health.routes.js` | Không auth | Controller trực tiếp | Liveness |
| Health | GET | `/health/ready` | idem | Không auth | DB + probe RAG (optional skip) | Readiness |
| Auth | POST | `/auth/register` | `modules/auth/auth.routes.js` | — | `auth.controller.js` + `users.repository.js` | Đăng ký + JWT |
| Auth | POST | `/auth/login` | idem | — | idem | Đăng nhập |
| Auth | POST | `/auth/logout` | idem | `authMiddleware` | Trả ok | Logout token phía server **stateless** (client bỏ token) |
| Users | GET/PUT/POST | `/users/profile`, `/users/stats`, `/users/preferences`, `/users/avatar` | `modules/users/users.routes.js` | auth + upload | `users.controller.js` | Hồ sơ |
| Favorites | GET/POST/DELETE | `/users/favorites`, … | `modules/favorites/favorites.routes.js` | auth | `favorites.service.js` | Yêu thích |
| Destinations | GET | `/destinations`, `/featured`, `/nearby`, `/:id` | `modules/destinations/destinations.routes.js` | auth | `destinations.service.js` | CRUD danh sách (đọc) |
| Reviews | GET/POST | `/destinations/:id/reviews`, `/reviews` | `modules/reviews/reviews.routes.js` | auth + `upload.array` | `reviews.service.js` | Đánh giá + ảnh |
| Itineraries | GET/POST/PUT/DELETE | `/itineraries`, `/:id`, `/:id/items`, `/save-ai` | `modules/itineraries/itineraries.routes.js` | auth | `itineraries.service.js` | Lịch trình |
| AI (public path) | POST | `/itineraries/create-from-option`, `/itineraries/create-from-selection` | `modules/ai/ai.routes.js` | auth | AI + itineraries services | Ghép itinerary từ option/selection |
| AI | POST | `/ai/suggest-itinerary`, `/ai/rag-chat`, `/ai/chat`, `/ai/itinerary-preview`, `/ai/itinerary-options` | idem | auth | `ai.controller.js`, `ai.service.js` | Gọi/thêm xử lý AI |

### Bảng Admin (`/admin` prefix, sau Basic Auth middleware)

*(Chỉ liệt kê route đăng ký — đầy đủ trong từng file.)*

| Màn / chức năng | Route | File |
|-----------------|-------|------|
| Dashboard | `GET /dashboard` | `dashboard.admin.routes.js` |
| Users CRUD HTML | `GET /users`, `GET /users/api/:id`, `POST /users/save`, `POST /users/delete/:id` | `users.admin.routes.js` |
| Destinations CRUD HTML | `GET /destinations`, `GET /destinations/api/:id`, `POST /destinations/save`, `POST /destinations/delete/:id` | `destinations.admin.routes.js` |
| System | `GET /system` | `system.admin.routes.js` |
| RAG AI Monitor + actions | `GET /rag-ai`, `POST /rag-ai/reload-place-store`, `POST /rag-ai/clear-cache`, `GET /rag-ai/data-quality-issues`, `GET /rag-ai/ai-metrics`, `GET /rag-ai/ai-logs`, `POST /rag-ai/debug-query` | `ragAi.admin.routes.js` |
| AI report | `GET /ai-report` | `aiReport.admin.routes.js` |

---

## 7. Thiết kế xử lý request/response (theo code)

### 7.1. Đăng nhập

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| Request body | `{ "email": string, "password": string }` (Zod) | `auth.controller.js` — `login` |
| Response thành công | `{ success: true, message, token, user }` — `user` qua `toUserDto` | `auth.controller.js` |
| Token | JWT, `signToken({ userId, email })`, `expiresIn` từ `JWT_EXPIRES_IN` hoặc **30d** | `auth.js` |
| Lỗi | 400 Invalid payload; 401 sai mật khẩu | `auth.controller.js` |

### 7.2. Tìm kiếm / xem địa điểm

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| Query | `page`, `limit`, `category`, `province`, `search`, `sort` | `ApiService.kt` — `getDestinations` |
| DB | Đọc từ bảng **`app_places`**, có join `EXISTS favorites` cho `is_favorite` | `destinations.repository.js` |
| Response | `DestinationResponse`: `success`, `data`, `total`, `page`, `limit` | `Models.kt` |

### 7.3. Tạo lịch trình

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| Request | `CreateItineraryRequest` fields: `title`, `description`, `startDate`, `endDate` | `Models.kt`, `itineraries.controller.js` (cần khớp service) |
| DB insert | Bảng `itineraries` (+ ngày con qua các service khác khi có items) | `itineraries.repository.js` — `insertItinerary` |

*(Chi tiết field validation nằm trong controller/service — báo cáo có thể trích đúng file `itineraries.controller.js` khi biên tập.)*

### 7.4. Gợi ý lịch trình AI / RAG

| Bước | Luồng | Chứng minh |
|------|-------|------------|
| Android | `AISuggestFragment` → `ItineraryViewModel.generateAIItinerary` → `GeminiService.suggestItinerary` → `POST /api/ai/suggest-itinerary` → nhận itinerary → build `SaveAIItineraryRequest` JSON → `POST /api/itineraries/save-ai` | `ItineraryDetailFragment.kt` (class `AISuggestFragment`), `ItineraryViewModel.kt`, `GeminiService.kt` |
| Node `/ai/suggest-itinerary` | Build prompt + gọi (optional) `AI_MODEL_URL` local; không có → **fallback `ragPostJson("/rag/chat", …)`** với suffix yêu cầu JSON; parse JSON lưu itinerary | `ai.controller.js` — `suggestItinerary`, `ai.service.js` — `generateSuggestItineraryAiResult` |
| Catalog địa điểm cho prompt Node | **`SELECT … FROM app_places`** | `ai.repository.js` |
| FastAPI | `POST /rag/chat`, `POST /rag/chat/simple`, v.v. | `backend/rag/app/routers/rag.py` |

### 7.5. Chatbot

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| Chính | Android `RagService` → Retrofit **`POST ai/rag-chat`** | `RagService.kt`, `ApiService.kt` |
| Node | `ragChat` → `requestRagChatSimple` → **`ragPostJson("/rag/chat/simple", …)`** | `ai.controller.js`, `ai.service.js` |
| Fallback / chỉnh sửa câu trả lời | `ChatbotViewModel` gọi thêm `GeminiService` với **`POST ai/chat`** (`chatFallback`) cho chuẩn hóa/validate/repair; nếu RAG fail → `geminiService.fallbackChat` (cũng `ai/chat`) | `ChatbotViewModel.kt`, `GeminiService.kt` |
| **Lưu ý đặt tên file** `GeminiService.kt` (**Android**): thực tế là **REST tới backend** `/ai/chat`, không thấy gọi Google Generative AI SDK trực tiếp trong Kotlin (dependency có trong Gradle nhưng **không** grep được usage) | `app/build.gradle`, grep `generativeai` |

### 7.6. Admin RAG AI Monitor

| Mục | Nội dung | Chứng minh |
|-----|----------|------------|
| Trang chủ monitor | `GET /admin/rag-ai` — song song fetch RAG: `/admin/system/overview`, `/admin/rag/status`, `/admin/system/self-test`, `/admin/ai/metrics`, `/admin/data-quality/status` | `ragAi.admin.routes.js` |
| Hành động | `POST /admin/rag-ai/reload-place-store` → RAG `/admin/rag/place-store/reload`; clear cache → `/admin/cache/clear`; debug → `POST /admin/rag-ai/debug-query` → RAG **`/admin/ai/debug-query`** | `ragAi.admin.routes.js` |
| FastAPI admin ví dụ | `GET /admin/ai/logs`, `GET /admin/ai/metrics`, … | `backend/rag/app/routers/admin.py` |
| Khi fetch lỗi | Template hiển thị HTTP/status và box JSON partial — handler `catch` 500 text | `ragAi.admin.routes.js` |

---

## 8. Thiết kế cơ sở dữ liệu

### Nguồn schema trong repo

- **Có file SQL migrate (v2):** `database/migrations/001`–`004` (và script populate `006`–`010` trong cùng thư mục).
- **Không có** `CREATE TABLE users / favorites / reviews / itineraries...` trong `database/migrations/` — cấu trúc các bảng này suy ra từ **câu SQL trong repositories** và `seed.js` (legacy).

### Bảng tổng hợp

| Tên bảng | Mục đích | Trường chính (theo SQL trong code) | Khóa / quan hệ | File/schema căn cứ | App Android / v2 / RAG |
|----------|----------|-----------------------------------|----------------|-------------------|------------------------|
| `users` | Tài khoản | `full_name`, `email`, `password_hash`, `phone`, `avatar`, `preferences_json`, `created_at` | PK `id` | `users.repository.js` | **App** |
| `app_places` | Địa điểm hiển thị app | Xem migrate 001 + SELECT `d.*` trong repo | PK `id`, UNIQUE `place_key` | `001_create_app_places.sql`, `destinations.repository.js` | **App (v2 table)** |
| `favorites` | Yêu thích | `user_id`, `destination_id`, `created_at` (có trong list query) | FK logic tới users + app_places | `favorites.repository.js` | **App** |
| `reviews` | Đánh giá | `user_id`, `destination_id`, `rating`, `comment`, `images_json`, `created_at` | FK tới users; destination = `app_places.id` | `reviews.repository.js` | **App** |
| `itineraries` | Lịch trình | `user_id`, `title`, `description`, `start_date`, `end_date`, `total_days`, `status`, `estimated_budget`, … | PK `id` | `itineraries.repository.js` | **App** |
| `itinerary_days` | Ngày trong lịch | `itinerary_id`, `day_number`, `date` | FK `itinerary_id` | `itineraries.repository.js` | **App** |
| `itinerary_items` | Item địa điểm trong ngày | `day_id`, `destination_id`, `start_time`, `end_time`, `note`, `order_index` | JOIN `app_places` | `itineraries.repository.js` | **App** |
| `place_images` | Ảnh địa điểm v2 | `app_place_id`, `image_url`, `is_primary`, `status`, … | FK → `app_places.id` | `003_create_place_images.sql` | **v2 / App** |
| `place_id_map` | Ánh xạ id RAG/raw → app place | `rag_place_id`, `new_app_place_id`, … | FK → `app_places.id` | `004_create_place_id_map.sql`, `placeIdMap.repository.js` | **v2 / AI bridge** |
| `rag_knowledge_base` | Kho tri thức RAG trong DB | Rất nhiều field mô tả địa điểm RAG | PK `id`, FK optional `app_place_id` | `002_create_rag_knowledge_base.sql` | **RAG / ingest** — export corpus qua script |
| Legacy `destinations` (nếu còn) | Migrate/seed cũ | **Chưa dùng trong queries destinations hiện tại** — code đọc **`app_places`** | — | Đảo chiều từ `seed.js` (vẫn nhắc `destinations`) vs `destinations.repository.js` chỉ `app_places` | **Phiên bản / dữ liệu:** repo runtime đã trỏ `app_places` |

### Kết luận cho báo cáo (an toàn)

- **Bảng phục vụ API destinations/favorites/reviews/itineraries hiện tại:** `users`, `app_places`, `favorites`, `reviews`, `itineraries`, `itinerary_days`, `itinerary_items` (chứng minh SQL).
- **Bảng hướng v2 / RAG / ánh xạ:** `place_images`, `place_id_map`, `rag_knowledge_base` (file migrate + script export `export_rag_knowledge_base_to_corpus.py`).
- **Seed:** `backend/nodejs/src/seed.js` tồn tại nhưng vẫn tham chiếu luồng legacy `destinations` — **cần xác nhận vận hành thực tế** khi DB đã chuyển hết sang `app_places` (xem mục 17).
- **Đủ dữ liệu demo:** **Chưa tìm thấy trong mã nguồn** đánh giá độ đầy đủ — chỉ có script/migration và seed; phụ thuộc DB đã import.

---

## 9. Thiết kế phân hệ AI/RAG

### Bảng thành phần

| Thành phần | File/path | Vai trò |
|------------|-----------|---------|
| FastAPI app | `backend/rag/app/main.py` | Khởi tạo pipeline, mount router, middleware |
| Health | `app/routers/health.py` | `/health`, `/health/ready`, `/runtime/status` |
| RAG API | `app/routers/rag.py` | `/chat`, `/rag/chat`, `/rag/chat/simple`, `/rag/retrieve` |
| Admin/metrics/logs | `app/routers/admin.py` | `/admin/*` AI metrics, logs, debug-query, data-quality, … |
| Itinerary AI | `app/ai_itinerary.py` (include trong `main.py`) | Preview/options itinerary qua HTTP |
| Cấu hình runtime AI | `backend/rag/core/config.py` | `AI_RUNTIME_MODE` (default **`mock`**), **`ENABLE_GEMINI` default `false`**, đọc `GEMINI_API_KEY` từ env |
| Node proxy | `backend/nodejs/src/services/ai.service.js`, `lib/ragUpstream.js` | Retry, timeout, gọi RAG có header key |
| Key nội bộ | `app/middleware.py` — `InternalApiKeyMiddleware` | Bảo vệ route khi set `RAG_INTERNAL_API_KEY` / `RAG_ADMIN_API_KEY` |

### Gemini / mock — kết luận **an toàn** cho báo cáo

- Trong **Python `Settings`**: `enable_gemini` mặc định **`False`**; `gemini_api_key` lấy từ **`os.getenv("GEMINI_API_KEY")`**; `ai_runtime_mode` mặc định **`mock`** (`core/config.py`).
- `.env.example` mang **ví dụ** `ENABLE_GEMINI=true` và `GEMINI_API_KEY=...` — đây là **khuyến nghị triển khai**, không thay đổi default trong code Python.
- **Không được khẳng định** “luôn dùng Gemini thật” — phải nói: *Gemini chỉ được dùng khi cấu hình **`ENABLE_GEMINI=true`** và biến môi trường **`GEMINI_API_KEY`** được set khớp thực tế; có chế độ **`AI_RUNTIME_MODE=mock`** mặc định và đường fallback trong Node/RAG.*

### DB `rag_knowledge_base`, `place_id_map` trong luồng

- Corpus build: script `backend/rag/scripts/export_rag_knowledge_base_to_corpus.py` đọc `rag_knowledge_base`.
- Backend Node mapping raw id: **`place_id_map`** qua `placeIdMap.repository.js`.

---

## 10. Thiết kế Dashboard Admin

### Tổng quan

- **Kiểu:** Web Express + HTML templates (`admin/templates`).
- **Bảo vệ:** `adminAuthMiddleware` — chỉ **bật Basic Auth khi có đủ `ADMIN_BASIC_USER` và `ADMIN_BASIC_PASS`**; nếu thiếu → **passthrough + cảnh báo log** (không authenticate).
- **Chứng minh:** `backend/nodejs/src/middlewares/adminAuth.middleware.js`, `app.js`.

### Bảng màn hình

| Màn hình | Route/URL | File xử lý | Chức năng | HTML? | API nội bộ |
|----------|-----------|------------|-----------|-------|-----------|
| Dashboard | `/admin/dashboard` | `dashboard.admin.routes.js` | Thống kê users/destinations/itineraries | Có (`dashboard.content.html`) | SQL MySQL |
| Users | `/admin/users` (+ api/save/delete) | `users.admin.routes.js` | CRUD người dùng HTML | Có | MySQL |
| Destinations | `/admin/destinations` | `destinations.admin.routes.js` | CRUD địa điểm | Có | MySQL (`app_places`) |
| System | `/admin/system` | `system.admin.routes.js` | Thống kê hệ thống | Có | MySQL |
| RAG AI | `/admin/rag-ai` + actions | `ragAi.admin.routes.js` | Giám sát RAG + reload/clear/cache/metrics/logs/debug | Có (`ragAi.content.html`) | HTTP → FastAPI `/admin/*` |
| AI Report | `/admin/ai-report` | `aiReport.admin.routes.js` | Báo cáo AI (aggregate DB/stats — chi tiết trong file) | Có | MySQL / helper repos |

### Quản lý model / training?

- Theo route FastAPI và admin hiện có: **ưu tiên mô tả là giám sát vận hành / debug / dữ liệu / metrics**, **không** thấy giao diện “training model” trong các path đã liệt kê. (**Chưa tìm thấy** màn huấn luyện trong `admin.routes` đã đọc.)

---

## 11. Thiết kế bản đồ và định vị

| Hạng mục | Nội dung | Chứng minh |
|----------|----------|------------|
| Thư viện bản đồ trong app | **OSMDroid** `MapView`, `TileSourceFactory.MAPNIK` | `MapFragment.kt` |
| Marker đích | Từ `arguments` lat/lng/tên địa điểm (truyền từ `DestinationDetailFragment`) | `DestinationDetailFragment.kt`, `MapFragment.kt` |
| Quyền | Manifest: `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION` | `AndroidManifest.xml` |
| GPS | **`FusedLocationProviderClient.lastLocation`** — thêm marker “Bạn đang ở đây” | `MapFragment.kt` |
| Không có quyền / null location | Toast thông báo; chỉ đường không dùng điểm xuất phát GPS → fallback `openNavigation` | `MapFragment.kt` |
| Mở chỉ đường | `MapIntentHelper.openRoute` / `openNavigation` — Google Maps app hoặc URL | `MapIntentHelper.kt` |
| Google Maps **API/SDK** trong app | **Không** — chỉ Intent/URL Maps bên ngoài; Manifest ghi **đã chuyển sang OSMDroid** | `AndroidManifest.xml`, `MapIntentHelper.kt` |

---

## 12. Thiết kế dự báo thời tiết

| Hạng mục | Nội dung | Chứng minh |
|----------|----------|------------|
| API | Open-Meteo **`https://api.open-meteo.com/v1/forecast`** | `WeatherService.kt` |
| Gọi từ đâu | **Android trực tiếp**, không qua Retrofit/backend | idem |
| Map thành phố | Dictionary `cityCoords` (chuẩn hóa lowercase, chứa nhiều alias) | `WeatherService.kt` |
| Fallback | Nếu không khớp chuỗi → **`Pair(21.0285, 105.8542)` (Hà Nội)** | `WeatherService.kt` (`?: Pair(21.0285, 105.8542)`) |
| Response parse | `current`: nhiệt độ, độ ẩm, `weather_code`, gió; `daily` 5 ngày → `ForecastDay` | `WeatherService.kt` |
| Màn hiển thị | **`DestinationDetailFragment`** (`loadWeather`) | `DestinationDetailFragment.kt` |
| Lỗi | `Resource.Error("Không thể lấy…")`; UI ẩn card weather | `WeatherService.kt`, `DestinationDetailFragment.kt` |

### Bảng thành phần weather

| Thành phần | File/path | Chức năng |
|------------|-----------|-----------|
| `WeatherService` | `app/src/main/java/.../utils/WeatherService.kt` | GET Open-Meteo + parse JSON |
| `WeatherInfo`, `ForecastDay` | `data/model/Models.kt` | Model dữ liệu |
| UI | `fragment_destination_detail.xml` + logic trong `DestinationDetailFragment` | Hiển thị/card |

---

## 13. Thiết kế bảo mật

### Bảng

| Nội dung | Cách triển khai hiện tại | File/path | Ghi chú / hạn chế |
|----------|---------------------------|-----------|-------------------|
| Mật khẩu | **bcrypt** `hashSync` / `compareSync` salt 10 | `auth.controller.js` | Theo code hiện tại |
| JWT | Ký/khớp **`JWT_SECRET`**; default dev **`smarttravel_dev_secret_change_me`** | `auth.js`, `config/env.js` | Production: **`assertSafeProductionConfig`** đòi secret khác default |
| Lưu token Android | **EncryptedSharedPreferences** + khóa `MasterKeys.AES256_GCM` | `SessionManager.kt` | |
| Gửi token API | Header `Authorization: Bearer …` cho hầu hết endpoint | `ApiService.kt` | Chatbot khởi tạo token raw — các service bọc Bearer |
| Admin | Basic Auth optional — **thiếu env → mở** | `adminAuth.middleware.js` | Rủi ro demo |
| Env | Node/RAG đọc **root `.env`** | `backend/nodejs/src/config/env.js` (dotenv path), `rag/core/config.py` | |
| RAG/Gemini key phía cloud | **`GEMINI_API_KEY`** chủ yếu cho **backend/rag**; comment `.env.example` nói Node proxy | `.env.example` | Android `GEMINI_API_KEY` trong `local.properties` là buildConfig — **grep không thấy** dùng SDK Generative trên Kotlin |
| CORS | `app.use(cors())` toàn cục API | `app.js` | Mở rộng theo mặc định thư viện |
| Helmet / CSP | `helmet` + nonce script admin | `app.js` | |
| HTTP cleartext Android | Main **tắt** cleartext; dev flavor **bật** | `AndroidManifest.xml`, `app/src/dev/...` | Prod cần HTTPS hoặc network config |
| RAG internal key | Header `X-RAG-Internal-Key` khi env set | `ragClient.js`, `middleware.py` | Nếu không set → middleware cho qua |

### Khuyến nghị ghi trong báo cáo (từ code)

- Đổi **`JWT_SECRET`** production; không dùng default.
- Bật **`ADMIN_BASIC_USER` / ADMIN_BASIC_PASS`** khi deploy.
- Cân nhắc thu hẹp **CORS** và bắt buộc **HTTPS** cho mobile prod.
- Thiết lập **`RAG_INTERNAL_API_KEY`** khớp giữa Node và RAG khi public mạng.

---

## 14. Thiết kế xử lý lỗi và fallback

| Tình huống | Cách xử lý trong code | File/path | Gợi ý cách viết báo cáo |
|------------|----------------------|-----------|-------------------------|
| HTTP lỗi Retrofit | Log body; `Resource.Error` / Toast | `RetrofitClient.kt`, repositories | Mô tả lớp repository + UX Toast |
| 404 API | `HttpError.notFound` → middleware JSON | `notFound.middleware.js`, `errorHandler.middleware.js` | |
| Chatbot RAG fail | Chuỗi trả về báo lỗi → `fallbackChat` qua **`/ai/chat`** | `ChatbotViewModel.kt` | Fallback theo lớp |
| Chatbot `/ai/chat` backend | Ưu tiên `AI_MODEL_URL` local nếu set; không thì **`/rag/chat/simple`** fallback | `ai.controller.js` — `chat` | |
| Gợi ý itinerary AI JSON sai | Response 500 `"AI trả về dữ liệu không hợp lệ"` | `ai.controller.js` | |
| Open-Meteo lỗi | `Resource.Error` | `WeatherService.kt` | Ẩn UI thời tiết |
| Map không có GPS | Toast; chỉ đường chỉ có đích | `MapFragment.kt` | |
| Nearby empty | Repo mở rộng radius rồi fallback featured/list | `DestinationRepository.kt` | |
| RAG downstream (Node→RAG) | Retry transient; timeout `RAG_FETCH_TIMEOUT_MS` | `ragUpstream.js`, `env.js` | |
| Admin RAG dashboard | KPI đỏ nếu `fetchRagJson` fail; catch 500 | `ragAi.admin.routes.js` | |

---

## 15. Danh sách hình/sơ đồ đề xuất cho Chương 3

| Đề xuất # | Tên hình | Nguồn dữ liệu để vẽ | Ưu tiên |
|-----------|----------|---------------------|---------|
| 3.1 | Sơ đồ tổng quan hệ thống | §2.1 nodes + luồng §1 | Cao |
| 3.2 | Kiến trúc client-server + AI/RAG | §2 + `ragUpstream.js`, `main.py` | Cao |
| 3.3 | Triển khai localhost/dev | §2.2 + `docker-compose.yml` | Cao |
| 3.4 | Navigation Android | `nav_graph.xml` + §4 | Cao |
| 3.5 | Fragment–ViewModel–Repository–API | §3–5 | Cao |
| 3.6 | ERD | §8 migrations + repos SQL | Cao |
| 3.7 | AI/RAG pipeline | §9 + `rag.py`, `pipeline` | Trung bình |
| 3.8 | RAG AI Monitor | §10 `/admin/rag-ai` | Trung bình |
| Misc | Screenshot các màn Android | Theo bảng mục 3 | Cao |
| Misc | Screenshot Admin | `/admin/dashboard`, `/admin/rag-ai` | Trung bình |

---

## 16. Gợi ý đoạn văn biên tập báo cáo (bám sát code)

**(3.1) Tổng quan:** Hệ gồm ứng dụng Android **UNU Trip** (`com.smarttravel`, flavor dev `.dev`), backend **Node.js/Express** phục vụ REST **`/api`**, MySQL (**`mysql2`**), dịch vụ **FastAPI RAG** (URL cấu hình `RAG_BASE_URL`, mặc định **`127.0.0.1:8001`**) và dashboard quản trị web **`/admin`**. Người dùng đăng nhập nhận **JWT**, lưu an toàn trên máy (**EncryptedSharedPreferences**). Android lấy nội dung du lịch qua Retrofit và gọi thời tiết trực tiếp Open-Meteo.

**(3.2) Kiến trúc:** Kiến trúc client–server có tách client mobile và máy chủ. Máy chủ tổ chức theo router module (health, auth, users, favorites, destinations, reviews, itineraries, ai); phía AI được proxy sang FastAPI.

**(3.3) Android:** Giao diện xây **Fragment + ViewBinding**, điều hướng **Navigation Component** (`nav_graph.xml`), `MainActivity` kết hợp BottomNavigation và anim ẩn/hiện theo destination. Hai activity: **AuthActivity** và **MainActivity**.

**(3.4) Backend API:** REST JSON; auth JWT cho hầu hết `/api` (ngoại trừ register/login và health).

**(3.5) DB:** Dữ liệu địa điểm phía server đọc chủ yếu từ **`app_places`** qua các repository đã chỉ định; có bảng **`place_id_map`**, **`place_images`**, **`rag_knowledge_base`** cho lộ trình chuẩn hóa/RAG trong thư mục migrate.

**(3.6) AI/RAG:** RAG là dịch vụ độc lập expose HTTP; Node gom log trace qua **`X-Request-ID`**. Chiến lược chạy Gemini phụ thuộc **`ENABLE_GEMINI` + `GEMINI_API_KEY`** ở dịch vụ FastAPI và mode runtime `AI_RUNTIME_MODE` (default **mock**).

**(3.7) Admin dashboard:** Serve HTML trong Express với các trang Dashboard / Users / Destinations / System / RAG AI; Basic Auth chỉ có hiệu lực khi cấu hình env.

**(3.8) Bản đồ và thời tiết:** Bản đồ nhúng dùng **OSMDroid**; định vị **Fused Location** để chỉ đường có điểm xuất phát. Thời tiết là gọi trực tiếp Open-Meteo dựa trên tên thành/phố của địa điểm với fallback tọa độ Hà Nội trong code (`WeatherService`).

**(3.9) Bảo mật và lỗi:** Mật khẩu **bcrypt**; JWT có **secret fallback dev** không dùng cho production; Retrofit và middleware Express đều có cơ chế log/handle lớp nhất định; admin mặc định **`/admin`** mở khi không cấu hình Basic Auth.

---

## 17. Điểm cần xác nhận thêm với chủ project

1. **Compose:** Project bật Compose build nhưng UI chính là XML Fragment — có kế hoạch chuyển Compose hay chỉ để dependency/theme?
2. **Lịch trình AI / UI:** `ItineraryFragment` codebase lớn — cần xác nhận demo thực tế đang show đủ các bước tour AI không.
3. **Gemini khi demo:** RAG có chạy với **`ENABLE_GEMINI=true`** + key hay thường để **`mock`** / fallback?
4. **Migration:** `database/migrations` có được import đầy đủ vào MySQL của demo chưa, đặc biệt **`place_id_map`**, **`rag_knowledge_base`**?
5. **Admin:** Có demo bảo vệ **`ADMIN_BASIC_USER/PASS`** chưa?
6. **`RAG AI` Dashboard:** Endpoint con nào thường fail trên máy dev (thiếu file index/BM25, RAG down, …)?
7. **Weather fallback Hà Nội:** Behavior khi không map được tên thành có chấp nhận được cho báo cáo?
8. **GPS thực:** Có kiểm thử emulator vs thiết bị ảnh hưởng `lastLocation == null`?
9. **`POST auth/logout`:** Backend có endpoint nhưng client hiện **không** gọi — có mục tiêu bổ sung hay cố ý chỉ revoke local?
10. **Dependency Google Generative AI Android:** có trong Gradle nhưng **chưa thấy Kotlin import** — dự định dùng sau hay có thể gỡ?
11. **`seed.js` và bảng `destinations`:** DB production đã bỏ hẳn legacy hay seed vẫn cần cho lab?
12. Có mockup/screenshot **Figma** chính thức không, hay chỉ screenshot app thật?

---

*Cuối file — chỉ chứa input cho biên tập Chương 3.*
