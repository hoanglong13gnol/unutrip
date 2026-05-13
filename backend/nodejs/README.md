# SmartTravel Backend - Cấu trúc Hybrid AI Proxy

Thư mục này chứa mã nguồn cho **Backend (Node.js)** và **AI Server (Python)**.

## 🚀 1. Hướng dẫn chạy AI Server (Python)
Đây là trái tim của hệ thống, nạp mô hình Qwen2.5-1.5B đã được fine-tune để xử lý lịch trình.

### Yêu cầu:
- Python 3.10 trở lên.
- Card đồ họa NVIDIA (RTX 30-series trở lên) để chạy GPU, hoặc 16GB RAM để chạy CPU.

### Cài đặt:
```bash
pip install torch transformers peft accelerate fastapi uvicorn
```

### Khởi chạy:
```bash
python server.py
```
*Hệ thống sẽ tự động thử chạy trên GPU (RTX 5060). Nếu không tương thích, nó sẽ tự động chuyển sang chế độ CPU mà không gây dừng chương trình.*

---

## 🛠️ 2. Hướng dẫn chạy Backend (Node.js)
Đóng vai trò điều phối dữ liệu và cầu nối xác thực.

### Cài đặt:
```bash
npm install
```

### Cấu hình `.env`:
Hãy tạo file `.env` và điền các thông tin:
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=smarttravel
PORT=3000
GEMINI_API_KEY=YOUR_KEY_HERE
AI_MODEL_URL=http://127.0.0.1:8000/chat
```

### Khởi chạy:
```bash
npm run dev
```

---

## 🧠 3. Cơ chế hoạt động của AI (Hybrid Flow)
Backend được thiết kế với tư duy **"Reliability First"**:

1. **Giai đoạn 1**: Thử kết nối với AI Server cục bộ (Python).
2. **Giai đoạn 2**: Nếu AI Local không phản hồi hoặc gặp lỗi nội bộ, Backend tự động chuyển hướng request sang **Gemini API** của Google.
3. **Giai đoạn 3**: Dữ liệu từ bất kỳ nguồn nào đều được Backend kiểm tra cấu trúc (Validation) và sửa lỗi ngày tháng trước khi trả về cho App Android.

## 🖥️ 4. Trang Quản trị (Admin Dashboard)
Truy cập tại: `http://localhost:3000/admin/dashboard`
- Xem thống kê người dùng, địa điểm.
- Tính năng **AI Smart Analysis**: Phân tích dữ liệu hệ thống thời gian thực bằng AI.

---
*Lưu ý: Luôn khởi động AI Server (Python) TRƯỚC khi chạy Backend (Node.js) để tính năng AI Itinerary hoạt động tối ưu nhất.*
