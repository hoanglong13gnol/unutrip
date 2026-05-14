# CHƯƠNG 2. KHẢO SÁT VÀ PHÂN TÍCH HỆ THỐNG

Ứng dụng được triển khai trong kho mã nguồn với **tên hiển thị “UNU Trip”** (`app/src/main/res/values/strings.xml`), gói ứng dụng **`com.smarttravel`** (`app/build.gradle`), và phần mềm máy chủ gắn với nhãn hiệu **UnuTrip** (ví dụ FastAPI: `backend/rag/app/main.py`). Chương này mô tả hiện trạng và yêu cầu bám theo **chứng cứ trong mã**, không phóng đoán ngoài phạm vi đã có.

[Chèn Hình 2.1. Phạm vi tổng quan UNU Trip – Android – Node API – MySQL – RAG]

---

## 2.1. Khảo sát hiện trạng

### 2.1.1. Tổng quan về nhu cầu sử dụng ứng dụng du lịch thông minh

Trong bối cảnh đời sống hiện đại, người dùng di động ngày càng mong muốn **thu gọn các bước** tìm điểm đến, xem tin tóm tắt, **vị trí địa lý**, **dự báo thời tiết**, **đánh giá cộng đồng** và **lập lịch trình** trong cùng một luồng trải nghiệm. Nhu cầu **tư vấn tự động** (chatbot hay gợi ý theo sở thích) cũng tăng, nhằm giảm thời gian đối chiếu nhiều nguồn thủ công.

Với UNU Trip trong mã nguồn hiện tại, các hướng nghiệp vụ tương ứng đã được gắn với chức năng có thể truy vết: **danh sách và chi tiết địa điểm** (`DestinationListFragment`, `DestinationDetailFragment`), **bản đồ OSMDroid** (`MapFragment`), **thời tiết Open-Meteo phía Android** (`WeatherService.kt`), **yêu thích và đánh giá** (`ApiService.kt`, backend `favorites.routes.js`, `reviews.routes.js`), **lịch trình** và **luồng AI** (`ItineraryFragment`, `AISuggestFragment`, các fragment AI lịch trình, `ChatbotFragment`). Phần tư vấn trò chuyện kết hợp gọi **API Node** và (qua proxy) **dịch vụ FastAPI RAG**.

### 2.1.2. Thực trạng hiện tại

Người dùng **không có công cụ tích hợp** thường phải lần lượt tra cứu trên các trang/blog, tra bản đồ, tra thời tiết, và tự ghép vào giấy hoặc bảng tính. **Thông tin phân tán** khiến khó đảm bảo độ nhất quán (giờ mở cửa, khoản phí, vị trí). Việc dùng **nhiều ứng dụng khác nhau** làm gián đoạn luồng suy nghĩ và dễ bỏ sót ràng buộc thời gian. Người dùng cũng gặp khó khăn khi **chọn điểm đến theo gu** nếu không có công cụ lọc/gợi ý và **thiếu tư vấn tự động** trong cùng môi trường đang lập kế hoạch.

### 2.1.3. Khó khăn và hạn chế

Tình trạng chung của việc lập kế hoạch thủ công bao gồm các hạn chế sau đây, phù hợp làm động lực đề xuất hệ UNU Trip.

- **Tìm kiếm thủ công tốn thời gian**: Người dùng phải lặp lại các từ khóa và lọc thông tin mỗi lần có nhu cầu mới.
- **Dữ liệu du lịch không tập trung**: Thông tin nằm rải rác và khó tái sử dụng cho các bước sau trong cùng hành trình.
- **Khó theo dõi lịch trình**: Khi chỉ có ghi chú rời hoặc nhiều tab, không dễ thấy tổng thể các ngày và địa điểm xen kẽ.
- **Chưa có hoặc hạn chế gợi ý thông minh trong một luồng đơn**: Người dùng không có chỉ báo khách quan từ dữ liệu nội bộ và mô hình truy vấn.
- **Bản đồ, thời tiết và đánh giá chưa được gộp trong một hệ**: Trong đời thường, ba yếu tố này thường phân tán trên các dịch vụ khác nhau; UNU Trip hướng tới đưa các trải nghiệm này gần với một ứng dụng và một API thống nhất — phần thời tiết trong phiên bản khảo sát được gọi trực tiếp Open-Meteo nên vẫn phụ thuộc một HTTP client ngoài Node (được ghi cụ thể ở mục kiến trúc và thời tiết).

### 2.1.4. Yêu cầu đặt ra đối với hệ thống

Dựa trên đề tài và chứng cứ mã nguồn, hệ UNU Trip được đặt ra các nhóm yêu cầu sau.

| Nhóm yêu cầu | Diễn giải bám code |
| :--- | :--- |
| Ứng dụng Android cho người dùng | Kotlin, Jetpack Navigation, các fragment trong `app/src/main/java/com/smarttravel/ui/...`; `RetrofitClient.kt` nhận `BuildConfig.BASE_URL`. |
| Backend Web API | Node Express, tiền tố `/api` (`backend/nodejs/src/app.js`, `routes/index.js`). |
| Cơ sở dữ liệu MySQL | Lược đồ cơ bản trong `backend/nodejs/database.sql`; mở rộng v2 trong `database/migrations/*.sql`. |
| Tìm kiếm, xem địa điểm | `GET /api/destinations`, `GET /api/destinations/:id`, `featured`, `nearby`; Android `ApiService.kt`, `DestinationRepository`. |
| Tạo, quản lý lịch trình | `GET/POST/PUT/DELETE /api/itineraries...`; Android `ItineraryViewModel`, `ItineraryFragment`; thêm điểm vào lịch từ `DestinationDetailFragment` qua `ItineraryRepository.addDestination`. **Cập nhật lịch trình PUT** có trên Retrofit/backend nhưng **chưa thấy** repository/màn gọi `updateItinerary` (xem phần xác nhận cuối file). |
| AI / RAG gợi ý lịch trình | `POST /api/ai/suggest-itinerary`, `POST /api/ai/itinerary-preview`, `POST /api/ai/itinerary-options`, lưu từ lựa chọn AI (`/api/itineraries/create-from-selection`, `/api/itineraries/create-from-option`); Node proxy FastAPI trong `services/ai.service.js` và `ragUpstream.js`; RAG trong `backend/rag/`. |
| Chatbot tư vấn | Android `ChatbotFragment` + `ChatbotViewModel`; `POST /api/ai/rag-chat` và dự phòng `POST /api/ai/chat`; RAG `/rag/chat/simple`. |
| Bản đồ | OSMDroid `MapFragment.kt`; có yêu cầu GPS (Fused Location) để chỉ đường/đánh dấu “Bạn đang ở đây”; mở Google Maps qua `MapIntentHelper`. |
| Thời tiết | **Android gọi trực tiếp** `https://api.open-meteo.com/v1/forecast` trong `WeatherService.kt` (không qua backend; không có route thời tiết trong `ApiService.kt` ngoài ghi chú). |
| Đánh giá, yêu thích | `GET/POST` reviews và `users/favorites` như trong `ApiService.kt` và các route backend tương ứng. |
| Admin / quản trị | **`/admin/*`** Express với các module trong `backend/nodejs/src/admin/`; xác thực HTTP Basic **tùy chọn** qua biến môi trường (`adminAuth.middleware.js`). **Không phải ứng dụng Android** mà là giao diện/phục vụ web phía máy chủ. |

---

## 2.2. Khảo sát quy trình nghiệp vụ thực tế

Đoạn sau mô tả quy trình **được xác minh trong mã**. Với mỗi quy trình có gợi ý BPMN và **lane**.

### 2.2.1. Quy trình đăng ký và đăng nhập tài khoản

**Giới thiệu.** Người dùng mới khởi tạo tài khoản hoặc đăng nhập để nhận JWT, phục vụ các API có `Authorization: Bearer`.

