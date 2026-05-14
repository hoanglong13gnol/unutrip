package com.smarttravel.data.model

import com.google.gson.annotations.SerializedName

// ==================== AUTH ====================

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val fullName: String,
    val email: String,
    val password: String,
    val phone: String? = null
)

data class AuthResponse(
    val success: Boolean,
    val message: String,
    val token: String? = null,
    val user: User? = null
)

// ==================== USER ====================

data class User(
    val id: Int,
    val fullName: String,
    val email: String,
    val phone: String?,
    val avatar: String?,
    val preferences: List<String>? = null,
    val createdAt: String? = null
)

data class UserStats(
    val itineraryCount: Int,
    val favoriteCount: Int,
    val reviewCount: Int
)

// ==================== DESTINATION ====================

data class Destination(
    val id: Int,
    val name: String,
    val description: String,
    val address: String,
    val city: String,
    val province: String,
    val latitude: Double,
    val longitude: Double,
    // Canonical app codes:
    // beach, mountain, city, heritage, nature, checkin, food, culture, religious
    val category: String,
    val images: List<String>,
    val rating: Float,
    val reviewCount: Int,
    val openTime: String?,
    val closeTime: String?,
    val entryFee: Double?,
    val tags: List<String>,
    var isFavorite: Boolean = false,
    @SerializedName(value = "distanceKm", alternate = ["distance_km"])
    val distanceKm: Double? = null
)

data class DestinationResponse(
    val success: Boolean,
    val data: List<Destination>,
    val total: Int,
    val page: Int,
    val limit: Int
)

data class DestinationDetailResponse(
    val success: Boolean,
    val data: Destination
)

// ==================== REVIEW ====================

data class Review(
    val id: Int,
    val userId: Int,
    val userName: String,
    val userAvatar: String?,
    val destinationId: Int,
    val rating: Float,
    val comment: String,
    val images: List<String>?,
    val createdAt: String
)

data class ReviewRequest(
    val destinationId: Int,
    val rating: Float,
    val comment: String
)

// ==================== ITINERARY ====================

data class Itinerary(
    @SerializedName("id") val id: Int,
    @SerializedName("userId") val userId: Int,
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("totalDays") val totalDays: Int,
    @SerializedName("status") val status: String,
    @SerializedName("days") val days: List<ItineraryDay>?,
    @SerializedName("estimatedBudget") val estimatedBudget: Double?,
    @SerializedName("createdAt") val createdAt: String
)

data class ItineraryDay(
    @SerializedName("id") val id: Int,
    @SerializedName("itineraryId") val itineraryId: Int,
    @SerializedName("dayNumber") val dayNumber: Int,
    @SerializedName("date") val date: String,
    @SerializedName("items") val items: List<ItineraryItem>
)

data class ItineraryItem(
    @SerializedName("id") val id: Int,
    @SerializedName("dayId") val dayId: Int,
    @SerializedName("destinationId") val destinationId: Int,
    @SerializedName("destination") val destination: Destination?,
    @SerializedName("startTime") val startTime: String,
    @SerializedName("endTime") val endTime: String,
    @SerializedName("note") val note: String?,
    @SerializedName("orderIndex") val orderIndex: Int
)

data class CreateItineraryRequest(
    val title: String,
    val description: String?,
    val startDate: String,
    val endDate: String,
    val destinationIds: List<Int>? = null
)

data class UpdateItineraryRequest(
    val title: String,
    val description: String? = null,
    val startDate: String,
    val endDate: String,
    val status: String? = null,
    val estimatedBudget: Double? = null
)

data class AddItineraryItemRequest(
    val destinationId: Int,
    val dayId: Int? = null,
    val startTime: String? = null,
    val endTime: String? = null,
    val note: String? = null
)

data class UpdateItineraryItemRequest(
    val dayId: Int? = null,
    val destinationId: Int? = null,
    val startTime: String? = null,
    val endTime: String? = null,
    val note: String? = null,
    val orderIndex: Int? = null
)

data class ItineraryResponse(
    val success: Boolean,
    val data: List<Itinerary>
)

// ==================== AI - OLD FLOW ====================

data class AISuggestRequest(
    @SerializedName("preferences") val preferences: List<String>,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("budget") val budget: Double?,
    @SerializedName("startLocation") val startLocation: String?
)

data class AISuggestResponse(
    val success: Boolean,
    val itinerary: Itinerary?,
    val message: String
)

data class SaveAIItineraryRequest(
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("budget") val budget: Double?,
    @SerializedName("days") val days: List<AIDayPlan>
)

data class AIDayPlan(
    @SerializedName("dayNumber") val dayNumber: Int,
    @SerializedName("items") val items: List<AIItemPlan>
)

data class AIItemPlan(
    @SerializedName("destinationId") val destinationId: Int,
    @SerializedName("startTime") val startTime: String,
    @SerializedName("endTime") val endTime: String,
    @SerializedName("note") val note: String?
)

// ==================== AI - PREVIEW + SELECTION FLOW ====================

data class AIItineraryPreviewRequest(
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("budget") val budget: Double?,
    @SerializedName("preferences") val preferences: List<String>,
    @SerializedName("province") val province: String? = null,
    /** Gửi cùng câu / truy vấn như chatbot để retrieve RAG khớp luồng chat (tùy chọn). */
    @SerializedName("contextQuery") val contextQuery: String? = null
)

data class AIItineraryPreviewResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("data") val data: AIItineraryPreviewData? = null
)

