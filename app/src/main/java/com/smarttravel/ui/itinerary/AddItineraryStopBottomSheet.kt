package com.smarttravel.ui.itinerary

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.os.bundleOf
import androidx.core.view.isVisible
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.chip.Chip
import com.google.android.material.textfield.TextInputEditText
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.Destination
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import com.smarttravel.databinding.BottomSheetAddItineraryStopBinding

class AddItineraryStopBottomSheet : BottomSheetDialogFragment() {

    private var _binding: BottomSheetAddItineraryStopBinding? = null
    private val binding get() = _binding!!

    private lateinit var destRepo: DestinationRepository
    private lateinit var token: String

    private val dayIds: IntArray by lazy { requireArguments().getIntArray(ARG_DAY_IDS)!! }
    private val dayLabels: Array<String> by lazy { requireArguments().getStringArray(ARG_DAY_LABELS)!! }
    private val fixedDayIndex: Int by lazy { requireArguments().getInt(ARG_FIXED_DAY_INDEX, -1) }

    private var selectedDayId: Int = -1
    private var searchJob: Job? = null
    private lateinit var listAdapter: PickDestinationAdapter

    override fun getTheme(): Int = R.style.BottomSheetSmartTravel

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = BottomSheetAddItineraryStopBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        destRepo = DestinationRepository(RetrofitClient.apiService)
        val raw = SessionManager.getInstance(requireContext()).getBearerToken()
        token = if (raw.startsWith("Bearer ")) raw else "Bearer $raw"

        setupDayChips()
        listAdapter = PickDestinationAdapter { dest ->
            val dayId = selectedDayId
            if (dayId <= 0) {
                Toast.makeText(requireContext(), "Chọn ngày trong lịch trình", Toast.LENGTH_SHORT).show()
                return@PickDestinationAdapter
            }
            (parentFragment as? ItineraryDetailFragment)?.onDestinationPickedForItinerary(dayId, dest.id)
            dismiss()
        }
        binding.rvPickDestinations.adapter = listAdapter

