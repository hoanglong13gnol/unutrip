package com.smarttravel.utils

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast

object MapIntentHelper {

    fun openPlace(
        context: Context,
        lat: Double?,
        lng: Double?,
        label: String? = null
    ) {
        if (!isValidLatLng(lat, lng)) {
            Toast.makeText(context, "Địa điểm chưa có tọa độ", Toast.LENGTH_SHORT).show()
            return
        }

        val uri = Uri.parse(
            "https://www.google.com/maps/search/?api=1&query=$lat,$lng"
        )

        context.startActivity(Intent(Intent.ACTION_VIEW, uri))
    }

    fun openNavigation(
        context: Context,
        lat: Double?,
        lng: Double?,
        label: String? = null
    ) {
        if (!isValidLatLng(lat, lng)) {
            Toast.makeText(context, "Địa điểm chưa có tọa độ", Toast.LENGTH_SHORT).show()
            return
        }

        val uri = Uri.parse("google.navigation:q=$lat,$lng&mode=d")
        val intent = Intent(Intent.ACTION_VIEW, uri).apply {
            setPackage("com.google.android.apps.maps")
        }

        try {
            context.startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            val fallbackUri = Uri.parse(
                "https://www.google.com/maps/dir/?api=1" +
                        "&destination=$lat,$lng" +
                        "&travelmode=driving"
            )
            context.startActivity(Intent(Intent.ACTION_VIEW, fallbackUri))
        }
    }

    fun openRoute(
        context: Context,
        points: List<Pair<Double, Double>>
    ) {
        if (points.isEmpty()) {
            Toast.makeText(context, "Chưa có địa điểm để chỉ đường", Toast.LENGTH_SHORT).show()
            return
        }

        if (points.size == 1) {
            openNavigation(context, points.first().first, points.first().second)
            return
        }

        val origin = "${points.first().first},${points.first().second}"
        val destination = "${points.last().first},${points.last().second}"
        val waypoints = points.drop(1).dropLast(1).joinToString("|") {
            "${it.first},${it.second}"
        }

        val url = buildString {
            append("https://www.google.com/maps/dir/?api=1")
            append("&origin=${Uri.encode(origin)}")
            append("&destination=${Uri.encode(destination)}")
            if (waypoints.isNotBlank()) {
                append("&waypoints=${Uri.encode(waypoints)}")
            }
            append("&travelmode=driving")
        }

        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    private fun isValidLatLng(lat: Double?, lng: Double?): Boolean {
        if (lat == null || lng == null) return false
        return lat in -90.0..90.0 && lng in -180.0..180.0
    }
}