**Bước 1.** Mở `AuthActivity` (`app/src/main/java/com/smarttravel/ui/auth/AuthActivity.kt`): chọn chế độ đăng nhập hoặc đăng ký (toggle).  
**Bước 2.** Nhập biểu mẫu; `AuthViewModel` gọi `AuthRepository.login` / `register` → Retrofit `POST auth/login` hoặc `POST auth/register` (`ApiService.kt`).  
**Bước 3.** Backend `auth.controller.js`: kiểm tra Zod → bcrypt (đăng ký) hoặc so khớp mật khẩu (đăng nhập) → ghi **`users`** qua repository → **`signToken`** (`auth.js`) trả `{ token, user }`.  
**Bước 4.** `SessionManager` lưu phiên; điều hướng `MainActivity`.

**Liên quan mã:** Android `AuthActivity.kt`, `ApiService.kt` (khối AUTH); Backend `modules/auth/auth.routes.js`, `auth.controller.js`; bảng **`users`** (`database.sql`).  
**Gợi ý BPMN:** “BPMN 2.x – Đăng ký/Đăng nhập UNU Trip”.  
**Lane:** Người dùng cuối (Android Client) · API Node (`/api/auth/*`) · Cơ sở dữ liệu MySQL (`users`).

---

### 2.2.2. Quy trình tìm kiếm và xem thông tin địa điểm du lịch

**Giới thiệu.** Người dùng xem danh sách (lọc, tìm), điểm nổi bật, gần đây và chi tiết một địa điểm.

**Bước 1.** `HomeFragment` / `DestinationListFragment` tải dữ liệu qua `HomeViewModel` / `DestinationViewModel` và `DestinationRepository`: `GET /api/destinations` (query `category`, `province`, `search`), `GET /api/destinations/featured`, `GET /api/destinations/nearby` (với `lat`, `lng` – được dùng từ `HomeViewModel`/`HomeFragment`).  
**Bước 2.** Chọn một mục → `DestinationDetailFragment` với argument `destinationId`.  
**Bước 3.** `GET /api/destinations/{id}`; đồng thời tải `GET /api/destinations/{id}/reviews`.

**Liên quan mã:** `modules/destinations/destinations.routes.js`; `DestinationRepository.kt`; `DestinationDetailFragment.kt`.  
**Bảng:** **`destinations`**, **`reviews`** (liên quan `destination_id`).  
**Gợi ý BPMN:** “BPMN – Tra cứu và xem địa điểm”.  
**Lane:** Client Android · REST `/api/destinations*`, `/api/destinations/:id/reviews` · DB.

---

### 2.2.3. Quy trình xem bản đồ và định vị địa điểm

**Giới thiệu.** Hiển thị bản đồ nền OSM và điểm đánh dấu địa điểm; có bổ sung vị trí người dùng qua GPS khi được cấp quyền.

**Bước 1.** Tại `DestinationDetailFragment`, nút xem bản đồ truyền `latitude`, `longitude`, `destinationName` vào `MapFragment` (`nav_graph.xml`).  
**Bước 2.** `MapFragment`: cấu hình OSMDroid, `GeoPoint(lat,lng)`, `Marker` cho địa điểm; `Google Play services` **`FusedLocationProviderClient`** lấy **`lastLocation`** nếu quyền `ACCESS_FINE_LOCATION` được cấp (`MapFragment.kt`).  
**Bước 3.** Mở Google Maps chỉ đường/quán tính (`MapIntentHelper`).

**Ghi chú theo code:** Bản đồ **ưu tiên hiển thị theo tọa độ** của địa điểm; GPS dùng khi có quyền và khi **`lastLocation` khác null**. Nếu không có điểm xuất phát đã cache, chỉ đường có thể fallback sang intent Google Maps như trong `MapFragment` (toast “Chưa có GPS…”). Không chứng minh theo dõi vị trí liên tục trong nền.

**Gợi ý BPMN:** “BPMN – Bản đồ OSMDroid và Intent Google Maps”.  
**Lane:** Người dùng · ứng dụng Android (OSMDroid, GMS Location) · dịch vụ bản đồ OSM/Google (bên thứ ba).

---

### 2.2.4. Quy trình xem dự báo thời tiết

**Giới thiệu.** Thời tiết hiển thị trên màn chi tiết địa điểm.

**Bước 1.** `DestinationDetailFragment` gọi `WeatherService.getWeather(destination.city)`.  
**Bước 2.** **`WeatherService` gọi trực tiếp** Open-Meteo (URL `api.open-meteo.com`), map tên thành phố vào một **bảng tọa độ cố định** trong mã hoặc mặc định Hà Nội; parse JSON và cập nhật UI (`WeatherService.kt`).

**Ghi chú:** Giai đoạn mã không dùng Nominatim dù có gợi ý trong comment tài liệu; chức năng này **được định hướng trong comment nhưng chưa hiện thực hóa** trong nhánh đọc HTTP.

**Gợi ý BPMN:** “BPMN – Lấy thời tiết Open-Meteo”.  
**Lane:** Client Android · Open-Meteo (HTTP GET).

---

### 2.2.5. Quy trình tạo và quản lý lịch trình du lịch

**Giới thiệu.** Người dùng tạo danh sách lịch, xem chi tiết các ngày và mục, xóa lịch, thêm địa điểm vào lịch từ chi tiết.

**Bước 1.** `ItineraryFragment`: tạo mới (`createItinerary` → `POST /api/itineraries`), tải danh sách (`GET /api/itineraries`).  
**Bước 2.** `ItineraryDetailFragment`: tải `GET /api/itineraries/{id}`.  
**Bước 3.** Xóa: `DELETE /api/itineraries/{id}` (`ItineraryViewModel.deleteItinerary`).  
**Bước 4.** Thêm điểm: từ `DestinationDetailFragment` chọn lịch và gọi `ItineraryRepository.addDestination` → `POST /api/itineraries/{id}/items`.

**Hạn chế theo chứng cứ:** Endpoint **`PUT /api/itineraries/:id`** tồn tại và có khai báo Retrofit **`updateItinerary`**, song **không thấy** `ItineraryRepository`/màn hình gọi. Do đó chức năng **sửa tiêu đề/mốc thời gian qua PUT** được xem là **có một phần (API và contract client) nhưng chưa có luồng UI hoàn chỉnh trong mã Android đã khảo sát**.

**Gợi ý BPMN:** “BPMN – Vòng đời lịch trình”.  
**Lane:** Người dùng Android · REST `/api/itineraries*` · DB (`itineraries`, `itinerary_days`, `itinerary_items`).

---

### 2.2.6. Quy trình gợi ý lịch trình bằng AI/RAG

**Giới thiệu.** Có hai hướng chính: (a) **`/api/ai/suggest-itinerary`** tạo lịch và lưu (pipeline Node + có thể gọi RAG/`AI_MODEL_URL`); (b) luồng **preview/phương án AI** và tạo từ lựa chọn.

**Luồng (b) điển hình trong Android.**

**Bước 1.** `AIItineraryRequestFragment` thu thập thông tin và gọi `ItineraryViewModel.getAIItineraryOptions` → `POST /api/ai/itinerary-options`.  
**Bước 2.** Node `ai.controller.js` → `requestItineraryOptions` trong `services/ai.service.js` → **`ragPostJson("/ai/itinerary-options", ...)`** sang FastAPI.  
**Bước 3.** FastAPI (router trong `backend/rag/app/ai_itinerary.py` được include trong `main.py`) xử lý và trả cấu trúc các “option” Tour.  
**Bước 4.** `AIItineraryOptionsFragment`, `AIItineraryEditorFragment` điều chỉnh; `createItineraryFromOption` → `POST /api/itineraries/create-from-option`.

**Luồng preview/chọn điểm (tóm tắt).**  
`POST /api/ai/itinerary-preview` (proxy **`/ai/itinerary-preview`** trên FastAPI); sau đó người dùng có thể `POST /api/itineraries/create-from-selection`.

