package com.smarttravel.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CategoryMapperTest {

    @Test
    fun canonical_mapsVietnameseAliases() {
        assertEquals(CategoryMapper.BEACH, CategoryMapper.canonical("biển"))
        assertEquals(CategoryMapper.MOUNTAIN, CategoryMapper.canonical("núi"))
        assertEquals(CategoryMapper.FOOD, CategoryMapper.canonical("ẩm_thực"))
    }

    @Test
    fun categoryParam_returnsOnlySupportedCodes() {
        assertEquals("beach", CategoryMapper.categoryParam("sea"))
        assertNull(CategoryMapper.categoryParam("unknown-category-xyz"))
    }

    @Test
    fun emojiLabel_fallsBackForUnknown() {
        assertEquals("📍 Địa điểm", CategoryMapper.emojiLabel("unknown-category-xyz"))
        assertEquals("🏖️ Biển", CategoryMapper.emojiLabel(CategoryMapper.BEACH))
    }

    @Test
    fun badgeLabel_matchesCanonicalCategory() {
        assertEquals("ẨM THỰC", CategoryMapper.badgeLabel("food"))
    }
}
