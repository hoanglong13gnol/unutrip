package com.smarttravel.ui.itinerary

import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.Space
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import com.google.gson.Gson
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.AIItineraryOption
import com.smarttravel.data.model.AIItineraryOptionDay
import com.smarttravel.data.model.AIRecommendedDestination
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.databinding.FragmentAiItineraryEditorBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.ItineraryViewModel
import com.smarttravel.viewmodel.ItineraryViewModelFactory
import androidx.activity.OnBackPressedCallback

class AIItineraryEditorFragment : Fragment() {

    private var _binding: FragmentAiItineraryEditorBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager

    private val gson = Gson()

    private var title: String = ""
    private var description: String? = null
    private var startDate: String = ""
    private var endDate: String = ""
    private var budget: Double? = null
    private var option: AIItineraryOption? = null

    private val dayCheckBoxes = mutableMapOf<Int, MutableList<Pair<CheckBox, AIRecommendedDestination>>>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        title = arguments?.getString("title").orEmpty()
        description = arguments?.getString("description")
        startDate = arguments?.getString("startDate").orEmpty()
        endDate = arguments?.getString("endDate").orEmpty()

        val rawBudget = arguments?.getDouble("budget", -1.0) ?: -1.0
        budget = if (rawBudget >= 0) rawBudget else null

        val optionJson = arguments?.getString("optionJson").orEmpty()
        option = if (optionJson.isNotBlank()) {
            try {
                gson.fromJson(optionJson, AIItineraryOption::class.java)
            } catch (e: Exception) {
                null
            }
        } else {
            null
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAiItineraryEditorBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())

        val itinRepo = ItineraryRepository(RetrofitClient.apiService)
        val destRepo = DestinationRepository(RetrofitClient.apiService)

        viewModel = ViewModelProvider(
            this,
            ItineraryViewModelFactory(itinRepo, destRepo)
        )[ItineraryViewModel::class.java]

        viewModel.init(sessionManager.getBearerToken())
        binding.btnBack.background = roundedBg(
            color = 0x33FFFFFF,
            radiusDp = 999
        )

        binding.btnBack.setOnClickListener {
            goBack()
        }

