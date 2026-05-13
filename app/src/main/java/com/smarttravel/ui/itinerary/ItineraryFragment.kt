package com.smarttravel.ui.itinerary

import android.app.AlertDialog
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.smarttravel.data.model.AIRecommendedDestination
import android.os.Bundle
import android.view.*
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.model.Itinerary
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.databinding.FragmentItineraryBinding
import com.smarttravel.databinding.ItemItineraryBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.ItineraryViewModel
import com.smarttravel.viewmodel.ItineraryViewModelFactory
import java.text.SimpleDateFormat
import java.util.*
import com.smarttravel.data.model.AIItineraryOption
import com.smarttravel.data.model.AIItineraryOptionDay
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity

import android.widget.Space

// ==================== ITINERARY FRAGMENT ====================

class ItineraryFragment : Fragment() {

    private var _binding: FragmentItineraryBinding? = null
    private val binding get() = _binding!!
    private lateinit var viewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager
    private lateinit var adapter: ItineraryAdapter
    private var pendingAITitle: String = ""
    private var pendingAIDescription: String? = null
    private var pendingAIStartDate: String = ""
    private var pendingAIEndDate: String = ""
    private var pendingAIBudget: Double? = null
    private var aiOptionsDialog: AlertDialog? = null
    private var aiEditorDialog: AlertDialog? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentItineraryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        val itinRepo = ItineraryRepository(RetrofitClient.apiService)
        val destRepo = DestinationRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, ItineraryViewModelFactory(itinRepo, destRepo))[ItineraryViewModel::class.java]
        viewModel.init(sessionManager.getBearerToken())

        setupAdapter()
        setupButtons()
        observeViewModel()

        // Show back button if navigated from Profile
        if (findNavController().currentDestination?.id == R.id.profileItineraryListFragment) {
            binding.btnBack.visibility = View.VISIBLE
            binding.btnBack.setOnClickListener {
                findNavController().popBackStack()
            }
        }

        viewModel.loadItineraries()
    }

    private fun setupAdapter() {
        adapter = ItineraryAdapter(
            onClick = { itinerary ->
                val bundle = Bundle().apply { putInt("itineraryId", itinerary.id) }
                val currentDest = findNavController().currentDestination?.id
                val actionId = if (currentDest == R.id.profileItineraryListFragment) {
                    R.id.action_profileItineraryListFragment_to_itineraryDetailFragment
                } else {
                    R.id.action_itineraryFragment_to_itineraryDetailFragment
                }
                findNavController().navigate(actionId, bundle)
            },
            onDelete = { itinerary ->
                viewModel.deleteItinerary(itinerary.id)
            }
        )
        binding.rvItineraries.adapter = adapter
    }

    private fun setupButtons() {
        binding.btnCreate.setOnClickListener {
            showCreateDialog()
        }
        binding.btnAISuggest.setOnClickListener {
            findNavController().navigate(R.id.action_itineraryFragment_to_aiItineraryRequestFragment)
        }
    }

    private fun showCreateDialog() {
        val dialog = CreateItineraryDialog { title, desc, startDate, endDate ->
            viewModel.createItinerary(title, desc, startDate, endDate)
        }
        dialog.show(parentFragmentManager, "create_itinerary")
    }

    private fun observeViewModel() {
        viewModel.itineraries.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> binding.progressBar.visibility = View.VISIBLE
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    adapter.submitList(result.data.toList())
                    binding.tvCount.text = "${result.data.size} lịch trình"
                    binding.layoutEmpty.visibility = if (result.data.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvItineraries.visibility = if (result.data.isNotEmpty()) View.VISIBLE else View.GONE
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, result.message, Toast.LENGTH_SHORT).show()
                }
            }
        }


        viewModel.messages.observe(viewLifecycleOwner) { msg ->
            msg?.let {
                Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
                viewModel.clearMessage()
            }
        }
        viewModel.aiPreview.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    showAISuggestionsDialog(result.data.suggestedDestinations)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, result.message, Toast.LENGTH_LONG).show()
                }
            }
        }

        viewModel.createFromAI.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, "Đã tạo lịch trình từ AI", Toast.LENGTH_SHORT).show()
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, result.message, Toast.LENGTH_LONG).show()
                }
            }
        }
        viewModel.aiOptions.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    showAITourOptionsDialog(result.data.options)
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, result.message, Toast.LENGTH_LONG).show()
                }
            }
        }

        viewModel.createFromOption.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    aiEditorDialog?.dismiss()
                    aiEditorDialog = null
                    Toast.makeText(context, "Đã tạo lịch trình từ tour AI 💙", Toast.LENGTH_SHORT).show()
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(context, result.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    private fun showAIPlannerDialog() {
        val context = requireContext()

        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(14), dp(22), dp(18))
            background = makeRoundedBg(0xFFF3FBF7.toInt(), radiusDp = 24)
        }

        val subtitle = TextView(context).apply {
            text = "Nói cho UnuTrip biết bạn muốn đi kiểu nào, AI sẽ gợi ý vài tour hợp gu nha ✨"
            textSize = 14f
            setTextColor(0xFF5E7671.toInt())
            setLineSpacing(dp(2).toFloat(), 1.0f)
            setPadding(0, 0, 0, dp(10))
        }
        root.addView(subtitle)

        fun styledEditText(
            hintText: String,
            defaultText: String = "",
            minLinesValue: Int = 1,
            inputTypeValue: Int? = null
        ): EditText {
            return EditText(context).apply {
                hint = hintText
                setText(defaultText)
                textSize = 14f
                setTextColor(0xFF213533.toInt())
                setHintTextColor(0xFF8CA7A1.toInt())
                background = makeRoundedBg(
                    color = 0xFFFFFFFF.toInt(),
                    radiusDp = 16,
                    strokeColor = 0xFFD7E9E2.toInt(),
                    strokeWidthDp = 1
                )
                setPadding(dp(14), dp(10), dp(14), dp(10))
                minLines = minLinesValue
                inputTypeValue?.let { inputType = it }

                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    bottomMargin = dp(10)
                }
            }
        }

        val etTitle = styledEditText(
            hintText = "Tên chuyến đi",
            defaultText = "Đi Cao Bằng"
        )

        val etProvince = styledEditText(
            hintText = "Bạn muốn đi đâu?",
            defaultText = "Cao Bằng"
        )

        val etDescription = styledEditText(
            hintText = "Bạn thích kiểu đi chơi nào?",
            defaultText = "muốn đi checkin ăn uống văn hóa",
            minLinesValue = 2
        )

        val etStartDate = styledEditText(
            hintText = "Ngày bắt đầu: yyyy-MM-dd",
            defaultText = "2026-05-10"
        )

        val etEndDate = styledEditText(
            hintText = "Ngày kết thúc: yyyy-MM-dd",
            defaultText = "2026-05-12"
        )

        val etBudget = styledEditText(
            hintText = "Ngân sách dự kiến",
            defaultText = "3000000",
            inputTypeValue = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL
        )

        val etPreferences = styledEditText(
            hintText = "Sở thích, cách nhau bằng dấu phẩy",
            defaultText = "checkin, food, culture"
        )

        root.addView(makeLabelText("Tên chuyến đi"))
        root.addView(etTitle)

        root.addView(makeLabelText("Điểm đến"))
        root.addView(etProvince)

        root.addView(makeLabelText("Gu đi chơi"))
        root.addView(etDescription)

        val dateRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val startBox = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
            ).apply {
                rightMargin = dp(6)
            }
            addView(makeLabelText("Ngày đi"))
            addView(etStartDate)
        }

        val endBox = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1f
            ).apply {
                leftMargin = dp(6)
            }
            addView(makeLabelText("Ngày về"))
            addView(etEndDate)
        }

        dateRow.addView(startBox)
        dateRow.addView(endBox)
        root.addView(dateRow)

        root.addView(makeLabelText("Ngân sách"))
        root.addView(etBudget)

        root.addView(makeLabelText("Sở thích"))
        root.addView(etPreferences)

        val hint = TextView(context).apply {
            text = "Gợi ý: checkin, food, culture, nature, mountain, heritage, religious"
            textSize = 12f
            setTextColor(0xFF8CA7A1.toInt())
            setPadding(0, dp(2), 0, 0)
        }
        root.addView(hint)

        val scrollView = ScrollView(context).apply {
            addView(root)
        }

        AlertDialog.Builder(context)
            .setTitle("Bạn muốn đi đâu nè? ✨")
            .setView(scrollView)
            .setNegativeButton("Để sau", null)
            .setPositiveButton("Gợi ý tour") { _, _ ->
                val title = etTitle.text.toString().trim()
                val province = etProvince.text.toString().trim().ifBlank { null }
                val description = etDescription.text.toString().trim().ifBlank { null }
                val startDate = etStartDate.text.toString().trim()
                val endDate = etEndDate.text.toString().trim()
                val budget = etBudget.text.toString().trim().toDoubleOrNull()
                val preferences = etPreferences.text.toString()
                    .split(",")
                    .map { it.trim() }
                    .filter { it.isNotBlank() }

                if (title.isBlank() || startDate.isBlank() || endDate.isBlank()) {
                    Toast.makeText(
                        context,
                        "Bạn nhập tên chuyến đi và ngày đi/ngày về nha",
                        Toast.LENGTH_SHORT
                    ).show()
                    return@setPositiveButton
                }

                pendingAITitle = title
                pendingAIDescription = description
                pendingAIStartDate = startDate
                pendingAIEndDate = endDate
                pendingAIBudget = budget

                viewModel.getAIItineraryOptions(
                    title = title,
                    description = description,
                    startDate = startDate,
                    endDate = endDate,
                    budget = budget,
                    preferences = preferences,
                    province = province
                )
            }
            .show()
    }
    private fun showAISuggestionsDialog(suggestions: List<AIRecommendedDestination>) {
        if (suggestions.isEmpty()) {
            Toast.makeText(context, "AI chưa tìm được địa điểm phù hợp", Toast.LENGTH_LONG).show()
            return
        }

        val context = requireContext()

        val container = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 16, 32, 16)
        }

        val checkBoxes = mutableListOf<Pair<CheckBox, AIRecommendedDestination>>()

        suggestions.forEach { destination ->
            val itemLayout = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, 12, 0, 12)
            }

            val checkBox = CheckBox(context).apply {
                isChecked = true
                text = buildString {
                    append(destination.name ?: "Không tên")
                    append(" • ")
                    append(destination.category ?: "other")
                    destination.recommendedDay?.let {
                        append(" • Ngày ")
                        append(it)
                    }
                }
            }

            val reason = TextView(context).apply {
                text = destination.reason ?: ""
                textSize = 13f
                setPadding(48, 0, 0, 0)
            }

            itemLayout.addView(checkBox)
            itemLayout.addView(reason)
            container.addView(itemLayout)

            checkBoxes.add(checkBox to destination)
        }

        val scrollView = ScrollView(context).apply {
            addView(container)
        }

        AlertDialog.Builder(context)
            .setTitle("Chọn địa điểm AI gợi ý")
            .setView(scrollView)
            .setNegativeButton("Hủy", null)
            .setPositiveButton("Tạo lịch trình") { _, _ ->
                val selected = checkBoxes
                    .filter { it.first.isChecked }
                    .map { it.second }

                if (selected.isEmpty()) {
                    Toast.makeText(context, "Bạn chưa chọn địa điểm nào", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }

                viewModel.createItineraryFromSelection(
                    title = pendingAITitle,
                    description = pendingAIDescription,
                    startDate = pendingAIStartDate,
                    endDate = pendingAIEndDate,
                    budget = pendingAIBudget,
                    selectedDestinations = selected
                )
            }
            .show()
    }
    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private fun makeRoundedBg(
        color: Int,
        radiusDp: Int = 18,
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

    private fun makeLabelText(text: String): TextView {
        return TextView(requireContext()).apply {
            this.text = text
            textSize = 13f
            setTextColor(0xFF5E7671.toInt())
            setPadding(0, dp(8), 0, dp(4))
            typeface = Typeface.DEFAULT_BOLD
        }
    }

    private fun makeChip(text: String, kind: String = "mint"): TextView {
        val bgColor = when (kind) {
            "coral" -> 0xFFFFE7DF.toInt()
            "green" -> 0xFFE7F8F1.toInt()
            "soft" -> 0xFFF3FBF7.toInt()
            else -> 0xFFE7F8F1.toInt()
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
            background = makeRoundedBg(bgColor, radiusDp = 999)
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

    private fun themeLabel(theme: String?): String {
        return when (theme) {
            "balanced" -> "🌈 Cân bằng"
            "checkin" -> "📸 Check-in"
            "food_culture" -> "🍜 Ẩm thực & văn hóa"
            "relax_nature" -> "🌿 Nhẹ nhàng"
            else -> "✨ Tour AI"
        }
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

    private fun formatBudget(value: Double?): String {
        return value?.let { "~${String.format("%,.0f", it)}đ" } ?: "Chưa ước tính"
    }
    private fun showAITourOptionsDialog(options: List<AIItineraryOption>) {
        if (options.isEmpty()) {
            Toast.makeText(context, "AI chưa tạo được phương án tour", Toast.LENGTH_LONG).show()
            return
        }

        val context = requireContext()

        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(16))
            background = makeRoundedBg(0xFFF3FBF7.toInt(), radiusDp = 24)
        }

        val intro = TextView(context).apply {
            text = "UnuTrip đã chuẩn bị vài tour hợp gu cho bạn nè ✨"
            textSize = 14f
            setTextColor(0xFF5E7671.toInt())
            setPadding(0, 0, 0, dp(12))
        }
        root.addView(intro)

        options.forEachIndexed { index, option ->
            val card = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(18), dp(16), dp(18), dp(16))
                background = makeRoundedBg(
                    color = 0xFFFFFFFF.toInt(),
                    radiusDp = 24,
                    strokeColor = 0xFFD7E9E2.toInt(),
                    strokeWidthDp = 1
                )
                elevation = dp(2).toFloat()
            }

            val topRow = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            val titleView = TextView(context).apply {
                text = "${index + 1}. ${option.title}"
                textSize = 18f
                setTextColor(0xFF213533.toInt())
                setTypeface(null, Typeface.BOLD)
                layoutParams = LinearLayout.LayoutParams(
                    0,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    1f
                )
            }

            val themeChip = makeChip(themeLabel(option.theme), kind = "coral")

            topRow.addView(titleView)
            topRow.addView(themeChip)
            card.addView(topRow)

            addGap(card, 8)

            val summaryView = TextView(context).apply {
                text = option.summary ?: "Một phương án tour được AI gợi ý theo nhu cầu của bạn."
                textSize = 14f
                setTextColor(0xFF5E7671.toInt())
                setLineSpacing(dp(2).toFloat(), 1.0f)
            }
            card.addView(summaryView)

            addGap(card, 10)

            val metaRow = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            metaRow.addView(makeChip("🗓 ${option.totalDays} ngày", "green"))
            metaRow.addView(Space(context).apply {
                layoutParams = LinearLayout.LayoutParams(dp(8), 1)
            })
            metaRow.addView(makeChip("💰 ${formatBudget(option.estimatedBudget)}", "soft"))

            card.addView(metaRow)

            if (option.highlights.isNotEmpty()) {
                addGap(card, 10)

                val highlights = TextView(context).apply {
                    text = "Nổi bật: ${option.highlights.take(4).joinToString(" • ")}"
                    textSize = 13f
                    setTextColor(0xFF2F876D.toInt())
                    setLineSpacing(dp(2).toFloat(), 1.0f)
                }
                card.addView(highlights)
            }

            addGap(card, 14)

            val chooseButton = TextView(context).apply {
                text = "Chọn tour này 💙"
                textSize = 15f
                gravity = Gravity.CENTER
                setTextColor(0xFFFFFFFF.toInt())
                setTypeface(null, Typeface.BOLD)
                background = makeRoundedBg(0xFFFF8C72.toInt(), radiusDp = 999)
                setPadding(dp(16), dp(11), dp(16), dp(11))
                setOnClickListener {
                    aiOptionsDialog?.dismiss()
                    showAITourEditorDialog(option)
                }
            }

            card.addView(chooseButton)

            root.addView(card)

            if (index != options.lastIndex) {
                addGap(root, 14)
            }
        }

        val scrollView = ScrollView(context).apply {
            addView(root)
        }

        aiOptionsDialog = AlertDialog.Builder(context)
            .setTitle("Chọn tour AI nè ✨")
            .setView(scrollView)
            .setNegativeButton("Đóng", null)
            .show()
    }
    private fun showAITourEditorDialog(option: AIItineraryOption) {
        val context = requireContext()

        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(12), dp(20), dp(16))
            background = makeRoundedBg(0xFFF3FBF7.toInt(), radiusDp = 24)
        }

        val summary = TextView(context).apply {
            text = "Bạn có thể bỏ bớt địa điểm chưa thích trước khi lưu lịch trình nha 🌿"
            textSize = 14f
            setTextColor(0xFF5E7671.toInt())
            setPadding(0, 0, 0, dp(12))
        }
        root.addView(summary)

        val dayCheckBoxes = mutableMapOf<Int, MutableList<Pair<CheckBox, AIRecommendedDestination>>>()

        option.days.forEach { day ->
            val dayBox = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(14), dp(12), dp(14), dp(12))
                background = makeRoundedBg(
                    color = 0xFFFFFFFF.toInt(),
                    radiusDp = 22,
                    strokeColor = 0xFFD7E9E2.toInt(),
                    strokeWidthDp = 1
                )
                elevation = dp(1).toFloat()
            }

            val selectedCountText = "${day.items.size} địa điểm"

            val dayHeader = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
            }

            val dayTitle = TextView(context).apply {
                text = "Ngày ${day.dayNumber} 🌤"
                textSize = 17f
                setTextColor(0xFF213533.toInt())
                setTypeface(null, Typeface.BOLD)
                layoutParams = LinearLayout.LayoutParams(
                    0,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    1f
                )
            }

            val dayChip = makeChip(selectedCountText, "green")

            dayHeader.addView(dayTitle)
            dayHeader.addView(dayChip)
            dayBox.addView(dayHeader)

            addGap(dayBox, 10)

            val list = mutableListOf<Pair<CheckBox, AIRecommendedDestination>>()
            dayCheckBoxes[day.dayNumber] = list

            day.items.forEachIndexed { index, destination ->
                val itemLayout = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(8), dp(8), dp(8), dp(10))
                    background = makeRoundedBg(
                        color = 0xFFFDFEFE.toInt(),
                        radiusDp = 16,
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
                    buttonTintList = android.content.res.ColorStateList.valueOf(0xFF62BE9B.toInt())
                }

                val metaRow = LinearLayout(context).apply {
                    orientation = LinearLayout.HORIZONTAL
                    setPadding(dp(48), dp(2), 0, 0)
                }

                metaRow.addView(makeChip(destination.category ?: "other", "soft"))

                destination.estimatedVisitDurationMinutes?.let {
                    metaRow.addView(Space(context).apply {
                        layoutParams = LinearLayout.LayoutParams(dp(8), 1)
                    })
                    metaRow.addView(makeChip("${it} phút", "coral"))
                }

                val reasonView = TextView(context).apply {
                    text = destination.reason ?: ""
                    textSize = 12.5f
                    setTextColor(0xFF5E7671.toInt())
                    setPadding(dp(48), dp(6), 0, 0)
                    setLineSpacing(dp(2).toFloat(), 1.0f)
                }

                itemLayout.addView(checkBox)
                itemLayout.addView(metaRow)
                itemLayout.addView(reasonView)

                dayBox.addView(itemLayout)

                if (index != day.items.lastIndex) {
                    addGap(dayBox, 8)
                }

                list.add(checkBox to destination)
            }

            root.addView(dayBox)
            addGap(root, 14)
        }

        val scrollView = ScrollView(context).apply {
            addView(root)
        }

        aiEditorDialog = AlertDialog.Builder(context)
            .setTitle("Chỉnh tour trước khi lưu ✨")
            .setView(scrollView)
            .setNegativeButton("Quay lại", null)
            .setPositiveButton("Tạo lịch trình") { _, _ ->
                val editedDays = option.days.map { day ->
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
                    Toast.makeText(context, "Bạn chưa chọn địa điểm nào", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }

                val editedOption = option.copy(days = editedDays)

                viewModel.createItineraryFromOption(
                    title = pendingAITitle.ifBlank { option.title },
                    description = option.summary,
                    startDate = pendingAIStartDate,
                    endDate = pendingAIEndDate,
                    budget = pendingAIBudget ?: option.estimatedBudget,
                    option = editedOption
                )
            }
            .show()
    }
    override fun onDestroyView() {
        super.onDestroyView()
        aiOptionsDialog?.dismiss()
        aiEditorDialog?.dismiss()
        aiOptionsDialog = null
        aiEditorDialog = null
        _binding = null
    }
}