        binding.etSearchStop.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(searchable: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                searchJob?.cancel()
                val q = s?.toString()?.trim().orEmpty()
                searchJob = viewLifecycleOwner.lifecycleScope.launch {
                    delay(320)
                    fetchDestinations(q)
                }
            }
        })

        viewLifecycleOwner.lifecycleScope.launch {
            fetchDestinations("")
        }
    }

    private fun setupDayChips() {
        binding.chipGroupDays.removeAllViews()
        if (dayIds.isEmpty() || dayLabels.size != dayIds.size) {
            binding.tvDaySectionLabel.visibility = View.GONE
            binding.scrollDayChips.visibility = View.GONE
            return
        }

        if (fixedDayIndex in dayIds.indices) {
            binding.tvDaySectionLabel.visibility = View.GONE
            binding.scrollDayChips.visibility = View.GONE
            selectedDayId = dayIds[fixedDayIndex]
            binding.tvSheetSubtitle.text = getString(
                R.string.itinerary_add_stop_subtitle_fixed,
                dayLabels[fixedDayIndex]
            )
            return
        }

        binding.tvDaySectionLabel.visibility = View.VISIBLE
        binding.scrollDayChips.visibility = View.VISIBLE
        binding.tvSheetSubtitle.text = getString(R.string.itinerary_add_stop_subtitle_pick_day)

        dayIds.indices.forEach { index ->
            val chip = Chip(requireContext(), null, com.google.android.material.R.attr.chipStyle).apply {
                id = View.generateViewId()
                text = dayLabels[index]
                isCheckable = true
                chipBackgroundColor = ContextCompat.getColorStateList(requireContext(), R.color.chip_bg_selector)
                setTextColor(ContextCompat.getColorStateList(requireContext(), R.color.chip_text_selector)!!)
                chipStrokeColor = ContextCompat.getColorStateList(requireContext(), R.color.chip_stroke_selector)
                chipStrokeWidth = resources.displayMetrics.density
            }
            binding.chipGroupDays.addView(chip)
        }

        val firstChip = binding.chipGroupDays.getChildAt(0) as? Chip
        firstChip?.isChecked = true
        selectedDayId = dayIds[0]

        binding.chipGroupDays.setOnCheckedStateChangeListener { group, checkedIds ->
            if (checkedIds.isEmpty()) return@setOnCheckedStateChangeListener
            val chipId = checkedIds.first()
            val idx = (0 until group.childCount).indexOfFirst { group.getChildAt(it).id == chipId }
            if (idx in dayIds.indices) {
                selectedDayId = dayIds[idx]
            }
        }
    }

    private fun fetchDestinations(query: String) {
        viewLifecycleOwner.lifecycleScope.launch {
            binding.progressStops.isVisible = true
            binding.tvEmptyStops.isVisible = false
            val res = withContext(Dispatchers.IO) {
                destRepo.getDestinations(
                    token = token,
                    page = 1,
                    limit = 40,
                    search = query.ifBlank { null }
                )
            }
            binding.progressStops.isVisible = false
            when (res) {
                is Resource.Success -> {
                    val list = res.data.data
                    listAdapter.submit(list)
                    binding.tvEmptyStops.isVisible = list.isEmpty()
                    binding.tvEmptyStops.text = if (query.isBlank()) {
                        getString(R.string.itinerary_add_stop_empty_browse)
                    } else {
                        getString(R.string.itinerary_add_stop_empty_search)
                    }
                }
                is Resource.Error -> {
                    listAdapter.submit(emptyList())
                    binding.tvEmptyStops.isVisible = true
                    binding.tvEmptyStops.text = res.message
                }
                else -> {}
            }
        }
    }

    override fun onStart() {
        super.onStart()
        val dlg = dialog as? BottomSheetDialog ?: return
        val bottomSheet = dlg.findViewById<View>(com.google.android.material.R.id.design_bottom_sheet) ?: return
        bottomSheet.layoutParams.height = ViewGroup.LayoutParams.MATCH_PARENT
        val behavior = BottomSheetBehavior.from(bottomSheet)
        behavior.state = BottomSheetBehavior.STATE_EXPANDED
        behavior.skipCollapsed = true
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    companion object {
        private const val ARG_DAY_IDS = "day_ids"
        private const val ARG_DAY_LABELS = "day_labels"
        private const val ARG_FIXED_DAY_INDEX = "fixed_day_index"

        fun newInstance(dayIds: IntArray, dayLabels: Array<String>, fixedDayIndex: Int): AddItineraryStopBottomSheet {
            return AddItineraryStopBottomSheet().apply {
                arguments = bundleOf(
                    ARG_DAY_IDS to dayIds,
                    ARG_DAY_LABELS to dayLabels,
                    ARG_FIXED_DAY_INDEX to fixedDayIndex
                )
            }
        }
    }
}

private class PickDestinationAdapter(
    private val onPick: (Destination) -> Unit
) : RecyclerView.Adapter<PickDestinationAdapter.VH>() {

    private var items: List<Destination> = emptyList()

    fun submit(list: List<Destination>) {
        items = list
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_pick_destination_row, parent, false)
        return VH(v, onPick)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount() = items.size

    class VH(itemView: View, private val onPick: (Destination) -> Unit) : RecyclerView.ViewHolder(itemView) {
        fun bind(d: Destination) {
            itemView.findViewById<android.widget.TextView>(R.id.tvDestName).text = d.name
            itemView.findViewById<android.widget.TextView>(R.id.tvDestAddress).text = d.address
            val categoryLabel = categoryLabelVi(d.category)
            val meta = buildString {
                if (d.city.isNotBlank()) {
                    append(d.city)
                    if (d.province.isNotBlank() && d.province != d.city) append(" · ").append(d.province)
                } else if (d.province.isNotBlank()) {
                    append(d.province)
                }
                if (categoryLabel != null) {
                    if (isNotEmpty()) append(" · ")
                    append(categoryLabel)
                }
            }
            itemView.findViewById<android.widget.TextView>(R.id.tvDestMeta).apply {
                text = meta.ifBlank { "Địa điểm" }
            }
            itemView.setOnClickListener { onPick(d) }
        }

        private fun categoryLabelVi(code: String): String? {
            return when (code.lowercase()) {
                "beach" -> "Biển"
                "mountain" -> "Núi"
                "city" -> "Thành phố"
                "heritage" -> "Di sản"
                "nature" -> "Thiên nhiên"
                "checkin" -> "Check-in"
                "food" -> "Ẩm thực"
                "culture" -> "Văn hóa"
                "religious" -> "Tâm linh"
                else -> code.replaceFirstChar { ch ->
                    if (ch.isLowerCase()) ch.titlecase() else ch.toString()
                }.takeIf { it.isNotBlank() }
            }
        }
    }
}
