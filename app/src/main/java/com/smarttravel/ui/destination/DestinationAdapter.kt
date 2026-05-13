package com.smarttravel.ui.destination

import android.view.LayoutInflater
import android.view.ViewGroup
import android.view.animation.AnimationUtils
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.smarttravel.BuildConfig
import com.smarttravel.R
import com.smarttravel.data.model.Destination
import com.smarttravel.databinding.ItemDestinationBinding
import com.smarttravel.databinding.ItemDestinationSmallBinding
import com.smarttravel.utils.CategoryMapper
import android.view.View

// ==================== FEATURED ADAPTER (Horizontal cards) ====================

class DestinationAdapter(
    private val onClick: (Destination) -> Unit,
    private val onFavoriteClick: ((Destination) -> Unit)? = null,
    private val onMapClick: ((Destination) -> Unit)? = null
) : ListAdapter<Destination, DestinationAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(private val binding: ItemDestinationBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(destination: Destination) {
            binding.tvName.text = destination.name
            binding.tvCity.text = "${destination.city}, ${destination.province}"
            binding.tvCategory.text = CategoryMapper.emojiLabel(destination.category)
            binding.tvRating.text = String.format("%.1f", destination.rating)
            binding.tvReviewCount.text = "(${destination.reviewCount})"
            binding.tvFee.text = if ((destination.entryFee ?: 0.0) == 0.0) {
                "MIỄN PHÍ"
            } else {
                "${String.format("%,.0f", destination.entryFee)}đ"
            }
            val distanceKm = destination.distanceKm

            if (distanceKm != null && distanceKm > 0) {
                binding.tvDistance.visibility = View.VISIBLE
                binding.tvDistance.text = if (distanceKm < 1) {
                    "Cách ${(distanceKm * 1000).toInt()} m"
                } else {
                    "Cách %.1f km".format(distanceKm)
                }
            } else {
                binding.tvDistance.visibility = View.GONE
            }

            binding.ivFavorite.setImageResource(
                if (destination.isFavorite) R.drawable.ic_favorite_filled
                else R.drawable.ic_favorite_outline
            )

            if (destination.images.isNotEmpty()) {
                Glide.with(binding.root)
                    .load(resolveImageUrl(destination.images.first()))
                    .placeholder(R.drawable.placeholder_destination)
                    .centerCrop()
                    .into(binding.ivDestination)
            } else {
                binding.ivDestination.setImageResource(R.drawable.placeholder_destination)
            }

            binding.root.setOnClickListener { onClick(destination) }
            binding.ivFavorite.setOnClickListener {
                it.startAnimation(AnimationUtils.loadAnimation(it.context, R.anim.scale_heart))
                onFavoriteClick?.invoke(destination)
            }
            if (onMapClick != null) {
                binding.ivMap.visibility = View.VISIBLE
                binding.ivMap.setOnClickListener {
                    onMapClick.invoke(destination)
                }
            } else {
                binding.ivMap.visibility = View.GONE
                binding.ivMap.setOnClickListener(null)
            }
        }

    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemDestinationBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class DiffCallback : DiffUtil.ItemCallback<Destination>() {
        override fun areItemsTheSame(a: Destination, b: Destination): Boolean {
            return a.id == b.id
        }

        override fun areContentsTheSame(a: Destination, b: Destination): Boolean {
            return a == b
        }
    }
}

// ==================== LIST ADAPTER (Vertical small cards) ====================

class DestinationListAdapter(
    private val onClick: (Destination) -> Unit,
    private val onFavoriteClick: ((Destination) -> Unit)? = null
) : ListAdapter<Destination, DestinationListAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(private val binding: ItemDestinationSmallBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(destination: Destination) {
            binding.tvName.text = destination.name
            binding.tvLocation.text = "${destination.city}, ${destination.province}"
            binding.tvCategory.text = CategoryMapper.badgeLabel(destination.category)
            binding.ratingBar.rating = destination.rating
            binding.tvRating.text = String.format("%.1f", destination.rating)

            binding.ivFavorite.setImageResource(
                if (destination.isFavorite) R.drawable.ic_favorite_filled
                else R.drawable.ic_favorite_outline
            )

            if (destination.images.isNotEmpty()) {
                Glide.with(binding.root)
                    .load(resolveImageUrl(destination.images.first()))
                    .placeholder(R.drawable.placeholder_destination)
                    .centerCrop()
                    .into(binding.ivDestination)
            } else {
                binding.ivDestination.setImageResource(R.drawable.placeholder_destination)
            }

            binding.root.setOnClickListener { onClick(destination) }
            binding.ivFavorite.setOnClickListener {
                it.startAnimation(AnimationUtils.loadAnimation(it.context, R.anim.scale_heart))
                onFavoriteClick?.invoke(destination)
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemDestinationSmallBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class DiffCallback : DiffUtil.ItemCallback<Destination>() {
        override fun areItemsTheSame(a: Destination, b: Destination): Boolean {
            return a.id == b.id
        }

        override fun areContentsTheSame(a: Destination, b: Destination): Boolean {
            return a == b
        }
    }
}

// ==================== HELPERS ====================

private fun resolveImageUrl(url: String): String {
    return if (url.startsWith("http://") || url.startsWith("https://")) {
        url
    } else {
        BuildConfig.BASE_URL.replace("/api/", "") + url
    }
}

// Giữ lại 2 hàm này để không vỡ code nếu nơi khác còn gọi.
fun getCategoryEmoji(category: String?): String {
    return CategoryMapper.emojiLabel(category)
}

fun getCategoryLabel(category: String?): String {
    return CategoryMapper.badgeLabel(category)
}