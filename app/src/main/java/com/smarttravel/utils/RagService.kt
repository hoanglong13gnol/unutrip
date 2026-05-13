package com.smarttravel.utils

import android.util.Log
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.ChatMessage
import com.smarttravel.data.model.ChatRequest
import com.smarttravel.data.model.ChatbotResult

class RagService {

    private val api = RetrofitClient.apiService

    suspend fun chat(
        token: String,
        @Suppress("UNUSED_PARAMETER")
        history: List<ChatMessage>,
        newMessage: String,
        targetProvince: String? = null,
        targetCity: String? = null
    ): ChatbotResult {
        return try {
            val cleanToken = token.trim()
            val authHeader = if (cleanToken.startsWith("Bearer ")) {
                cleanToken
            } else {
                "Bearer $cleanToken"
            }

            val request = ChatRequest(
                message = newMessage,
                top_k = 8,
                mode = "balanced",
                targetProvince = targetProvince,
                targetCity = targetCity
            )

            val response = api.chat(
                token = authHeader,
                request = request
            )

            if (response.isSuccessful && response.body()?.success == true) {
                val body = response.body()
                val places = body?.places ?: emptyList()

                Log.d("RAG_PLACES", "places size=${places.size}")
                places.take(5).forEachIndexed { index, place ->
                    Log.d(
                        "RAG_PLACES",
                        "#$index rawPlaceId=${place.rawPlaceId} name=${place.name} province=${place.province}"
                    )
                }

                ChatbotResult(
                    answer = body?.answer ?: "Xin lỗi, tôi không nhận được câu trả lời.",
                    places = places
                )
            } else {
                Log.d("RAG_PLACES", "RAG failed code=${response.code()} message=${response.message()}")

                ChatbotResult(
                    answer = "RAG không trả được câu trả lời: ${response.body()?.message ?: response.message()}",
                    places = emptyList()
                )
            }
        } catch (e: Exception) {
            Log.e("RAG_PLACES", "RAG exception", e)

            ChatbotResult(
                answer = "Không gọi được RAG: ${e.message}",
                places = emptyList()
            )
        }
    }
}