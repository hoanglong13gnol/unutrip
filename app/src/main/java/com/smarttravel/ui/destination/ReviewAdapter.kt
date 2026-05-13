package com.smarttravel.ui.destination

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.MediaStore
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.RatingBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.DialogFragment
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.smarttravel.BuildConfig
import com.smarttravel.R
import com.smarttravel.data.model.Review
import com.smarttravel.databinding.ItemReviewBinding
import com.smarttravel.databinding.ItemReviewImageBinding
import java.text.SimpleDateFormat
import java.util.*

// ==================== REVIEW ADAPTER ====================

class ReviewAdapter : ListAdapter<Review, ReviewAdapter.ViewHolder>(DiffCallback()) {

    inner class ViewHolder(private val binding: ItemReviewBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(review: Review) {
            binding.tvUserName.text = review.userName
            binding.ratingBar.rating = review.rating
            binding.tvComment.text = review.comment ?: ""

            // Format date
            try {
                val inputFmt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                val outputFmt = SimpleDateFormat("dd/MM/yyyy", Locale.getDefault())
                val date = inputFmt.parse(review.createdAt)
                binding.tvDate.text = date?.let { outputFmt.format(it) } ?: review.createdAt
            } catch (e: Exception) {
                binding.tvDate.text = review.createdAt.take(10)
            }

            // Avatar
            if (!review.userAvatar.isNullOrBlank()) {
                val avatarUrl = if (review.userAvatar.startsWith("http")) review.userAvatar 
                                else BuildConfig.BASE_URL.replace("/api/", "") + review.userAvatar
                Glide.with(binding.root)
                    .load(avatarUrl)
                    .placeholder(R.drawable.ic_default_avatar)
                    .circleCrop()
                    .into(binding.ivAvatar)
            } else {
                binding.ivAvatar.setImageResource(R.drawable.ic_default_avatar)
            }

            // Review Images
            if (!review.images.isNullOrEmpty()) {
                binding.rvReviewImages.visibility = View.VISIBLE
                val imageAdapter = ReviewImageAdapter(review.images)
                binding.rvReviewImages.adapter = imageAdapter
            } else {
                binding.rvReviewImages.visibility = View.GONE
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemReviewBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) = holder.bind(getItem(position))

    class DiffCallback : DiffUtil.ItemCallback<Review>() {
        override fun areItemsTheSame(a: Review, b: Review) = a.id == b.id
        override fun areContentsTheSame(a: Review, b: Review) = a == b
    }
}

// ==================== REVIEW IMAGE ADAPTER ====================

class ReviewImageAdapter(private val images: List<String>) : 
    RecyclerView.Adapter<ReviewImageAdapter.ViewHolder>() {

    inner class ViewHolder(val binding: ItemReviewImageBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemReviewImageBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val url = images[position]
        val fullUrl = if (url.startsWith("http")) url 
                      else BuildConfig.BASE_URL.replace("/api/", "") + url
        
        Glide.with(holder.binding.root)
            .load(fullUrl)
            .placeholder(R.drawable.placeholder_destination)
            .centerCrop()
            .into(holder.binding.ivReviewImage)
    }

    override fun getItemCount() = images.size
}

// ==================== REVIEW DIALOG ====================

class ReviewDialog(
    private val destinationId: Int,
    private val onSubmit: (Float, String, List<Uri>) -> Unit
) : DialogFragment() {

    private val selectedImages = mutableListOf<Uri>()
    private lateinit var layoutPreview: LinearLayout

    private val pickImagesLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val data = result.data
            if (data?.clipData != null) {
                val count = data.clipData!!.itemCount
                for (i in 0 until count) {
                    if (selectedImages.size < 3) {
                        selectedImages.add(data.clipData!!.getItemAt(i).uri)
                    }
                }
            } else if (data?.data != null) {
                if (selectedImages.size < 3) {
                    selectedImages.add(data.data!!)
                }
            }
            updateImagePreviews()
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return inflater.inflate(R.layout.dialog_review, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val ratingBar = view.findViewById<RatingBar>(R.id.ratingBarInput)
        val etComment = view.findViewById<EditText>(R.id.etComment)
        val btnSubmit = view.findViewById<Button>(R.id.btnSubmitReview)
        val btnCancel = view.findViewById<Button>(R.id.btnCancel)
        val btnPick = view.findViewById<Button>(R.id.btnPickImages)
        layoutPreview = view.findViewById(R.id.layoutImagePreview)

        btnPick.setOnClickListener {
            val intent = Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI)
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
            pickImagesLauncher.launch(intent)
        }

        btnSubmit.setOnClickListener {
            val rating = ratingBar.rating
            val comment = etComment.text.toString().trim()
            if (rating > 0) {
                onSubmit(rating, comment, selectedImages)
                dismiss()
            } else {
                Toast.makeText(context, "Vui lòng chọn số sao!", Toast.LENGTH_SHORT).show()
            }
        }

        btnCancel.setOnClickListener { dismiss() }
    }

    private fun updateImagePreviews() {
        // Keep the add button, remove others
        val addButton = layoutPreview.findViewById<View>(R.id.btnPickImages)
        layoutPreview.removeAllViews()
        layoutPreview.addView(addButton)

        selectedImages.forEach { uri ->
            val imageView = ImageView(context).apply {
                layoutParams = LinearLayout.LayoutParams(dpToPx(72), dpToPx(72)).apply {
                    setMargins(0, 0, dpToPx(8), 0)
                }
                scaleType = ImageView.ScaleType.CENTER_CROP
                Glide.with(this).load(uri).into(this)
                
                setOnClickListener {
                    selectedImages.remove(uri)
                    updateImagePreviews()
                }
            }
            // Add before the button
            layoutPreview.addView(imageView, layoutPreview.childCount - 1)
        }
        
        addButton.visibility = if (selectedImages.size >= 3) View.GONE else View.VISIBLE
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }

    override fun onStart() {
        super.onStart()
        dialog?.window?.setLayout(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
    }
}
