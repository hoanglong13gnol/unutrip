package com.smarttravel.ui.itinerary

import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.databinding.FragmentAiSuggestBinding
import com.smarttravel.databinding.FragmentItineraryDetailBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.ItineraryViewModel
import com.smarttravel.viewmodel.ItineraryViewModelFactory

// ==================== ITINERARY DETAIL ====================

class ItineraryDetailFragment : Fragment() {

    private var _binding: FragmentItineraryDetailBinding? = null
    private val binding get() = _binding!!
    private lateinit var viewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentItineraryDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        val itinRepo = ItineraryRepository(RetrofitClient.apiService)
        val destRepo = DestinationRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, ItineraryViewModelFactory(itinRepo, destRepo))[ItineraryViewModel::class.java]
        viewModel.init(sessionManager.getBearerToken())

        binding.toolbar.setNavigationOnClickListener { findNavController().navigateUp() }

        val id = arguments?.getInt("itineraryId") ?: return
        viewModel.loadDetail(id)

        viewModel.itineraryDetail.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Success -> {
                    val it = result.data
                    binding.tvTitle.text = it.title
                    binding.tvDates.text = "${it.startDate} → ${it.endDate}"
                    binding.tvDays.text = "${it.totalDays} ngày"
                    binding.tvDescription.text = it.description ?: "Không có mô tả"
                    it.estimatedBudget?.let { b ->
                        binding.tvBudget.text = "Ngân sách: ${String.format("%,.0f", b)}đ"
                    }
                    
                    // Render days
                    if (!it.days.isNullOrEmpty()) {
                        val adapter = ItineraryDayAdapter(it.days) { destId ->
                            val action = ItineraryDetailFragmentDirections.actionItineraryDetailFragmentToDestinationDetailFragment(destId)
                            findNavController().navigate(action)
                        }
                        binding.rvDays.adapter = adapter
                    }
                }
                is Resource.Error -> Toast.makeText(context, result.message, Toast.LENGTH_SHORT).show()
                else -> {}
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

class ItineraryDayAdapter(
    private val days: List<com.smarttravel.data.model.ItineraryDay>,
    private val onItemClick: (Int) -> Unit
) : androidx.recyclerview.widget.RecyclerView.Adapter<ItineraryDayAdapter.ViewHolder>() {

    class ViewHolder(view: View) : androidx.recyclerview.widget.RecyclerView.ViewHolder(view) {
        val tvDayTitle: android.widget.TextView = view.findViewById(R.id.tvDayTitle)
        val tvDayDate: android.widget.TextView = view.findViewById(R.id.tvDayDate)
        val rvDestinations: androidx.recyclerview.widget.RecyclerView = view.findViewById(R.id.rvDestinations)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_itinerary_day, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val day = days[position]
        holder.tvDayTitle.text = "Ngày ${day.dayNumber}"
        holder.tvDayDate.text = day.date
        
        holder.rvDestinations.layoutManager = androidx.recyclerview.widget.LinearLayoutManager(holder.itemView.context)
        holder.rvDestinations.adapter = ItineraryDestinationAdapter(day.items, onItemClick)
    }

    override fun getItemCount() = days.size
}

class ItineraryDestinationAdapter(
    private val items: List<com.smarttravel.data.model.ItineraryItem>,
    private val onItemClick: (Int) -> Unit
) : androidx.recyclerview.widget.RecyclerView.Adapter<ItineraryDestinationAdapter.ViewHolder>() {

    class ViewHolder(view: View) : androidx.recyclerview.widget.RecyclerView.ViewHolder(view) {
        val tvStartTime: android.widget.TextView = view.findViewById(R.id.tvStartTime)
        val tvEndTime: android.widget.TextView = view.findViewById(R.id.tvEndTime)
        val tvDestName: android.widget.TextView = view.findViewById(R.id.tvDestName)
        val tvDestAddress: android.widget.TextView = view.findViewById(R.id.tvDestAddress)
        val tvNote: android.widget.TextView = view.findViewById(R.id.tvNote)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_itinerary_destination, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.tvStartTime.text = item.startTime
        holder.tvEndTime.text = item.endTime
        holder.tvDestName.text = item.destination?.name ?: "Địa điểm trống"
        holder.tvDestAddress.text = item.destination?.address ?: ""
        
        if (!item.note.isNullOrBlank()) {
            holder.tvNote.visibility = View.VISIBLE
            holder.tvNote.text = "Ghi chú: ${item.note}"
        } else {
            holder.tvNote.visibility = View.GONE
        }
        
        holder.itemView.setOnClickListener {
            onItemClick(item.destinationId)
        }
    }

    override fun getItemCount() = items.size
}

