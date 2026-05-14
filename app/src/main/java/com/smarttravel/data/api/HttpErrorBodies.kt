package com.smarttravel.data.api

import org.json.JSONObject
import retrofit2.Response

/**
 * Đọc một lần [errorBody] (Retrofit); chỉ gọi khi response không thành công.
 */
fun Response<*>.parseErrorMessageOrNull(): String? {
    val body = errorBody() ?: return null
    return try {
        val raw = body.string().trim()
        if (raw.isEmpty()) return null
        runCatching { JSONObject(raw).optString("message", "") }
            .getOrNull()
            ?.takeIf { it.isNotBlank() }
            ?: raw.take(280).takeIf { it.isNotBlank() }
    } catch (_: Exception) {
        null
    }
}