**Luồng (a)** `AISuggestFragment` / repository `suggestItinerary`: `POST /api/ai/suggest-itinerary` (`ai.controller.js` + `generateSuggestItineraryAiResult` — truy danh mục từ MySQL, có **fallback sang `ragPostJson("/rag/chat", ...)`** khi không có `AI_MODEL_URL` hoặc lỗi).

**Gợi ý BPMN:** “BPMN – AI gợi ý lịch (Android → Node → FastAPI → DB địa điểm)”.  
**Lane:** Android · Node `/api/ai/*`, `/api/itineraries/create-from-*` · FastAPI RAG · MySQL **`destinations`**.

---

### 2.2.7. Quy trình tương tác Chatbot AI tư vấn du lịch

**Giới thiệu.** Người dùng nhập tin nhắn; Android chuẩn hóa ngữ nghĩa qua **`POST /api/ai/chat`** (payload map `message`), sau đó gọi RAG và có bước kiểm/“repair” tiếp tục dùng cùng endpoint phụ hoặc RAG.

**Bước 1.** `ChatbotFragment` → `ChatbotViewModel.sendMessage`.  
**Bước 2.** `GeminiService.prepareRagQuery` gửi **`api.chatFallback` → `/api/ai/chat`** để cố nhận JSON chuẩn hóa truy vấn (prompt trong `GeminiService.kt` có ngữ cảnh “UnuTrip”).  
**Bước 3.** `RagService.chat` gửi **`POST /api/ai/rag-chat`** với JSON `ChatRequest` (`message`, `top_k`, `mode`, `targetProvince`, `targetCity`). Node `ragChat` trong `ai.controller.js` → **`requestRagChatSimple` → `ragPostJson("/rag/chat/simple", payload)`**.  
**Bước 4.** FastAPI `services/rag_service.py`: `rag_chat_simple` → `RagPipeline.run` → JSON trả **`answer`, `places`, `warnings`, …, `model_used`, `fallback_used`, `runtime_mode`**. Node chuẩn hóa và trả về HTTP 200 hoặc 502.

**Luồng dự phòng:** Nếu RAG không thành công trong ViewModel → `GeminiService.fallbackChat` lại gọi **`/api/ai/chat`** (`ai.controller.js`: ưu tiên `AI_MODEL_URL` khi có, không thì **`requestRagChatFallbackForAiChat`** cũng dùng `/rag/chat/simple`).

**Gợi ý BPMN:** “BPMN – Chatbot RAG với tiền xử lý /api/chat”.  
**Lane:** Người dùng Android · Node `/api/ai/chat`, `/api/ai/rag-chat` · FastAPI RAG.

---

### 2.2.8. Quy trình đánh giá địa điểm du lịch

**Giới thiệu.** Xem danh sách đánh giá và gửi đánh giá mới (điểm số, nội dung; có multipart ảnh).

**Bước 1.** `DestinationDetailFragment` tải `GET /api/destinations/:id/reviews`.  
**Bước 2.** Người dùng mở `ReviewDialog`; `DestinationViewModel.postReview` có thể dùng `POST /api/reviews` JSON hoặc multipart (`ApiService.kt` có cả hai).  
**Bước 3.** Backend `reviews.routes.js` và controller lưu bảng **`reviews`**.

**Gợi ý BPMN:** “BPMN – Đánh giá địa điểm”.  
**Lane:** Android · REST reviews · DB `reviews`.

---

### 2.2.9. Quy trình quản lý dữ liệu của quản trị viên

**Giới thiệu.** Hoạt động **phía máy chủ** tại **`/admin`**, không nhúng trong APK Android đã khảo sát. Đăng ký trong `admin/index.js`: dashboard người dùng đích, đích đến, hệ thống, báo cáo AI/RAG, v.v. Xác thực HTTP Basic chỉ có hiệu lực khi đặt **đầy đủ** `ADMIN_BASIC_USER` và `ADMIN_BASIC_PASS`; nếu thiếu, middleware chỉ **cảnh báo và cho qua** (chế độ dev mặc định trong code).

**Bước 1.** Trình duyệt/`curl` vào **`/admin/...`** (chi tiết từng route nằm trong `dashboard.admin.routes.js`, `users.admin.routes.js`, …).  
**Bước 2.** Nếu bật Basic Auth, gửi header `Authorization: Basic ...`; so khớp an toàn thời gian (hằng số-so sánh trong `adminAuth.middleware.js`).  
**Bước 3.** Một số thao tác admin có thể gọi tiếp FastAPI qua **`ragAdminJsonHeaders`** (file `ragClient.js`).

**Gợi ý BPMN:** “BPMN – Quản trị web UnuTrip (Node `/admin`).  
**Lane:** Quản trị viên · Trình duyệt HTTP · Node Express `/admin` · MySQL và/hoặc FastAPI admin.

---

## 2.3. Yêu cầu hệ thống

### 2.3.1. Yêu cầu chức năng chi tiết

| Mã yêu cầu | Tên chức năng | Mô tả chi tiết | Căn cứ từ mã nguồn |
| :--- | :--- | :--- | :--- |
| FR01 | Đăng ký tài khoản | Nhập họ tên, email, mật khẩu, điện thoại tuỳ chọn; nhận JWT. | Android `AuthActivity.kt` (`register`), `POST auth/register`; `auth.controller.js` |
| FR02 | Đăng nhập | Email/mật khẩu; nhận JWT. | `AuthActivity.kt`; `POST auth/login`; `auth.controller.js`; `signToken` `auth.js` |
| FR03 | Quản lý tài khoản / hồ sơ | Xem/stats trong `ProfileFragment` (`GET users/stats`), sửa tên/SĐT (`PUT users/profile`), tải ảnh (`POST users/avatar`). **`GET users/profile` và `PUT users/preferences`** khai báo Retrofit **`ApiService.kt`** nhưng **chưa thấy** màn Kotlin gọi chúng. | `ProfileFragment.kt`, `ApiService.kt`, `users.routes.js` |
| FR04 | Tìm kiếm địa điểm | Tham số `search`, `province`, `category`. | `GET /api/destinations`; `DestinationRepository.getDestinations` |
| FR05 | Xem danh sách địa điểm | Danh sách phân trang; lọc; mục nổi bật; “gần bạn”. | `HomeFragment.kt`, `HomeViewModel.kt`, `DestinationListFragment`; `featured`, `nearby` |
| FR06 | Xem chi tiết địa điểm | Thông tin, ảnh, giờ/phí/tag. | `DestinationDetailFragment.kt`; `GET /api/destinations/:id` |
| FR07 | Xem bản đồ địa điểm | OSMDroid + marker; có GPS khi được quyền. | `MapFragment.kt`; `nav_graph.xml` |
| FR08 | Xem thời tiết | Dự báo qua Open-Meteo trên chi tiết. | `WeatherService.kt`; `DestinationDetailFragment.loadWeather` |
| FR09 | Đánh giá địa điểm | Xem và gửi review. | `DestinationDetailFragment`, `DestinationViewModel`; `reviews.routes.js`, bảng `reviews` |
| FR10 | Quản lý yêu thích | Thêm/bỏ yêu thích; danh sách qua điều hướng favorites. | `DestinationDetailFragment` (`toggleFavorite`); `users/favorites` trong `ApiService.kt`; `favorites.routes.js` |
| FR11 | Tạo và quản lý lịch trình | Tạo, xóa, xem chi tiết, thêm điểm từ đích đến. **Sửa PUT chưa thấy dùng từ Android.** | `ItineraryFragment`, `ItineraryDetailFragment`, `DestinationDetailFragment`; `itineraries.routes.js` |
| FR12 | Gợi ý lịch trình AI/RAG | `/ai/suggest-itinerary`, preview/options và lưu từ AI. | `AISuggestFragment`, `AIItinerary*Fragment`, `ItineraryViewModel`; `ai.routes.js`; RAG FastAPI |
| FR13 | Chatbot tư vấn du lịch | Hội thoại với routing RAG và tiền xử lý qua `/ai/chat`. | `ChatbotFragment`, `ChatbotViewModel`; `GeminiService.kt`, `RagService.kt` |
| FR14 | Quản lý dữ liệu / admin | Giao diện `/admin`; Basic Auth tuỳ cấu hình. | `backend/nodejs/src/admin/*`, `adminAuth.middleware.js`, `app.js` |
| FR15 | Cung cấp Web API cho Android | REST JSON dưới `/api`; CORS và Helmet trong `createApp`. | `app.js`, `routes/index.js` |

