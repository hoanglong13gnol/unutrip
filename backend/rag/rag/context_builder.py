from typing import Any


class ContextBuilder:
    def build_context(self, retrieved_payload: dict[str, Any], max_places: int = 5) -> str:
        results = retrieved_payload.get("results", [])[:max_places]

        blocks = []

        for index, item in enumerate(results, start=1):
            meta = item.get("metadata") or {}
            block = self._build_place_block(index, item, meta)
            blocks.append(block)

        return "\n\n".join(blocks)

    def _build_place_block(
        self,
        index: int,
        item: dict[str, Any],
        meta: dict[str, Any],
    ) -> str:
        title = item.get("title") or meta.get("name") or item.get("place_id")
        text = item.get("text") or ""

        short_text = self._shorten_text(text, max_chars=450)

        reasons = item.get("reasons") or []

        lines = [
            f"[PLACE {index}]",
            f"id: {item.get('place_id')}",
            f"name: {title}",
            f"province: {meta.get('province')}",
            f"area: {meta.get('area')}",
            f"category: {meta.get('category_main')} / {meta.get('category_sub')}",
            f"budget: {meta.get('budget_level_norm')}",
            f"walking: {meta.get('walking_level_norm')}",
            f"kid_friendly: {meta.get('kid_friendly_norm')}",
            f"elderly_friendly: {meta.get('elderly_friendly_norm')}",
            f"slot: {meta.get('slot_norm')}",
            f"quality: {meta.get('quality_score')}",
            f"use: {meta.get('recommended_use_norm')}",
            f"not_main: {meta.get('must_not_schedule_as_main')}",
            f"realtime: {meta.get('requires_realtime_check')}",
            f"why_retrieved: {', '.join(reasons[:6])}",
            f"note: {short_text}",
            f"[/PLACE {index}]",
        ]

        return "\n".join(lines)

    def _shorten_text(self, text: str, max_chars: int = 450) -> str:
        text = str(text or "").strip()

        # Bỏ bớt xuống dòng thừa để context gọn hơn.
        text = " ".join(text.split())

        if len(text) <= max_chars:
            return text

        return text[:max_chars].rstrip() + "..."