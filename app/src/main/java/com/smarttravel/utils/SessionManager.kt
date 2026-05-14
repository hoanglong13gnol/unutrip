package com.smarttravel.utils

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.google.gson.Gson
import com.smarttravel.data.model.User

/**
 * Session an toàn hơn: [EncryptedSharedPreferences] (AES-GCM).
 * Dùng [MasterKeys] + overload `create(name, alias, context, …)` (tương thích security-crypto 1.0.x).
 * Tự động chuyển dữ liệu từ prefs legacy [LEGACY_PREF_NAME] một lần.
 */
class SessionManager private constructor(context: Context) {

    private val prefs: SharedPreferences = createEncryptedPrefs(context.applicationContext)
    private val gson = Gson()

    companion object {
        private const val LEGACY_PREF_NAME = "SmartTravelSession"
        private const val ENCRYPTED_PREF_NAME = "SmartTravelSession_secure"
        private const val KEY_TOKEN = "auth_token"
        private const val KEY_USER = "user_data"
        private const val KEY_IS_LOGGED_IN = "is_logged_in"

        private val lock = Any()

        @Volatile
        private var INSTANCE: SessionManager? = null

        fun getInstance(context: Context): SessionManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: SessionManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    private fun createEncryptedPrefs(context: Context): SharedPreferences {
        synchronized(lock) {
            val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)

            val encrypted = EncryptedSharedPreferences.create(
                ENCRYPTED_PREF_NAME,
                masterKeyAlias,
                context,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )

            migrateLegacyIfNeeded(context, encrypted)
            return encrypted
        }
    }

    private fun migrateLegacyIfNeeded(context: Context, encrypted: SharedPreferences) {
        val legacy = context.getSharedPreferences(LEGACY_PREF_NAME, Context.MODE_PRIVATE)
        if (legacy.all.isEmpty()) return
        if (encrypted.all.isNotEmpty()) {
            legacy.edit().clear().apply()
            return
        }

        val token = legacy.getString(KEY_TOKEN, null)
        val userJson = legacy.getString(KEY_USER, null)
        val loggedIn = legacy.getBoolean(KEY_IS_LOGGED_IN, false)

        encrypted.edit().apply {
            if (!token.isNullOrBlank()) putString(KEY_TOKEN, token)
            if (!userJson.isNullOrBlank()) putString(KEY_USER, userJson)
            putBoolean(KEY_IS_LOGGED_IN, loggedIn)
            apply()
        }
        legacy.edit().clear().apply()
    }

    fun saveSession(token: String, user: User) {
        prefs.edit().apply {
            putString(KEY_TOKEN, token)
            putString(KEY_USER, gson.toJson(user))
            putBoolean(KEY_IS_LOGGED_IN, true)
            apply()
        }
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun getBearerToken(): String = "Bearer ${getToken() ?: ""}"

    fun getUser(): User? {
        val json = prefs.getString(KEY_USER, null) ?: return null
        return gson.fromJson(json, User::class.java)
    }

    fun isLoggedIn(): Boolean = prefs.getBoolean(KEY_IS_LOGGED_IN, false)

    fun clearSession() {
        prefs.edit().clear().apply()
    }

    fun updateUser(user: User) {
        prefs.edit().putString(KEY_USER, gson.toJson(user)).apply()
    }
}
