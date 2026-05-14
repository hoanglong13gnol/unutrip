# Đầu vào báo cáo: Dashboard Admin — mục RAG AI (giám sát FastAPI RAG)

Tài liệu phân tích **dựa trên mã nguồn** trong repo UNU Trip (`backend/nodejs/src/admin/` và `backend/rag/app/routers/`). Không kết luận “Gemini đang hoạt động”; giá trị runtime/Gemini trên dashboard là **dữ liệu đọc từ phản hồi API** của FastAPI, phụ thuộc biến môi trường thực tế.

**Phân biệt vai trò (theo đề xuất đưa vào báo cáo):**

- Chatbot và gợi ý lịch trình phía người dùng là **chức năng ứng dụng Android** gọi `POST /api/ai/rag-chat`, `POST /api/ai/*`, …
- **Mục “RAG AI”** trên admin là **giám sát và vận hành** phân hệ RAG FastAPI (**monitor**), kèm vài **thao tác vận hành** (reload store, xóa cache, thử debug query); **không** phải màn **quản lý huấn luyện mô hình AI** trong code khảo sát.

---

## RAG AI Dashboard / Giám sát hệ thống AI

### 1. Tổng quan chức năng RAG AI Dashboard

| Câu hỏi | Trả lời theo mã |
| :--- | :--- |
| Mục “RAG AI” trên admin dùng để làm gì? | **Theo dõi** FastAPI UnuTrip RAG: tổng quan runtime (mode, Gemini bật/cấu hình), trạng thái “ready”, file chỉ mục/dữ liệu (`places_*`, BM25…), **self-test** tự động, **metrics** tổng hợp từ log JSONL, **data quality**, và **thiết bị/thao tác** vận hành (`reload-place-store`, `clear-cache`). Có ô **Debug Query** chạy pipeline đầy đủ và hiển thị answer/places/raw JSON. |
| Có phải màn hình giám sát FastAPI RAG không? | **Đúng.** Tiêu đề và mô tả trong template ghi rõ **“FastAPI RAG Monitor”** và **theo dõi trạng thái FastAPI RAG** (`ragAi.content.html`). |
| Có hiển thị trạng thái hoạt động của RAG service không? | **Có.** Dùng các KPI `ready`, HTTP status từng gọi, self-test passed/failed, grid check (health, files, cache, retrieval smoke…). Nguồn: **`GET /admin/rag/status`** và **`GET /admin/system/self-test`**, và tổng hợp **`GET /admin/system/overview`**. |
| Có hiển thị trạng thái model/runtime không? | **Có.** Từ `overview.data.runtime`: **`runtime_mode`**, **`enable_gemini`**, **`gemini_model`**, **`gemini_configured`** (bool API key trong settings FastAPI — không chứng minh “Gemini đang gọi thành công”). |
| Có hiển thị health, số liệu, logs, cấu hình, endpoint? | **health/self-test + metrics**: có từ API trên và **metrics** **`GET /admin/ai/metrics`**. **Logs**: nút UI gọi proxy **`GET /admin/rag-ai/ai-logs`** → FastAPI **`GET /admin/ai/logs`** (đọc `ai_request_logs.jsonl`). **Cấu hình URL**: hiển thị **`RAG_BASE_URL`** từ Node (`process.env`). **Endpoint được liệt kê** trong ghi chú cuối trang (overview, rag/status, self-test, metrics, data-quality/status). **`/health`** và **`/health/ready`** trên FastAPI **không thấy** được trang admin gọi trực tiếp trong `GET /rag-ai` (dashboard dùng bộ **`/admin/...`** thay cho đường health công khai). |
| Có thao tác quản trị như reload, test, xem kết nối? | **Reload** place store: `POST /admin/rag-ai/reload-place-store` → FastAPI **`POST /admin/rag/place-store/reload`**. **Clear cache**: `POST /admin/rag-ai/clear-cache` → **`POST /admin/cache/clear`**. **Test**: **Debug Query** `POST /admin/rag-ai/debug-query` → **`POST /admin/ai/debug-query`**. Các nút khác chủ yếu **GET JSON** và hiển thị (data-quality issues, ai-metrics, ai-logs). **Không có** chức năng train/fine-tune model trong các route khảo sát. |
| Monitor vs quản lý huấn luyện | Đặt đúng tên là **giám sát / vận hành** (monitor & ops). Không gọi là **quản lý huấn luyện AI**. |

