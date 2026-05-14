package com.smarttravel.ui.itinerary

import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.view.LayoutInflater
import android.view.Menu
import android.view.MenuInflater
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.view.MenuProvider
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.textfield.MaterialAutoCompleteTextView
import com.google.android.material.textfield.TextInputEditText
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.Itinerary
import com.smarttravel.data.model.ItineraryDay
import com.smarttravel.data.model.ItineraryItem
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.data.repository.ItineraryRepository
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
    private lateinit var destRepo: DestinationRepository
    private var currentItinerary: Itinerary? = null
    private var itineraryIdArg: Int = 0

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentItineraryDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        destRepo = DestinationRepository(RetrofitClient.apiService)
        val itinRepo = ItineraryRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, ItineraryViewModelFactory(itinRepo, destRepo))[ItineraryViewModel::class.java]
        viewModel.init(sessionManager.getBearerToken())

        itineraryIdArg = arguments?.getInt("itineraryId") ?: return

        binding.toolbar.setNavigationOnClickListener { findNavController().navigateUp() }
        binding.toolbar.addMenuProvider(
            object : MenuProvider {
                override fun onCreateMenu(menu: Menu, menuInflater: MenuInflater) {
                    menuInflater.inflate(R.menu.menu_itinerary_detail, menu)
                }

                override fun onMenuItemSelected(menuItem: MenuItem): Boolean {
                    if (menuItem.itemId == R.id.itinerary_action_edit_meta) {
                        val itin = currentItinerary ?: return true
                        EditItineraryDialog(itin) { title, desc, start, end, budget ->
                            viewModel.updateItineraryMeta(
                                id = itin.id,
                                title = title,
                                description = desc,
                                startDate = start,
                                endDate = end,
                                estimatedBudget = budget,
                                status = itin.status
                            )
                        }.show(parentFragmentManager, "edit_itinerary")
                        return true
                    }
                    return false
                }
            },
            viewLifecycleOwner,
            Lifecycle.State.RESUMED
        )

        binding.fabAddStop.setOnClickListener {
            showAddDestinationPicker(preselectedDay = null)
        }

        binding.btnAddDay.setOnClickListener {
            viewModel.addItineraryDay(itineraryIdArg)
        }

        viewModel.loadDetail(itineraryIdArg)

        viewModel.itineraryDetail.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Success -> {
                    val it = result.data
                    currentItinerary = it
                    binding.tvTitle.text = it.title
                    binding.chipDateRange.text = "${it.startDate} → ${it.endDate}"
                    binding.chipDayCount.text = getString(R.string.days_format, it.totalDays)
                    binding.tvDescription.text = it.description ?: "Không có mô tả"
                    it.estimatedBudget?.let { b ->
                        binding.tvBudget.text = "Ngân sách: ${String.format("%,.0f", b)}đ"
                        binding.tvBudget.visibility = View.VISIBLE
                    } ?: run {
                        binding.tvBudget.visibility = View.GONE
                    }

                    if (!it.days.isNullOrEmpty()) {
                        val adapter = ItineraryDayAdapter(
                            days = it.days,
                            onDestinationClick = { destId ->
                                val action =
                                    ItineraryDetailFragmentDirections.actionItineraryDetailFragmentToDestinationDetailFragment(
                                        destId
                                    )
                                findNavController().navigate(action)
                            },
                            onAddToDay = { day -> showAddDestinationPicker(preselectedDay = day) },
                            onDeleteDay = { day -> confirmDeleteDay(it, day) },
                            onEditItem = { item -> showEditItemDialog(it, item) },
                            onDeleteItem = { item -> confirmDeleteItem(it, item) }
                        )
                        binding.rvDays.adapter = adapter
                    } else {
                        binding.rvDays.adapter = null
                    }
                }
                is Resource.Error -> Toast.makeText(context, result.message, Toast.LENGTH_SHORT).show()
                else -> {}
            }
        }

        viewModel.messages.observe(viewLifecycleOwner) { msg ->
            msg?.let {
                Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
                viewModel.clearMessage()
            }
        }
    }

    private fun showAddDestinationPicker(preselectedDay: ItineraryDay?) {
        val itin = currentItinerary ?: return
        val days = itin.days
        if (days.isNullOrEmpty()) {
            Toast.makeText(context, "Lịch trình chưa có ngày nào", Toast.LENGTH_SHORT).show()
            return
        }
        val dayIds = days.map { d -> d.id }.toIntArray()
        val labels = days.map { d -> "Ngày ${d.dayNumber} · ${d.date}" }.toTypedArray()
        val fixedIdx = preselectedDay?.let { d -> days.indexOfFirst { x -> x.id == d.id } } ?: -1
        AddItineraryStopBottomSheet.newInstance(dayIds, labels, fixedIdx)
            .show(childFragmentManager, "add_itinerary_stop")
    }

    internal fun onDestinationPickedForItinerary(dayId: Int, destinationId: Int) {
        viewModel.addItemToItinerary(itineraryIdArg, dayId, destinationId)
    }

    private fun showEditItemDialog(itinerary: Itinerary, item: ItineraryItem) {
        val days = itinerary.days ?: return
        val ctx = requireContext()
        val form = layoutInflater.inflate(R.layout.dialog_edit_itinerary_item, null, false)
        val labels = days.map { d -> "Ngày ${d.dayNumber} · ${d.date}" }
        val actDay = form.findViewById<MaterialAutoCompleteTextView>(R.id.actDay)
        actDay.setAdapter(
            android.widget.ArrayAdapter(ctx, R.layout.item_dropdown_day_line, labels)
        )
        val dayIndex = days.indexOfFirst { d -> d.id == item.dayId }.coerceAtLeast(0)
        var selectedIdx = dayIndex
        actDay.setText(labels[dayIndex], false)
        actDay.threshold = 0
        actDay.setOnItemClickListener { _, _, position, _ -> selectedIdx = position }

        val etStart = form.findViewById<TextInputEditText>(R.id.etStartTime)
        val etEnd = form.findViewById<TextInputEditText>(R.id.etEndTime)
        val etNote = form.findViewById<TextInputEditText>(R.id.etNote)
        etStart.setText(item.startTime)
        etEnd.setText(item.endTime)
        etNote.setText(item.note ?: "")

        val dialog = MaterialAlertDialogBuilder(ctx)
            .setView(form)
            .create()
        dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))

        form.findViewById<MaterialButton>(R.id.btnEditItemCancel).setOnClickListener { dialog.dismiss() }
        form.findViewById<MaterialButton>(R.id.btnEditItemSave).setOnClickListener {
            val selDay = days[selectedIdx]
            val start = etStart.text?.toString()?.trim().orEmpty()
            val end = etEnd.text?.toString()?.trim().orEmpty()
            val note = etNote.text?.toString()?.trim().orEmpty().ifBlank { null }
            if (start.isBlank() || end.isBlank()) {
                Toast.makeText(ctx, "Nhập giờ bắt đầu và kết thúc", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            viewModel.updateItineraryItem(itinerary.id, item, selDay.id, start, end, note)
            dialog.dismiss()
        }
        dialog.show()
    }

    private fun confirmDeleteDay(itinerary: Itinerary, day: ItineraryDay) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle(R.string.itinerary_delete_day_confirm_title)
            .setMessage(R.string.itinerary_delete_day_confirm_message)
            .setNegativeButton("Hủy", null)
            .setPositiveButton("Xóa ngày") { _, _ ->
                viewModel.deleteItineraryDay(itinerary.id, day.id)
            }
            .show()
    }

    private fun confirmDeleteItem(itinerary: Itinerary, item: ItineraryItem) {
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Xóa hoạt động này?")
            .setMessage(item.destination?.name ?: "Địa điểm")
            .setNegativeButton("Hủy", null)
            .setPositiveButton("Xóa") { _, _ ->
                viewModel.deleteItineraryItem(itinerary.id, item.id)
            }
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

class ItineraryDayAdapter(
    private val days: List<ItineraryDay>,
    private val onDestinationClick: (Int) -> Unit,
    private val onAddToDay: (ItineraryDay) -> Unit,
    private val onDeleteDay: (ItineraryDay) -> Unit,
    private val onEditItem: (ItineraryItem) -> Unit,
    private val onDeleteItem: (ItineraryItem) -> Unit
) : androidx.recyclerview.widget.RecyclerView.Adapter<ItineraryDayAdapter.ViewHolder>() {

    class ViewHolder(view: View) : androidx.recyclerview.widget.RecyclerView.ViewHolder(view) {
        val tvDayTitle: android.widget.TextView = view.findViewById(R.id.tvDayTitle)
        val tvDayDate: android.widget.TextView = view.findViewById(R.id.tvDayDate)
        val btnAddToDay: MaterialButton = view.findViewById(R.id.btnAddToDay)
        val btnDeleteDay: MaterialButton = view.findViewById(R.id.btnDeleteDay)
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
        holder.btnAddToDay.setOnClickListener { onAddToDay(day) }
        holder.btnDeleteDay.setOnClickListener { onDeleteDay(day) }

        holder.rvDestinations.layoutManager = androidx.recyclerview.widget.LinearLayoutManager(holder.itemView.context)
        holder.rvDestinations.adapter = ItineraryDestinationAdapter(
            items = day.items,
            onItemClickIds = onDestinationClick,
            onEditItem = onEditItem,
            onDeleteItem = onDeleteItem
        )
    }

    override fun getItemCount() = days.size
}

class ItineraryDestinationAdapter(
    private val items: List<ItineraryItem>,
    private val onItemClickIds: (Int) -> Unit,
    private val onEditItem: (ItineraryItem) -> Unit,
    private val onDeleteItem: (ItineraryItem) -> Unit
) : androidx.recyclerview.widget.RecyclerView.Adapter<ItineraryDestinationAdapter.ViewHolder>() {

    class ViewHolder(view: View) : androidx.recyclerview.widget.RecyclerView.ViewHolder(view) {
        val tvStartTime: android.widget.TextView = view.findViewById(R.id.tvStartTime)
        val tvEndTime: android.widget.TextView = view.findViewById(R.id.tvEndTime)
        val tvDestName: android.widget.TextView = view.findViewById(R.id.tvDestName)
        val tvDestAddress: android.widget.TextView = view.findViewById(R.id.tvDestAddress)
        val tvNote: android.widget.TextView = view.findViewById(R.id.tvNote)
        val btnEditItem: MaterialButton = view.findViewById(R.id.btnEditItem)
        val btnDeleteItem: MaterialButton = view.findViewById(R.id.btnDeleteItem)
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
            onItemClickIds(item.destinationId)
        }

        holder.btnEditItem.setOnClickListener {
            onEditItem(item)
        }
        holder.btnDeleteItem.setOnClickListener {
            onDeleteItem(item)
        }
    }

    override fun getItemCount() = items.size
}

// ==================== AI SUGGEST FRAGMENT ====================

class AISuggestFragment : Fragment() {

    private var _binding: com.smarttravel.databinding.FragmentAiSuggestBinding? = null
    private val binding get() = _binding!!
    private lateinit var itineraryViewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = com.smarttravel.databinding.FragmentAiSuggestBinding.inflate(inflater, container, false)
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
