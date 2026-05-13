package com.smarttravel.utils

import com.google.gson.Gson
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.AIDayPlan
import com.smarttravel.data.model.AIItemPlan
import com.smarttravel.data.model.AISuggestRequest
import com.smarttravel.data.model.ChatPlace
import com.smarttravel.data.model.ChatbotResult
import com.smarttravel.data.model.GeminiPreparedQuery
import com.smarttravel.data.model.GeminiRagValidation
import com.smarttravel.data.model.ItineraryDay
import com.smarttravel.data.model.ItineraryItem
import com.smarttravel.data.model.SaveAIItineraryRequest

class GeminiService {

    private val api = RetrofitClient.apiService
    private val gson = Gson()

    suspend fun fallbackChat(
        token: String,
        userMessage: String
    ): ChatbotResult {
        return try {
            val authHeader = buildAuthHeader(token)

            val response = api.chatFallback(
                token = authHeader,
                body = mapOf("message" to userMessage)
            )

            if (response.isSuccessful && response.body()?.success == true) {
                ChatbotResult(
                    answer = response.body()?.answer ?: "Gemini không trả được câu trả lời.",
                    places = emptyList()
                )
            } else {
                ChatbotResult(
                    answer = "Gemini fallback lỗi: ${response.body()?.message ?: response.message()}",
                    places = emptyList()
                )
            }
        } catch (e: Exception) {
            ChatbotResult(
                answer = "Gemini fallback lỗi: ${e.message}",
                places = emptyList()
            )
        }
    }

    suspend fun prepareRagQuery(
        token: String,
        userMessage: String
    ): GeminiPreparedQuery {
        return try {
            val authHeader = buildAuthHeader(token)

            val prompt = """
                Bạn là bộ chuẩn hóa truy vấn cho hệ thống RAG du lịch UnuTrip.

                Nhiệm vụ:
                - Đọc USER_MESSAGE.
                - Viết lại thành câu truy vấn rõ ràng, cụ thể, dễ hiểu cho RAG.
                - Nếu người dùng nhắc tỉnh/thành, phải giữ đúng tỉnh/thành đó.
                - Nếu người dùng viết không dấu, hãy tự khôi phục tiếng Việt có dấu nếu chắc chắn.
                - Nếu người dùng nhắc số ngày/đêm, phải giữ đúng số ngày.
                - Nếu người dùng muốn tạo lịch trình, query phải nêu rõ "lịch trình".
                - Không tự thêm tỉnh/thành khác.
                - Không tự thêm địa điểm cụ thể nếu người dùng chưa nói.
                - Trả về JSON thuần, không markdown, không giải thích.

                JSON schema:
                {
                  "query": "string",
                  "targetProvince": "string hoặc null",
                  "targetCity": "string hoặc null",
                  "tripDays": number hoặc null,
                  "intent": "itinerary|places|food|transport|general"
                }

                Ví dụ 1:
                USER_MESSAGE: "tao lich trinh di thai nguyen 3 ngay 2 dem"
                OUTPUT:
                {
                  "query": "Gợi ý lịch trình du lịch Thái Nguyên 3 ngày 2 đêm. Chỉ lấy địa điểm thuộc Thái Nguyên, ưu tiên địa điểm tham quan phù hợp để tạo lịch trình.",
                  "targetProvince": "Thái Nguyên",
                  "targetCity": null,
                  "tripDays": 3,
                  "intent": "itinerary"
                }

                Ví dụ 2:
                USER_MESSAGE: "goi y da nang"
                OUTPUT:
                {
                  "query": "Gợi ý các địa điểm du lịch ở Đà Nẵng. Chỉ lấy địa điểm thuộc Đà Nẵng.",
                  "targetProvince": "Đà Nẵng",
                  "targetCity": null,
                  "tripDays": null,
                  "intent": "places"
                }

                USER_MESSAGE:
                $userMessage
            """.trimIndent()

            val response = api.chatFallback(
                token = authHeader,
                body = mapOf("message" to prompt)
            )

            val raw = cleanJsonText(response.body()?.answer.orEmpty())

            if (response.isSuccessful && response.body()?.success == true && raw.isNotBlank()) {
                runCatching {
                    gson.fromJson(raw, GeminiPreparedQuery::class.java)
                }.getOrElse {
                    fallbackPreparedQuery(userMessage)
                }
            } else {
                fallbackPreparedQuery(userMessage)
            }
        } catch (e: Exception) {
            fallbackPreparedQuery(userMessage)
        }
    }