**Lưu ý giao diện:** Trong **`ragAi.content.html`** có huy hiệu tĩnh **“Ready for demo”** (không đọc API). Khi báo cáo, nên căn cứ **self-test** và **`ready`** từ JSON, không chỉ vào nhãn tĩnh này.

---

### 2. Route và file mã nguồn liên quan

Đăng ký router admin Node: **`registerRagAiAdminRoutes`** được gọi từ **`backend/nodejs/src/admin/index.js`**.

**URL người dùng quản trị (trình duyệt):** Base **`/admin/...`** (mount trong `backend/nodejs/src/app.js` trước `buildAdminRouter`).

| Thành phần | Route/URL | Method | File xử lý | Mô tả |
| :--- | :--- | :--- | :--- | :--- |
| Trang dashboard RAG AI (HTML đầy đủ) | `/admin/rag-ai` | GET | `backend/nodejs/src/admin/ragAi.admin.routes.js` | Server-side **`Promise.all`** gọi 5 upstream FastAPI, fill template **`templates/ragAi.content.html`**, bọc **`renderLayout`** → `layout.html` (sidebar có link RAG AI). |
| Reload place store (proxy) | `/admin/rag-ai/reload-place-store` | POST | `ragAi.admin.routes.js` | **`postRagJson("/admin/rag/place-store/reload"`** |
| Clear response cache RAG (proxy) | `/admin/rag-ai/clear-cache` | POST | idem | **`postRagJson("/admin/cache/clear"`** |
| Data quality issues (proxy) | `/admin/rag-ai/data-quality-issues` | GET | idem | **`fetchRagJson("/admin/data-quality/issues"`**, timeout **5000** ms |
| AI metrics (proxy) | `/admin/rag-ai/ai-metrics` | GET | idem | **`fetchRagJson("/admin/ai/metrics"`**, timeout **5000** ms |
| AI logs (proxy) | `/admin/rag-ai/ai-logs` | GET | idem | **`fetchRagJson("/admin/ai/logs"`**, timeout **5000** ms |
| Debug query đầy pipeline (proxy) | `/admin/rag-ai/debug-query` | POST | idem | Body JSON `{ message }` hoặc `{ query }`; **`postRagJson("/admin/ai/debug-query", { message }, RAG_ADMIN_DEBUG_TIMEOUT_MS)`** (xem `backend/nodejs/src/config/env.js`) |
| Helper HTTP Admin → FastAPI | *(path bất kỳ, ghép vào `RAG_BASE_URL`)* | GET/POST | `backend/nodejs/src/admin/_shared/ragHttp.js` | **`fetchRagJson`**, **`postRagJson`**: header **`ragAdminJsonHeaders()`** cho path bắt đầu `/admin/`; timeout mặc định GET **3000 ms**, POST **5000 ms** (debug-query override bằng biến env). **Không dùng** `ragUpstream.js` retry. |
| Cấu hình base URL FastAPI | *(biến môi trường)* | — | `backend/nodejs/src/config/env.js` **`RAG_BASE_URL`** hoặc `RAG_API_BASE`; default **`http://127.0.0.1:8001`** | Dùng bởi **`ragUrl()`** trong `ragClient.js` |
| Sidebar “RAG AI” | `/admin/rag-ai` | — | `backend/nodejs/src/admin/templates/layout.html` (`<a href="/admin/rag-ai">`), active class qua `layout.js` **`NAV_RAG_AI`** | |
| Fragment nội dung + inline JS client | *(nhúng trong response GET `/admin/rag-ai`)* | — | `backend/nodejs/src/admin/templates/ragAi.content.html` | Tailwind CDN class; script `runRagAction`, `runDebugQuery`, `toggleRawJson`, `renderLogSummary` với CSP nonce **`SCRIPT_NONCE_ATTR`** |

