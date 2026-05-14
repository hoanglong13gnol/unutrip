package com.smarttravel

import android.app.Application
import android.os.StrictMode
import android.util.Log
import com.smarttravel.data.api.RetrofitClient

/**
 * Khởi tạo toàn process: [RetrofitClient.install] (HTTP cache), StrictMode khi debug.
 */
class SmartTravelApp : Application() {

    override fun onCreate() {
        super.onCreate()
        RetrofitClient.install(this)
        if (BuildConfig.DEBUG) {
            StrictMode.setThreadPolicy(
                StrictMode.ThreadPolicy.Builder()
                    .detectDiskReads()
                    .detectDiskWrites()
                    .detectNetwork()
                    .penaltyLog()
                    .build()
            )
            Log.d(TAG, "SmartTravel ${BuildConfig.VERSION_NAME} (${BuildConfig.BUILD_TYPE})")
        }
    }

    private companion object {
        private const val TAG = "SmartTravelApp"
    }
}
