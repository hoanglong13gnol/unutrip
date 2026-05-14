package com.smarttravel.data.repository

import android.util.Log
import com.smarttravel.data.api.ApiService
import retrofit2.Response
import com.smarttravel.data.api.parseErrorMessageOrNull
import com.smarttravel.data.model.*
import com.smarttravel.utils.Resource
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody

// ==================== AUTH REPOSITORY ====================

class AuthRepository(private val api: ApiService) {

    suspend fun login(email: String, password: String): Resource<AuthResponse> {
        return try {
            val response = api.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val detail = response.parseErrorMessageOrNull()
                    ?: response.message()
                    ?: "Đăng nhập thất bại"
                Resource.Error(detail)
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun register(
        fullName: String,
        email: String,
        password: String,
        phone: String?
    ): Resource<AuthResponse> {
        return try {
            val response = api.register(RegisterRequest(fullName, email, password, phone))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                val detail = response.parseErrorMessageOrNull()
                    ?: response.message()
                    ?: "Đăng ký thất bại"
                Resource.Error(detail)
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }
}

// ==================== DESTINATION REPOSITORY ====================

class DestinationRepository(private val api: ApiService) {

    suspend fun getDestinations(
        token: String,
        page: Int = 1,
        limit: Int = 10,
        category: String? = null,
        province: String? = null,
        search: String? = null
    ): Resource<DestinationResponse> {
        return try {
            val response = api.getDestinations(token, page, limit, category, province, search)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error("Không thể tải danh sách địa điểm")
            }
        } catch (e: Exception) {
            Log.e("DestinationRepo", "getDestinations error: ", e)
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getDestinationDetail(token: String, id: Int): Resource<Destination> {
        return try {
            val response = api.getDestinationDetail(token, id)
            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data)
            } else {
                Resource.Error("Không thể tải thông tin địa điểm")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getFeatured(token: String): Resource<List<Destination>> {
        return try {
            val response = api.getFeaturedDestinations(token)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!.data)
            } else {
                Resource.Error("Không thể tải địa điểm nổi bật")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getNearby(
        token: String,
        lat: Double,
        lng: Double,
        radiusKm: Int = 50,
        limit: Int = 20
    ): Resource<List<Destination>> {
        return try {
            suspend fun fetch(radius: Int): Response<DestinationResponse> =
                api.getNearbyDestinations(
                    token = token,
                    lat = lat,
                    lng = lng,
                    radiusKm = radius,
                    limit = limit,
                )

            var response = fetch(radiusKm)
            if (!response.isSuccessful || response.body() == null) {
                return Resource.Error("Không thể tải địa điểm gần đây")
            }
            var data = response.body()!!.data
            if (data.isNotEmpty()) {
                return Resource.Success(sortDestinationsNearestFirst(data))
            }

            val widerRadii = listOf(120, 200, 350, 600, 1000, 2000, 4000).filter { it > radiusKm }
            for (r in widerRadii) {
                response = fetch(r)
                if (response.isSuccessful && response.body() != null) {
                    data = response.body()!!.data
                    if (data.isNotEmpty()) {
                        return Resource.Success(sortDestinationsNearestFirst(data))
                    }
                }
            }

            val featured = api.getFeaturedDestinations(token)
            if (featured.isSuccessful && featured.body() != null) {
                val featuredData = featured.body()!!.data
                if (featuredData.isNotEmpty()) {
                    return Resource.Success(sortDestinationsNearestFirst(featuredData.take(limit)))
                }
            }

            val listResp = api.getDestinations(token, page = 1, limit = limit, null, null, null)
            if (listResp.isSuccessful && listResp.body() != null) {
                return Resource.Success(sortDestinationsNearestFirst(listResp.body()!!.data))
            }

            Resource.Success(emptyList())
        } catch (e: Exception) {
            Log.e("DestinationRepo", "getNearby error: ", e)
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    /**
     * Gần nhất trước; nếu không có [Destination.distanceKm] hợp lệ thì gợi ý theo rating.
     */
    private fun sortDestinationsNearestFirst(destinations: List<Destination>): List<Destination> {
        if (destinations.isEmpty()) return destinations
        val hasUsableDistance = destinations.any { d ->
            val km = d.distanceKm
            km != null && km > 0.0 && km.isFinite()
        }
        if (!hasUsableDistance) {
            return destinations.sortedWith(
                compareByDescending<Destination> { it.rating }.thenBy { it.id },
            )
        }
        return destinations.sortedWith(
            compareBy<Destination> { d ->
                val km = d.distanceKm
                if (km == null || km <= 0.0 || !km.isFinite()) Double.POSITIVE_INFINITY else km
            }
                .thenByDescending { it.rating }
                .thenBy { it.id },
        )
    }

    suspend fun toggleFavorite(token: String, destinationId: Int, isFav: Boolean): Resource<Unit> {
        return try {
            val response = if (isFav) {
                api.removeFavorite(token, destinationId)
            } else {
                api.addFavorite(token, FavoriteRequest(destinationId))
            }

            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error("Thao tác thất bại")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getFavorites(token: String): Resource<List<Destination>> {
        return try {
            val response = api.getFavorites(token)
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!.data)
            } else {
                Resource.Error("Không thể tải danh sách yêu thích")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getReviews(token: String, destinationId: Int): Resource<List<Review>> {
        return try {
            val response = api.getReviews(token, destinationId)
            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể tải đánh giá")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun postReview(token: String, request: ReviewRequest): Resource<Review> {
        return try {
            val response = api.postReview(token, request)
            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể gửi đánh giá")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun postReviewWithImages(
        token: String,
        destinationId: Int,
        rating: Float,
        comment: String,
        imageParts: List<okhttp3.MultipartBody.Part>
    ): Resource<Review> {
        return try {
            val destBody = destinationId.toString().toRequestBody("text/plain".toMediaTypeOrNull())
            val ratingBody = rating.toString().toRequestBody("text/plain".toMediaTypeOrNull())
            val commentBody = comment.toRequestBody("text/plain".toMediaTypeOrNull())

            val response = api.postReviewWithImages(
                token,
                destBody,
                ratingBody,
                commentBody,
                imageParts
            )

            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể gửi đánh giá")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }
}

// ==================== ITINERARY REPOSITORY ====================

class ItineraryRepository(private val api: ApiService) {

    suspend fun getItineraries(token: String): Resource<List<Itinerary>> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.getItineraries(authHeader)

            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!.data)
            } else {
                Resource.Error("Không thể tải lịch trình")
            }
        } catch (e: Exception) {
            Log.e("ItineraryRepo", "getItineraries error: ", e)
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun getItineraryDetail(token: String, id: Int): Resource<Itinerary> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.getItineraryDetail(authHeader, id)

            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể tải chi tiết lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun createItinerary(
        token: String,
        request: CreateItineraryRequest
    ): Resource<Itinerary> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.createItinerary(authHeader, request)

            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể tạo lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun updateItinerary(
        token: String,
        id: Int,
        body: UpdateItineraryRequest
    ): Resource<Itinerary> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.updateItinerary(authHeader, id, body)
            if (response.isSuccessful && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error("Không thể cập nhật lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun previewAIItinerary(
        token: String,
        request: AIItineraryPreviewRequest
    ): Resource<AIItineraryPreviewData> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.previewAIItinerary(authHeader, request)

            if (response.isSuccessful && response.body()?.success == true && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error(response.body()?.message ?: "AI không trả được gợi ý địa điểm")
            }
        } catch (e: Exception) {
            Log.e("ItineraryRepo", "previewAIItinerary error: ", e)
            Resource.Error("Lỗi gọi AI preview: ${e.message}")
        }
    }

    suspend fun createItineraryFromSelection(
        token: String,
        request: CreateItineraryFromSelectionRequest
    ): Resource<CreateItineraryFromSelectionResult> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.createItineraryFromSelection(authHeader, request)

            if (response.isSuccessful && response.body()?.success == true && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error(response.body()?.message ?: "Không tạo được lịch trình từ AI")
            }
        } catch (e: Exception) {
            Log.e("ItineraryRepo", "createItineraryFromSelection error: ", e)
            Resource.Error("Lỗi tạo lịch trình từ AI: ${e.message}")
        }
    }
    suspend fun getAIItineraryOptions(
        token: String,
        request: AIItineraryPreviewRequest
    ): Resource<AIItineraryOptionsData> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.getAIItineraryOptions(authHeader, request)

            if (response.isSuccessful && response.body()?.success == true && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error(response.body()?.message ?: "AI không trả được phương án tour")
            }
        } catch (e: Exception) {
            Log.e("ItineraryRepo", "getAIItineraryOptions error: ", e)
            Resource.Error("Lỗi lấy phương án tour AI: ${e.message}")
        }
    }

    suspend fun createItineraryFromOption(
        token: String,
        request: CreateItineraryFromOptionRequest
    ): Resource<CreateItineraryFromOptionResult> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.createItineraryFromOption(authHeader, request)

            if (response.isSuccessful && response.body()?.success == true && response.body()?.data != null) {
                Resource.Success(response.body()!!.data!!)
            } else {
                Resource.Error(response.body()?.message ?: "Không tạo được lịch trình từ tour AI")
            }
        } catch (e: Exception) {
            Log.e("ItineraryRepo", "createItineraryFromOption error: ", e)
            Resource.Error("Lỗi tạo lịch trình từ tour AI: ${e.message}")
        }
    }

    suspend fun addDestination(
        token: String,
        itineraryId: Int,
        destinationId: Int,
        dayId: Int? = null,
        startTime: String? = null,
        endTime: String? = null,
        note: String? = null
    ): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val request = AddItineraryItemRequest(
                destinationId = destinationId,
                dayId = dayId,
                startTime = startTime,
                endTime = endTime,
                note = note
            )
            val response = api.addDestinationToItinerary(authHeader, itineraryId, request)

            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error("Không thể thêm vào lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun updateItineraryItem(
        token: String,
        itineraryId: Int,
        itemId: Int,
        body: UpdateItineraryItemRequest
    ): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.updateItineraryItem(authHeader, itineraryId, itemId, body)
            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error("Không thể cập nhật hoạt động")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun deleteItineraryItem(token: String, itineraryId: Int, itemId: Int): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.deleteItineraryItem(authHeader, itineraryId, itemId)
            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error("Không thể xóa hoạt động")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun addItineraryDay(token: String, itineraryId: Int): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.addItineraryDay(authHeader, itineraryId)
            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error(response.parseErrorMessageOrNull() ?: "Không thể thêm ngày")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun deleteItineraryDay(token: String, itineraryId: Int, dayId: Int): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.deleteItineraryDay(authHeader, itineraryId, dayId)
            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error(response.parseErrorMessageOrNull() ?: "Không thể xóa ngày")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun deleteItinerary(token: String, id: Int): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.deleteItinerary(authHeader, id)

            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                Resource.Error("Không thể xóa lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun suggestItinerary(
        token: String,
        request: AISuggestRequest
    ): Resource<Itinerary> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.suggestItinerary(authHeader, request)

            if (response.isSuccessful && response.body()?.itinerary != null) {
                Resource.Success(response.body()!!.itinerary!!)
            } else {
                Resource.Error(response.body()?.message ?: "AI không thể gợi ý lịch trình")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }

    suspend fun saveAIItinerary(
        token: String,
        request: SaveAIItineraryRequest
    ): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val response = api.saveAIItinerary(authHeader, request)

            if (response.isSuccessful) {
                Resource.Success(Unit)
            } else {
                val errorMsg = try {
                    val errorObj = com.google.gson.Gson()
                        .fromJson(response.errorBody()?.string(), ApiResponse::class.java)
                    errorObj.message
                } catch (e: Exception) {
                    "Không thể lưu lịch trình AI"
                }

                Resource.Error(errorMsg)
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
    }
}