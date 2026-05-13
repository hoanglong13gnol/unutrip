package com.smarttravel.utils

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

object FileUtils {
    fun getPartFromUri(context: Context, uri: Uri, partName: String): MultipartBody.Part? {
        val contentResolver = context.contentResolver
        val fileName = getFileName(context, uri) ?: "temp_image.jpg"
        val tempFile = File(context.cacheDir, fileName)
        
        try {
            val inputStream: InputStream? = contentResolver.openInputStream(uri)
            val outputStream = FileOutputStream(tempFile)
            inputStream?.copyTo(outputStream)
            inputStream?.close()
            outputStream.close()
            
            val requestFile = tempFile.asRequestBody(
                (contentResolver.getType(uri) ?: "image/*").toMediaTypeOrNull()
            )
            return MultipartBody.Part.createFormData(partName, tempFile.name, requestFile)
        } catch (e: Exception) {
            e.printStackTrace()
            return null
        }
    }

    private fun getFileName(context: Context, uri: Uri): String? {
        var result: String? = null
        if (uri.scheme == "content") {
            val cursor = context.contentResolver.query(uri, null, null, null, null)
            try {
                if (cursor != null && cursor.moveToFirst()) {
                    result = cursor.getString(cursor.getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME))
                }
            } finally {
                cursor?.close()
            }
        }
        if (result == null) {
            result = uri.path
            val cut = result?.lastIndexOf('/')
            if (cut != -1) {
                result = result?.substring(cut!! + 1)
            }
        }
        return result
    }
}