---

### 2.3.2. Yêu cầu phi chức năng chi tiết

| Mã | Loại yêu cầu | Mô tả chi tiết | Căn cứ/ghi chú |
| :--- | :--- | :--- | :--- |
| NFR01 | Hiệu năng | Cache HTTP OkHttp trong `RetrofitClient.install`; Node có timeout và retry có giới hạn cho RAG (`ragUpstream.js`). | `RetrofitClient.kt`, `ragUpstream.js` |
| NFR02 | Bảo mật | JWT `Authorization Bearer` cho `/api`; Helmet CSP; bcrypt mật khẩu. | `auth.js`, `auth.controller.js`, `app.js` |
| NFR03 | Tính chính xác dữ liệu | Dữ liệu địa điểm lưu trong `destinations` và các bảng mở rộng trong migration khi được áp dụng. Đánh giá/đếm trong review. | `database.sql`, migration |
| NFR04 | Tính khả dụng | Health và ready (trong backend Node có module health; có tuỳ chọn bỏ qua probe RAG). | `registerHealthRoutes`, `env.js` `HEALTHCHECK_SKIP_RAG` |
| NFR05 | Khả năng mở rộng | Tách backend Node và dịch vụ RAG; cấu hình `RAG_BASE_URL`. | `env.js`, `ragClient.js` |
| NFR06 | Giao diện dễ sử dụng | Material 3 themes; Navigation component. | `themes.xml`, `nav_graph.xml` |
| NFR07 | Tương thích Android | `minSdk 26`, `compileSdk/` `targetSdk` 34 trong `build.gradle`. | `app/build.gradle` |
| NFR08 | Khả năng bảo trì | Modular routes Node (auth, destinations, ai, …); RAG chia `services`, `routers`. | Cấu trúc `backend/nodejs/src` |
| NFR09 | An toàn cấu hình env/API key | `dotenv` gốc dự án; `JWT_SECRET`, `RAG_INTERNAL_API_KEY`, `AI_MODEL_URL`; **mặc định JWT dev** được khai báo trong code (production phải đổi). | `env.js` `DEFAULT_JWT_SECRET`, `assertSafeProductionConfig`; `gemini`/RAG trong `backend/rag/core/config.py` |
| NFR10 | Xử lý lỗi | Chuẩn hóa lời đáp lỗi RAG (`normalizeRagChatSimpleResponse`), HTTP 502 từ `ragChat`; ViewModel báo lỗi trong `ChatbotViewModel`; thời tiết `Resource.Error`. | `ai.service.js`, `ChatbotViewModel.kt`, `WeatherService.kt` |
| NFR11 | Khả năng kiểm thử API | Thư mục `backend/nodejs/tests` (auth, rag upstream, ai-rag-chat, …). | `backend/nodejs/tests/` |
| NFR12 | Khả năng triển khai localhost/dev | `BASE_URL` mặc định emulator `http://10.0.2.2:3000/api/` trong `build.gradle`; RAG URL mặc định loopback `:8001`. | `build.gradle`, `env.js`, `backend/rag` |

---

## 2.4. Các chức năng của hệ thống

### 2.4.1. Đối với người dùng

Người dùng UNU Trip được hỗ trợ các nhóm chức năng sau, **theo chứng cứ Đã lập**.

- **Tài khoản:** đăng ký, đăng nhập qua một activity kết hợp (`AuthActivity`); lưu phiên cục bộ.  
- **Khám phá địa điểm:** danh sách có lọc/tìm, điểm nổi bật, khu vực gần (nếu cấp quyền và lấy được tọa độ), điều hướng tới chi tiết.  
- **Chi tiết địa điểm:** mô tả, ảnh, đánh giá tổng hợp, thẻ, yêu thích, thêm vào một lịch trình có sẵn, mở bản đồ nội bộ/OSM, và thẻ thời tiết lấy từ Open-Meteo phía máy khách.  
- **Đánh giá:** xem và gửi đánh giá (có hỗ trợ kèm ảnh theo Retrofit/backend).  
- **Lịch trình:** tạo, xem chi tiết, xóa, thêm điểm; các luồng AI để sinh/phương án và lưu (xem các fragment AI và `AISuggestFragment`).  
- **Trợ lý trò chuyện:** màn **Trợ lý AI** với luồng RAG/phụ qua `/ai/chat`.

[Chèn Hình 2.2. Luồng chức năng người dùng trên UNU Trip Android]

---

### 2.4.2. Đối với quản trị viên và hệ thống quản trị

Hệ không cung cấp ứng dụng riêng trên điện thoại cho admin. **Quản trị được thực hiện qua đường dẫn `/admin`** trên máy chủ Node, có nhiều nhóm chức năng được đăng ký trong `admin/index.js` (dashboard, người dùng, đích đến, hệ thống, báo cáo RAG/AI). Xác thực **HTTP Basic** là **tuỳ chọn** và mặc định trong mã có thể **mở** nếu chưa cấu biến môi trường (xem middleware).

---

### 2.4.3. Đối với phân hệ AI/RAG

FastAPI (**“UnuTrip RAG”** trong `main.py`) đảm nhận:

- **`/rag/chat/simple` và `/rag/chat`**: truy xuất (RAG) và sinh câu trả lời; trả **`places`** và metadata (`model_used`, `fallback_used`, `runtime_mode` trong payload). Service bọc **`RagPipeline`** (`services/rag_service.py`).  
- **Itinerary AI** qua các route include `ai_itinerary` (preview, options…) được Node proxy với **`ragPostJson("/ai/itinerary-…")`**.  
- **Chế độ chạy:** `AI_RUNTIME_MODE` mặc định **`mock`** trong `backend/rag/core/config.py`; **`ENABLE_GEMINI`** mặc định tắt; pipeline có nhánh **`mock`** (`rag/pipeline.py`). Trạng thái Gemini thực **phụ thuộc biến môi trường và quá trình khởi tạo**, không được suy luận “luôn bật” từ mặc định.  
- **Fallback/mock:** Chuỗi trả **`model_used`** có thể là `"mock"`; pipeline có **`_build_mock_answer`**.

Phía Node:

- **`/api/ai/chat`**: có thể gọi dịch vụ cụ bộ **`AI_MODEL_URL`** (POST JSON `{ message }` → `{ answer }`), nếu không cấu hình thì chuyển sang **RAG fallback** qua **`/rag/chat/simple`**.

---

### 2.4.4. Yêu cầu đặt ra đối với vận hành

- **API ổn định:** JSON rõ ràng; mã HTTP chuẩn (401 khi JWT thiếu/sai trong `authMiddleware`).  
- **Cơ sở dữ liệu:** bả lõi `database.sql`; migration v2 là lớp bổ sung khi triển khai.  
- **Android hiển thị và chịu lỗi:** pattern `Resource` và thông báo Toast trong nhiều fragment.  
- **RAG và AI:** Chuẩn hóa hợp đồng phản hồi trong Node; có log cảnh báo khi contract lệch.  
- **Lỗi dịch vụ ngoài:** Thời tiết và Open-Meteo có `try/catch`; bản đồ có fallback intent; Chatbot có nhánh báo RAG không gọi được.

---

## 2.5. Phân tích hệ thống

### 2.5.1. Phân tích tổng quan kiến trúc

