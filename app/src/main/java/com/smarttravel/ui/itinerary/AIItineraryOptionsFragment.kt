package com.smarttravel.ui.itinerary

import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.Space
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.smarttravel.R
import com.smarttravel.data.model.AIItineraryOption
import com.smarttravel.databinding.FragmentAiItineraryOptionsBinding
import androidx.activity.OnBackPressedCallback

class AIItineraryOptionsFragment : Fragment() {

    private var _binding: FragmentAiItineraryOptionsBinding? = null
    private val binding get() = _binding!!

    private val gson = Gson()

    private var title: String = ""
    private var description: String? = null
    private var startDate: String = ""
    private var endDate: String = ""
    private var budget: Double? = null
    private var province: String? = null
    private var preferences: Array<String> = emptyArray()
    private var options: List<AIItineraryOption> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        title = arguments?.getString("title").orEmpty()
        description = arguments?.getString("description")
        startDate = arguments?.getString("startDate").orEmpty()
        endDate = arguments?.getString("endDate").orEmpty()

        val rawBudget = arguments?.getDouble("budget", -1.0) ?: -1.0
        budget = if (rawBudget >= 0) rawBudget else null

        province = arguments?.getString("province")
        preferences = arguments?.getStringArray("preferences") ?: emptyArray()

        val optionsJson = arguments?.getString("optionsJson").orEmpty()
        options = if (optionsJson.isNotBlank()) {
            try {
                val type = object : TypeToken<List<AIItineraryOption>>() {}.type
                gson.fromJson(optionsJson, type)
            } catch (e: Exception) {
                emptyList()
            }
        } else {
            emptyList()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAiItineraryOptionsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.btnBack.background = roundedBg(
            color = 0x33FFFFFF,
            radiusDp = 999
        )
        binding.btnBack.isClickable = true
        binding.btnBack.isFocusable = true
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
        binding.tvHeaderSubtitle.text = if (province.isNullOrBlank()) {
            "UnuTrip đã chuẩn bị vài phương án tour hợp gu cho bạn."
        } else {
            "UnuTrip đã chuẩn bị vài tour cho $province. Chọn một tour để chỉnh sửa nhé."
        }


        renderOptions()
    }

    private fun renderOptions() {
        binding.layoutOptions.removeAllViews()

        if (options.isEmpty()) {
            Toast.makeText(requireContext(), "Chưa có phương án tour", Toast.LENGTH_LONG).show()
            return
        }

        options.forEachIndexed { index, option ->
            binding.layoutOptions.addView(createOptionCard(index, option))

            if (index != options.lastIndex) {
                binding.layoutOptions.addView(Space(requireContext()).apply {
                    layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        dp(16)
                    )
                })
            }
        }
    }

    private fun createOptionCard(index: Int, option: AIItineraryOption): View {
        val context = requireContext()

        val card = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(16))
            background = roundedBg(
                color = 0xFFFFFFFF.toInt(),
                radiusDp = 24,
                strokeColor = 0xFFDCEBE5.toInt(),
                strokeWidthDp = 1
            )
            elevation = dp(3).toFloat()
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

        topRow.addView(titleView)
        topRow.addView(chip(themeLabel(option.theme), "coral"))
        card.addView(topRow)

        addGap(card, 10)

        val summaryView = TextView(context).apply {
            text = option.summary ?: "Một tour được AI gợi ý theo nhu cầu của bạn."
            textSize = 14f
            setTextColor(0xFF5E7671.toInt())
            setLineSpacing(dp(2).toFloat(), 1.0f)
        }
        card.addView(summaryView)

        addGap(card, 12)

        val metaRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        metaRow.addView(chip("🗓 ${option.totalDays} ngày", "green"))

        metaRow.addView(Space(context).apply {
            layoutParams = LinearLayout.LayoutParams(dp(8), 1)
        })

        metaRow.addView(chip("💰 ${formatBudget(option.estimatedBudget)}", "soft"))

        card.addView(metaRow)

        if (option.highlights.isNotEmpty()) {
            addGap(card, 12)

            val highlightsLabel = TextView(context).apply {
                text = "Điểm nổi bật"
                textSize = 13f
                setTextColor(0xFF5E7671.toInt())
                setTypeface(null, Typeface.BOLD)
            }
            card.addView(highlightsLabel)

            addGap(card, 6)

            val highlightsView = TextView(context).apply {
                text = option.highlights.take(4).joinToString("  •  ")
                textSize = 13f
                setTextColor(0xFF2F876D.toInt())
                setLineSpacing(dp(2).toFloat(), 1.0f)
            }

            card.addView(highlightsView)
        }

        addGap(card, 16)

        val chooseButton = TextView(context).apply {
            text = "Chọn tour này 💙"
            textSize = 15f
            gravity = Gravity.CENTER
            setTextColor(0xFFFFFFFF.toInt())
            setTypeface(null, Typeface.BOLD)
            background = roundedBg(0xFFFF8C72.toInt(), radiusDp = 999)
            setPadding(dp(16), dp(12), dp(16), dp(12))
            setOnClickListener {
                openEditor(option)
            }
        }

        card.addView(chooseButton)

        return card
    }

    private fun openEditor(option: AIItineraryOption) {
        val bundle = Bundle().apply {
            putString("title", title.ifBlank { option.title })
            putString("description", description ?: option.summary)
            putString("startDate", startDate)
            putString("endDate", endDate)
            putDouble("budget", budget ?: option.estimatedBudget ?: -1.0)
            putString("province", province)
            putStringArray("preferences", preferences)
            putString("optionJson", gson.toJson(option))
        }

        findNavController().navigate(
            R.id.action_aiItineraryOptionsFragment_to_aiItineraryEditorFragment,
            bundle
        )
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

    private fun themeLabel(theme: String?): String {
        return when (theme) {
            "balanced" -> "🌈 Cân bằng"
            "checkin" -> "📸 Check-in"
            "food_culture" -> "🍜 Ẩm thực & văn hóa"
            "relax_nature" -> "🌿 Nhẹ nhàng"
            else -> "✨ Tour AI"
        }
    }

    private fun formatBudget(value: Double?): String {
        return value?.let { "~${String.format("%,.0f", it)}đ" } ?: "Chưa ước tính"
    }
    private fun goBack() {
        findNavController().popBackStack(
            R.id.aiItineraryRequestFragment,
            false
        )
    }
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}