package com.smarttravel.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smarttravel.data.model.ChatMessage
import com.smarttravel.data.model.ChatbotResult
import com.smarttravel.utils.ChatTripDayParser
import com.smarttravel.utils.GeminiService
import com.smarttravel.utils.RagService
import kotlinx.coroutines.launch

class ChatbotViewModel : ViewModel() {

    private val ragService = RagService()
    private val geminiService = GeminiService()

    private val _messages = MutableLiveData<List<ChatMessage>>(emptyList())
    val messages: LiveData<List<ChatMessage>> = _messages

    private val _isLoading = MutableLiveData(false)
    val isLoading: LiveData<Boolean> = _isLoading

    private val conversationHistory = mutableListOf<ChatMessage>()

    private var token: String = ""

    // Context hội thoại gần nhất
    private var lastTargetProvince: String? = null
    private var lastTargetCity: String? = null
    private var lastTripDays: Int? = null

    init {
        val welcome = ChatMessage(
            role = "model",
            content = "Xin chào! 👋 Tôi là trợ lý du lịch SmartTravel.\n\nTôi có thể giúp bạn:\n• 🗺️ Gợi ý địa điểm du lịch\n• 📅 Lập kế hoạch chuyến đi\n• 🍜 Tư vấn ẩm thực địa phương\n• 💰 Ước tính chi phí\n• 🚗 Hướng dẫn di chuyển\n\nBạn muốn khám phá đâu hôm nay?"
        )

        conversationHistory.add(welcome)
        _messages.value = conversationHistory.toList()
    }

    fun init(token: String) {
        this.token = token
    }

    fun sendMessage(userMessage: String) {
        val userText = userMessage.trim()
        if (userText.isBlank()) return

        val userMsg = ChatMessage(
            role = "user",
            content = userText
        )

        conversationHistory.add(userMsg)
        _messages.value = conversationHistory.toList()

        viewModelScope.launch {
            _isLoading.value = true

            try {
                val finalResult = getFinalChatbotResult(userText)

                val aiMsg = ChatMessage(
                    role = "model",
                    content = finalResult.answer,
                    places = finalResult.places,
                    tripDaysHint = finalResult.tripDaysHint
                )

                conversationHistory.add(aiMsg)
                _messages.value = conversationHistory.toList()
            } catch (e: Exception) {
                val errorMsg = ChatMessage(
                    role = "model",
                    content = "Đã xảy ra lỗi: ${e.message}. Vui lòng thử lại."
                )

                conversationHistory.add(errorMsg)
                _messages.value = conversationHistory.toList()
            } finally {
                _isLoading.value = false
            }
        }
    }