    suspend fun validateRagOutputFull(
        token: String,
        userMessage: String,
        preparedQuery: GeminiPreparedQuery,
        ragAnswer: String,
        places: List<ChatPlace>
    ): GeminiRagValidation {
        return try {
            val authHeader = buildAuthHeader(token)

            val placesText = places.take(12).joinToString("\n") { place ->
                "- name=${place.name ?: ""}, province=${place.province ?: ""}, city=${place.city ?: ""}, area=${place.area ?: ""}, place_id=${place.rawPlaceId ?: ""}"
            }

            val prompt = """
                Bạn là bộ kiểm tra chất lượng output RAG du lịch UnuTrip.

                Nhiệm vụ:
                - Kiểm tra RAG_OUTPUT và PLACES có trả lời đúng USER_MESSAGE/PREPARED_QUERY không.
                - Nếu user yêu cầu một tỉnh/thành cụ thể, đa số PLACES phải thuộc đúng tỉnh/thành đó.
                - Nếu targetProvince là "Thái Nguyên" mà PLACES là Long An, Bình Dương, Yên Bái, Bạc Liêu, Bắc Ninh... thì valid=false.
                - Nếu targetProvince là "Đà Nẵng" mà PLACES ở tỉnh khác thì valid=false.
                - Nếu user hỏi lịch trình, output phải có địa điểm phù hợp để tạo lịch trình.
                - Không chấp nhận output trả địa điểm ở tỉnh/thành khác với yêu cầu.
                - Trả về JSON thuần, không markdown, không giải thích.

                JSON schema:
                {
                  "valid": true/false,
                  "reason": "lý do ngắn",
                  "correctedQuery": "query sửa lại nếu valid=false, ngược lại null"
                }

                Nếu valid=false:
                - correctedQuery phải ép rất rõ tỉnh/thành đúng.
                - Ví dụ: "Tìm lại các địa điểm du lịch chỉ thuộc tỉnh Thái Nguyên. Không lấy địa điểm ở tỉnh/thành khác. Ưu tiên địa điểm phù hợp để tạo lịch trình."

                USER_MESSAGE:
                $userMessage

                PREPARED_QUERY:
                ${gson.toJson(preparedQuery)}

                RAG_OUTPUT:
                $ragAnswer

                PLACES:
                $placesText
            """.trimIndent()

            val response = api.chatFallback(
                token = authHeader,
                body = mapOf("message" to prompt)
            )

            val raw = cleanJsonText(response.body()?.answer.orEmpty())

            if (response.isSuccessful && response.body()?.success == true && raw.isNotBlank()) {
                runCatching {
                    gson.fromJson(raw, GeminiRagValidation::class.java)
                }.getOrElse {
                    GeminiRagValidation(valid = true)
                }
            } else {
                GeminiRagValidation(valid = true)
            }
        } catch (e: Exception) {
            GeminiRagValidation(valid = true)
        }
    }

    suspend fun repairRagAnswer(
        token: String,
        userMessage: String,
        ragAnswer: String,
        places: List<ChatPlace>,
        tripDays: Int? = null
    ): ChatbotResult {
        return try {
            val authHeader = buildAuthHeader(token)

            val safeTripDays = tripDays?.takeIf { it > 0 }
            val dayRule = if (safeTripDays != null && safeTripDays > 1) {
                """
            - Người dùng yêu cầu lịch trình $safeTripDays ngày.
            - BẮT BUỘC chia câu trả lời thành đúng $safeTripDays phần: Ngày 1, Ngày 2${if (safeTripDays >= 3) ", ... Ngày $safeTripDays" else ""}.
            - Không được chỉ liệt kê địa điểm chung.
            - Mỗi ngày nên có 2-3 địa điểm nếu đủ dữ liệu.
            - Nếu số địa điểm ít hơn số ngày, vẫn phải tạo đủ $safeTripDays ngày và ghi nhẹ nhàng rằng có thể bổ sung thêm điểm sau.
            """.trimIndent()
            } else {
                """
            - Nếu người dùng hỏi lịch trình, hãy trình bày theo dạng lịch trình ngắn gọn.
            - Nếu không có số ngày cụ thể, có thể gợi ý theo 1 ngày hoặc danh sách địa điểm.
            """.trimIndent()
            }

            val placesText = places.take(12).joinToString("\n") { place ->
                "- ${place.name ?: "Địa điểm"}" +
                        " | province=${place.province ?: ""}" +
                        " | city=${place.city ?: ""}" +
                        " | area=${place.area ?: ""}" +
                        " | category=${place.categoryMain ?: ""}" +
                        " | place_id=${place.rawPlaceId ?: ""}"
            }

            val prompt = """
            Bạn là trợ lý du lịch UnuTrip.

            Nhiệm vụ:
            - Viết lại câu trả lời cho người dùng sao cho tự nhiên, rõ ràng, thân thiện.
            - Chỉ dùng thông tin từ RAG_RESULT và PLACES.
            - Không tự thêm địa điểm mới.
            - Không đổi tỉnh/thành của địa điểm.
            - Không nhắc tới từ "RAG", "database", "retrieval".
            - Trả lời bằng tiếng Việt.
            - Cuối câu trả lời phải có câu: "Bạn có thể bấm Tạo lịch trình để chỉnh sửa trước khi lưu."

            Quy tắc lịch trình:
            $dayRule

            USER_MESSAGE:
            $userMessage

            RAG_RESULT:
            $ragAnswer

            PLACES:
            $placesText

            Hãy viết lại câu trả lời cuối cùng cho người dùng:
        """.trimIndent()

            val response = api.chatFallback(
                token = authHeader,
                body = mapOf("message" to prompt)
            )

            if (response.isSuccessful && response.body()?.success == true) {
                ChatbotResult(
                    answer = response.body()?.answer ?: ragAnswer,
                    places = places
                )
            } else {
                ChatbotResult(
                    answer = buildTemplateItineraryAnswer(
                        userMessage = userMessage,
                        places = places,
                        tripDays = safeTripDays
                    ),
                    places = places
                )
            }
        } catch (e: Exception) {
            ChatbotResult(
                answer = buildTemplateItineraryAnswer(
                    userMessage = userMessage,
                    places = places,
                    tripDays = tripDays
                ),
                places = places
            )
        }
    }
    private fun buildTemplateItineraryAnswer(
        userMessage: String,
        places: List<ChatPlace>,
        tripDays: Int?
    ): String {
        if (places.isEmpty()) {
            return "Mình chưa tìm được địa điểm phù hợp với yêu cầu của bạn. Bạn thử nhập rõ hơn tỉnh/thành hoặc nhu cầu chuyến đi nhé."
        }

        val safeDays = tripDays?.takeIf { it > 0 } ?: 1

        if (safeDays <= 1) {
            val lines = mutableListOf<String>()
            lines.add("Mình gợi ý một số địa điểm phù hợp cho bạn:")
            lines.add("")

            places.take(8).forEachIndexed { index, place ->
                lines.add("${index + 1}. ${place.name ?: "Địa điểm"} (${place.province ?: "chưa rõ tỉnh/thành"})")
            }

            lines.add("")
            lines.add("Bạn có thể bấm Tạo lịch trình để chỉnh sửa trước khi lưu.")
            return lines.joinToString("\n")
        }

        val lines = mutableListOf<String>()
        lines.add("Mình gợi ý lịch trình $safeDays ngày dựa trên các địa điểm phù hợp:")
        lines.add("")

        for (day in 1..safeDays) {
            val dayPlaces = places
                .filterIndexed { index, _ -> index % safeDays == day - 1 }
                .take(3)

            lines.add("Ngày $day:")

            if (dayPlaces.isEmpty()) {
                lines.add("- Bạn có thể bổ sung thêm địa điểm phù hợp trong màn chỉnh sửa lịch trình.")
            } else {
                dayPlaces.forEach { place ->
                    lines.add("- ${place.name ?: "Địa điểm"} (${place.area ?: place.city ?: place.province ?: "chưa rõ khu vực"})")
                }
            }

            lines.add("")
        }

        lines.add("Bạn có thể bấm Tạo lịch trình để chỉnh sửa trước khi lưu.")
        return lines.joinToString("\n").trim()
    }

