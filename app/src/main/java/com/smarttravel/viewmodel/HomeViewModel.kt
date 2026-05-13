package com.smarttravel.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smarttravel.data.model.Destination
import com.smarttravel.data.model.WeatherInfo
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.utils.Resource
import kotlinx.coroutines.launch

class HomeViewModel(
    private val destinationRepo: DestinationRepository
) : ViewModel() {

    private val _featured = MutableLiveData<Resource<List<Destination>>>()
    val featured: LiveData<Resource<List<Destination>>> = _featured

    private val _nearby = MutableLiveData<Resource<List<Destination>>>()
    val nearby: LiveData<Resource<List<Destination>>> = _nearby

    private val _weather = MutableLiveData<WeatherInfo?>()
    val weather: LiveData<WeatherInfo?> = _weather

    fun loadFeatured(token: String) {
        viewModelScope.launch {
            _featured.value = Resource.Loading
            _featured.value = destinationRepo.getFeatured(token)
        }
    }

    fun loadNearby(
        token: String,
        lat: Double,
        lng: Double,
        radiusKm: Int = 50,
        limit: Int = 20
    ) {
        viewModelScope.launch {
            _nearby.value = Resource.Loading
            _nearby.value = destinationRepo.getNearby(
                token = token,
                lat = lat,
                lng = lng,
                radiusKm = radiusKm,
                limit = limit
            )
        }
    }

    fun toggleFavorite(token: String, destinationId: Int, isFav: Boolean) {
        viewModelScope.launch {
            destinationRepo.toggleFavorite(token, destinationId, isFav)
        }
    }
}

class HomeViewModelFactory(private val repo: DestinationRepository) :
    androidx.lifecycle.ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return HomeViewModel(repo) as T
    }
}