        requireActivity().onBackPressedDispatcher.addCallback(
            viewLifecycleOwner,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    goBack()
                }
            }
        )
        binding.tvHeaderTitle.text = option?.title ?: "Chỉnh tour trước khi lưu ✨"
        binding.tvHeaderSubtitle.text = option?.summary
            ?: "Bạn có thể bỏ bớt địa điểm chưa thích trước khi tạo lịch trình."

        renderOption()
        setupActions()
        observeViewModel()
    }

    private fun renderOption() {
        val currentOption = option

        binding.layoutDays.removeAllViews()
        dayCheckBoxes.clear()

        if (currentOption == null) {
            Toast.makeText(requireContext(), "Không đọc được tour đã chọn", Toast.LENGTH_LONG).show()
            return
        }

        currentOption.days.forEach { day ->
            binding.layoutDays.addView(createDayCard(day))
            binding.layoutDays.addView(Space(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dp(14)
                )
            })
        }

        updateSelectedSummary()
    }

    private fun createDayCard(day: AIItineraryOptionDay): View {
        val context = requireContext()

        val dayBox = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = roundedBg(
                color = 0xFFFFFFFF.toInt(),
                radiusDp = 24,
                strokeColor = 0xFFDCEBE5.toInt(),
                strokeWidthDp = 1
            )
            elevation = dp(3).toFloat()
        }

        val header = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val dayTitle = TextView(context).apply {
            text = "Ngày ${day.dayNumber} 🌤"
            textSize = 18f
            setTextColor(0xFF213533.toInt())
            setTypeface(null, Typeface.BOLD)
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
            )
        }

        header.addView(dayTitle)
        header.addView(chip("${day.items.size} địa điểm", "green"))
        dayBox.addView(header)

        addGap(dayBox, 12)

        val list = mutableListOf<Pair<CheckBox, AIRecommendedDestination>>()
        dayCheckBoxes[day.dayNumber] = list

        day.items.forEachIndexed { index, destination ->
            dayBox.addView(createDestinationItem(destination, list))

            if (index != day.items.lastIndex) {
                addGap(dayBox, 10)
            }
        }

        return dayBox
    }

    private fun createDestinationItem(
        destination: AIRecommendedDestination,
        list: MutableList<Pair<CheckBox, AIRecommendedDestination>>
    ): View {
        val context = requireContext()

        val itemLayout = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), dp(10), dp(10), dp(12))
            background = roundedBg(
                color = 0xFFFDFEFE.toInt(),
                radiusDp = 18,
                strokeColor = 0xFFE5F1EC.toInt(),
                strokeWidthDp = 1
            )
        }

        val checkBox = CheckBox(context).apply {
            isChecked = true
            text = buildString {
                append(categoryEmoji(destination.category))
                append(" ")
                append(destination.name ?: "Không tên")
            }
            textSize = 15f
            setTextColor(0xFF213533.toInt())
            setTypeface(null, Typeface.BOLD)
            setOnCheckedChangeListener { _, _ ->
                updateSelectedSummary()
            }
        }

        val metaRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(48), dp(4), 0, 0)
        }

        metaRow.addView(chip(destination.category ?: "other", "soft"))

        destination.estimatedVisitDurationMinutes?.let {
            metaRow.addView(Space(context).apply {
                layoutParams = LinearLayout.LayoutParams(dp(8), 1)
            })
            metaRow.addView(chip("${it} phút", "coral"))
        }

        val reasonView = TextView(context).apply {
            text = destination.reason ?: ""
            textSize = 12.5f
            setTextColor(0xFF5E7671.toInt())
            setPadding(dp(48), dp(8), 0, 0)
            setLineSpacing(dp(2).toFloat(), 1.0f)
        }

        itemLayout.addView(checkBox)
        itemLayout.addView(metaRow)
        itemLayout.addView(reasonView)

        list.add(checkBox to destination)

        return itemLayout
    }

    private fun setupActions() {
        binding.btnCreateItinerary.setOnClickListener {
            createItineraryFromEditedOption()
        }
    }

    private fun createItineraryFromEditedOption() {
        val currentOption = option ?: return

        val editedDays = currentOption.days.map { day ->
            val selectedItems = dayCheckBoxes[day.dayNumber]
                ?.filter { it.first.isChecked }
                ?.map { it.second }
                ?: emptyList()

            AIItineraryOptionDay(
                dayNumber = day.dayNumber,
                items = selectedItems
            )
        }.filter { it.items.isNotEmpty() }

        if (editedDays.isEmpty()) {
            Toast.makeText(requireContext(), "Bạn chưa chọn địa điểm nào", Toast.LENGTH_SHORT).show()
            return
        }

        val editedOption = currentOption.copy(days = editedDays)

        viewModel.createItineraryFromOption(
            title = title.ifBlank { currentOption.title },
            description = description ?: currentOption.summary,
            startDate = startDate,
            endDate = endDate,
            budget = budget ?: currentOption.estimatedBudget,
            option = editedOption
        )
    }

    private fun observeViewModel() {
        viewModel.createFromOption.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnCreateItinerary.isEnabled = false
                }

                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnCreateItinerary.isEnabled = true
                    Toast.makeText(
                        requireContext(),
                        "Đã tạo lịch trình từ tour AI 💙",
                        Toast.LENGTH_SHORT
                    ).show()

                    findNavController().popBackStack(R.id.itineraryFragment, false)
                }

                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnCreateItinerary.isEnabled = true
                    Toast.makeText(requireContext(), result.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun updateSelectedSummary() {
        val selectedCount = dayCheckBoxes.values
            .flatten()
            .count { it.first.isChecked }

        binding.tvSelectedSummary.text = "Đã chọn $selectedCount địa điểm"
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private fun roundedBg(
        color: Int,
        radiusDp: Int,
        strokeColor: Int? = null,
        strokeWidthDp: Int = 1
    ): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = dp(radiusDp).toFloat()
            setColor(color)
            if (strokeColor != null) {
                setStroke(dp(strokeWidthDp), strokeColor)
            }
        }
    }

    private fun chip(text: String, kind: String): TextView {
        val bgColor = when (kind) {
            "coral" -> 0xFFFFE7DF.toInt()
            "green" -> 0xFFE7F8F1.toInt()
            else -> 0xFFF3FBF7.toInt()
        }

        val textColor = when (kind) {
            "coral" -> 0xFFE96F56.toInt()
            else -> 0xFF2F876D.toInt()
        }

        return TextView(requireContext()).apply {
            this.text = text
            textSize = 12f
            setTextColor(textColor)
            setTypeface(null, Typeface.BOLD)
            background = roundedBg(bgColor, radiusDp = 999)
            setPadding(dp(10), dp(5), dp(10), dp(5))
        }
    }

    private fun addGap(parent: LinearLayout, heightDp: Int) {
        parent.addView(Space(requireContext()).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(heightDp)
            )
        })
    }

    private fun categoryEmoji(category: String?): String {
        return when (category) {
            "checkin" -> "📸"
            "food" -> "🍜"
            "culture" -> "🎎"
            "heritage" -> "🏛"
            "religious" -> "🙏"
            "mountain" -> "⛰"
            "nature" -> "🌿"
            "beach" -> "🏖"
            "city" -> "🏙"
            else -> "📍"
        }
    }
    private fun goBack() {
        val source = arguments?.getString("source")

        if (source == "chatbot") {
            findNavController().navigateUp()
        } else {
            findNavController().popBackStack(
                R.id.aiItineraryOptionsFragment,
                false
            )
        }
    }
}