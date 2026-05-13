import json
from typing import Any


class PromptBuilder:
    def build_prompt(self, retrieved_payload: dict[str, Any], context: str) -> str:
        query = retrieved_payload.get("query", "")
        intent = retrieved_payload.get("intent", {})

        if intent.get("intent") == "itinerary":
            output_instruction = self._itinerary_output_instruction()
        else:
            output_instruction = self._search_output_instruction()

        compact_intent = self._compact_intent(intent)

        prompt = f"""
Bạn là UnuTrip AI, trợ lý du lịch Việt Nam.

Chỉ trả lời dựa trên CONTEXT. Không tự thêm địa điểm ngoài CONTEXT. Không bịa giá vé, giờ mở cửa, địa chỉ, tọa độ, thời tiết.
Nếu thiếu thông tin, nói: "Dữ liệu hiện chưa đủ để kết luận chính xác".
Nếu realtime=true, nhắc người dùng kiểm tra thông tin thực tế trước khi đi.
Không dùng not_main=true làm điểm chính trong lịch trình.
Trả lời tiếng Việt, rõ ràng, ngắn gọn.

USER_QUERY:
{query}

INTENT:
{json.dumps(compact_intent, ensure_ascii=False)}

CONTEXT:
{context}

OUTPUT:
{output_instruction}
""".strip()

        return prompt

    def _compact_intent(self, intent: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "intent",
            "province_norm",
            "days",
            "time_slot",
            "budget_level",
            "has_children",
            "has_elderly",
            "walking_preference",
            "interests",
            "avoid",
        ]

        return {
            key: intent.get(key)
            for key in keys
            if intent.get(key) not in [None, False, [], ""]
        }

    def _search_output_instruction(self) -> str:
        return """
Gợi ý 3-5 địa điểm phù hợp nhất.
Mỗi địa điểm gồm:
- Tên
- Lý do phù hợp
- Lưu ý ngân sách/mức đi bộ/đối tượng nếu có
- Không lặp cảnh báo cho từng địa điểm.
- Nếu cần lưu ý về giờ mở cửa, giá vé hoặc tình trạng dịch vụ, chỉ viết 1 mục "Lưu ý chung" ở cuối câu trả lời.
- Không dùng từ "Cảnh báo" trừ khi có rủi ro an toàn nghiêm trọng.
Không nhắc địa điểm ngoài CONTEXT.
""".strip()

    def _itinerary_output_instruction(self) -> str:
        return """
Lập lịch trình theo Sáng / Trưa / Chiều / Tối nếu đủ dữ liệu.
Mỗi khung giờ gồm:
- Địa điểm
- Thời lượng dự kiến nếu có
- Lý do chọn
- Lưu ý ngân sách/mức đi bộ/đối tượng nếu có
- Không lặp cảnh báo cho từng địa điểm.
- Nếu cần lưu ý về giờ mở cửa, giá vé hoặc tình trạng dịch vụ, chỉ viết 1 mục "Lưu ý chung" ở cuối câu trả lời.
- Không dùng từ "Cảnh báo" trừ khi có rủi ro an toàn nghiêm trọng.
Không dùng not_main=true làm điểm chính.
Không nhắc địa điểm ngoài CONTEXT.
""".strip()