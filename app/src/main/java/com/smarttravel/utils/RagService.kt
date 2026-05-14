package com.smarttravel.utils

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.ChatMessage
import com.smarttravel.data.model.ChatRequest
import com.smarttravel.data.model.ChatbotResult
import retrofit2.Response

class RagService {

    private val api = RetrofitClient.apiService
    private val gson = Gson()

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

                Log.d(TAG, "RAG ok places=${places.size}")
                places.take(5).forEachIndexed { index, place ->
                    Log.d(
                        TAG,
                        "#$index rawPlaceId=${place.rawPlaceId} name=${place.name} province=${place.province}"
                    )
                }

                ChatbotResult(
                    answer = body?.answer ?: "Xin lỗi, tôi không nhận được câu trả lời.",
                    places = places
                )
            } else {
                val detail = extractServerMessage(response)
                    ?: response.body()?.message
                    ?: response.message()

                Log.w(TAG, "RAG HTTP ${response.code()} detail=$detail")

                ChatbotResult(
                    answer = "RAG không trả được câu trả lời (${response.code()}): $detail",
                    places = emptyList()
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "RAG exception", e)

            ChatbotResult(
                answer = "Không gọi được RAG: ${e.message}",
                places = emptyList()
            )
        }
    }

    private fun extractServerMessage(response: Response<*>): String? {
        val raw = response.errorBody()?.string()?.trim().orEmpty()
        if (raw.isEmpty()) return null
        return try {
            val obj = gson.fromJson(raw, JsonObject::class.java)
            when {
                obj.has("message") && !obj.get("message").isJsonNull ->
                    obj.get("message").asString
                obj.has("detail") && obj.get("detail").isJsonPrimitive ->
                    obj.get("detail").asString
                else -> raw.take(280)
            }
        } catch (_: Exception) {
            raw.take(280)
        }
    }

    private companion object {
        private const val TAG = "RagService"
    }
}