Hình thành Kiến trúc ba tầng tách biệt:

1. **Tầng trình diễn (Android):** ứng dụng Kotlin, Jetpack Navigation, ViewModel + LiveData trong nhiều màn (`ui/`), gọi HTTP qua **Retrofit + Gson** và **OkHttp cache** (`RetrofitClient.kt`). BASE URL cấu hình `BuildConfig.BASE_URL`.

2. **Tầng ứng dụng và cấp REST (Node.js Express):** ứng dụng được dựng trong `createApp()`, mount **`/api`** (`buildRouter`) và **`/admin`** (`buildAdminRouter`). Middleware: `authMiddleware`, `adminAuthMiddleware`, xử lý lỗi chuẩn.

3. **Tầng dữ liệu (MySQL):** bảng nghiệp vụ lõi và migration mở rộng như **`app_places`**, **`place_id_map`**, **`rag_knowledge_base`**, **`place_images`** (khi chạy migration).

4. **Tầng trí tuệ nhân tạo (FastAPI):** có CORS và middleware key nội bộ (`InternalApiKeyMiddleware` trong `middleware.py`). Node gọi bằng **`fetch`** với header `X-RAG-Internal-Key` khi cấu hình (`ragJsonHeaders`).

**Luồng tổng quát (tóm lược ASCII):**

```
[UNU Trip Android] --Retrofit JWT--> [Node /api/*] --mysql2/repo--> [MySQL]
       |                                                       |
       |                                    ragPostJson -----> [FastAPI RAG]
       |
       +---HTTPS direct-----------------> [Open-Meteo forecast API]
```

[Chèn Hình 2.3. Kiến trúc vật lý và logical UNU Trip]

---

### 2.5.2. Luồng xử lý dữ liệu Android ↔ Backend ↔ Database

Ví dụ **lấy danh sách địa điểm:**  
Android gửi `GET {BASE_URL}destinations?page=&limit=&search=&province=&category=` với header `Authorization: Bearer <JWT>`.  
Node `listDestinations` truy MySQL và trả JSON **`{ success, data: [...], total, page, limit }`** (mapping khớp `DestinationResponse`).  
Ví dụ **chi tiết:** `GET /destinations/:id` trả **`{ success, data: Destination }`**.

**Ví lịch:** `GET /itineraries` trả bọc trong `success` và mảng `data` các `Itinerary` có `days/items` (theo serializer backend).

Người dùng không kết nối MySQL trực tiếp từ APK; chỉ qua HTTPS REST.

---

### 2.5.3. Phân tích luồng xử lý AI/RAG

Điểm neo kỹ thuật:

- **`ragUpstream.ragPostJson(path, body, traceHeaders)`** ghép **`RAG_BASE_URL` + path** (ví dụ `/rag/chat/simple`, `/ai/itinerary-options`). Timeout và số lần thử từ `env.js`.

- **`requestRagChatSimple`** và **`normalizeRagChatSimpleResponse`** (`schemas/ragContract.js`) là lớp bảo đảm hình dạng phản hồi mong đợi để route trả nhất quán.

Trên FastAPI **`RagService.rag_chat_simple`** cố định hóa danh sách `places` (field `place_id`, `name`, điểm số RAG…) trước khi hoàn trả.

**Gemini/mock:** Theo `rag/pipeline.py` và **`core/config.py`**, **`AI_RUNTIME_MODE` mặc định là `mock`**, **`ENABLE_GEMINI`** mặc định `false`; ngoài runtime còn phụ thuộc **`GEMINI_API_KEY`** và trạng thái **`GeminiGenerator`**. Chi tiết cụ thể môi trường triển khai của tác giả luôn là **ngoài phạm vi suy luận từ mặc định trong code**.

---

### 2.5.4. Phân tích luồng chatbot

Chatbot không gọi RAG hoàn toàn độc lập mà kết hợp **`/api/ai/chat`** (chuẩn hóa truy vấn, và fallback) và **`/api/ai/rag-chat`** (RAG có `places`).

Đoạn **`ChatTripDayParser`** hỗ trợ chiết xuất số ngày từ văn bản và hiển thị gợi ý tạo lịch trong UI (gom trong `ChatbotViewModel`). Phần **`GeminiService.repairRagAnswer` / validate** trong file `GeminiService.kt` bổ sung lớp chất lượng phản hồi hiển thị cho người dùng.

---

### 2.5.5. Luồng bản đồ và thời tiết

- **Bản đồ:** OSMDroid tải tile Mapnik trong `MapFragment`; **GPS** qua fused location chỉ là bổ sung vị trí người dùng.  
- **Thời tiết:** **`WeatherService`** dùng `java.net.URL` gọi **Open-Meteo** và map mã (`weather_code`). **Không** đi Node.

---

### 2.5.6. Phân tích bảo mật hệ thống

- **JWT:** Ký và xác minh trong `auth.js`; payload chứa `userId`, `email` (minimal). Middleware từ chối 401 khi Bearer thiếu/hỏng token.  
- **Mật khẩu:** bcrypt hash khi đăng ký; so khớp khi đăng nhập.  
- **dotenv:** nạp từ gốc dự án (`env.js`).  
- **Tách DB:** chỉ máy chủ Node + connection pool chứ không phơi vào APK.  
- **Validate input:** Dùng `zod` trong nhiều controller (`auth.controller.js`, `ai.controller.js`).  
- **Admin:** Basic Auth có thể bật; nếu **không cấu hình**, đường `/admin` vẫn “mở” theo middleware (ghi log cảnh báo) — là **điểm rủi ro môi trường triển khai**.  
- **RAG Internal key:** có thể bắt buộc ở phía FastAPI qua **`InternalApiKeyMiddleware`** và header **`X-RAG-Internal-Key`** (Node và RAG chia sẻ cấu hình). Chi tiết bắt buộc tùy môi trường.  
- **Helmet CSP:** chỉ báo các nguồn script/style cho phần `/admin`/web.

---

## 2.6. Các biểu đồ

### 2.6.1. Biểu đồ Use Case tổng quát

**Tác nhân:** Người dùng ứng dụng UNU Trip; Quản trị viên máy chủ (trình duyệt `/admin`); Dịch vụ nền FastAPI RAG; Dịch vụ Open-Meteo; Dịch vụ Tile OSM / Google Maps (intent).

**Use Case cấp cao:** Đăng ký; Đăng nhập; Tìm/xem địa điểm; Đánh giá; Quản yêu thích; Quản lý lịch trình; Gợi ý AI/RAG; Trò chuyện Chatbot; Xem thời tiết; Xem bản đồ; Quản trị dữ liệu (đường `/admin`).  
**quan hệ `<<include>>` gợi ý:** Tất cả UC gọi API (trừ thời tiết trực tiếp) **include “Xác thực JWT”** sau khi đăng nhập.  
**`<<extend>>` gợi ý:** “Gợi ý AI RAG” **extend** “Tạo lịch trình” khi người dùng chọn luồng AI.

**Gợi ý đồ họa:** Một ellipse lớn “Hệ thống UNU Trip”, tác nhân hai bên Người dùng và Quản trị; phía dưới stereotype «external system» cho RAG, Open-Meteo, Maps.

---

#### 2.6.1.1. UC phân rã – Người dùng

Tìm theo danh mục; Tìm theo từ khóa; Lọc tỉnh; Xem nổi bật; Xem “gần bạn”; Mở chi tiết địa điểm; Bật yêu thích; Gửi review; Danh sách yêu thích; Tạo lịch; Xóa lịch; Xem chi tiết lịch; Thêm địa điểm vào ngày; Mở bản đồ nội bộ; Mở Google Maps chỉ đường; Gọi trợ lý AI; Dùng suggest-itinerary; Dùng tour AI đa phương án; Lưu từ lựa chọn AI.

---

#### 2.6.1.2. UC phân rã – Quản trị viên

