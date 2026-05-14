package com.smarttravel.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.smarttravel.data.model.AIItineraryPreviewData
import com.smarttravel.data.model.AIItineraryPreviewRequest
import com.smarttravel.data.model.AIRecommendedDestination
import com.smarttravel.data.model.CreateItineraryFromSelectionRequest
import com.smarttravel.data.model.CreateItineraryFromSelectionResult
import com.smarttravel.data.model.CreateItineraryRequest
import com.smarttravel.data.model.Itinerary
import com.smarttravel.data.model.ItineraryItem
import com.smarttravel.data.model.UpdateItineraryItemRequest
import com.smarttravel.data.model.UpdateItineraryRequest
import com.smarttravel.data.model.SaveAIItineraryRequest
import com.smarttravel.data.model.SelectedAIDestination
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.utils.Resource
import kotlinx.coroutines.launch
import com.smarttravel.data.model.AIItineraryOption
import com.smarttravel.data.model.AIItineraryOptionsData
import com.smarttravel.data.model.CreateItineraryFromOptionRequest
import com.smarttravel.data.model.CreateItineraryFromOptionResult

class ItineraryViewModel(
    private val repo: ItineraryRepository,
    private val destRepo: DestinationRepository
) : ViewModel() {

    private val geminiService = com.smarttravel.utils.GeminiService()
    private val gson = Gson()

    private val _itineraries = MutableLiveData<Resource<List<Itinerary>>>()
    val itineraries: LiveData<Resource<List<Itinerary>>> = _itineraries

    private val _itineraryDetail = MutableLiveData<Resource<Itinerary>>()
    val itineraryDetail: LiveData<Resource<Itinerary>> = _itineraryDetail

    private val _aiSuggest = MutableLiveData<Resource<Unit>>()
    val aiSuggest: LiveData<Resource<Unit>> = _aiSuggest

    private val _aiPreview = MutableLiveData<Resource<AIItineraryPreviewData>>()
    val aiPreview: LiveData<Resource<AIItineraryPreviewData>> = _aiPreview

    private val _createFromAI = MutableLiveData<Resource<CreateItineraryFromSelectionResult>>()
    val createFromAI: LiveData<Resource<CreateItineraryFromSelectionResult>> = _createFromAI

    private val _aiOptions = MutableLiveData<Resource<AIItineraryOptionsData>>()
    val aiOptions: LiveData<Resource<AIItineraryOptionsData>> = _aiOptions

    private val _createFromOption = MutableLiveData<Resource<CreateItineraryFromOptionResult>>()
    val createFromOption: LiveData<Resource<CreateItineraryFromOptionResult>> = _createFromOption
    private val _isGenerating = MutableLiveData(false)
    val isGenerating: LiveData<Boolean> = _isGenerating

    private val _messages = MutableLiveData<String?>()
    val messages: LiveData<String?> = _messages

    private var token: String = ""

    fun init(token: String) {
        this.token = token
    }

    fun clearMessage() {
        _messages.value = null
    }

    fun loadItineraries() {
        viewModelScope.launch {
            _itineraries.value = Resource.Loading
            _itineraries.value = repo.getItineraries(token)
        }
    }

    fun loadDetail(id: Int) {
        viewModelScope.launch {
            _itineraryDetail.value = Resource.Loading
            _itineraryDetail.value = repo.getItineraryDetail(token, id)
        }
    }

    fun createItinerary(
        title: String,
        description: String?,
        startDate: String,
        endDate: String
    ) {
        viewModelScope.launch {
            val request = CreateItineraryRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate
            )

            val result = repo.createItinerary(token, request)

            if (result is Resource.Success) {
                _messages.value = "Tạo lịch trình thành công!"
                loadItineraries()
            } else if (result is Resource.Error) {
                _messages.value = result.message
            }
        }
    }

    fun deleteItinerary(id: Int) {
        viewModelScope.launch {
            repo.deleteItinerary(token, id)
            loadItineraries()
        }
    }

    fun updateItineraryMeta(
        id: Int,
        title: String,
        description: String?,
        startDate: String,
        endDate: String,
        estimatedBudget: Double?,
        status: String
    ) {
        viewModelScope.launch {
            val body = UpdateItineraryRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate,
                status = status,
                estimatedBudget = estimatedBudget
            )
            when (val r = repo.updateItinerary(token, id, body)) {
                is Resource.Success -> {
                    _messages.value = "Đã cập nhật thông tin lịch trình"
                    loadDetail(id)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun addItemToItinerary(
        itineraryId: Int,
        dayId: Int,
        destinationId: Int,
        startTime: String? = "09:00",
        endTime: String? = "11:00",
        note: String? = null
    ) {
        viewModelScope.launch {
            when (
                val r = repo.addDestination(
                    token,
                    itineraryId,
                    destinationId,
                    dayId,
                    startTime,
                    endTime,
                    note
                )
            ) {
                is Resource.Success -> {
                    _messages.value = "Đã thêm địa điểm"
                    loadDetail(itineraryId)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun updateItineraryItem(
        itineraryId: Int,
        item: ItineraryItem,
        dayId: Int,
        startTime: String,
        endTime: String,
        note: String?
    ) {
        viewModelScope.launch {
            val body = UpdateItineraryItemRequest(
                dayId = dayId,
                destinationId = item.destinationId,
                startTime = startTime,
                endTime = endTime,
                note = note
            )
            when (val r = repo.updateItineraryItem(token, itineraryId, item.id, body)) {
                is Resource.Success -> {
                    _messages.value = "Đã cập nhật hoạt động"
                    loadDetail(itineraryId)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun deleteItineraryItem(itineraryId: Int, itemId: Int) {
        viewModelScope.launch {
            when (val r = repo.deleteItineraryItem(token, itineraryId, itemId)) {
                is Resource.Success -> {
                    _messages.value = "Đã xóa hoạt động"
                    loadDetail(itineraryId)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun addItineraryDay(itineraryId: Int) {
        viewModelScope.launch {
            when (val r = repo.addItineraryDay(token, itineraryId)) {
                is Resource.Success -> {
                    _messages.value = "Đã thêm ngày mới"
                    loadDetail(itineraryId)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun deleteItineraryDay(itineraryId: Int, dayId: Int) {
        viewModelScope.launch {
            when (val r = repo.deleteItineraryDay(token, itineraryId, dayId)) {
                is Resource.Success -> {
                    _messages.value = "Đã xóa ngày"
                    loadDetail(itineraryId)
                }
                is Resource.Error -> {
                    _messages.value = r.message
                }
                else -> {}
            }
        }
    }

    fun previewAIItinerary(
        title: String,
        description: String?,
        startDate: String,
        endDate: String,
        budget: Double?,
        preferences: List<String>,
        province: String?
    ) {
        viewModelScope.launch {
            _isGenerating.value = true
            _aiPreview.value = Resource.Loading

            val request = AIItineraryPreviewRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate,
                budget = budget,
                preferences = preferences,
                province = province
            )

            val result = repo.previewAIItinerary(token, request)
            _aiPreview.value = result

            if (result is Resource.Error) {
                _messages.value = result.message
            }

            _isGenerating.value = false
        }
    }
    fun getAIItineraryOptions(
        title: String,
        description: String?,
        startDate: String,
        endDate: String,
        budget: Double?,
        preferences: List<String>,
        province: String?
    ) {
        viewModelScope.launch {
            _isGenerating.value = true
            _aiOptions.value = Resource.Loading

            val request = AIItineraryPreviewRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate,
                budget = budget,
                preferences = preferences,
                province = province
            )

            val result = repo.getAIItineraryOptions(token, request)
            _aiOptions.value = result

            if (result is Resource.Error) {
                _messages.value = result.message
            }

            _isGenerating.value = false
        }
    }
    fun createItineraryFromOption(
        title: String,
        description: String?,
        startDate: String,
        endDate: String,
        budget: Double?,
        option: AIItineraryOption
    ) {
        viewModelScope.launch {
            _isGenerating.value = true
            _createFromOption.value = Resource.Loading

            val request = CreateItineraryFromOptionRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate,
                estimatedBudget = budget,
                optionId = option.optionId,
                days = option.days
            )

            val result = repo.createItineraryFromOption(token, request)
            _createFromOption.value = result

            if (result is Resource.Success) {
                _messages.value = "Tạo lịch trình từ tour AI thành công!"
                loadItineraries()
            } else if (result is Resource.Error) {
                _messages.value = result.message
            }

            _isGenerating.value = false
        }
    }

    fun createItineraryFromSelection(
        title: String,
        description: String?,
        startDate: String,
        endDate: String,
        budget: Double?,
        selectedDestinations: List<AIRecommendedDestination>
    ) {
        viewModelScope.launch {
            _isGenerating.value = true
            _createFromAI.value = Resource.Loading

            val request = CreateItineraryFromSelectionRequest(
                title = title,
                description = description,
                startDate = startDate,
                endDate = endDate,
                estimatedBudget = budget,
                selectedDestinations = selectedDestinations.map { destination ->
                    SelectedAIDestination(
                        rawPlaceId = destination.rawPlaceId,
                        destinationId = destination.destinationId
                    )
                }
            )

            val result = repo.createItineraryFromSelection(token, request)
            _createFromAI.value = result

            if (result is Resource.Success) {
                _messages.value = "Tạo lịch trình từ AI thành công!"
                loadItineraries()
            } else if (result is Resource.Error) {
                _messages.value = result.message
            }

            _isGenerating.value = false
        }
    }

    // Old flow: keep for compatibility. ItineraryFragment no longer calls this.
    fun generateAIItinerary(
        preferences: List<String>,
        startDate: String,
        endDate: String,
        budget: Double?,
        startLocation: String?
    ) {
        viewModelScope.launch {
            _isGenerating.value = true
            _aiSuggest.value = Resource.Loading

            try {
                val aiResponse = geminiService.suggestItinerary(
                    token,
                    preferences,
                    startDate,
                    endDate,
                    budget,
                    startLocation
                )

                val saveRequest = try {
                    gson.fromJson(aiResponse, SaveAIItineraryRequest::class.java)
                } catch (e: Exception) {
                    _aiSuggest.value = Resource.Error("Lỗi cấu trúc lịch trình AI: ${e.message}")
                    return@launch
                }

                val saveResult = repo.saveAIItinerary(token, saveRequest)
                _aiSuggest.value = saveResult

                if (saveResult is Resource.Success) {
                    loadItineraries()
                }
            } catch (e: Exception) {
                android.util.Log.e("AI_SUGGEST", "Error", e)
                _aiSuggest.value = Resource.Error("Lỗi AI: ${e.message}")
            } finally {
                _isGenerating.value = false
            }
        }
    }
}

class ItineraryViewModelFactory(
    private val repo: ItineraryRepository,
    private val destRepo: DestinationRepository
) : androidx.lifecycle.ViewModelProvider.Factory {

    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return ItineraryViewModel(repo, destRepo) as T
    }
}