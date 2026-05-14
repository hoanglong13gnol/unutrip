package com.smarttravel.data.api

import com.smarttravel.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ==================== AUTH ====================

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("auth/logout")
    suspend fun logout(
        @Header("Authorization") token: String
    ): Response<ApiResponse<Unit>>

    // ==================== USER ====================

    @GET("users/profile")
    suspend fun getProfile(
        @Header("Authorization") token: String
    ): Response<ApiResponse<User>>

    @GET("users/stats")
    suspend fun getUserStats(
        @Header("Authorization") token: String
    ): Response<ApiResponse<UserStats>>

    @PUT("users/profile")
    suspend fun updateProfile(
        @Header("Authorization") token: String,
        @Body user: User
    ): Response<ApiResponse<User>>

    @PUT("users/preferences")
    suspend fun updatePreferences(
        @Header("Authorization") token: String,
        @Body body: Map<String, List<String>>
    ): Response<ApiResponse<User>>

    @Multipart
    @POST("users/avatar")
    suspend fun uploadAvatar(
        @Header("Authorization") token: String,
        @Part avatar: okhttp3.MultipartBody.Part
    ): Response<ApiResponse<User>>

    // ==================== DESTINATIONS ====================

    @GET("destinations")
    suspend fun getDestinations(
        @Header("Authorization") token: String,
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 10,
        @Query("category") category: String? = null,
        @Query("province") province: String? = null,
        @Query("search") search: String? = null,
        @Query("sort") sort: String? = null
    ): Response<DestinationResponse>

    @GET("destinations/{id}")
    suspend fun getDestinationDetail(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<DestinationDetailResponse>

    @GET("destinations/featured")
    suspend fun getFeaturedDestinations(
        @Header("Authorization") token: String
    ): Response<DestinationResponse>

    @GET("destinations/nearby")
    suspend fun getNearbyDestinations(
        @Header("Authorization") token: String,
        @Query("lat") lat: Double,
        @Query("lng") lng: Double,
        @Query("radiusKm") radiusKm: Int = 50,
        @Query("limit") limit: Int = 20
    ): Response<DestinationResponse>

    // ==================== FAVORITES ====================

    @GET("users/favorites")
    suspend fun getFavorites(
        @Header("Authorization") token: String
    ): Response<DestinationResponse>

    @POST("users/favorites")
    suspend fun addFavorite(
        @Header("Authorization") token: String,
        @Body request: FavoriteRequest
    ): Response<ApiResponse<Unit>>

    @DELETE("users/favorites/{destinationId}")
    suspend fun removeFavorite(
        @Header("Authorization") token: String,
        @Path("destinationId") destinationId: Int
    ): Response<ApiResponse<Unit>>

    // ==================== REVIEWS ====================

    @GET("destinations/{id}/reviews")
    suspend fun getReviews(
        @Header("Authorization") token: String,
        @Path("id") destinationId: Int
    ): Response<ApiResponse<List<Review>>>

    @POST("reviews")
    suspend fun postReview(
        @Header("Authorization") token: String,
        @Body request: ReviewRequest
    ): Response<ApiResponse<Review>>

    @Multipart
    @POST("reviews")
    suspend fun postReviewWithImages(
        @Header("Authorization") token: String,
        @Part("destinationId") destinationId: okhttp3.RequestBody,
        @Part("rating") rating: okhttp3.RequestBody,
        @Part("comment") comment: okhttp3.RequestBody,
        @Part images: List<okhttp3.MultipartBody.Part>
    ): Response<ApiResponse<Review>>

    // ==================== ITINERARY ====================

    @GET("itineraries")
    suspend fun getItineraries(
        @Header("Authorization") token: String
    ): Response<ItineraryResponse>

    @GET("itineraries/{id}")
    suspend fun getItineraryDetail(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<ApiResponse<Itinerary>>

    @POST("itineraries")
    suspend fun createItinerary(
        @Header("Authorization") token: String,
        @Body request: CreateItineraryRequest
    ): Response<ApiResponse<Itinerary>>

    @PUT("itineraries/{id}")
    suspend fun updateItinerary(
        @Header("Authorization") token: String,
        @Path("id") id: Int,
        @Body body: UpdateItineraryRequest
    ): Response<ApiResponse<Itinerary>>

    @DELETE("itineraries/{id}")
    suspend fun deleteItinerary(
        @Header("Authorization") token: String,
        @Path("id") id: Int
    ): Response<ApiResponse<Unit>>

    @POST("itineraries/{id}/items")
    suspend fun addDestinationToItinerary(
        @Header("Authorization") token: String,
        @Path("id") itineraryId: Int,
        @Body request: AddItineraryItemRequest
    ): Response<ApiResponse<Unit>>

    @PUT("itineraries/{itineraryId}/items/{itemId}")
    suspend fun updateItineraryItem(
        @Header("Authorization") token: String,
        @Path("itineraryId") itineraryId: Int,
        @Path("itemId") itemId: Int,
        @Body body: UpdateItineraryItemRequest
    ): Response<ApiResponse<Unit>>

    @DELETE("itineraries/{itineraryId}/items/{itemId}")
    suspend fun deleteItineraryItem(
        @Header("Authorization") token: String,
        @Path("itineraryId") itineraryId: Int,
        @Path("itemId") itemId: Int
    ): Response<ApiResponse<Unit>>

    @POST("itineraries/{id}/days")
    suspend fun addItineraryDay(
        @Header("Authorization") token: String,
        @Path("id") itineraryId: Int
    ): Response<ApiResponse<Unit>>

    @DELETE("itineraries/{itineraryId}/days/{dayId}")
    suspend fun deleteItineraryDay(
        @Header("Authorization") token: String,
        @Path("itineraryId") itineraryId: Int,
        @Path("dayId") dayId: Int
    ): Response<ApiResponse<Unit>>

    @POST("itineraries/create-from-selection")
    suspend fun createItineraryFromSelection(
        @Header("Authorization") token: String,
        @Body request: CreateItineraryFromSelectionRequest
    ): Response<ApiResponse<CreateItineraryFromSelectionResult>>

    // ==================== AI ====================

    @POST("ai/itinerary-preview")
    suspend fun previewAIItinerary(
        @Header("Authorization") token: String,
        @Body request: AIItineraryPreviewRequest
    ): Response<AIItineraryPreviewResponse>

    @POST("itineraries/save-ai")
    suspend fun saveAIItinerary(
        @Header("Authorization") token: String,
        @Body request: SaveAIItineraryRequest
    ): Response<ApiResponse<Unit>>

    @POST("ai/suggest-itinerary")
    suspend fun suggestItinerary(
        @Header("Authorization") token: String,
        @Body request: AISuggestRequest
    ): Response<AISuggestResponse>

    @POST("ai/rag-chat")
    suspend fun chat(
        @Header("Authorization") token: String,
        @Body request: ChatRequest
    ): Response<ChatResponse>
    @POST("ai/chat")
    suspend fun chatFallback(
        @Header("Authorization") token: String,
        @Body body: Map<String, String>
    ): Response<ChatResponse>
    @POST("ai/itinerary-options")
    suspend fun getAIItineraryOptions(
        @Header("Authorization") token: String,
        @Body request: AIItineraryPreviewRequest
    ): Response<AIItineraryOptionsResponse>

    @POST("itineraries/create-from-option")
    suspend fun createItineraryFromOption(
        @Header("Authorization") token: String,
        @Body request: CreateItineraryFromOptionRequest
    ): Response<ApiResponse<CreateItineraryFromOptionResult>>
    
    // ==================== WEATHER ====================
    // Đã chuyển sang Open-Meteo (WeatherService.kt) — miễn phí, không cần API key
}