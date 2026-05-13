package com.smarttravel.ui.itinerary

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.data.repository.ItineraryRepository
import com.smarttravel.databinding.FragmentAiItineraryRequestBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.ItineraryViewModel
import com.smarttravel.viewmodel.ItineraryViewModelFactory
import androidx.activity.OnBackPressedCallback
import android.graphics.drawable.GradientDrawable


class AIItineraryRequestFragment : Fragment() {

    private var _binding: FragmentAiItineraryRequestBinding? = null
    private val binding get() = _binding!!

    private lateinit var viewModel: ItineraryViewModel
    private lateinit var sessionManager: SessionManager

    private var pendingTitle: String = ""
    private var pendingDescription: String? = null
    private var pendingStartDate: String = ""
    private var pendingEndDate: String = ""
    private var pendingBudget: Double? = null
    private var pendingProvince: String? = null
    private var pendingPreferences: Array<String> = emptyArray()
    private var hasNavigatedToOptions: Boolean = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAiItineraryRequestBinding.inflate(inflater, container, false)
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
        setupActions()
        observeViewModel()

    }

    private fun setupActions() {
        binding.btnGenerateOptions.setOnClickListener {
            val title = binding.etTitle.text.toString().trim()
            val province = binding.etProvince.text.toString().trim().ifBlank { null }
            val description = binding.etDescription.text.toString().trim().ifBlank { null }
            val startDate = binding.etStartDate.text.toString().trim()
            val endDate = binding.etEndDate.text.toString().trim()
            val budget = binding.etBudget.text.toString().trim().toDoubleOrNull()
            val preferences = binding.etPreferences.text.toString()
                .split(",")
                .map { it.trim() }
                .filter { it.isNotBlank() }

            if (title.isBlank() || startDate.isBlank() || endDate.isBlank()) {
                Toast.makeText(
                    requireContext(),
                    "Bạn nhập tên chuyến đi và ngày đi/ngày về nha",
                    Toast.LENGTH_SHORT
                ).show()
                return@setOnClickListener
            }

            pendingTitle = title
            pendingDescription = description
            pendingStartDate = startDate
            pendingEndDate = endDate
            pendingBudget = budget
            pendingProvince = province
            pendingPreferences = preferences.toTypedArray()

            hasNavigatedToOptions = false
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
    }

    private fun observeViewModel() {
        viewModel.aiOptions.observe(viewLifecycleOwner) { result ->
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.btnGenerateOptions.isEnabled = false
                }

                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnGenerateOptions.isEnabled = true

                    if (hasNavigatedToOptions) {
                        return@observe
                    }

                    hasNavigatedToOptions = true

                    val bundle = Bundle().apply {
                        putString("title", pendingTitle)
                        putString("description", pendingDescription)
                        putString("startDate", pendingStartDate)
                        putString("endDate", pendingEndDate)
                        putDouble("budget", pendingBudget ?: -1.0)
                        putString("province", pendingProvince)
                        putStringArray("preferences", pendingPreferences)
                        putString("optionsJson", com.google.gson.Gson().toJson(result.data.options))
                    }

                    findNavController().navigate(
                        R.id.action_aiItineraryRequestFragment_to_aiItineraryOptionsFragment,
                        bundle
                    )
                }

                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.btnGenerateOptions.isEnabled = true
                    Toast.makeText(requireContext(), result.message, Toast.LENGTH_LONG).show()
                }
            }
        }
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

    private fun goBack() {
        findNavController().popBackStack()
    }
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}