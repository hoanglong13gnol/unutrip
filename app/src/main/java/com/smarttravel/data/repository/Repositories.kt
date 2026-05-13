package com.smarttravel.data.repository

import android.util.Log
import com.smarttravel.data.api.ApiService
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
                Resource.Error(response.message() ?: "Đăng nhập thất bại")
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
                Resource.Error(response.message() ?: "Đăng ký thất bại")
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
            val response = api.getNearbyDestinations(
                token = token,
                lat = lat,
                lng = lng,
                radiusKm = radiusKm,
                limit = limit
            )

            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!.data)
            } else {
                Resource.Error("Không thể tải địa điểm gần đây")
            }
        } catch (e: Exception) {
            Resource.Error("Lỗi kết nối: ${e.message}")
        }
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
        destinationId: Int
    ): Resource<Unit> {
        return try {
            val authHeader = if (token.startsWith("Bearer ")) token else "Bearer $token"
            val request = AddItineraryItemRequest(destinationId = destinationId)
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