package com.smarttravel.utils

import com.smarttravel.data.model.AIRecommendedDestination
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatTripDayParserTest {

    @Test
    fun normalize_stripsDiacriticsAndCollapseWhitespace() {
        assertEquals(
            "2 ngay 1 dem o ha noi",
            ChatTripDayParser.normalize("  2 ngày 1 đêm ở Hà Nội  ")
        )
    }

    @Test
    fun extractTripDays_prefersNgayDemPair() {
        assertEquals(3, ChatTripDayParser.extractTripDays("đi 3 ngày 2 đêm"))
    }

    @Test
    fun extractTripDays_fallsBackToNgayOnly() {
        assertEquals(5, ChatTripDayParser.extractTripDays("lịch 5 ngày"))
    }

    @Test
    fun extractTripDays_blankReturnsNull() {
        assertNull(ChatTripDayParser.extractTripDays("   "))
    }

    @Test
    fun splitDestinationsAcrossDays_whenFewerItemsThanDays_onePerDayInOrder() {
        val items = listOf(
            dest("A"),
            dest("B")
        )
        val days = ChatTripDayParser.splitDestinationsAcrossDays(items, totalDays = 3)
        assertEquals(2, days.size)
        assertEquals(1, days[0].dayNumber)
        assertEquals(listOf("A"), days[0].items.map { it.name })
        assertEquals(1, days[0].items[0].recommendedDay)
        assertEquals(2, days[1].dayNumber)
        assertEquals(listOf("B"), days[1].items.map { it.name })
    }

    @Test
    fun splitDestinationsAcrossDays_chunksSequentiallyWhenMoreItemsThanDays() {
        val items = (1..7).map { dest("P$it") }
        val days = ChatTripDayParser.splitDestinationsAcrossDays(items, totalDays = 3)
        assertEquals(3, days.size)
        assertEquals(listOf("P1", "P2", "P3"), days[0].items.map { it.name })
        assertEquals(listOf("P4", "P5"), days[1].items.map { it.name })
        assertEquals(listOf("P6", "P7"), days[2].items.map { it.name })
        assertTrue(days[0].items.all { it.recommendedDay == 1 })
        assertTrue(days[1].items.all { it.recommendedDay == 2 })
        assertTrue(days[2].items.all { it.recommendedDay == 3 })
    }

    private fun dest(name: String) = AIRecommendedDestination(
        destinationId = null,
        rawPlaceId = null,
        name = name,
        province = null,
        city = null,
        area = null,
        category = null,
        imageUrl = null,
        reason = null,
        estimatedVisitDurationMinutes = null,
        recommendedDay = null,
        qualityScore = null
    )
}
