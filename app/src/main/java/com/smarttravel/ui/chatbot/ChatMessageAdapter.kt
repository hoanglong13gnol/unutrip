package com.smarttravel.ui.chatbot

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.AccelerateDecelerateInterpolator
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.smarttravel.data.model.ChatMessage
import com.smarttravel.databinding.ItemChatBotBinding
import com.smarttravel.databinding.ItemChatTypingBinding
import com.smarttravel.databinding.ItemChatUserBinding

class ChatMessageAdapter(
    private val onCreateItineraryClick: (ChatMessage) -> Unit
) : ListAdapter<ChatMessage, RecyclerView.ViewHolder>(DiffCallback()) {

    companion object {
        const val VIEW_TYPE_USER = 1
        const val VIEW_TYPE_BOT = 2
        const val VIEW_TYPE_TYPING = 3
    }

    override fun getItemViewType(position: Int): Int {
        val message = getItem(position)

        return when (message.role) {
            "user" -> VIEW_TYPE_USER
            "typing" -> VIEW_TYPE_TYPING
            else -> VIEW_TYPE_BOT
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)

        return when (viewType) {
            VIEW_TYPE_USER -> {
                val binding = ItemChatUserBinding.inflate(inflater, parent, false)
                UserMessageViewHolder(binding)
            }

            VIEW_TYPE_BOT -> {
                val binding = ItemChatBotBinding.inflate(inflater, parent, false)
                BotMessageViewHolder(binding)
            }

            VIEW_TYPE_TYPING -> {
                val binding = ItemChatTypingBinding.inflate(inflater, parent, false)
                TypingViewHolder(binding)
            }

            else -> {
                val binding = ItemChatBotBinding.inflate(inflater, parent, false)
                BotMessageViewHolder(binding)
            }
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = getItem(position)

        when (holder) {
            is UserMessageViewHolder -> holder.bind(message)
            is BotMessageViewHolder -> holder.bind(message)
            is TypingViewHolder -> holder.bind()
        }
    }

    inner class UserMessageViewHolder(
        private val binding: ItemChatUserBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(message: ChatMessage) {
            binding.tvMessage.text = message.content
        }
    }

    inner class BotMessageViewHolder(
        private val binding: ItemChatBotBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(message: ChatMessage) {
            binding.tvMessage.text = cleanMarkdownText(message.content)

            val canCreate = message.places.any {
                !it.rawPlaceId.isNullOrBlank()
            }

            binding.btnCreateItinerary.visibility = if (canCreate) {
                View.VISIBLE
            } else {
                View.GONE
            }

            binding.btnCreateItinerary.text = "Tạo lịch trình"

            binding.btnCreateItinerary.setOnClickListener {
                onCreateItineraryClick(message)
            }
        }
    }

    inner class TypingViewHolder(
        private val binding: ItemChatTypingBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind() {
            startDotAnimation(binding.dot1, 0L)
            startDotAnimation(binding.dot2, 150L)
            startDotAnimation(binding.dot3, 300L)
        }

        private fun startDotAnimation(view: View, delay: Long) {
            view.clearAnimation()

            ObjectAnimator.ofFloat(view, "translationY", 0f, -10f, 0f).apply {
                duration = 650L
                startDelay = delay
                repeatCount = ValueAnimator.INFINITE
                interpolator = AccelerateDecelerateInterpolator()
                start()
            }
        }
    }

    private fun cleanMarkdownText(text: String): String {
        return text
            .replace("**", "")
            .replace(Regex("(?m)^\\s*\\*\\s+"), "   • ")
            .replace(Regex("(?m)^\\s*-\\s+"), "   • ")
            .replace(Regex("\\n\\s*•"), "\n   •")
            .replace(Regex("\\n{3,}"), "\n\n")
            .trim()
    }

    class DiffCallback : DiffUtil.ItemCallback<ChatMessage>() {
        override fun areItemsTheSame(a: ChatMessage, b: ChatMessage): Boolean {
            return a.timestamp == b.timestamp && a.role == b.role
        }

        override fun areContentsTheSame(a: ChatMessage, b: ChatMessage): Boolean {
            return a == b
        }
    }
}