**Upstream FastAPI (service thực) — các endpoint được gọi khi mở trang GET `/admin/rag-ai`:**

| Thành phần | Path trên FastAPI (sau `RAG_BASE_URL`) | Method | File xử lý | Mô tả |
| :--- | :--- | :--- | :--- | :--- |
| System overview | `/admin/system/overview` | GET | `backend/rag/app/routers/admin.py` **`admin_system_overview`** | Gộp runtime, rag files, **`place_store.status()`**, cache, ai_metrics snapshot, data_quality snapshot |
| RAG status | `/admin/rag/status` | GET | **`admin_rag_status`** | `ready`, **`files`** (places_*, bm25…), artifacts |
| Self-test | `/admin/system/self-test` | GET | **`admin_system_self_test`** | `checks`: health_ok, rag_files_ready, place_store_ready, retrieve smoke Khánh Hòa / Huế, … → `passed`/`failed`/`ready` |
| AI metrics | `/admin/ai/metrics` | GET | **`admin_ai_metrics`** | Tính toán từ **`reports/ai_request_logs.jsonl`** |
| Data quality status | `/admin/data-quality/status` | GET | **`admin_data_quality_status`** | Scan issues JSON, autofix report, reviewed file |

**FastAPI có thêm các endpoint `/admin/*` không thấy trang RAG AI gọi trực tiếp khi load** (chứng cứ chỉ các path trong bảng trên + các proxy nút): ví dụ **`GET /admin/rag/retrieve-debug`**, **`GET /admin/rag/place/{place_id}`**, **`GET /admin/cache/status`**, **`GET /admin/data-quality/summary-by-province`**, … — có thể dùng bằng Postman/thủ công hoặc mở rộng dashboard sau này.

---

### 3. Các thông tin hiển thị trên RAG AI Dashboard