**Chỉ ghi các UC có chứng cứ module admin:** Theo `admin/index.js`, có nhóm Dashboard, Người dùng đích, Đích đến, Hệ thống, báo cáo RAG/AI. UC chi tiết từng form HTML nên mở đúng file `*.admin.routes.js` khi vẽ. Nếu môi trường chưa bật Basic Auth, ghi chú “Use case vẫn tồn tại trong hệ nhưng mức bảo vệ phụ thuộc env”.

---

#### 2.6.1.3. UC tương tác AI/RAG

**Theo chứng cứ:** Nhập câu/truy vấn; Chuẩn hoá (`/ai/chat`); Truy xuất dữ liệu địa điểm (trong pipeline RAG); Sinh hoặc chọn chiến lược mock/Gemini; Gợi ý địa điểm theo embedding/BM25 (chi tiết nội bộ pipeline); Chatbot nhận `answer + places`; Gợi ý itinerary preview/options và tạo bản ghi MySQL sau khi lưu Node.

---

## 2.7. Đặc tả Use Case

Định dạng sau lặp lại **một bảng** cho mỗi UC theo khung báo cáo mẫu.

---

### UC-01 Đăng ký tài khoản

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Đăng ký tài khoản |
| Mô tả | Người dùng tạo mới người dùng và nhận JWT để vào các chức năng được bảo vệ |
| Tác nhân chính | Người dùng UNU Trip |
| Tác nhân phụ | Hệ Node API · MySQL |
| Điều kiện tiên quyết | Ứng dụng mở; kết nối tới máy chủ `{BASE_URL}` |
| Luồng chính | 1. Mở AuthActivity.<br>2. Chọn chế độ đăng ký và điền form.<br>3. Retrofit POST `/auth/register`.<br>4. Backend tạo bản ghi `users`.<br>5. Token trả về lưu `SessionManager` và vào Main. |
| Luồng thay thế | 4a. Email trùng → HTTP 400 “Email đã tồn tại”; hiển thị lỗi từ `AuthViewModel`.<br/>3a. Mất mạng → Resource.Error trong repository. |
| Dữ liệu liên quan | Bảng `users`, DTO đăng ký trong `Models.kt`, schema Zod trong `auth.controller.js` |
| Hậu điều kiện | `SessionManager` chứa `token` và `User` cục bộ |
| Biểu đồ liên quan | [Chèn Hình 2.x. BPMN đăng ký] · Sequence mục 2.8.1 |
| Căn cứ trong mã nguồn | `AuthActivity.kt`; `POST auth/register` `ApiService.kt`; `auth.controller.js`; `database.sql` bảng `users` |

---

### UC-02 Đăng nhập

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Đăng nhập |
| Mô tả | Xác minh Email/mật khẩu, cấp JWT |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | Node API · JWT |
| Điều kiện tiên quyết | Người dùng có tài khoản trong `users` |
| Luồng chính | 1. Chế độ đăng nhập trong AuthActivity.<br>2. POST `/auth/login`.<br>3. So bcrypt; ký JWT; lưu session. |
| Luồng thay thế | Sai mật khẩu → 401; hiển thị thông điệp tiếng Việt trong controller |
| Dữ liệu liên quan | JWT payload `userId`, `email` |
| Hậu điều kiện | Token hợp lệ dùng cho các API Bearer |
| Biểu đồ liên quan | [Chèn Hình 2.x. BPMN đăng nhập] · 2.8.2 |
| Căn cứ trong mã nguồn | `auth.controller.js`; `signToken` `auth.js`; `login` Retrofit |

---

### UC-03 Tìm kiếm địa điểm du lịch

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Tìm kiếm / lọc địa điểm |
| Mô tả | Người dùng truy danh mục theo điều kiện truy vấn |
| Tác nhân chính | Người dùng đã đăng nhập (JWT trong các luồng hiện tại của API đích đến) |
| Tác nhân phụ | Node API · DB |
| Điều kiện tiên quyết | Phiên JWT còn hạn |
| Luồng chính | 1. Mở `DestinationListFragment` hoặc từ `HomeFragment`.<br>2. `GET /destinations?search=…&province=…&category=…`.<br>3. Cập nhật RecyclerView. |
| Luồng thay thế | Lỗi mạng / 401 → báo không tải được |
| Dữ liệu liên quan | Danh `Destination`, trường `category` theo tập mã trong `Models.kt` |
| Biểu đồ liên quan | 2.8.3 |
| Căn cứ trong mã nguồn | `destinations.routes.js`; `DestinationRepository.getDestinations` |

---

### UC-04 Xem chi tiết địa điểm

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Xem chi tiết địa điểm |
| Mô tả | Hiển thị một địa điểm đầy đủ và nạp đánh giá/thời tiết |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | REST Node · Open-Meteo |
| Tiên quyết | Biết `destinationId` điều hướng |
| Luồng chính | 1. `GET /destinations/:id`<br>2. `GET /destinations/:id/reviews`<br>3. Gọi `WeatherService`. |
| Thay thế | Thành phố không map trong `WeatherService.cityCoords` → mặc định trở **Hà Nội** theo đoạn `?: Pair(21.0285,...)` (**hạn chế độ chính xác theo thành**). |
| Biểu đồ liên quan | 2.8.4 |
| Căn cứ trong mã nguồn | `DestinationDetailFragment.kt`, `WeatherService.kt` |

---

### UC-05 Xem bản đồ địa điểm

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Xem bản đồ và vị trí địa điểm |
| Mô tả | Zoom OSM và marker điểm; GPS nếu cho phép |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | OSMDroid · GMS fused location · Maps intent |
| Tiên quyết | Nav tới MapFragment có `lat/lng` |
| Luồng chính | Hiển thị tile + marker đích; Request quyền; `lastLocation` success → marker “Bạn đang ở đây”. |
| Thay thế | `lastLocation == null` → Toast “Chưa lấy được vị trí hiện tại”. |
| Biểu đồ liên quan | 2.8.5 |
| Căn cứ trong mã nguồn | `MapFragment.kt` |

---

### UC-06 Xem thời tiết

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Xem thời tiết khu vực liên quan địa điểm |
| Mô tả | Hiển thị nền và dự báo vài ngày |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | Open-Meteo HTTPS |
| Luồng chính | `loadWeather(city)` khi có destination |
| Thay thế | Lỗi mạng / JSON → ẩn card thời tiết |
| Biểu đồ liên quan | 2.8.6 |
| Căn cứ trong mã nguồn | `WeatherService.kt`; `DestinationDetailFragment` |

---

### UC-07 Quản lý lịch trình

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Quản lý lịch trình (create/list/detail/delete/add item; **sửa PUT chưa đồng nhất**) |
| Mô tả | Theo dõi kế hoạch nhiều ngày với các `itinerary_items` |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | Node và DB itineraries |
| Luồng chính | Tạo, xóa, xem, thêm điểm từ DestinationDetail như các bước mục 2.2.5 |
| Thay thế | **Sửa metadata lịch** qua `PUT /api/itineraries/:id` được khai báo nhưng **chưa thấy Repository Android gọi** |
| Biểu đồ liên quan | 2.8.7 |
| Căn cứ trong mã nguồn | `ItineraryFragment.kt`, `ItineraryDetailFragment.kt`, `itineraries.routes.js` |

---

### UC-08 Gợi ý lịch trình bằng AI/RAG

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Gợi ý lịch AI/RAG |
| Mô tả | Preview/options/suggest và lưu thành itinerary |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | Node · FastAPI RAG · DB |
| Luồng chính | Nhập tham số → `previewItinerary` / `getAIItineraryOptions` hoặc `suggestItinerary` → lưu bằng endpoint `create-from-*` hoặc service persist suggest |
| Thay thế | 502 FastAPI trong `ragChat`/preview/options |
| Biểu đồ liên quan | 2.8.8 |
| Căn cứ trong mã nguồn | `ItineraryViewModel.kt`, các fragment AI; `ai.controller.js`; `backend/rag` |

