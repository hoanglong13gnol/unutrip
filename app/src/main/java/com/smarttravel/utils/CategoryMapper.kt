package com.smarttravel.utils

object CategoryMapper {
    const val BEACH = "beach"
    const val MOUNTAIN = "mountain"
    const val CITY = "city"
    const val HERITAGE = "heritage"
    const val NATURE = "nature"
    const val CHECKIN = "checkin"
    const val FOOD = "food"
    const val CULTURE = "culture"
    const val RELIGIOUS = "religious"

    private val supportedCodes = setOf(
        BEACH,
        MOUNTAIN,
        CITY,
        HERITAGE,
        NATURE,
        CHECKIN,
        FOOD,
        CULTURE,
        RELIGIOUS
    )

    private fun normalize(raw: String?): String {
        return raw
            ?.trim()
            ?.lowercase()
            ?.replace("_", "")
            ?.replace("-", "")
            ?.replace(" ", "")
            ?: ""
    }

    fun canonical(raw: String?): String {
        return when (normalize(raw)) {
            "beach", "sea", "island", "coast", "bien", "biển", "dao", "đảo", "vinh", "vịnh" -> BEACH

            "mountain", "mountains", "hill", "cave", "waterfall", "nui", "núi", "thac", "thác", "hang" -> MOUNTAIN

            "city", "urban", "thanhpho", "thànhphố", "dothi", "đôthị" -> CITY

            "heritage", "history", "historical", "relic", "museum", "ditich", "ditích", "lichsu", "lịchsử" -> HERITAGE

            "nature", "natural", "eco", "ecotourism", "forest", "lake", "river", "park", "thiennhien", "thiênnhiên" -> NATURE

            "checkin", "entertainment", "resort", "themepark", "amusement", "giaitri", "giảitrí", "congvien", "côngviên" -> CHECKIN

            "food", "restaurant", "market", "amthuc", "ẩmthực", "cho", "chợ" -> FOOD

            "culture", "cultural", "vanhoa", "vănhóa", "langnghe", "làngnghề" -> CULTURE

            "religious", "religion", "spiritual", "temple", "pagoda", "tamlinh", "tâmlinh", "chua", "chùa", "den", "đền" -> RELIGIOUS

            else -> raw?.trim()?.lowercase().orEmpty()
        }
    }

    fun categoryParam(raw: String?): String? {
        val code = canonical(raw)
        return code.takeIf { it in supportedCodes }
    }

    fun emojiLabel(raw: String?): String {
        return when (canonical(raw)) {
            BEACH -> "🏖️ Biển"
            MOUNTAIN -> "⛰️ Núi"
            CITY -> "🏙️ Thành phố"
            HERITAGE -> "🏛️ Di tích"
            NATURE -> "🌿 Thiên nhiên"
            CHECKIN -> "📸 Check-in"
            FOOD -> "🍜 Ẩm thực"
            CULTURE -> "🎭 Văn hóa"
            RELIGIOUS -> "🙏 Tâm linh"
            else -> "📍 Địa điểm"
        }
    }

    fun badgeLabel(raw: String?): String {
        return when (canonical(raw)) {
            BEACH -> "BIỂN"
            MOUNTAIN -> "NÚI"
            CITY -> "THÀNH PHỐ"
            HERITAGE -> "DI TÍCH"
            NATURE -> "THIÊN NHIÊN"
            CHECKIN -> "CHECK-IN"
            FOOD -> "ẨM THỰC"
            CULTURE -> "VĂN HÓA"
            RELIGIOUS -> "TÂM LINH"
            else -> "ĐỊA ĐIỂM"
        }
    }
}