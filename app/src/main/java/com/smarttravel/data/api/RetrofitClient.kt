package com.smarttravel.data.api

import android.util.Log
import com.smarttravel.BuildConfig
import okhttp3.Cache
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.util.concurrent.TimeUnit

object RetrofitClient {

    private const val TAG = "RetrofitClient"
    private const val CACHE_SIZE_BYTES = 10L * 1024 * 1024

    @Volatile
    private var httpCacheDir: File? = null

    /**
     * Gọi một lần từ [com.smarttravel.SmartTravelApp] để bật cache HTTP (GET) trong [cacheDir]/http_cache.
     */
    fun install(context: android.content.Context) {
        if (httpCacheDir != null) return
        synchronized(this) {
            if (httpCacheDir != null) return
            httpCacheDir = File(context.applicationContext.cacheDir, "http_cache").apply {
                if (!exists()) mkdirs()
            }
        }
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    }

    private val errorLoggingInterceptor = okhttp3.Interceptor { chain ->
        val request = chain.request()
        val response = chain.proceed(request)
        if (!response.isSuccessful) {
            Log.e("RetrofitError", "HTTP ${response.code} ${response.message} for URL: ${request.url}")
            val bodyString = response.peekBody(Long.MAX_VALUE).string()
            Log.e("RetrofitError", "Error Body: $bodyString")
        }
        response
    }

    private val okHttpClient by lazy {
        val builder = OkHttpClient.Builder()
            .addInterceptor(RequestHeadersInterceptor())
            .addInterceptor(loggingInterceptor)
            .addInterceptor(errorLoggingInterceptor)
            .connectTimeout(120, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)

        httpCacheDir?.let { dir ->
            try {
                builder.cache(Cache(dir, CACHE_SIZE_BYTES))
            } catch (e: Exception) {
                Log.w(TAG, "Không khởi tạo HTTP cache", e)
            }
        }

        builder.build()
    }

    val apiService: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
