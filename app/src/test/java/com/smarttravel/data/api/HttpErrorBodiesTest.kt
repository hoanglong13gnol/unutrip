package com.smarttravel.data.api

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import retrofit2.Response

class HttpErrorBodiesTest {

    @Test
    fun parseErrorMessageOrNull_readsJsonMessageField() {
        val body = """{"message":"Không tìm thấy","data":null}"""
            .toResponseBody("application/json".toMediaType())
        val response = Response.error<Any>(404, body)
        assertEquals("Không tìm thấy", response.parseErrorMessageOrNull())
    }

    @Test
    fun parseErrorMessageOrNull_emptyBodyReturnsNull() {
        val body = "".toResponseBody("application/json".toMediaType())
        val response = Response.error<Any>(400, body)
        assertNull(response.parseErrorMessageOrNull())
    }

    @Test
    fun parseErrorMessageOrNull_plainTextTruncatesTo280() {
        val long = "x".repeat(400)
        val body = long.toResponseBody("text/plain".toMediaType())
        val response = Response.error<Any>(500, body)
        assertEquals(280, response.parseErrorMessageOrNull()?.length)
    }
}