| Thông tin hiển thị | Ý nghĩa | Nguồn dữ liệu/API | Có trong code không |
| :--- | :--- | :--- | :--- |
| **`RAG_BASE_URL`** hiển thị cho admin | Endpoint Node đang cấu hình để gọi FastAPI | Biến **`RAG_BASE_URL`**/`RAG_API_BASE` trong **`env.js`**, nhét vào template **`RAG_BASE_URL_ESC`** | Có (`ragAi.admin.routes.js` + template) |
| **RAG Ready** (top KPI + blocks) | Tổng hợp “sẵn sàng”: ưu tiên `rag_status.data.ready`/`status`/… fallback `overview`/`self-test` (`unknown` nếu thiếu) | **`/admin/rag/status`**, **`/admin/system/overview`**, **`/admin/system/self-test`** trong `Promise.all` | Có |
| **HTTP status** các panel (overview, rag status, self-test, metrics, data quality) | Kết quả HTTP khi Node gọi FastAPI (**timeout có thể = 0, ok false**) | **`fetchRagJson` trả `{ ok, status, data }`** | Có |
| **Self-test Passed/Failed**, ratio | Đếm **`passed`/`failed`** trong payload self-test | **`/admin/system/self-test`** | Có |
| **Places / place_store** (`place_count`, `using_reviewed`) | Quy mô dữ liệu trong **`place_store`** | **`/admin/rag/status`** và **`overview.rag.place_store`** | Có |
| **BM25 index** có tồn tại, dung lượng | Chuẩn bị truy xuất BM25 | **`ragStatus.data.files.bm25_index`** | Có (grid files) |
| **Lưới file RAG** (places_master, places_app, …) | Artifact tệp có tồn tại không | **`/admin/rag/status`** `files.*` | Có |
| **Self-test checklist** (Health OK, RAG files ready, …) | Checkbox tự động hóa vận hành | **`self-test.data.checks.*`** trong `ragAi.admin.routes.js` | Có |
| **Runtime mode** | Ví dụ mock / các mode pipeline cấu hình | **`overview.data.runtime.runtime_mode`** từ `settings.ai_runtime_mode` | Có |
| **Gemini enabled / model / configured** | Cấu hình (có API key không, model name khi enabled) — **không** khẳng định “Gemini đang chạy tốt” | **`overview.data.runtime.*`** trong FastAPI **`admin_system_overview`** | Có |
| **RAG Ready (overview subsection)** | Lặp/`rag.ready` trong overview | **`overview.data.rag.ready`** | Có |
| **Cache enabled** | Trạng thái **`response_cache.status()`** | **`overview.data.cache`** | Có |
| **AI Metrics** (total_requests, fallback_rate, quota, cache hit, model_usage…) | Thống kê từ log | **`/admin/ai/metrics`** | Có (UI map `gemini-2.5-flash`, `template_after_gemini_error` — phụ thuộc có key trong `model_usage`) |
| **Data quality** issues / severity / autofix / reviewed | Báo cáo offline JSON/CSV trong `reports/` và file reviewed | **`/admin/data-quality/status`** | Có |
| **Issue types** grid | Histogram `scan.issue_counts` | Cùng nguồn data-quality | Có |
| Raw JSON các panel | `Show Raw JSON` | Nội dung đã parse trên server | Có (template + `renderJsonBox`) |
| **Cổng FastAPI cố định “8001”** trong card | Hiển thị text ** cố định** không đọc từ URL | **`ragAi.content.html`** literal `8001` | Có (**cần lưu ý**: có thể lệch nếu RAG chạy port/domain khác) |
| Link **FastAPI Docs** | Mở tab mới | **`http://127.0.0.1:8001/docs`** hardcode trong HTML | Có (**có thể sai** nếu `RAG_BASE_URL` không phải `127.0.0.1:8001`) |
| Log summary khi Xem AI Logs | Tóm tắt bản log mới nhất: runtime_mode, model_used, fallback_used, generation_error | Client JS **`renderLogSummary(data)`** từ **`GET /admin/rag-ai/ai-logs`** | Có |
| Debug Query: Answer + Top Places + raw JSON | Thử **`pipeline.run`** với **`include_prompt`** mặc định trong schema FastAPI (`AdminAiDebugQueryRequest`) | **`POST /admin/ai/debug-query`** | Có |

---

### 4. Luồng nghiệp vụ quản trị viên giám sát RAG AI (điều chỉnh theo code)

**Điều kiện nền:** Trình duyệt vào được **`https://host/admin/...`**; nếu cấu hình **`ADMIN_BASIC_USER`** và **`ADMIN_BASIC_PASS`** thì nhập Basic Auth (**`middlewares/adminAuth.middleware.js`**). Node phải chạy và có thể resolve **`ragUrl(...)`**.

**Luồng mở trang giám sát**

1. **Bước 1.** Quản trị viên mở dashboard admin và xác thực (nếu bật Basic Auth).

2. **Bước 2.** Chọn menu **“RAG AI”** → trình duyệt **`GET /admin/rag-ai`**.

3. **Bước 3.** Node **`ragAi.admin.routes.js`** đồng thời gọi **`fetchRagJson`** tới **`/admin/system/overview`**, **`/admin/rag/status`**, **`/admin/system/self-test`**, **`/admin/ai/metrics`**, **`/admin/data-quality/status`** (mỗi lần gọi timeout mặc định **3000 ms** theo **`ragHttp.js`**).

4. **Bước 4.** FastAPI các handler trong **`backend/rag/app/routers/admin.py`** đọc `settings`, pipeline, file JSON/JSONL báo cáo, trả JSON.

