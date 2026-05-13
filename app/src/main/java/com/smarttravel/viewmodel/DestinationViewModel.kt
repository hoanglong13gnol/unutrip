package com.smarttravel.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smarttravel.data.model.Destination
import com.smarttravel.data.model.DestinationResponse
import com.smarttravel.data.model.Review
import com.smarttravel.data.model.ReviewRequest
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.utils.CategoryMapper
import com.smarttravel.utils.Resource
import kotlinx.coroutines.launch

class DestinationViewModel(
    private val repo: DestinationRepository
) : ViewModel() {

    private val _destinationsList = MutableLiveData<MutableList<Destination>>(mutableListOf())
    private val _destinations = MutableLiveData<Resource<DestinationResponse>>()
    val destinations: LiveData<Resource<DestinationResponse>> = _destinations

    private val _destinationDetail = MutableLiveData<Resource<Destination>>()
    val destinationDetail: LiveData<Resource<Destination>> = _destinationDetail

    private val _reviews = MutableLiveData<Resource<List<Review>>>()
    val reviews: LiveData<Resource<List<Review>>> = _reviews

    private val _favorites = MutableLiveData<Resource<List<Destination>>>()
    val favorites: LiveData<Resource<List<Destination>>> = _favorites

    private val _searchQuery = MutableLiveData<String>("")
    val searchQuery: LiveData<String> = _searchQuery

    private var currentPage = 1
    private var isLastPage = false
    private var isLoadingMore = false
    private var currentCategory: String? = null
    private var currentProvince: String? = null
    private var currentSearch: String? = null
    private var token: String = ""

    fun init(token: String) {
        this.token = token
    }

    fun loadDestinations(
        category: String? = null,
        province: String? = null,
        search: String? = null,
        page: Int = 1
    ) {
        currentPage = page

        val normalizedCategory = CategoryMapper.categoryParam(category)
        currentCategory = normalizedCategory
        currentProvince = province
        currentSearch = search
        isLastPage = false

        viewModelScope.launch {
            _destinations.value = Resource.Loading

            val result = repo.getDestinations(
                token = token,
                page = page,
                limit = 20,
                category = normalizedCategory,
                province = province,
                search = search
            )

            if (result is Resource.Success) {
                _destinationsList.value = result.data.data.toMutableList()
                if (result.data.data.size < 20) {
                    isLastPage = true
                }
            }

            _destinations.value = result
        }
    }

    fun loadMoreDestinations() {
        if (isLoadingMore || isLastPage) return

        isLoadingMore = true
        currentPage++

        viewModelScope.launch {
            val result = repo.getDestinations(
                token = token,
                page = currentPage,
                limit = 20,
                category = currentCategory,
                province = currentProvince,
                search = currentSearch
            )

            if (result is Resource.Success) {
                val currentList = _destinationsList.value ?: mutableListOf()
                currentList.addAll(result.data.data)
                _destinationsList.value = currentList

                val combinedResponse = DestinationResponse(
                    success = true,
                    data = currentList.toList(),
                    total = result.data.total,
                    page = currentPage,
                    limit = 20
                )

                _destinations.value = Resource.Success(combinedResponse)

                if (result.data.data.size < 20) {
                    isLastPage = true
                }
            }

            isLoadingMore = false
        }
    }

    fun loadDetail(id: Int) {
        viewModelScope.launch {
            _destinationDetail.value = Resource.Loading
            _destinationDetail.value = repo.getDestinationDetail(token, id)
        }
    }

    fun loadReviews(destinationId: Int) {
        viewModelScope.launch {
            _reviews.value = Resource.Loading
            _reviews.value = repo.getReviews(token, destinationId)
        }
    }

    fun toggleFavorite(destinationId: Int, isFav: Boolean) {
        viewModelScope.launch {
            repo.toggleFavorite(token, destinationId, isFav)

            if (_favorites.value is Resource.Success) {
                loadFavorites()
            }
        }
    }

    fun loadFavorites() {
        viewModelScope.launch {
            _favorites.value = Resource.Loading
            _favorites.value = repo.getFavorites(token)
        }
    }

    fun postReview(
        context: android.content.Context,
        destinationId: Int,
        rating: Float,
        comment: String,
        imageUris: List<android.net.Uri>
    ) {
        viewModelScope.launch {
            if (imageUris.isEmpty()) {
                repo.postReview(
                    token,
                    ReviewRequest(destinationId, rating, comment)
                )
            } else {
                val imageParts = imageUris.mapNotNull { uri ->
                    com.smarttravel.utils.FileUtils.getPartFromUri(
                        context,
                        uri,
                        "images"
                    )
                }

                repo.postReviewWithImages(
                    token,
                    destinationId,
                    rating,
                    comment,
                    imageParts
                )
            }

            loadReviews(destinationId)
        }
    }

    fun search(query: String) {
        _searchQuery.value = query
        loadDestinations(search = query)
    }
}

class DestinationViewModelFactory(
    private val repo: DestinationRepository
) : androidx.lifecycle.ViewModelProvider.Factory {

    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return DestinationViewModel(repo) as T
    }
}