// ==================== ITINERARY ADAPTER ====================

class ItineraryAdapter(
    private val onClick: (Itinerary) -> Unit,
    private val onDelete: (Itinerary) -> Unit
) : ListAdapter<Itinerary, ItineraryAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(private val binding: ItemItineraryBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(itinerary: Itinerary) {
            binding.tvTitle.text = itinerary.title
            binding.tvDuration.text = "${itinerary.totalDays} ngày"

            // Format dates
            try {
                val inputFmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val outputFmt = SimpleDateFormat("dd/MM", Locale.getDefault())
                val start = inputFmt.parse(itinerary.startDate)
                val end = inputFmt.parse(itinerary.endDate)
                binding.tvDates.text = "${start?.let { outputFmt.format(it) }} - ${end?.let { outputFmt.format(it) }}"
            } catch (e: Exception) {
                binding.tvDates.text = "${itinerary.startDate} - ${itinerary.endDate}"
            }

            // Budget
            itinerary.estimatedBudget?.let { budget ->
                binding.tvBudget.text = "Ngân sách: ${String.format("%,.0f", budget)}đ"
                binding.layoutBudget.visibility = View.VISIBLE
            } ?: run {
                binding.layoutBudget.visibility = View.GONE
            }

            // Status
            binding.tvStatus.text = when (itinerary.status) {
                "planned" -> "Đã lên kế hoạch"
                "completed" -> "Hoàn thành"
                "cancelled" -> "Đã hủy"
                else -> "Nháp"
            }

            // AI badge
            binding.tvAIBadge.visibility = View.GONE // set based on field if available

            binding.root.setOnClickListener { onClick(itinerary) }

            binding.btnMore.setOnClickListener { view ->
                val popup = android.widget.PopupMenu(view.context, view)
                popup.menu.add("Xóa lịch trình")
                popup.setOnMenuItemClickListener {
                    onDelete(itinerary)
                    true
                }
                popup.show()
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemItineraryBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) = holder.bind(getItem(position))

    class DiffCallback : DiffUtil.ItemCallback<Itinerary>() {
        override fun areItemsTheSame(a: Itinerary, b: Itinerary) = a.id == b.id
        override fun areContentsTheSame(a: Itinerary, b: Itinerary) = a == b
    }
}