5. **Bước 5.** Node map dữ liệu vào placeholder template **`ragAi.content.html`** (class màu, grid, các ô runtime/Gemini, v.v.), ghép **`renderLayout`** và **`layout.html`**, gửi **HTML một lần** (không phải SPA).

6. **Bước 6.** Trình duyệt hiển thị KPI và panel.

7. **Bước 7 (lỗi).**  
   - Nếu **một trong các `fetchRagJson` lỗi mạng/timeout**, object trả **`ok: false`**, **`status: 0`**, **`data.error`** (**`AbortError`** → chuỗi “Timeout khi gọi FastAPI RAG”). UI vẫn render với các trường **`N/A`/`unknown`** và class màu đỏ một phần (HTTP **`0`** trên các thẻ).  
   - Nếu **`GET /rag-ai` ném exception**, Node **`res.status(500).send("RAG AI Dashboard Error: " + …)`**.  
   - Các thao tác nút/phím debug dùng **`fetch`** từ JavaScript trong trang (**same-origin**) tới **`/admin/rag-ai/...`**; nếu lỗi, JS hiển thị tiêu đề “Kết nối thất bại…” và nội dung lỗi trong ô raw JSON.

**Luồng thử Debug Query** (khác bước load trang)

- Người dùng nhập câu → **`fetch('/admin/rag-ai/debug-query', POST JSON)`** → Node proxy **`POST {RAG_BASE_URL}/admin/ai/debug-query`** với **`RAG_ADMIN_DEBUG_TIMEOUT_MS`**.

---

### 5. Yêu cầu chức năng bổ sung cho Chương 2 (FR admin RAG)

| Mã FR | Mô tả | Căn cứ file/path/route | Trạng thái |
| :--- | :--- | :--- | :--- |
| **FR-ADMIN-RAG01** | **Xem trạng thái** tổng hợp phân hệ RAG (ready, KPI, các panel overview/status/self-test) | **`GET /admin/rag-ai`**, upstream **`/admin/system/overview`**, **`/admin/rag/status`**, **`/admin/system/self-test`** | **Đã có đầy đủ** (server render + upstream) |
| **FR-ADMIN-RAG02** | **Theo dõi** FastAPI qua chỉ báo artifact (file chỉ mục, bm25…), place store | **`GET /admin/rag/status`**, **`admin_rag_status`** | **Đã có đầy đủ** |
| **FR-ADMIN-RAG03** | **Kiểm tra kết nối** Node admin ↔ FastAPI (HTTP **`ok`/status/`0` trong UI, timeout) | **`ragHttp.fetchRagJson`**, cấu hình **`ragClient.ragUrl`**, header internal key **`ragAdminJsonHeaders`** | **Có một phần**: có hiển thị HTTP và lỗi timeout; không có chỉ báo heartbeat **riêng** ngoài gọi admin API |
| **FR-ADMIN-RAG04** | **Xem thông tin runtime/model** như báo cáo (mode, Gemini enabled/model/configured) | **`overview.runtime`** trong FastAPI và binding template | **Đã có đầy đủ** (đây là **cấu hình/metadata**, không phải chứng chỉ realtime inference) |
| **FR-ADMIN-RAG05** | **Thử nghiệm** trả lời RAG qua dashboard | **`POST /admin/rag-ai/debug-query`** ↔ **`POST /admin/ai/debug-query`**; các nút GET metrics/logs/issues | **Đã có đầy đủ** cho debug-query; các nút còn lại là **lấy JSON quan sát** |

---

### 6. Use Case bổ sung — tác nhân Quản trị viên

