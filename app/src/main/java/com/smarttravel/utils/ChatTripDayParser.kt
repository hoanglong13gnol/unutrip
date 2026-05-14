package com.smarttravel.utils

import com.smarttravel.data.model.AIItineraryOptionDay
import com.smarttravel.data.model.AIRecommendedDestination
import java.text.Normalizer

/**
 * Chuẩn hóa tiếng Việt (bỏ dấu) và bóc số ngày/đêm từ chat (vd: "2 ngay 1 dem", "2 ngày 1 đêm").
 */
object ChatTripDayParser {

    fun normalize(text: String): String {
        val temp = Normalizer.normalize(text.lowercase(), Normalizer.Form.NFD)
        return temp
            .replace("\\p{InCombiningDiacriticalMarks}+".toRegex(), "")
            .replace("đ", "d")
            .replace("\\s+".toRegex(), " ")
            .trim()
    }

    fun extractTripDays(text: String): Int? {
        if (text.isBlank()) return null
        val n = normalize(text)

        Regex("""(\d+)\s*ngay\s*(\d+)\s*dem""").find(n)?.groupValues?.get(1)?.toIntOrNull()?.coerceIn(1, 10)
            ?.let { return it }

        Regex("""(\d+)\s*ngay""").find(n)?.groupValues?.get(1)?.toIntOrNull()?.coerceIn(1, 10)
            ?.let { return it }

        return null
    }

    /**
     * Chia danh sách địa điểm theo số ngày, **giữ thứ tự** như trong chat/RAG:
     * ngày 1 nhận chunk đầu, ngày 2 chunk tiếp, … (không round-robin).
     */
    fun splitDestinationsAcrossDays(
        items: List<AIRecommendedDestination>,
        totalDays: Int
    ): List<AIItineraryOptionDay> {
        val d = totalDays.coerceIn(1, 10)
        if (items.isEmpty()) return emptyList()

        if (items.size < d) {
            return items.mapIndexed { index, item ->
                val day = index + 1
                AIItineraryOptionDay(
                    dayNumber = day,
                    items = listOf(item.copy(recommendedDay = day))
                )
            }
        }

        val n = items.size
        val base = n / d
        val remainder = n % d
        val sizes = List(d) { idx -> base + if (idx < remainder) 1 else 0 }
        var offset = 0
        val out = mutableListOf<AIItineraryOptionDay>()
        for (day in 1..d) {
            val sz = sizes[day - 1]
            if (sz <= 0) continue
            val slice = items.subList(offset, offset + sz).map { it.copy(recommendedDay = day) }
            out.add(AIItineraryOptionDay(dayNumber = day, items = slice))
            offset += sz
        }
        return out
    }
}
