package com.smarttravel.utils

import com.smarttravel.data.model.WeatherInfo
import com.smarttravel.data.model.ForecastDay
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.URL

/**
 * WeatherService dùng Open-Meteo API — HOÀN TOÀN MIỄN PHÍ, không cần API key
 * Docs: https://open-meteo.com/en/docs
 *
 * Để lấy tọa độ từ tên thành phố, dùng Nominatim (OpenStreetMap) — cũng miễn phí
 */
object WeatherService {

    // Tọa độ các thành phố Việt Nam phổ biến
    private val cityCoords = mapOf(
        "hanoi"    to Pair(21.0285, 105.8542),
        "hà nội"   to Pair(21.0285, 105.8542),
        "danang"   to Pair(16.0544, 108.2022),
        "đà nẵng"  to Pair(16.0544, 108.2022),
        "hoian"    to Pair(15.8800, 108.3380),
        "hội an"   to Pair(15.8800, 108.3380),
        "hue"      to Pair(16.4637, 107.5909),
        "huế"      to Pair(16.4637, 107.5909),
        "halong"   to Pair(20.9517, 107.0840),
        "hạ long"  to Pair(20.9517, 107.0840),
        "sapa"     to Pair(22.3364, 103.8438),
        "sa pa"    to Pair(22.3364, 103.8438),
        "nhatrang" to Pair(12.2388, 109.1967),
        "nha trang" to Pair(12.2388, 109.1967),
        "phuquoc"  to Pair(10.2899, 103.9840),
        "phú quốc" to Pair(10.2899, 103.9840),
        "dalat"    to Pair(11.9404, 108.4583),
        "đà lạt"   to Pair(11.9404, 108.4583),
        "hochiminh" to Pair(10.8231, 106.6297),
        "hồ chí minh" to Pair(10.8231, 106.6297),
        "saigon"   to Pair(10.8231, 106.6297),
    )

    suspend fun getWeather(cityName: String): Resource<WeatherInfo> = withContext(Dispatchers.IO) {
        try {
            val key = cityName.lowercase().trim()
            val (lat, lng) = cityCoords.entries
                .firstOrNull { key.contains(it.key) }
                ?.value
                ?: Pair(21.0285, 105.8542) // Default: Hà Nội

            // Open-Meteo API — miễn phí, không cần key
            val url = "https://api.open-meteo.com/v1/forecast" +
                "?latitude=$lat&longitude=$lng" +
                "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m" +
                "&daily=weather_code,temperature_2m_max,temperature_2m_min" +
                "&timezone=Asia%2FHo_Chi_Minh&forecast_days=5"

            val json = JSONObject(URL(url).readText())
            val current = json.getJSONObject("current")
            val daily   = json.getJSONObject("daily")

            val tempNow  = current.getDouble("temperature_2m")
            val humidity = current.getInt("relative_humidity_2m")
            val wCode    = current.getInt("weather_code")
            val wind     = current.getDouble("wind_speed_10m")

            val dates    = daily.getJSONArray("time")
            val maxTemps = daily.getJSONArray("temperature_2m_max")
            val minTemps = daily.getJSONArray("temperature_2m_min")
            val codes    = daily.getJSONArray("weather_code")

            val forecast = (0 until minOf(5, dates.length())).map { i ->
                ForecastDay(
                    date        = dates.getString(i),
                    tempMin     = minTemps.getDouble(i),
                    tempMax     = maxTemps.getDouble(i),
                    description = weatherCodeToDesc(codes.getInt(i)),
                    icon        = weatherCodeToIcon(codes.getInt(i))
                )
            }

            Resource.Success(WeatherInfo(
                city        = cityName,
                temperature = tempNow,
                description = weatherCodeToDesc(wCode),
                humidity    = humidity,
                icon        = weatherCodeToIcon(wCode),
                forecast    = forecast
            ))
        } catch (e: Exception) {
            Resource.Error("Không thể lấy thông tin thời tiết: ${e.message}")
        }
    }

    private fun weatherCodeToDesc(code: Int): String = when (code) {
        0         -> "Trời quang"
        1, 2, 3   -> "Ít mây"
        45, 48    -> "Sương mù"
        51, 53, 55 -> "Mưa phùn"
        61, 63, 65 -> "Mưa"
        71, 73, 75 -> "Tuyết"
        80, 81, 82 -> "Mưa rào"
        95        -> "Giông"
        96, 99    -> "Giông có mưa đá"
        else      -> "Không rõ"
    }

    private fun weatherCodeToIcon(code: Int): String = when (code) {
        0         -> "01d"
        1, 2, 3   -> "02d"
        45, 48    -> "50d"
        51, 53, 55 -> "09d"
        61, 63, 65 -> "10d"
        71, 73, 75 -> "13d"
        80, 81, 82 -> "09d"
        95, 96, 99 -> "11d"
        else       -> "01d"
    }
}