#### UC-GV-RAG-A: Giám sát hệ thống RAG AI

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | Giám sát hệ thống RAG AI |
| Mô tả | Quản trị viên mở mục RAG AI trên admin để **quan sát** trạng thái phân hệ FastAPI phục vụ chatbot/gợi ý — file dữ liệu, chỉ mục, self-test và cấu hình runtime được hiển thị trong một trang. |
| Tác nhân chính | Quản trị viên |
| Tác nhân phụ | **Node Express Admin Dashboard** (`/admin/rag-ai`); **FastAPI UnuTrip RAG** (`/admin/*`). |
| Điều kiện tiên quyết | Backend Node và RAG reachable theo **`RAG_BASE_URL`** (và khóa nội bộ nếu FastAPI yêu cầu **`X-RAG-Internal-Key`** khớp cấu hình). |

**Luồng chính (theo code):** như **mục 4**, các bước 1–6.

**Luồng thay thế:** timeout 3 giây từng panel; **`ok: false`**; exception 500 HTML; **`RAG_BASE_URL` sai**/RAG không chạy.

**Hậu điều kiện:** Trang KPI/panel được render (có thể một phần **N/A** nếu upstream lỗi).

**Căn cứ mã nguồn:** `ragAi.admin.routes.js`, `ragAi.content.html`, `_shared/ragHttp.js`, **`backend/rag/app/routers/admin.py`**.

---

#### UC-GV-RAG-B: Kiểm tra trạng thái FastAPI RAG / kết nối

Đặc tả rút gọn (cùng loại như UC-GV-RAG-A, đọc các field HTTP trong template): **Tác nhân** quản trị viên; **Mục tiêu** xác nhận panel **overview/rag-status/self-test** hiển thị HTTP 2xx và `ready`; **Luồng lỗi** khi `status === 0` hoặc dữ liệu `unknown`.

---

#### UC-GV-RAG-C: Thử nghiệm phản hồi AI/RAG qua Dashboard

| Mục | Nội dung |
| :--- | :--- |
| Tên Use Case | **Debug Query** pipeline RAG từ admin |
| Tác nhân chính | Quản trị viên |
| Luồng chính | Nhập câu → JS **`runDebugQuery()`** → **`POST /admin/rag-ai/debug-query`** → Node **`postRagJson("/admin/ai/debug-query", { message })`** timeout lớn → hiển thị answer/places và raw JSON (**`ragAi.content.html`**) |
| Luồng thay thế | Body trống (Node 400 “Thiếu message”), 502 từ proxy, JS catch mạng |
| Căn cứ | `ragAi.admin.routes.js` **`router.post("/rag-ai/debug-query")`**, FastAPI **`admin_ai_debug_query`**, JS cuối `ragAi.content.html` |

*(Nếu cần một UC riêng “Đọc AI logs”: nút **`GET /admin/rag-ai/ai-logs`** + `renderLogSummary` trong cùng file HTML.)*

---

### 7. Nội dung đưa vào báo cáo Chương 2 (“Đối với quản trị viên hệ thống”) — đoạn soạn thảo

*Ngoài các chức năng quản lý dữ liệu người dùng và địa điểm được triển khai qua các route trong `backend/nodejs/src/admin/`, dashboard còn cung cấp mục menu **«RAG AI»** (**`/admin/rag-ai`**) phục vụ **giám sát và vận hành** phân hệ **FastAPI UnuTrip RAG**. Trang được render phía máy chủ Node, đồng thời gọi các API nội bộ FastAPI dưới tiền tố **`/admin/`** (**tổng quan hệ thống**, **`/admin/rag/status`**, **`/admin/system/self-test`**, **metrics**, **data quality**) để hiển thị trạng thái readiness, artefact chỉ mục BM25, cấu hình **`runtime_mode`**, các cờ Gemini (bật tắt, model, đã có API key trong cấu hình hay chưa), và tóm tắt chỉ báo AI từ file log JSONL.*

