package com.smarttravel.ui.destination

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.bumptech.glide.Glide
import com.google.android.material.chip.Chip
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.Destination
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.databinding.FragmentDestinationDetailBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.utils.WeatherService
import com.smarttravel.viewmodel.DestinationViewModel
import com.smarttravel.viewmodel.DestinationViewModelFactory
import kotlinx.coroutines.launch
import com.smarttravel.BuildConfig

class DestinationDetailFragment : Fragment() {

    private var _binding: FragmentDestinationDetailBinding? = null
    private val binding get() = _binding!!
    private lateinit var viewModel: DestinationViewModel
    private lateinit var sessionManager: SessionManager
    private lateinit var reviewAdapter: ReviewAdapter
    private var currentDestination: Destination? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentDestinationDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        val repo = DestinationRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, DestinationViewModelFactory(repo))[DestinationViewModel::class.java]
        viewModel.init(sessionManager.getBearerToken())

        val destinationId = arguments?.getInt("destinationId") ?: return

        setupToolbar()
        setupReviewAdapter()
        observeViewModel()

        viewModel.loadDetail(destinationId)
        viewModel.loadReviews(destinationId)
    }

    private fun setupToolbar() {
        binding.toolbar.setNavigationOnClickListener {
            findNavController().navigateUp()
        }
    }

    private fun setupReviewAdapter() {
        reviewAdapter = ReviewAdapter()
        binding.rvReviews.apply {
            layoutManager = LinearLayoutManager(context)
            adapter = reviewAdapter
            isNestedScrollingEnabled = false
        }
    }

    private fun bindDestination(destination: Destination) {
        currentDestination = destination

        // Hero image
        if (destination.images.isNotEmpty()) {
            Glide.with(this)
                .load(resolveImageUrl(destination.images.first()))
                .placeholder(R.drawable.placeholder_destination)
                .centerCrop()
                .into(binding.ivHero)
        }

        binding.tvName.text = destination.name
        binding.tvLocation.text = "${destination.city}, ${destination.province}"
        binding.tvRatingBig.text = String.format("%.1f", destination.rating)
        binding.tvReviewCount.text = destination.reviewCount.toString()
        binding.tvDescription.text = destination.description ?: "Chưa có mô tả"

        // Fee
        binding.tvFee.text = if (destination.entryFee == 0.0) "Miễn phí"
        else "${String.format("%,.0f", destination.entryFee)}đ"

        // Hours
        if (destination.openTime != null && destination.closeTime != null) {
            binding.tvHours.text = "Mở cửa: ${destination.openTime} - ${destination.closeTime}"
            binding.layoutHours.visibility = View.VISIBLE
        } else {
            binding.layoutHours.visibility = View.GONE
        }

        // Tags
        binding.chipGroupTags.removeAllViews()
        destination.tags.forEach { tag ->
            val chip = Chip(requireContext()).apply {
                text = tag
                isClickable = false
                setChipBackgroundColorResource(R.color.surface_variant)
                setTextColor(resources.getColor(R.color.text_secondary, null))
            }
            binding.chipGroupTags.addView(chip)
        }

        // Favorite button
        binding.fabFavorite.setImageResource(
            if (destination.isFavorite) R.drawable.ic_favorite_filled
            else R.drawable.ic_favorite_outline
        )

        binding.fabFavorite.setOnClickListener {
            viewModel.toggleFavorite(destination.id, destination.isFavorite)
            Toast.makeText(context,
                if (destination.isFavorite) "Đã xóa khỏi yêu thích" else "Đã thêm vào yêu thích",
                Toast.LENGTH_SHORT).show()
        }

        binding.btnAddToItinerary.setOnClickListener {
            val destId = destination.id
            val token = sessionManager.getBearerToken()
            val itinRepo = ItineraryRepository(RetrofitClient.apiService)
            
            viewLifecycleOwner.lifecycleScope.launch {
                val result = itinRepo.getItineraries(token)
                if (result is Resource.Success) {
                    val dialog = SelectItineraryDialog(result.data) { selectedItin ->
                        viewLifecycleOwner.lifecycleScope.launch {
                            val addResult = itinRepo.addDestination(token, selectedItin.id, destId)
                            if (addResult is Resource.Success) {
                                Toast.makeText(requireContext(), "Đã thêm vào lịch trình!", Toast.LENGTH_SHORT).show()
                            } else if (addResult is Resource.Error) {
                                Toast.makeText(requireContext(), addResult.message, Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                    dialog.show(parentFragmentManager, "select_itinerary")
                } else {
                    Toast.makeText(requireContext(), "Không thể tải danh sách lịch trình", Toast.LENGTH_SHORT).show()
                }
            }
        }

        binding.btnViewMap.setOnClickListener {
            val bundle = Bundle().apply {
                putFloat("latitude", destination.latitude.toFloat())
                putFloat("longitude", destination.longitude.toFloat())
                putString("destinationName", destination.name)
            }
            findNavController().navigate(R.id.action_destinationDetailFragment_to_mapFragment, bundle)
        }

        binding.tvWriteReview.setOnClickListener {
            showReviewDialog(destination.id)
        }

        // Load weather for this destination's city
        loadWeather(destination.city)
    }

    private fun loadWeather(cityName: String) {
        binding.progressWeather.visibility = View.VISIBLE
        binding.cardWeather.visibility = View.GONE

        viewLifecycleOwner.lifecycleScope.launch {
            val result = WeatherService.getWeather(cityName)
            if (!isAdded) return@launch

            binding.progressWeather.visibility = View.GONE
            when (result) {
                is Resource.Success -> {
                    val weather = result.data
                    binding.cardWeather.visibility = View.VISIBLE
                    binding.tvWeatherTemp.text = "${weather.temperature.toInt()}°C"
                    binding.tvWeatherDesc.text = weather.description
                    binding.tvWeatherHumidity.text = "Độ ẩm: ${weather.humidity}%"
                    binding.tvWeatherIcon.text = weatherIconEmoji(weather.icon)
                }
                is Resource.Error -> {
                    binding.cardWeather.visibility = View.GONE
                }
                else -> {}
            }
        }
    }

    private fun weatherIconEmoji(iconCode: String): String = when (iconCode) {
        "01d" -> "☀️"
        "02d" -> "⛅"
        "09d" -> "🌧️"
        "10d" -> "🌦️"
        "11d" -> "⛈️"
        "13d" -> "❄️"
        "50d" -> "🌫️"
        else -> "🌡️"
    }

    private fun showReviewDialog(destinationId: Int) {
        val dialog = ReviewDialog(destinationId) { rating, comment, uris ->
            viewModel.postReview(requireContext(), destinationId, rating, comment, uris)
            Toast.makeText(context, "Đang gửi đánh giá...", Toast.LENGTH_SHORT).show()
        }
        dialog.show(parentFragmentManager, "review_dialog")
    }

    private fun observeViewModel() {
        viewModel.destinationDetail.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Success -> bindDestination(result.data)
                is Resource.Error -> Toast.makeText(context, result.message, Toast.LENGTH_SHORT).show()
                else -> {}
            }
        }

        viewModel.reviews.observe(viewLifecycleOwner) { result ->
            if (result is Resource.Success) {
                reviewAdapter.submitList(result.data)
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
    private fun resolveImageUrl(url: String): String {
        return if (url.startsWith("http://") || url.startsWith("https://")) {
            url
        } else {
            BuildConfig.BASE_URL.replace("/api/", "") + url
        }
    }
}
