package com.smarttravel.ui.home

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.DefaultItemAnimator
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.gms.location.LocationServices
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.databinding.FragmentHomeBinding
import com.smarttravel.ui.destination.DestinationAdapter
import com.smarttravel.utils.CategoryMapper
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.HomeViewModel
import com.smarttravel.viewmodel.HomeViewModelFactory
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: HomeViewModel
    private lateinit var sessionManager: SessionManager
    private lateinit var featuredAdapter: DestinationAdapter
    private lateinit var nearbyAdapter: DestinationAdapter

    private val locationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                loadNearbyByCurrentLocation()
            } else {
                Toast.makeText(
                    requireContext(),
                    "Bạn chưa cấp quyền vị trí, dùng vị trí mặc định ICTU",
                    Toast.LENGTH_SHORT
                ).show()
                loadNearbyFallback()
            }
        }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())

        val repo = DestinationRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, HomeViewModelFactory(repo))[HomeViewModel::class.java]

        val user = sessionManager.getUser()
        val hour = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        val greetingBase = when (hour) {
            in 5..11 -> "Chào buổi sáng"
            in 12..17 -> "Chào buổi chiều"
            else -> "Chào buổi tối"
        }
        val firstName = user?.fullName?.split(" ")?.last() ?: "bạn"
        binding.tvGreeting.text = "$greetingBase, $firstName! ✨"
        binding.tvSubtitle.text = "Khám phá Việt Nam"

        setupAdapters()
        setupClickListeners()
        observeViewModel()
        loadData()
    }

    private fun setupAdapters() {
        featuredAdapter = DestinationAdapter(
            onClick = { dest ->
                val bundle = Bundle().apply {
                    putInt("destinationId", dest.id)
                }
                findNavController().navigate(
                    R.id.action_homeFragment_to_destinationDetailFragment,
                    bundle
                )
            },
            onFavoriteClick = { dest ->
                viewModel.toggleFavorite(
                    sessionManager.getBearerToken(),
                    dest.id,
                    dest.isFavorite
                )
                dest.isFavorite = !dest.isFavorite
                featuredAdapter.notifyDataSetChanged()
            }
        )

        binding.rvFeatured.apply {
            layoutManager = LinearLayoutManager(context, LinearLayoutManager.HORIZONTAL, false)
            adapter = featuredAdapter
            itemAnimator = DefaultItemAnimator().apply {
                addDuration = 220
                changeDuration = 140
                moveDuration = 200
                removeDuration = 160
            }
        }

        nearbyAdapter = DestinationAdapter(
            onClick = { dest ->
                val bundle = Bundle().apply {
                    putInt("destinationId", dest.id)
                }
                findNavController().navigate(
                    R.id.action_homeFragment_to_destinationDetailFragment,
                    bundle
                )
            },
            onFavoriteClick = { dest ->
                viewModel.toggleFavorite(
                    sessionManager.getBearerToken(),
                    dest.id,
                    dest.isFavorite
                )
                dest.isFavorite = !dest.isFavorite
                nearbyAdapter.notifyDataSetChanged()
            },
            onMapClick = { dest ->
                val bundle = Bundle().apply {
                    putFloat("latitude", dest.latitude.toFloat())
                    putFloat("longitude", dest.longitude.toFloat())
                    putString("destinationName", dest.name)
                }
                findNavController().navigate(R.id.mapFragment, bundle)
            }
        )

        binding.rvNearby.apply {
            layoutManager = LinearLayoutManager(context, LinearLayoutManager.HORIZONTAL, false)
            adapter = nearbyAdapter
            itemAnimator = DefaultItemAnimator().apply {
                addDuration = 220
                changeDuration = 140
                moveDuration = 200
                removeDuration = 160
            }
        }
    }

    private fun setupClickListeners() {
        binding.searchView.setOnClickListener {
            findNavController().navigate(R.id.action_homeFragment_to_homeDestinationListFragment)
        }

        binding.btnViewAllFeatured.setOnClickListener {
            findNavController().navigate(R.id.action_homeFragment_to_homeDestinationListFragment)
        }

        binding.btnViewAllNearby.setOnClickListener {
            findNavController().navigate(R.id.action_homeFragment_to_homeDestinationListFragment)
        }

        binding.chipBeach.setOnClickListener {
            navigateToCategory(CategoryMapper.BEACH)
        }

        binding.chipMountain.setOnClickListener {
            navigateToCategory(CategoryMapper.MOUNTAIN)
        }

        binding.chipCity.setOnClickListener {
            navigateToCategory(CategoryMapper.CITY)
        }

        binding.chipHeritage.setOnClickListener {
            navigateToCategory(CategoryMapper.HERITAGE)
        }

        binding.chipNature.setOnClickListener {
            navigateToCategory(CategoryMapper.NATURE)
        }

        binding.chipCheckin.setOnClickListener {
            navigateToCategory(CategoryMapper.CHECKIN)
        }

        binding.chipHistorical.setOnClickListener {
            navigateToCategory(CategoryMapper.HERITAGE)
        }

        binding.chipFood.setOnClickListener {
            navigateToCategory(CategoryMapper.FOOD)
        }

        binding.chipCulture.setOnClickListener {
            navigateToCategory(CategoryMapper.CULTURE)
        }

        binding.chipReligious.setOnClickListener {
            navigateToCategory(CategoryMapper.RELIGIOUS)
        }

        binding.ivNotification.setOnClickListener {
            Toast.makeText(
                requireContext(),
                "Bạn không có thông báo mới 🔔",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    private fun navigateToCategory(category: String) {
        val normalizedCategory = CategoryMapper.categoryParam(category) ?: return
        val bundle = Bundle().apply {
            putString("category", normalizedCategory)
        }
        findNavController().navigate(
            R.id.action_homeFragment_to_homeDestinationListFragment,
            bundle
        )
    }

    private fun loadData() {
        val token = sessionManager.getBearerToken()
        viewModel.loadFeatured(token)

        requestNearbyLocation()
    }

    private fun requestNearbyLocation() {
        val permission = Manifest.permission.ACCESS_FINE_LOCATION

        if (
            ContextCompat.checkSelfPermission(requireContext(), permission)
            == PackageManager.PERMISSION_GRANTED
        ) {
            loadNearbyByCurrentLocation()
        } else {
            locationPermissionLauncher.launch(permission)
        }
    }

    private fun loadNearbyByCurrentLocation() {
        val token = sessionManager.getBearerToken()
        val fusedLocationClient = LocationServices.getFusedLocationProviderClient(requireActivity())

        if (
            ContextCompat.checkSelfPermission(
                requireContext(),
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            loadNearbyFallback()
            return
        }

        val cancellationTokenSource = CancellationTokenSource()

        fusedLocationClient.getCurrentLocation(
            Priority.PRIORITY_HIGH_ACCURACY,
            cancellationTokenSource.token
        )
            .addOnSuccessListener { location ->
                if (
                    location == null ||
                    isInvalidOrUnusableLocation(location.latitude, location.longitude)
                ) {
                    Toast.makeText(
                        requireContext(),
                        "Không lấy được vị trí hợp lệ, dùng khu vực mặc định",
                        Toast.LENGTH_SHORT
                    ).show()
                    loadNearbyFallback()
                    return@addOnSuccessListener
                }

                viewModel.loadNearby(
                    token = token,
                    lat = location.latitude,
                    lng = location.longitude,
                    radiusKm = 50,
                    limit = 20
                )
            }
            .addOnFailureListener { error ->
                Toast.makeText(
                    requireContext(),
                    "GPS lỗi: ${error.message}",
                    Toast.LENGTH_LONG
                ).show()
                loadNearbyFallback()
            }
    }

    private fun loadNearbyFallback() {
        val token = sessionManager.getBearerToken()

        viewModel.loadNearby(
            token = token,
            lat = 21.5878,
            lng = 105.8069,
            radiusKm = 50,
            limit = 20
        )
    }

    /**
     * FusedLocationProvider đôi khi trả (0,0) hoặc NaN trên emulator — Haversine sẽ không khớp địa điểm VN trong 50km.
     */
    private fun isInvalidOrUnusableLocation(lat: Double, lng: Double): Boolean {
        if (!lat.isFinite() || !lng.isFinite()) return true
        if (kotlin.math.abs(lat) < 1e-5 && kotlin.math.abs(lng) < 1e-5) return true
        return false
    }

    private fun observeViewModel() {
        viewModel.featured.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressFeatured.visibility = View.VISIBLE
                }

                is Resource.Success -> {
                    binding.progressFeatured.visibility = View.GONE
                    featuredAdapter.submitList(result.data.toList())
                }

                is Resource.Error -> {
                    binding.progressFeatured.visibility = View.GONE
                }
            }
        }

        viewModel.nearby.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressNearby.visibility = View.VISIBLE
                }

                is Resource.Success -> {
                    binding.progressNearby.visibility = View.GONE
                    nearbyAdapter.submitList(result.data.toList())
                }

                is Resource.Error -> {
                    binding.progressNearby.visibility = View.GONE
                    Toast.makeText(
                        requireContext(),
                        "Không tải được địa điểm gần bạn",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}