data class AIItineraryPreviewData(
    @SerializedName("title") val title: String?,
    @SerializedName("summary") val summary: String?,
    @SerializedName("suggestedDestinations") val suggestedDestinations: List<AIRecommendedDestination>
)

data class AIRecommendedDestination(
    @SerializedName("destinationId") val destinationId: Int?,
    @SerializedName("rawPlaceId") val rawPlaceId: String?,
    @SerializedName("name") val name: String?,
    @SerializedName("province") val province: String?,
    @SerializedName("city") val city: String?,
    @SerializedName("area") val area: String?,
    @SerializedName("category") val category: String?,
    @SerializedName("imageUrl") val imageUrl: String?,
    @SerializedName("reason") val reason: String?,
    @SerializedName("estimatedVisitDurationMinutes") val estimatedVisitDurationMinutes: Int?,
    @SerializedName("recommendedDay") val recommendedDay: Int?,
    @SerializedName("qualityScore") val qualityScore: Double?,
    var isSelected: Boolean = true
)

data class CreateItineraryFromSelectionRequest(
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("estimatedBudget") val estimatedBudget: Double?,
    @SerializedName("selectedDestinations") val selectedDestinations: List<SelectedAIDestination>
)

data class SelectedAIDestination(
    @SerializedName("rawPlaceId") val rawPlaceId: String?,
    @SerializedName("destinationId") val destinationId: Int?
)

data class CreateItineraryFromSelectionResult(
    @SerializedName("id") val id: Int?,
    @SerializedName("itineraryId") val itineraryId: Int?,
    @SerializedName("selectedCount") val selectedCount: Int?,
    @SerializedName("destinationIds") val destinationIds: List<Int>?,
    @SerializedName("unresolved") val unresolved: List<Any>?
)
data class AIItineraryOptionsResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("message") val message: String? = null,
    @SerializedName("data") val data: AIItineraryOptionsData? = null
)

data class AIItineraryOptionsData(
    @SerializedName("title") val title: String?,
    @SerializedName("summary") val summary: String?,
    @SerializedName("options") val options: List<AIItineraryOption>
)

data class AIItineraryOption(
    @SerializedName("optionId") val optionId: String,
    @SerializedName("title") val title: String,
    @SerializedName("summary") val summary: String?,
    @SerializedName("theme") val theme: String?,
    @SerializedName("estimatedBudget") val estimatedBudget: Double?,
    @SerializedName("totalDays") val totalDays: Int,
    @SerializedName("highlights") val highlights: List<String>,
    @SerializedName("days") val days: List<AIItineraryOptionDay>
)

data class AIItineraryOptionDay(
    @SerializedName("dayNumber") val dayNumber: Int,
    @SerializedName("items") val items: List<AIRecommendedDestination>
)

data class CreateItineraryFromOptionRequest(
    @SerializedName("title") val title: String,
    @SerializedName("description") val description: String?,
    @SerializedName("startDate") val startDate: String,
    @SerializedName("endDate") val endDate: String,
    @SerializedName("estimatedBudget") val estimatedBudget: Double?,
    @SerializedName("optionId") val optionId: String?,
    @SerializedName("days") val days: List<AIItineraryOptionDay>
)

data class CreateItineraryFromOptionResult(
    @SerializedName("id") val id: Int?,
    @SerializedName("itineraryId") val itineraryId: Int?,
    @SerializedName("optionId") val optionId: String?,
    @SerializedName("selectedCount") val selectedCount: Int?,
    @SerializedName("unresolved") val unresolved: List<Any>?
)
// ==================== CHAT ====================

data class ChatMessage(
    val role: String,
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val places: List<ChatPlace> = emptyList(),
    /** Số ngày đã dùng cho RAG (ưu tiên khi tạo lịch từ tin nhắn bot). */
    val tripDaysHint: Int? = null
)

data class ChatRequest(
    val message: String,
    val top_k: Int = 6,
    val mode: String = "balanced",
    val targetProvince: String? = null,
    val targetCity: String? = null
)
data class ChatResponse(
    val answer: String? = null,
    val success: Boolean? = null,
    val message: String? = null,
    val places: List<ChatPlace>? = null
)

data class ChatPlace(
    @SerializedName(value = "place_id", alternate = ["rawPlaceId", "placeId", "raw_place_id"])
    val rawPlaceId: String? = null,

    val name: String? = null,
    val province: String? = null,
    val city: String? = null,
    val area: String? = null,

    @SerializedName("category_main")
    val categoryMain: String? = null,

    val score: Double? = null
)
data class GeminiPreparedQuery(
    val query: String,
    val targetProvince: String? = null,
    val targetCity: String? = null,
    val tripDays: Int? = null,
    val intent: String? = null
)
data class GeminiRagValidation(
    val valid: Boolean = true,
    val reason: String? = null,
    val correctedQuery: String? = null
)

data class ChatbotResult(
    val answer: String,
    val places: List<ChatPlace> = emptyList(),
    val tripDaysHint: Int? = null
)

// ==================== WEATHER ====================

data class WeatherInfo(
    val city: String,
    val temperature: Double,
    val description: String,
    val humidity: Int,
    val icon: String,
    val forecast: List<ForecastDay>?
)

data class ForecastDay(
    val date: String,
    val tempMin: Double,
    val tempMax: Double,
    val description: String,
    val icon: String
)

// ==================== GENERIC ====================

data class ApiResponse<T>(
    val success: Boolean,
    val message: String,
    val data: T? = null
)

data class FavoriteRequest(
    val destinationId: Int
)