    private suspend fun getFinalChatbotResult(userText: String): ChatbotResult {
        val preparedQuery = geminiService.prepareRagQuery(
            token = token,
            userMessage = userText
        )

        val currentProvince = preparedQuery.targetProvince
            ?: extractProvinceFromText(userText)
            ?: extractProvinceFromText(preparedQuery.query)

        val currentTripDays = preparedQuery.tripDays
            ?: extractTripDaysFromText(userText)

        val isFollowUp = isFollowUpTravelRequest(userText)

        val targetProvince = currentProvince
            ?: if (isFollowUp) lastTargetProvince else null

        val targetCity = preparedQuery.targetCity
            ?: if (isFollowUp) lastTargetCity else null

        val tripDays = currentTripDays
            ?: if (isFollowUp) lastTripDays else null

        val ragQuery = buildContextAwareRagQuery(
            userText = userText,
            preparedQuery = preparedQuery.query,
            targetProvince = targetProvince,
            tripDays = tripDays,
            isFollowUp = isFollowUp && currentProvince.isNullOrBlank()
        )

        updateConversationContext(
            targetProvince = targetProvince,
            targetCity = targetCity,
            tripDays = tripDays
        )

        var ragResult = ragService.chat(
            token = token,
            history = conversationHistory.dropLast(1),
            newMessage = ragQuery,
            targetProvince = targetProvince,
            targetCity = targetCity
        )

        var ragFailed = isRagFailed(ragResult)

        var hardMismatch = if (!ragFailed) {
            isProvinceMismatch(
                targetProvince = targetProvince,
                places = ragResult.places
            )
        } else {
            false
        }

        if (!ragFailed && hardMismatch && !targetProvince.isNullOrBlank()) {
            val strictQuery = buildStrictProvinceQuery(
                userText = userText,
                targetProvince = targetProvince,
                tripDays = tripDays
            )

            ragResult = ragService.chat(
                token = token,
                history = conversationHistory.dropLast(1),
                newMessage = strictQuery,
                targetProvince = targetProvince,
                targetCity = targetCity
            )

            ragFailed = isRagFailed(ragResult)

            hardMismatch = if (!ragFailed) {
                isProvinceMismatch(
                    targetProvince = targetProvince,
                    places = ragResult.places
                )
            } else {
                false
            }
        }

        if (!ragFailed && hardMismatch) {
            return ChatbotResult(
                answer = "Mình chưa tìm được địa điểm phù hợp đúng với ${targetProvince ?: "khu vực bạn yêu cầu"} trong dữ liệu UnuTrip. Bạn thử nhập rõ hơn tên tỉnh/thành hoặc chọn khu vực khác nhé.",
                places = emptyList(),
                tripDaysHint = computeTripDaysHint(userText, tripDays)
            )
        }

        if (!ragFailed) {
            val validation = geminiService.validateRagOutputFull(
                token = token,
                userMessage = buildValidationUserMessage(
                    userText = userText,
                    targetProvince = targetProvince,
                    tripDays = tripDays
                ),
                preparedQuery = preparedQuery,
                ragAnswer = ragResult.answer,
                places = ragResult.places
            )

            if (!validation.valid && !validation.correctedQuery.isNullOrBlank()) {
                ragResult = ragService.chat(
                    token = token,
                    history = conversationHistory.dropLast(1),
                    newMessage = validation.correctedQuery,
                    targetProvince = targetProvince,
                    targetCity = targetCity
                )

                ragFailed = isRagFailed(ragResult)

                val secondMismatch = if (!ragFailed) {
                    isProvinceMismatch(
                        targetProvince = targetProvince,
                        places = ragResult.places
                    )
                } else {
                    false
                }

                if (!ragFailed && secondMismatch) {
                    return ChatbotResult(
                        answer = "Mình chưa tìm được địa điểm phù hợp đúng với ${targetProvince ?: "khu vực bạn yêu cầu"} trong dữ liệu UnuTrip. Bạn thử nhập rõ hơn tên tỉnh/thành hoặc chọn khu vực khác nhé.",
                        places = emptyList(),
                        tripDaysHint = computeTripDaysHint(userText, tripDays)
                    )
                }
            } else if (!validation.valid) {
                return ChatbotResult(
                    answer = "Mình chưa tìm được địa điểm phù hợp đúng với yêu cầu của bạn trong dữ liệu UnuTrip. Bạn thử nhập rõ hơn tên tỉnh/thành hoặc chọn khu vực khác nhé.",
                    places = emptyList(),
                    tripDaysHint = computeTripDaysHint(userText, tripDays)
                )
            }
        }

        val tripHint = computeTripDaysHint(userText, tripDays)
        return if (ragFailed) {
            geminiService.fallbackChat(
                token = token,
                userMessage = userText
            ).copy(tripDaysHint = tripHint)
        } else {
            geminiService.repairRagAnswer(
                token = token,
                userMessage = buildRepairUserMessage(
                    userText = userText,
                    targetProvince = targetProvince,
                    tripDays = tripDays
                ),
                ragAnswer = ragResult.answer,
                places = ragResult.places,
                tripDays = tripDays
            ).copy(tripDaysHint = tripHint)
        }
    }

    private fun computeTripDaysHint(userText: String, tripDays: Int?): Int? {
        return (tripDays ?: extractTripDaysFromText(userText) ?: lastTripDays)?.coerceIn(1, 10)
    }

    private fun updateConversationContext(
        targetProvince: String?,
        targetCity: String?,
        tripDays: Int?
    ) {
        if (!targetProvince.isNullOrBlank()) {
            lastTargetProvince = targetProvince
        }

        if (!targetCity.isNullOrBlank()) {
            lastTargetCity = targetCity
        }

        if (tripDays != null && tripDays > 0) {
            lastTripDays = tripDays
        }
    }

    private fun buildValidationUserMessage(
        userText: String,
        targetProvince: String?,
        tripDays: Int?
    ): String {
        return buildString {
            append(userText)

            if (!targetProvince.isNullOrBlank()) {
                append("\nNgữ cảnh tỉnh/thành cần giữ đúng: $targetProvince.")
            }

            if (tripDays != null && tripDays > 0) {
                append("\nNgữ cảnh thời lượng: $tripDays ngày ${maxOf(tripDays - 1, 0)} đêm.")
            }
        }
    }

    private fun buildRepairUserMessage(
        userText: String,
        targetProvince: String?,
        tripDays: Int?
    ): String {
        return buildString {
            append(userText)

            if (!targetProvince.isNullOrBlank()) {
                append("\nNgữ cảnh hội thoại: người dùng đang hỏi về chuyến đi $targetProvince.")
            }

            if (tripDays != null && tripDays > 0) {
                append("\nYêu cầu bắt buộc: lập lịch trình $tripDays ngày ${maxOf(tripDays - 1, 0)} đêm.")
            }
        }
    }

    private fun isRagFailed(result: ChatbotResult): Boolean {
        return result.answer.startsWith("Không gọi được RAG") ||
                result.answer.startsWith("RAG không trả được") ||
                result.answer.isBlank()
    }

    private fun normalizeVietnamese(text: String): String = ChatTripDayParser.normalize(text)