*Trang cũng có **form Debug Query** gửi **`POST /admin/rag-ai/debug-query`** và các nút gọi **reload place store**, **clear cache**, cùng xem metrics/logs báo cáo. Đây không phải chức năng người dùng của ứng dụng Android mà là kênh **quản trị/giám sát** và **thiết hành** rất hữu ích cho việc chẩn đoán sự cố trong luồng chatbot và gợi ý lịch trình. Một vài nhãn giao diện (như cổng 8001 hoặc huy hiệu “Ready for demo”) là **đoạn text tĩnh** trong template; khi trình bày kết luận vận hành cần ưu tiên dữ liệu **self-test** và trường **`ready`** trả về từ API.*

---

### 8. Nội dung gợi ý Chương 4 (triển khai / hướng dẫn demo)

- **Giao diện RAG AI Dashboard:** Trang full-width nhiều panel (gradient header “FastAPI RAG Monitor”), KPI ô lớn, checklist validation, và khu raw JSON collapsible (**`templates/ragAi.content.html`**, stylesheet Tailwind CDN qua **`layout.html`**).

- **Sidebar:** **`layout.html`** có mục **“RAG AI”** điều hướng tới **`/admin/rag-ai`**; **`layout.js`** highlight khi **`activePath === "rag-ai"`**.

- **Khu “FastAPI RAG Monitor”:** Header badge + **`RAG_BASE_URL`** và nhóm nút vận hành (**Reload**, **Clear Cache**, **Data Quality Issues**, **AI Metrics**, **AI Logs**, **FastAPI Docs**, **Print**).

- **Chức năng theo dõi:** Panel **System Overview**, **RAG Status**, **Self-test**, **AI Metrics**, **Data Quality** — mỗi panel hiển thị **HTTP status** của lần gọi Node→FastAPI khi build trang.

- **Điều kiện monitor hoạt động đúng:**  
  1. **Node admin** chạy, mount **`/admin`**.  
  2. **FastAPI RAG** chạy tại URL trùng **`RAG_BASE_URL`** (mặc định code **`http://127.0.0.1:8001`**).  
  3. **Khóa nội bộ** (nếu bật trên FastAPI **`InternalApiKeyMiddleware`**) phải khớp **`RAG_INTERNAL_API_KEY` / `RAG_ADMIN_API_KEY`** phía Node như mô tả **`ragClient.ragAdminJsonHeaders`**.  
  4. Timeout **3 giây** mỗi GET khi load trang: môi trường chậm có thể cần tăng trong **`ragHttp.fetchRagJson`** hoặc tối ưu RAG.  
  5. **Metrics/logs** phụ thuộc file **`ai_request_logs.jsonl`** và báo cáo data quality trong thư mục **`reports/`** phía RAG (nếu chưa có file, UI vẫn hiển thị nhưng **N/A/0**).

**Không nên viết trong Chương 4:** “Màn hình quản lý huấn luyện mô hình AI” — **không có** trong code. Tránh câu “Gemini đang hoạt động” nếu chỉ thấy **`enable_gemini`** hoặc **`gemini_configured`**; cần nói **theo cấu hình hiển thị** hoặc **theo log/metrics** (fallback, quota, timeout).

---

## Phụ lục: File tham chiếu nhanh

| Vai trò | Đường dẫn |
| :--- | :--- |
| Đăng ký route RAG admin Node | `backend/nodejs/src/admin/ragAi.admin.routes.js` |
| Template nội dung + JS client | `backend/nodejs/src/admin/templates/ragAi.content.html` |
| Layout + sidebar | `backend/nodejs/src/admin/templates/layout.html`, `_shared/layout.js` |
| Fetch helper | `backend/nodejs/src/admin/_shared/ragHttp.js` |
| Cấu hình URL RAG | `backend/nodejs/src/config/env.js`, `backend/nodejs/src/config/ragClient.js` |
| FastAPI admin/monitor API | `backend/rag/app/routers/admin.py` |
| Health công khai (không dùng trong GET `/rag-ai`) | `backend/rag/app/routers/health.py` (`/health`, `/health/ready`, `/runtime/status`) |

---

*Cập nhật theo mã nguồn tại thời điểm phân tích trong workspace.*