// ==================== AI SUGGEST FRAGMENT ====================

class AISuggestFragment : Fragment() {

    private var _binding: FragmentAiSuggestBinding? = null
    private val binding get() = _binding!!
    private lateinit var itineraryViewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAiSuggestBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        val itinRepo = ItineraryRepository(RetrofitClient.apiService)
        val destRepo = DestinationRepository(RetrofitClient.apiService)

        itineraryViewModel = ViewModelProvider(this, ItineraryViewModelFactory(itinRepo, destRepo))[ItineraryViewModel::class.java]
        itineraryViewModel.init(sessionManager.getBearerToken())

        binding.btnBack.setOnClickListener { findNavController().navigateUp() }

        // Date pickers
        binding.etStartDate.setOnClickListener { showDatePicker(true) }
        binding.etEndDate.setOnClickListener { showDatePicker(false) }

        binding.btnGenerate.setOnClickListener { generateItinerary() }

        observeViewModel()
    }

    private fun showDatePicker(isStart: Boolean) {
        val picker = com.google.android.material.datepicker.MaterialDatePicker.Builder.datePicker()
            .setTitleText(if (isStart) "Chọn ngày đi" else "Chọn ngày về")
            .build()

        picker.addOnPositiveButtonClickListener { selection ->
            val sdf = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault())
            val dateStr = sdf.format(java.util.Date(selection))
            if (isStart) binding.etStartDate.setText(dateStr)
            else binding.etEndDate.setText(dateStr)
        }
        picker.show(parentFragmentManager, "date_picker")
    }

    private fun generateItinerary() {
        val startDate = binding.etStartDate.text.toString().trim()
        val endDate = binding.etEndDate.text.toString().trim()

        if (startDate.isEmpty() || endDate.isEmpty()) {
            Toast.makeText(context, "Vui lòng chọn ngày đi và ngày về", Toast.LENGTH_SHORT).show()
            return
        }

        val preferences = mutableListOf<String>()
        if (binding.chipPrefBeach.isChecked) preferences.add("beach")
        if (binding.chipPrefMountain.isChecked) preferences.add("mountain")
        if (binding.chipPrefCity.isChecked) preferences.add("city")
        if (binding.chipPrefHeritage.isChecked) preferences.add("heritage")
        if (binding.chipPrefNature.isChecked) preferences.add("nature")
        if (binding.chipPrefFood.isChecked) preferences.add("food")
        if (binding.chipPrefCheckin.isChecked) preferences.add("checkin")
        if (binding.chipPrefCulture.isChecked) preferences.add("culture")
        if (binding.chipPrefShopping.isChecked) preferences.add("shopping")
        if (binding.chipPrefRelax.isChecked) preferences.add("relax")

        val budget = binding.etBudget.text.toString().toDoubleOrNull()
        val startLocation = binding.etStartLocation.text.toString().trim().takeIf { it.isNotBlank() }

        // Show loading
        binding.layoutLoading.visibility = View.VISIBLE
        binding.btnGenerate.isEnabled = false

        itineraryViewModel.generateAIItinerary(
            preferences = if (preferences.isEmpty()) listOf("city", "heritage", "nature") else preferences,
            startDate = startDate,
            endDate = endDate,
            budget = budget,
            startLocation = startLocation
        )
    }

    private fun observeViewModel() {
        itineraryViewModel.aiSuggest.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Success -> {
                    binding.layoutLoading.visibility = View.GONE
                    binding.btnGenerate.isEnabled = true
                    Toast.makeText(context, "✨ Đã tạo lịch trình AI thành công!", Toast.LENGTH_LONG).show()
                    findNavController().navigate(R.id.itineraryFragment)
                }
                is Resource.Error -> {
                    binding.layoutLoading.visibility = View.GONE
                    binding.btnGenerate.isEnabled = true
                    Toast.makeText(context, "Lỗi: ${result.message}", Toast.LENGTH_LONG).show()
                }
                else -> {}
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
