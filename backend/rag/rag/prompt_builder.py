import json
from typing import Any


class PromptBuilder:
    def build_prompt(self, retrieved_payload: dict[str, Any], context: str) -> str:
        query = retrieved_payload.get("query", "")
        intent = retrieved_payload.get("intent", {})
        is_itinerary = intent.get("intent") == "itinerary"

        if is_itinerary:
            output_instruction = self._itinerary_output_instruction()
            rules_block = self._itinerary_rules_block()
        else:
            output_instruction = self._search_output_instruction()
            rules_block = self._search_rules_block()

        compact_intent = self._compact_intent(intent)

        prompt = f"""
Bạn là UnuTrip AI, trợ lý du lịch Việt Nam.

{rules_block}

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

    def _search_rules_block(self) -> str:
        return """
Chỉ trả lời dựa trên CONTEXT. Không tự thêm địa điểm ngoài CONTEXT. Không bịa giá vé, giờ mở cửa, địa chỉ, tọa độ, thời tiết.
Nếu thiếu thông tin, nói: "Dữ liệu hiện chưa đủ để kết luận chính xác".
Nếu realtime=true, nhắc người dùng kiểm tra thông tin thực tế trước khi đi.
Trả lời tiếng Việt, rõ ràng, ngắn gọn.
""".strip()

    def _itinerary_rules_block(self) -> str:
        return """
Chỉ được dùng địa điểm có trong CONTEXT (theo id/name khớp từng PLACE). Không bịa thêm địa điểm mới. Không bịa giá vé, giờ mở cửa, địa chỉ cụ thể, tọa độ, thời tiết.

Phân bổ lịch trình nhiều ngày:
- Chia các PLACE trong CONTEXT cho từng ngày và các khung Sáng / Trưa / Chiều / Tối một cách hợp lý (tránh lặp cùng một điểm nhiều lần trừ khi hợp lý vì khoảng cách thời gian).
- Trường slot trong CONTEXT là gợi ý: nếu slot là any, full_day hoặc không rõ, bạn được xếp điểm đó vào Sáng, Trưa hoặc Chiều miễn không mâu thuẫn với mô tả (ví dụ chợ đêm → Tối).
- Chỉ dùng câu "Dữ liệu hiện chưa đủ để kết luận chính xác" cho một khung giờ khi thực sự không còn địa điểm nào trong CONTEXT chưa gán mà vẫn phù hợp; không được lặp câu đó cho cả Sáng, Trưa và Chiều nếu vẫn còn địa điểm có thể gán hợp lý.
- Nếu realtime=true trong CONTEXT, nhắc kiểm tra thông tin thực tế trước khi đi (có thể gộp một mục "Lưu ý chung" cuối bài).
- Không dùng not_main=true làm điểm chính trong lịch trình.
Trả lời tiếng Việt, rõ ràng.
""".strip()

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
Lập lịch trình theo từng ngày, mỗi ngày có các khung Sáng / Trưa / Chiều / Tối; mỗi khung có thể gợi ý 1–2 địa điểm từ CONTEXT (ưu tiên đa dạng, xen kẽ tham quan / ẩm thực / đi bộ nhẹ nếu phù hợp).
Mỗi mục địa điểm gồm:
- Tên (trùng với CONTEXT)
- Thời lượng dự kiến (ước lượng hợp lý, không cần chính xác tuyệt đối)
- Lý do chọn (gắn với nhu cầu trong USER_QUERY hoặc metadata trong CONTEXT)
- Lưu ý ngân sách/mức đi bộ/đối tượng nếu có trong CONTEXT
- Không lặp cảnh báo cho từng địa điểm.
- Nếu cần lưu ý về giờ mở cửa, giá vé hoặc tình trạng dịch vụ, chỉ viết 1 mục "Lưu ý chung" ở cuối câu trả lời.
- Không dùng từ "Cảnh báo" trừ khi có rủi ro an toàn nghiêm trọng.
Không dùng not_main=true làm điểm chính.
Không nhắc địa điểm ngoài CONTEXT.
""".strip()