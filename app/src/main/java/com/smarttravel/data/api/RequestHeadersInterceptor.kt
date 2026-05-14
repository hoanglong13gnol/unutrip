package com.smarttravel.data.api

import com.smarttravel.BuildConfig
import okhttp3.Interceptor
import okhttp3.Response
import java.util.UUID

/**
 * Adds correlation headers so Node/FastAPI logs can be tied to a single app request.
 */
class RequestHeadersInterceptor : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val requestId = request.header(HEADER_REQUEST_ID) ?: UUID.randomUUID().toString()
        val next = request.newBuilder()
            .header(HEADER_REQUEST_ID, requestId)
            .header(HEADER_CLIENT, "${BuildConfig.APPLICATION_ID}/${BuildConfig.VERSION_NAME}")
            .build()
        return chain.proceed(next)
    }

    private companion object {
        private const val HEADER_REQUEST_ID = "X-Request-ID"
        private const val HEADER_CLIENT = "X-Client-Version"
    }
}