---

### UC-09 Tương tác Chatbot AI

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Chatbot tư vấn du lịch |
| Mô tả | Nhập văn bản và nhận câu trả lời kèm `places` (RAG), có lớp chuẩn hóa/kiểm qua `/ai/chat` |
| Tác nhân chính | Người dùng |
| Tác nhân phụ | Node `ai` và RAG FastAPI |
| Luồng chính | `ChatbotViewModel.getFinalChatbotResult`: prepare → rag → validate/repair → hiển thị |
| Thay thế | RAG lỗi → `fallbackChat` (`/api/ai/chat`) |
| Biểu đồ liên quan | 2.8.9 |
| Căn cứ trong mã nguồn | `ChatbotFragment`; `ChatbotViewModel.kt`; `RagService.kt`; `GeminiService.kt`; `ai.controller.js` |

---

### UC-10 Đánh giá địa điểm

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Đánh giá địa điểm |
| Mô tả | Viết và gửi nhận xét và đánh giá sao; xem các review trước |
| Luồng chính | `GET reviews` → dialog → POST review |
| Thay thế | Multipart có giới hạn số ảnh trong route Node |
| Biểu đồ liên quan | 2.8.10 |
| Căn cứ trong mã nguồn | `DestinationDetailFragment`; `reviews.routes.js` |

---

### UC-11 Lưu/xóa yêu thích

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Đánh dấu và bỏ yêu thích |
| Luồng chính | Toggle qua FAB trên DestinationDetail và API `DELETE/POST users/favorites` như Retrofit định nghĩa |
| Căn cứ trong mã | `fabFavorite`; `FavoriteRequest`; `favorites.routes.js` và controller |

---

### UC-12 Quản lý dữ liệu / Admin

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Quản trị dữ liệu qua máy chủ `/admin` |
| Mô tả | Dashboard và module quản trị HTML do Node render/route |
| Tác nhân chính | Quản trị viên · Trình duyệt HTTP |
| Thay thế | Basic Auth tắt nếu thiếu env → chức năng về mặt code vẫn truy cập được |
| Căn cứ trong mã | `admin/index.js`, `admin/*.admin.routes.js`, `adminAuth.middleware.js`, `app.js` mount `/admin` |

---

## 2.8. Biểu đồ trình tự (mô tả văn bản để vẽ lại)

Định danh các thực thể: **Người dùng**, **Fragment/Activity**, **ViewModel**, **Retrofit/API Service**, **Node Controller**, **Service/Repository**, **MySQL**, **FastAPI RagService**, (**OpenMeteo**) khi thích hợp.

### 2.8.1. Đăng ký
1. Người dùng nhấn gửi trên AuthActivity.  
2. AuthViewModel → AuthRepository.`register(...)`.  
3. HTTP `POST /api/auth/register` JSON `{fullName,email,password,phone}`.  
4. auth.controller **`createUser`** ghi **`users`** (bcrypt).  
5. `signToken`; HTTP 200 JSON `{success,token,user}`.  
6. SessionManager lưu và chuyển MainActivity.

### 2.8.2. Đăng nhập
1–3 thay **`POST /api/auth/login`**.  
4. **`getUserByEmailWithPasswordHash`** + bcrypt.  
5. Trả JWT; lưu session.

### 2.8.3. Tìm kiếm địa điểm
1. DestinationList/Home load.  
2. ViewModel gọi `GET /api/destinations`.  
3. destinations.controller truy vấn và trả `DestinationResponse`.

### 2.8.4. Chi tiết địa điểm
1. Điều hướng với `destinationId`.  
2. **`GET /api/destinations/:id`** rồi **`GET …/reviews`**.  
3. Coroutine **`WeatherService.getWeather`** tới api.open-meteo.com khác với các bước trước (không qua Node).

### 2.8.5. Xem bản đồ
1. Chuẩn bị MapFragment và OSMDroid.  
2. (Tuỳ) Fused location `lastLocation` → thêm Marker người dùng.

### 2.8.6. Xem thời tiết – sequence riêng
**Android** → HTTPS **GET Open-Meteo forecast** như trong `WeatherService` (latitude/longitude được suy luận từ danh `cityCoords`).

### 2.8.7. Quản lý lịch trình
1. **`GET /itineraries`** khi vào fragment.  
2. **`POST /itineraries`** tạo.  
3. **`DELETE /itineraries/:id`**.  
4. **`POST …/items`** sau chọn trong dialog DestinationDetail.

### 2.8.8. Gợi ý AI/RAG
1. Android `POST /api/ai/itinerary-options` (hoặc preview/suggest).  
2. Node `ragPostJson` → FastAPI `/ai/itinerary-options` (ưng với routing).  
3. Trả options/preview JSON.  
4. Android `POST /api/itineraries/create-from-option` hoặc tương đương → MySQL itineraries.

### 2.8.9. Chatbot
1. `GeminiService.prepareRagQuery` → `POST /api/ai/chat`.  
2. `RagService.chat` → `POST /api/ai/rag-chat`.  
3. Node `ragPostJson('/rag/chat/simple')`.  
4. FastAPI Rag pipeline trả `{answer, places, …}`.

### 2.8.10. Đánh giá
1. **`GET …/reviews`**.  
2. Dialog → **`POST /api/reviews`** (multipart tùy chọn đường dẫn).  
3. Lưu bảng `reviews`.

---

## 2.9. Biểu đồ hoạt động (Activity – mô tả)

Đối với **mỗi** quy trình: *bước tuần tự* và *điều kiện rẽ nhánh*.

### Đăng ký
Bắt đầu → điền form → có lỗi validate client? [có→quay]/[không] → POST → email tồn tại [có→báo lỗi]/[không] → trả JWT → lưu session → kết thúc.

### Đăng nhập
Bắt đầu → POST → bcrypt OK? [không→401]/[có→JWT]/ → lưu session → Main.

### Tìm kiếm địa điểm
Bắt đầu → nhập/thay đổi bộ lọc → GET list → có dữ liệu? → refresh adapter.

### Xem chi tiết
Bắt đầu → GET chi tiết + GET reviews → bind UI → có city? → gọi thời tiết → có lỗi? ẩn card.

### Tạo lịch trình (thủ công)
Dialog tiêu đề/ngày → POST create → tái load list.

### Gợi ý AI/RAG
Thu thập tham số → POST Node → có 502 FastAPI [có→báo AI service]/[không]/ → người dùng confirm option → POST create-from → kết.

### Chatbot
Nhập text → nhánh prepare `/ai/chat` → nhánh rag `/rag/chat` có places → validate trong client → không hợp lệ có thể re-query `/rag/chat` như trong ViewModel → nếu vẫn fail → nhánh fallback `/api/ai/chat` → đẩy lên RecyclerView tin nhắn.

### Đánh giá
Mở dialog → có ảnh? → POST multipart hay JSON một phần tùy `postReview`.

### Xem thời tiết
Trích city → ghép vào keyword map có sẵn? [không→dùng tọa độ mặc định] → đọc Open-Meteo.

### Xem bản đồ
Khởi tạo map → có quyền vị trí? [không→chỉ hiển thị điểm đích]/[có]/ → lastLocation có? [không→toast]/[có]/ → thêm overlay.

---

## 2.10. Biểu đồ lớp (theo chứng cứ trong mã)

Dưới đây liệt kê các “lớp” (Kotlin `data class` hoặc tương đương) **chính** có thể dùng khi vẽ class diagram. Node không dùng ORM entities rõ trong luận giải nhanh — DTO chuyển qua repositories.

