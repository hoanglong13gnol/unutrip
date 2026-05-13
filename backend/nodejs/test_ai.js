import fetch from 'node-fetch';

async fun testAI() {
    const aiUrl = "http://127.0.0.1:8000/chat";
    console.log("--- BẮT ĐẦU KIỂM THỬ KẾT NỐI AI ---");
    console.log(`Đang gọi AI tại: ${aiUrl}`);

    try {
        const response = await fetch(aiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "Xin chào, hãy giới thiệu ngắn gọn về bạn." })
        });

        if (response.ok) {
            const data = await response.json();
            console.log("✅ KẾT NỐI THÀNH CÔNG!");
            console.log("AI trả lời:", data.answer);
        } else {
            console.log("❌ LỖI KẾT NỐI:", response.status, response.statusText);
        }
    } catch (error) {
        console.log("❌ LỖI NGHIÊM TRỌNG:", error.message);
        console.log("Gợi ý: Đảm bảo bạn đã chạy 'python server.py' ở terminal khác.");
    }
}

testAI();