    private fun extractProvinceFromText(text: String): String? {
        val normalized = normalizeVietnamese(text)

        val provinceMap = linkedMapOf(
            "thai nguyen" to "Thái Nguyên",
            "ha noi" to "Hà Nội",
            "da nang" to "Đà Nẵng",
            "hoi an" to "Quảng Nam",
            "quang nam" to "Quảng Nam",
            "hue" to "Thừa Thiên Huế",
            "thua thien hue" to "Thừa Thiên Huế",
            "ho chi minh" to "TP. Hồ Chí Minh",
            "tp hcm" to "TP. Hồ Chí Minh",
            "sai gon" to "TP. Hồ Chí Minh",
            "nha trang" to "Khánh Hòa",
            "khanh hoa" to "Khánh Hòa",
            "da lat" to "Lâm Đồng",
            "lam dong" to "Lâm Đồng",
            "phu quoc" to "Kiên Giang",
            "kien giang" to "Kiên Giang",
            "can tho" to "Cần Thơ",
            "hai phong" to "Hải Phòng",
            "ninh binh" to "Ninh Bình",
            "quang ninh" to "Quảng Ninh",
            "ha long" to "Quảng Ninh",
            "lao cai" to "Lào Cai",
            "sapa" to "Lào Cai",
            "sa pa" to "Lào Cai"
        )

        return provinceMap.entries.firstOrNull { (keyword, _) ->
            normalized.contains(keyword)
        }?.value
    }

    private fun extractTripDaysFromText(text: String): Int? = ChatTripDayParser.extractTripDays(text)

    private fun isFollowUpTravelRequest(text: String): Boolean {
        val normalized = normalizeVietnamese(text)

        return normalized.contains("lich trinh") ||
                normalized.contains("ngay") ||
                normalized.contains("dem") ||
                normalized.contains("di ") ||
                normalized.startsWith("di") ||
                normalized.contains("an gi") ||
                normalized.contains("choi gi") ||
                normalized.contains("them dia diem") ||
                normalized.contains("goi y them") ||
                normalized.contains("sap xep") ||
                normalized.contains("chia ngay") ||
                normalized.contains("ke hoach")
    }

    private fun buildContextAwareRagQuery(
        userText: String,
        preparedQuery: String,
        targetProvince: String?,
        tripDays: Int?,
        isFollowUp: Boolean
    ): String {
        if (targetProvince.isNullOrBlank()) {
            return preparedQuery
        }

        if (!isFollowUp) {
            return preparedQuery
        }

        val tripText = if (tripDays != null && tripDays > 0) {
            "$tripDays ngày ${maxOf(tripDays - 1, 0)} đêm"
        } else {
            ""
        }

        return """
            Ngữ cảnh hội thoại trước đó: người dùng đang hỏi về chuyến đi $targetProvince.
            Yêu cầu mới của người dùng: $userText.
            Hãy gợi ý lịch trình du lịch $targetProvince $tripText.
            Chỉ lấy địa điểm thuộc $targetProvince.
            Không lấy địa điểm ở tỉnh/thành khác.
            Ưu tiên địa điểm phù hợp để tạo lịch trình.
        """.trimIndent()
    }

    private fun isProvinceMismatch(
        targetProvince: String?,
        places: List<com.smarttravel.data.model.ChatPlace>
    ): Boolean {
        if (targetProvince.isNullOrBlank()) return false
        if (places.isEmpty()) return true

        val target = normalizeVietnamese(targetProvince)

        val matchedCount = places.count { place ->
            val province = normalizeVietnamese(place.province.orEmpty())
            val city = normalizeVietnamese(place.city.orEmpty())
            val area = normalizeVietnamese(place.area.orEmpty())
            val name = normalizeVietnamese(place.name.orEmpty())

            province == target ||
                    province.contains(target) ||
                    target.contains(province) ||
                    city.contains(target) ||
                    area.contains(target) ||
                    name.contains(target)
        }

        return matchedCount < places.size / 2.0
    }

    private fun buildStrictProvinceQuery(
        userText: String,
        targetProvince: String,
        tripDays: Int?
    ): String {
        val tripText = if (tripDays != null && tripDays > 0) {
            "$tripDays ngày ${maxOf(tripDays - 1, 0)} đêm"
        } else {
            ""
        }

        return """
            Gợi ý lịch trình du lịch ở $targetProvince $tripText.
            Chỉ lấy các địa điểm thuộc $targetProvince.
            Không lấy địa điểm ở Đà Nẵng, Khánh Hòa, Quảng Bình, Thanh Hóa, Long An, Bình Dương, Yên Bái, Bạc Liêu, Bắc Ninh hoặc tỉnh/thành khác.
            Ưu tiên địa điểm tham quan phù hợp để tạo lịch trình.
            Yêu cầu gốc của người dùng: $userText
        """.trimIndent()
    }

    fun clearChat() {
        conversationHistory.clear()

        lastTargetProvince = null
        lastTargetCity = null
        lastTripDays = null

        val welcome = ChatMessage(
            role = "model",
            content = "Chat mới đã được bắt đầu. Tôi có thể giúp gì cho bạn? 😊"
        )

        conversationHistory.add(welcome)
        _messages.value = conversationHistory.toList()
    }
}