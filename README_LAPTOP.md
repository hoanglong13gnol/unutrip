# UNUtrip — Thiết lập trên laptop mới (báo cáo / demo)

Hướng dẫn cho máy **chưa cài gì**, muốn chạy **backend đầy đủ qua Docker** và **demo app bằng Android Studio + emulator** (đúng kiểu làm hiện tại).

Chi tiết kiến trúc và từng module xem **`README.md`**.

---

## 1. Phần mềm nền (cài một lần)

| Phần mềm | Vai trò |
|----------|---------|
| **Git** | Clone repo (`https://github.com/hoanglong13gnol/unutrip`) |
| **Docker Desktop** | MySQL, Redis, RAG (FastAPI), backend Node trong `docker-compose.yml` |
| **Android Studio** | Gradle, emulator, Run app variant **devDebug** |

- **Windows:** Docker Desktop yêu cầu **WSL2** / ảo hóa bật theo wizard cài đặt. RAM khuyến nghị **≥ 16 GB** nếu vừa emulator vừa Docker.
- JDK riêng: **không cần** nếu chỉ build qua Android Studio (Studio cấp JDK cho Gradle).

---

## 2. Lấy mã nguồn

```powershell
git clone https://github.com/hoanglong13gnol/unutrip.git
cd unutrip
git checkout v2/database-refactor
```

Nhánh **`main`** trên GitHub có thể là snapshot cũ; code báo cáo nằm trên nhánh trên (hoặc nhánh bạn đã đồng bộ — kiểm tra `git branch -a`).

---

## 3. Biến môi trường `.env`

1. Từ thư mục gốc repo:

   ```powershell
   copy .env.example .env
   ```

2. Mở `.env` và chỉnh tối thiểu:
   - **`JWT_SECRET`** — chuỗi bí mật (dev có thể tùy ý, đủ dài).
   - **`GEMINI_API_KEY`** — nếu demo **chat / AI** qua RAG (xem `.env.example`).
   - Mật khẩu MySQL (`MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, …) nếu không dùng mặc định trong file mẫu.

**Không commit** file `.env` (đã nằm trong `.gitignore`).

---

## 4. Cơ sở dữ liệu MySQL (quan trọng: **`app_places`**)

Backend Node đọc danh sách địa điểm từ bảng **`app_places`**, **không** đọc trực tiếp **`destinations`**. Import chỉ **`backend/nodejs/database.sql`** sẽ tạo **`destinations` + INSERT** nhưng app vẫn có thể hiện **0 địa điểm** nếu **`app_places` trống**.

Quy trình gọn cho laptop báo cáo (đổi `-u/-p`/DB nếu bạn đã chỉnh trong `.env`):

```powershell
docker compose up -d mysql
# Đợi mysql healthy, rồi:

# (A) Legacy schema + ví dụ dữ liệu vào `destinations`
Get-Content .\backend\nodejs\database.sql -Raw | docker compose exec -T mysql mysql -uunutrip -punutrip_pass unudata

# (B) Tạo bảng `app_places`
Get-Content .\database\migrations\001_create_app_places.sql -Raw | docker compose exec -T mysql mysql -uunutrip -punutrip_pass unudata

# (C) Copy dữ liệu từ `destinations` → `app_places` (bản script tương thích `database.sql`)
Get-Content .\database\quick_populate_app_places_from_legacy_database_sql.sql -Raw | docker compose exec -T mysql mysql -uunutrip -punutrip_pass unudata
```

Kiểm tra nhanh có bản ghi:

```powershell
docker compose exec -T mysql mysql -uunutrip -punutrip_pass unudata -e "SELECT COUNT(*) AS n FROM app_places;"
```

> Nếu bạn dùng **dump v2 đầy đủ** trên máy phát triển, không dùng bước (C): hãy chạy chuỗi migration trong `database/migrations/README.md` (đặc biệt **`006_populate_app_places.sql`** khi legacy đã có đủ cột).

---

## 5. Chạy toàn stack (Docker)

Từ **thư mục gốc** repo (cùng cấp `docker-compose.yml`):

```powershell
docker compose up -d --build
```

Kiểm tra nhanh:

- API Node: [http://localhost:3000/api/health](http://localhost:3000/api/health)
- RAG (tùy cấu hình): [http://localhost:8001/docs](http://localhost:8001/docs)

Dừng stack: `docker compose down` (volume MySQL được giữ theo `docker-compose.yml`; xóa sạch dữ liệu cần hiểu rõ volume `unutrip_mysql_data`).

---

## 6. Android Studio + emulator

1. **File → Open** → chọn thư mục `unutrip` (Gradle root).
2. Đợi **Gradle sync** xong.
3. **Device Manager** → tạo/start **Virtual Device (AVD)**.
4. Chọn **build variant** **`devDebug`** (flavor **`dev`** + **debug**).

### URL API khi chạy trên emulator

Emulator không dùng `127.0.0.1` của máy host để gọi API; project mặc định **`http://10.0.2.2:3000/api/`** trong `app/build.gradle` (`API_BASE_URL`).

Tuỳ chọn: thêm vào **`local.properties`** (file này **không** commit — Gradle/Android Studio có thể tự tạo/`sdk.dir`):

```properties
sdk.dir=C\:\\Users\\<BẠN>\\AppData\\Local\\Android\\Sdk
API_BASE_URL=http://10.0.2.2:3000/api/
GEMINI_API_KEY=
```

(`GEMINI_API_KEY` chỉ cần nếu đường build của app có dùng trực tiếp; chủ yếu AI đi qua backend/RAG và `.env` Docker.)

### Thiết bị thật (USB/Wi‑Fi)

Đặt **`API_BASE_URL=http://<IP_LAN_máy_laptop>:3000/api/`** (kết thúc bằng `/`), máy điện thoại cùng mạng với laptop.

---

## 7. Thứ tự gợi ý trước khi demo

1. Docker Desktop đang chạy.
2. `docker compose up -d` và MySQL đã import dữ liệu.
3. `GET /api/health` trả OK.
4. Mở Android Studio → **devDebug** → Run trên emulator.

---

## 8. Sự cố thường gặp

| Hiện tượng | Hướng xử lý |
|------------|-------------|
| Emulator không gọi được API | Backend có đang chạy trên host cổng **3000**? Thử `API_BASE_URL` `http://10.0.2.2:3000/api/`. |
| `connection refused` / timeout | Firewall Windows chặn cổng 3000; tắt thử hoặc mở rule cho Node/Docker. |
| App trắng / lỗi login | DB chưa import hoặc sai user/DB/password so với `.env`. |
| RAG / AI lỗi | Container **rag** healthy? `GEMINI_API_KEY`, artifact BM25 trong image (build RAG Dockerfile) — xem **`README.md`** phần RAG. |
| Docker hết RAM | Giảm số container không cần thiết trong demo hoặc tăng RAM cho Docker Desktop / đóng app nặng. |

---

## 9. Không dùng Docker (tùy chọn)

Nếu máy yếu hoặc không cài được Docker: cần **MySQL**, **Node.js**, **Python + venv**, **Redis** (nếu RAG dùng) cài tay; chạy Node và RAG theo **`README.md`**. Cách này nhiều bước hơn; laptop “trống” nên ưu tiên Docker như trên.

---

*Tài liệu kèm repo — cập nhật theo nhánh `v2/database-refactor` và `docker-compose.yml` hiện tại.*
