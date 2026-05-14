import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os
import sys

app = FastAPI(title="SmartTravel AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình đường dẫn
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_PATH = r"c:/web and app/SmartTravelApp/smarttravel-qwen2.5-1.5b-lora-v2 (1)/kaggle/working/smarttravel-qwen2.5-1.5b-lora-v2"

SYSTEM_PROMPT = (
    "Bạn là AI trợ lý du lịch SmartTravel. Chỉ trả lời bằng tiếng Việt. "
    "Nhiệm vụ: Tư vấn địa điểm, lịch trình Việt Nam. "
    "Trình bày rõ ràng sáng/chiều/tối."
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str

def load_model():
    # Thử chạy GPU trước
    if torch.cuda.is_available():
        try:
            print("--- THỬ NGHIỆM KHỞI CHẠY TRÊN GPU (RTX 5060) ---")
            tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)
            
            # Load base model với float16
            base = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            
            # Thử load adapter (Bước này hay lỗi sm_120)
            print("Đang nạp bộ lọc LoRA lên GPU...")
            model = PeftModel.from_pretrained(base, ADAPTER_PATH)
            model.eval()
            print("✅ THÀNH CÔNG: ĐANG CHẠY BẰNG GPU (TỐC ĐỘ CAO)")
            return tokenizer, model, "cuda"
        except Exception as e:
            print(f"⚠️ GPU KHÔNG TƯƠNG THÍCH (Lỗi: {str(e)[:100]}...)")
            print("--- ĐANG CHUYỂN HÀNH TRÌNH SANG CPU ĐỂ ĐẢM BẢO ỔN ĐỊNH ---")
            # Giải phóng bộ nhớ GPU nếu có
            if 'base' in locals(): del base
            torch.cuda.empty_cache()

    # Chạy CPU (Fallback)
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        device_map={"": "cpu"},
        trust_remote_code=True,
        torch_dtype=torch.float32
    )
    model = PeftModel.from_pretrained(base, ADAPTER_PATH)
    model.eval()
    print("ℹ️ HỆ THỐNG ĐANG CHẠY TRÊN CPU (CHẾ ĐỘ ỔN ĐỊNH)")
    return tokenizer, model, "cpu"

# Khởi tạo model khi start server
tokenizer, model, current_device = load_model()

@app.get("/")
def root():
    return {"status": "online", "device": current_device, "model": "Qwen2.5-1.5B-LoRA"}


@app.get("/chat")
def chat_get_help():
    """Mở http://127.0.0.1:8000/chat trên trình duyệt là GET — route thật là POST JSON."""
    return {
        "message": "Đây không phải trang web. Dùng POST JSON {\"message\": \"...\"} hoặc xem GET / .",
        "post_url": "/chat",
        "content_type": "application/json",
        "example": 'curl -s http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\\"message\\":\\"Xin chào\\"}"',
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    print(f"[AI] Request: {req.message[:50]}...")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": req.message}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # Đảm bảo inputs ở đúng thiết bị
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    ans = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
    return ChatResponse(answer=ans)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
