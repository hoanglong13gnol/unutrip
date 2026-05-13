package com.smarttravel.ui.destination

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.preference.PreferenceManager
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.google.android.gms.location.LocationServices
import com.smarttravel.databinding.FragmentMapBinding
import com.smarttravel.utils.MapIntentHelper
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.MapView
import org.osmdroid.views.overlay.Marker

class MapFragment : Fragment() {

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private lateinit var mapView: MapView

    private var currentLat: Double? = null
    private var currentLng: Double? = null

    private val locationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                loadCurrentLocation()
            } else {
                Toast.makeText(requireContext(), "Bạn chưa cấp quyền vị trí", Toast.LENGTH_SHORT).show()
            }
        }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        Configuration.getInstance().load(
            requireContext(),
            PreferenceManager.getDefaultSharedPreferences(requireContext())
        )
        Configuration.getInstance().userAgentValue = requireContext().packageName

        val lat = arguments?.getFloat("latitude")?.toDouble() ?: 21.5878
        val lng = arguments?.getFloat("longitude")?.toDouble() ?: 105.8069
        val name = arguments?.getString("destinationName") ?: "ICTU Thái Nguyên"

        binding.tvDestName.text = name

        binding.btnBack.setOnClickListener {
            findNavController().navigateUp()
        }

        binding.btnOpenGoogleMap.setOnClickListener {
            MapIntentHelper.openPlace(requireContext(), lat, lng, name)
        }

        binding.btnDirection.setOnClickListener {
            val startLat = currentLat
            val startLng = currentLng

            if (startLat != null && startLng != null) {
                MapIntentHelper.openRoute(
                    requireContext(),
                    listOf(
                        Pair(startLat, startLng),
                        Pair(lat, lng)
                    )
                )
            } else {
                Toast.makeText(
                    requireContext(),
                    "Chưa có GPS, sẽ dùng vị trí hiện tại của Google Maps",
                    Toast.LENGTH_SHORT
                ).show()

                MapIntentHelper.openNavigation(requireContext(), lat, lng, name)
            }
        }

        mapView = binding.map
        mapView.setTileSource(TileSourceFactory.MAPNIK)
        mapView.setMultiTouchControls(true)

        val point = GeoPoint(lat, lng)
        mapView.controller.setZoom(15.0)
        mapView.controller.setCenter(point)

        val marker = Marker(mapView).apply {
            position = point
            title = name
            setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
        }

        mapView.overlays.add(marker)
        mapView.invalidate()

        requestCurrentLocationIfNeeded()
    }

    private fun requestCurrentLocationIfNeeded() {
        val permission = Manifest.permission.ACCESS_FINE_LOCATION

        if (
            ContextCompat.checkSelfPermission(requireContext(), permission)
            == PackageManager.PERMISSION_GRANTED
        ) {
            loadCurrentLocation()
        } else {
            locationPermissionLauncher.launch(permission)
        }
    }

    private fun loadCurrentLocation() {
        val fusedLocationClient = LocationServices.getFusedLocationProviderClient(requireActivity())

        if (
            ContextCompat.checkSelfPermission(
                requireContext(),
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        fusedLocationClient.lastLocation
            .addOnSuccessListener { location ->
                if (location == null) {
                    Toast.makeText(
                        requireContext(),
                        "Chưa lấy được vị trí hiện tại",
                        Toast.LENGTH_SHORT
                    ).show()
                    return@addOnSuccessListener
                }

                currentLat = location.latitude
                currentLng = location.longitude

                val currentPoint = GeoPoint(location.latitude, location.longitude)

                val currentMarker = Marker(mapView).apply {
                    position = currentPoint
                    title = "Bạn đang ở đây"
                    setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                }

                mapView.overlays.add(currentMarker)
                mapView.invalidate()
            }
            .addOnFailureListener {
                Toast.makeText(
                    requireContext(),
                    "Không lấy được vị trí hiện tại",
                    Toast.LENGTH_SHORT
                ).show()
            }
    }

    override fun onResume() {
        super.onResume()
        if (::mapView.isInitialized) {
            mapView.onResume()
        }
    }

    override fun onPause() {
        super.onPause()
        if (::mapView.isInitialized) {
            mapView.onPause()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}