| Lớp (Kotlin model) | Thuộc tính chính | Quan hệ | File căn cứ |
| :--- | :--- | :--- | :--- |
| `User` | `id`, `fullName`, `email`, `phone`, `avatar`, `preferences` | 1‑N logic với itineraries/reviews (qua DB) | `Models.kt` |
| `Destination` | `latitude`, `longitude`, `rating`, `images`, … | được tham chiếu trong reviews, favorites bằng `destinationId` | `Models.kt` |
| `Review` | `userId`, `destinationId`, `rating`, `comment`, … | assoc `User`, `Destination` | `Models.kt` |
| `FavoriteRequest` | `destinationId` | với Favorite API | `Models.kt` |
| `Itinerary` | `title`, dates, `days` | chứa `ItineraryDay[]` | `Models.kt` |
| `ItineraryDay` | `dayNumber`, `date` | chứa `ItineraryItem[]` | `Models.kt` |
| `ItineraryItem` | `destination`, `startTime`, `endTime` | tới một `Destination` | `Models.kt` |
| `ChatMessage`/`ChatRequest`/`ChatResponse` | `role`, `content`; `places` | với RagService.Chatbot flow | `Models.kt`, `ChatbotViewModel` |
| Các payload AI itinerary | `AIItineraryPreviewRequest`, `AIRecommendedDestination`, … | với các endpoint `/ai/itinerary-*` | `Models.kt` |
| `WeatherInfo`/`ForecastDay` | `temperature`, `forecast`… | chỉ phía OS (không có entity DB trong app client) | `Models.kt`; nguồn Open‑Meteo |

**Nếu cần lớp “Category” độc lập trong Android:** chỉ có **chuỗi mã (`category`)** trong `Destination` và logic map (`CategoryMapper.kt`) — **chưa thấy** class `Category` trong `Models.kt`.

**Phía RAG:** Python dùng Pydantic schema (`app/schemas.py`, `core/schemas.py`); không lặp ở đây chi tiết từng field.

---

## 2.11. Mô hình hóa cơ sở dữ liệu

| Tên bảng | Mục đích | Trường chính | Khóa chính | Khóa ngoại / quan hệ | File căn cứ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `users` | Người dùng ứng dụng | `email`, `password_hash`, … | `id` | tới itineraries, reviews, favorites | `backend/nodejs/database.sql` |
| `destinations` | Danh điểm du lịch lõi của app/API hiện tại | `name`, lat/lng, `category`, `images_json`, `rating`, … | `id` | reviews, favorites FK | `database.sql` |
| `favorites` | Người dùng‑địa điểm yêu thích | `user_id`, `destination_id` | PK ghép `(user_id, destination_id)` | FK tới users, destinations | `database.sql` |
| `reviews` | Đánh giá | `rating`, `comment`, `images_json`… | `id` | FK user, destination | `database.sql` |
| `itineraries` | Chuyến đi/ngày của user | tiêu đề, dates, budget | `id` | FK user | `database.sql` |
| `itinerary_days` | Ngày cụ thể trong chuyến | `day_number`, `date` | `id` | FK itinerary | `database.sql` |
| `itinerary_items` | Địa điểm trong ngày | `start_time`, `end_time`, … | `id` | FK day và destination | `database.sql` |
| `app_places` | Lược đồ địa điểm v2 (migration) | `place_key`, thuộc tính mở rộng AI-friendly | `id` UNIQUE `place_key` | – | `database/migrations/001_create_app_places.sql` |
| `place_id_map` | Ánh xạ khóa RAG/legacy → app_place | các cột rag/legacy và `place_key` | `id`; UNIQUE các khóa nghiệp vụ | FK `new_app_place_id→app_places` | `004_create_place_id_map.sql` |
| `rag_knowledge_base` | Nội dung tri thức RAG có cấu trúc | `content`, các trường địa lý/category | `id` | tham chiếu tùy dữ liệu | `002_create_rag_knowledge_base.sql` |
| `place_images` | Ảnh đa môi của địa điểm v2 | `image_url`, `is_primary`, `status` | `id` | FK `app_place_id` | `003_create_place_images.sql` |

[Chèn Hình 2.4. ER hoặc sơ đồ quan hệ lõi UNU Trip]

---

## 2.12. Nhận xét cuối chương

Chương hai đã phác thảo **hiện trạng và nhu cầu**, **chuỗi nghiệp vụ được xác nhận từ mã**, **danh yêu cầu chức năng và phi chức năng**, **đặc tả use case và hướng dẫn vẽ lại các biểu đồ** với chỉ dẫn cho **Android UNU Trip**, **Node API**, **MySQL**, **FastAPI RAG** và dịch vụ thời tiết. Nền phân tích này tạo cơ sở để sang **Chương 3 – Thiết kế chi tiết hệ thống** và chọn biểu đồ BPMN/UCD/sequence phù hợp báo cáo.

---

# CÁC THÔNG TIN CẦN XÁC NHẬN THÊM

Chúng các điểm **đã không kết luận tuyệt đối** khi chỉ đọc mã và cần quyết định triển khai thực tế của chủ đề luận hoặc môi trường thí nghiệm:

1. **Cập nhật lịch trình PUT:** Backend và Retrofit có `PUT /itineraries/{id}`, nhưng **không thấy** `ItineraryRepository`/UI gọi — cần xác nhận có kế hoạch bổ sung màn chỉnh sửa hay chỉ là dự phòng.

2. **Đăng xuất phía máy chủ:** `POST /api/auth/logout` định nghĩa trong Retrofit **`ApiService.kt`** nhưng **`ProfileFragment` chỉ `clearSession` cục bộ** và không gọi API logout — JWT vẫn có thể còn “hợp lệ” về phía máy chủ cho đến khi hết hạn (`JWT_EXPIRES_IN` trong `auth.js`). Cần nêu rõ thiết kế mong đợi trong luận (stateless không revoke vs cần danh sách đen).

3. **`GET /users/profile`, `PUT /users/preferences`:** Có trong `ApiService.kt` nhưng **không có** chỗ gọi rõ trong `ProfileFragment`; hồ sơ hiển thị chủ yếu từ **`SessionManager`**. Xác nhận chiến lược đồng bộ.

4. **Khóa `GEMINI_API_KEY` BuildConfig trong Android (`build.gradle`)** có **ghi nhận vào APK** trong cấu hình build nhưng **kotlin source không grep thấy sử dụng** BuildConfig GEMINI_API_KEY — cần rõ chủ đích (dự phòng, legacy, hay chỉ tái hiện tài liệu).

5. **Mô hình Gemini trên máy chủ chat:** **`/api/ai/chat`** phụ thuộc **`AI_MODEL_URL`** (nullable mặc định) để không treo chờ không cần thiết; khi không cấu, fallback RAG **`/rag/chat/simple`**. Cần mô tả chính xác trong luận: môi trường thử nghiệm đặt URL như thế nào.

6. **Thời tiết:** chỉ có map thành phố **cố định** trong **`WeatherService`**, chưa dùng Nominatim dù có gợi ý comment — với các thành chưa map, có **fallback Hà Nội** và có thể lệch thực tế địa lý của địa điểm.

7. **Admin:** **`/admin` mặc định có thể “mở”** khi không cấu `ADMIN_BASIC_*` — cần ghi trong luận rủi ro và checklist triển khai production (`assertSafeProductionConfig` đã ép `JWT_SECRET` khi NODE_ENV production).

8. **Bảng v2 trong `database/migrations`:** chứng minh lược đồ mới cho RAG/UnuTrip v2; cần xác nhận CSDL trong máy dự án của bạn **đã chạy** các migration và app Node/RAG có **đang đọc** `destinations` cũ, `rag_places`, hay đã migrate sang **`app_places`** (ngoài khả năng kết luận tại đây mà chỉ căn cứ các file và comment repository).

9. **RAG Gemini vs mock trong môi trường của bạn:** mặc định **`AI_RUNTIME_MODE=mock`** và **`ENABLE_GEMINI=false`**; cần bạn báo `.env` thực để luận mô tả đúng hành vi.

10. **Weather** xác nhận lại: **Android trực tiếp**, không có proxy backend UNU Trip trong build hiện tại.

