package com.smarttravel.ui.chatbot

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.gson.Gson
import com.smarttravel.R
import com.smarttravel.data.model.AIItineraryOption
import com.smarttravel.data.model.AIRecommendedDestination
import com.smarttravel.data.model.ChatMessage
import com.smarttravel.databinding.FragmentChatbotBinding
import com.smarttravel.utils.ChatTripDayParser
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.ChatbotViewModel
import java.time.LocalDate

class ChatbotFragment : Fragment() {

    private var _binding: FragmentChatbotBinding? = null
    private val binding get() = _binding!!

    private val viewModel: ChatbotViewModel by viewModels()
    private lateinit var adapter: ChatMessageAdapter
    private lateinit var sessionManager: SessionManager
    private var currentMessages: List<ChatMessage> = emptyList()
    private var isTypingVisible: Boolean = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentChatbotBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())

        viewModel.init(sessionManager.getToken() ?: "")

        setupAdapter()
        setupUI()
        observeViewModel()
    }

    private fun setupAdapter() {
        adapter = ChatMessageAdapter { message ->
            openChatbotItineraryEditor(message)
        }

        binding.rvMessages.apply {
            layoutManager = LinearLayoutManager(context).apply {
                stackFromEnd = true
            }
            adapter = this@ChatbotFragment.adapter
        }
    }

    private fun setupUI() {
        binding.btnSend.setOnClickListener {
            sendMessage()
        }

        binding.etMessage.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                sendMessage()
                true
            } else {
                false
            }
        }

        binding.btnClearChat.setOnClickListener {
            viewModel.clearChat()
        }

        binding.chipSuggest1.setOnClickListener {
            binding.etMessage.setText("Gợi ý địa điểm du lịch đẹp ở Đà Nẵng")
            sendMessage()
        }

        binding.chipSuggest2.setOnClickListener {
            binding.etMessage.setText("Lịch trình 3 ngày ở Hội An")
            sendMessage()
        }

        binding.chipSuggest3.setOnClickListener {
            binding.etMessage.setText("Ăn gì khi đến Hà Nội?")
            sendMessage()
        }
    }

    private fun sendMessage() {
        val message = binding.etMessage.text.toString().trim()
        if (message.isBlank()) return

        binding.etMessage.text?.clear()
        viewModel.sendMessage(message)
    }

    private fun observeViewModel() {
        viewModel.messages.observe(viewLifecycleOwner) { messages ->
            currentMessages = messages.toList()
            renderMessages()
        }

        viewModel.isLoading.observe(viewLifecycleOwner) { isLoading ->
            isTypingVisible = isLoading

            binding.progressTyping.visibility = View.GONE
            binding.btnSend.isEnabled = !isLoading

            renderMessages()
        }
    }
    private fun renderMessages() {
        val displayMessages = if (isTypingVisible) {
            currentMessages + ChatMessage(
                role = "typing",
                content = "",
                timestamp = Long.MAX_VALUE
            )
        } else {
            currentMessages
        }

        adapter.submitList(displayMessages) {
            if (adapter.itemCount > 0) {
                binding.rvMessages.scrollToPosition(adapter.itemCount - 1)
            }
        }
    }

    /** Số ngày: ưu tiên hint từ ViewModel (đồng bộ RAG), sau đó câu user, rồi nội dung bot. */
    private fun resolveTripDayCount(message: ChatMessage): Int {
        val fromHint = message.tripDaysHint?.takeIf { it > 0 }
        val prev = getPreviousUserMessage(message)
        val fromUser = ChatTripDayParser.extractTripDays(prev)
        val fromBot = ChatTripDayParser.extractTripDays(message.content)
        return (fromHint ?: fromUser ?: fromBot)?.coerceIn(1, 10) ?: 1
    }

    private fun getPreviousUserMessage(botMessage: ChatMessage): String {
        val messages = viewModel.messages.value.orEmpty()
        val botIndex = messages.indexOf(botMessage)

        return if (botIndex > 0) {
            messages
                .take(botIndex)
                .lastOrNull { it.role == "user" }
                ?.content
                .orEmpty()
        } else {
            messages
                .lastOrNull { it.role == "user" }
                ?.content
                .orEmpty()
        }
    }

    private fun openChatbotItineraryEditor(message: ChatMessage) {
        val validPlaces = message.places.filter {
            !it.rawPlaceId.isNullOrBlank()
        }

        if (validPlaces.isEmpty()) {
            Toast.makeText(
                requireContext(),
                "Chưa có địa điểm hợp lệ để tạo lịch trình",
                Toast.LENGTH_SHORT
            ).show()
            return
        }

        val totalDays = resolveTripDayCount(message)

        val today = LocalDate.now()
        val endDate = today.plusDays((totalDays - 1).toLong())

        val items = validPlaces.map { place ->
            AIRecommendedDestination(
                rawPlaceId = place.rawPlaceId,
                destinationId = null,
                name = place.name ?: "Địa điểm",
                province = place.province,
                city = place.city,
                area = place.area,
                category = place.categoryMain ?: "other",
                imageUrl = null,
                reason = "Gợi ý từ chatbot RAG",
                recommendedDay = 1,
                estimatedVisitDurationMinutes = null,
                qualityScore = place.score
            )
        }

        val days = ChatTripDayParser.splitDestinationsAcrossDays(
            items = items,
            totalDays = totalDays
        )

        val option = AIItineraryOption(
            optionId = "chatbot",
            title = "Lịch trình từ chatbot ($totalDays ngày)",
            theme = "chatbot",
            summary = "Gợi ý theo tin nhắn của bạn ($totalDays ngày). Có thể chỉnh sửa trước khi lưu.",
            totalDays = totalDays,
            estimatedBudget = null,
            highlights = validPlaces.mapNotNull { it.name }.take(5),
            days = days
        )

        val optionJson = Gson().toJson(option)

        val bundle = Bundle().apply {
            putString("title", "Lịch trình từ chatbot")
            putString("description", "Tạo từ gợi ý RAG chatbot")
            putString("startDate", today.toString())
            putString("endDate", endDate.toString())
            putDouble("budget", -1.0)
            putString("optionJson", optionJson)
            putString("source", "chatbot")
        }

        findNavController().navigate(
            R.id.aiItineraryEditorFragment,
            bundle
        )
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}