    suspend fun suggestItinerary(
        token: String,
        preferences: List<String>,
        startDate: String,
        endDate: String,
        budget: Double?,
        startLocation: String?
    ): String {
        return try {
            val request = AISuggestRequest(
                preferences = preferences,
                startDate = startDate,
                endDate = endDate,
                budget = budget,
                startLocation = startLocation
            )

            val authHeader = buildAuthHeader(token)

            val response = api.suggestItinerary(
                token = authHeader,
                request = request
            )

            if (response.isSuccessful && response.body()?.success == true) {
                val itinerary = response.body()?.itinerary

                if (itinerary != null) {
                    val saveReq = SaveAIItineraryRequest(
                        title = itinerary.title,
                        description = itinerary.description,
                        startDate = itinerary.startDate,
                        endDate = itinerary.endDate,
                        budget = itinerary.estimatedBudget ?: budget,
                        days = itinerary.days?.map { d: ItineraryDay ->
                            AIDayPlan(
                                dayNumber = d.dayNumber,
                                items = d.items.map { i: ItineraryItem ->
                                    AIItemPlan(
                                        destinationId = i.destinationId,
                                        startTime = i.startTime,
                                        endTime = i.endTime,
                                        note = i.note
                                    )
                                }
                            )
                        } ?: emptyList()
                    )

                    gson.toJson(saveReq)
                } else {
                    "{\"error\": \"Không có dữ liệu lịch trình\"}"
                }
            } else {
                "{\"error\": \"Lỗi: ${response.message()}\"}"
            }
        } catch (e: Exception) {
            "{\"error\": \"${e.message}\"}"
        }
    }

    suspend fun analyzeDestination(
        token: String,
        destinationName: String,
        reviews: List<String>
    ): String {
        val prompt = "Hãy tóm tắt địa điểm $destinationName dựa trên các đánh giá: ${
            reviews.take(3).joinToString("; ")
        }"

        return fallbackChat(
            token = token,
            userMessage = prompt
        ).answer
    }

    private fun buildAuthHeader(token: String): String {
        val cleanToken = token.trim()
        return if (cleanToken.startsWith("Bearer ")) {
            cleanToken
        } else {
            "Bearer $cleanToken"
        }
    }

    private fun fallbackPreparedQuery(userMessage: String): GeminiPreparedQuery {
        return GeminiPreparedQuery(
            query = userMessage,
            targetProvince = null,
            targetCity = null,
            tripDays = null,
            intent = null
        )
    }

    private fun cleanJsonText(text: String): String {
        return text
            .replace("```json", "")
            .replace("```", "")
            .trim()
    }
}