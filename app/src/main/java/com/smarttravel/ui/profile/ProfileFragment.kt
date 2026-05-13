package com.smarttravel.ui.profile

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.smarttravel.R
import com.smarttravel.databinding.FragmentProfileBinding
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.ui.auth.AuthActivity
import com.smarttravel.utils.SessionManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream

class ProfileFragment : Fragment() {

    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!
    private lateinit var sessionManager: SessionManager

    private val imagePicker = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { uploadAvatar(it) }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentProfileBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())
        val user = sessionManager.getUser()

        // Bind user info
        user?.let {
            binding.tvName.text = it.fullName
            binding.tvEmail.text = it.email

            if (!it.avatar.isNullOrBlank()) {
                Glide.with(this)
                    .load(it.avatar)
                    .placeholder(R.drawable.ic_default_avatar)
                    .circleCrop()
                    .into(binding.ivAvatar)
            }
        }

        setupMenuItems()
        setupLogout()
        loadStats()
        
        binding.btnEditAvatar.setOnClickListener {
            imagePicker.launch("image/*")
        }
    }

    private fun loadStats() {
        val token = sessionManager.getBearerToken()
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.apiService.getUserStats(token)
                if (response.isSuccessful && response.body()?.data != null) {
                    val stats = response.body()!!.data!!
                    binding.tvItineraryCount.text = stats.itineraryCount.toString()
                    binding.tvFavoriteCount.text = stats.favoriteCount.toString()
                    binding.tvReviewCount.text = stats.reviewCount.toString()
                }
            } catch (e: Exception) {
                // Silently fail or log
            }
        }
    }

    private fun setupMenuItems() {

        // Edit profile
        binding.menuEditProfile.ivIcon.setImageResource(R.drawable.ic_edit)
        binding.menuEditProfile.tvLabel.text = "Chỉnh sửa hồ sơ"
        binding.menuEditProfile.root.setOnClickListener {
            showEditProfileDialog()
        }

        // Favorites
        binding.menuFavorites.ivIcon.setImageResource(R.drawable.ic_favorite_filled)
        binding.menuFavorites.tvLabel.text = "Danh sách yêu thích"
        binding.menuFavorites.root.setOnClickListener {
            val bundle = Bundle().apply { putBoolean("isFavoriteOnly", true) }
            findNavController().navigate(R.id.profileFavoriteListFragment, bundle)
        }

        // Itineraries
        binding.menuItineraries.ivIcon.setImageResource(R.drawable.ic_nav_itinerary)
        binding.menuItineraries.tvLabel.text = "Lịch trình của tôi"
        binding.menuItineraries.root.setOnClickListener {
            findNavController().navigate(R.id.profileItineraryListFragment)
        }

        // Settings
        binding.menuSettings.ivIcon.setImageResource(R.drawable.ic_more_vertical)
        binding.menuSettings.tvLabel.text = "Cài đặt"
        binding.menuSettings.root.setOnClickListener {
            findNavController().navigate(R.id.action_profileFragment_to_settingsFragment)
        }
    }
    
    private fun showEditProfileDialog() {
        val user = sessionManager.getUser() ?: return
        
        val dialogView = layoutInflater.inflate(R.layout.dialog_edit_profile, null)
        val etFullName = dialogView.findViewById<TextInputEditText>(R.id.etFullName)
        val etPhone = dialogView.findViewById<TextInputEditText>(R.id.etPhone)
        val btnCancel = dialogView.findViewById<MaterialButton>(R.id.btnCancel)
        val btnSave = dialogView.findViewById<MaterialButton>(R.id.btnSave)
        
        etFullName.setText(user.fullName)
        etPhone.setText(user.phone ?: "")
        
        val dialog = AlertDialog.Builder(requireContext())
            .setView(dialogView)
            .create()
            
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
            
        btnCancel.setOnClickListener {
            dialog.dismiss()
        }
        
        btnSave.setOnClickListener {
            val newName = etFullName.text.toString().trim()
            val newPhone = etPhone.text.toString().trim()
            
            if (newName.isEmpty()) {
                etFullName.error = "Vui lòng nhập họ tên"
                return@setOnClickListener
            }
            
            updateProfile(newName, newPhone)
            dialog.dismiss()
        }
        
        dialog.show()
    }
    
    private fun uploadAvatar(uri: android.net.Uri) {
        val token = sessionManager.getBearerToken()
        
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // Show loading placeholder
                withContext(Dispatchers.Main) {
                    binding.ivAvatar.alpha = 0.5f
                    Toast.makeText(requireContext(), "Đang tải ảnh lên...", Toast.LENGTH_SHORT).show()
                }

                val file = getFileFromUri(uri)
                val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                val body = MultipartBody.Part.createFormData("avatar", file.name, requestFile)

                val response = RetrofitClient.apiService.uploadAvatar(token, body)
                
                withContext(Dispatchers.Main) {
                    binding.ivAvatar.alpha = 1.0f
                    if (response.isSuccessful && response.body()?.data != null) {
                        val updatedUser = response.body()!!.data!!
                        sessionManager.updateUser(updatedUser)
                        
                        Glide.with(this@ProfileFragment)
                            .load(updatedUser.avatar)
                            .placeholder(R.drawable.ic_default_avatar)
                            .circleCrop()
                            .into(binding.ivAvatar)
                            
                        Toast.makeText(requireContext(), "Đã cập nhật ảnh đại diện", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(requireContext(), "Lỗi tải ảnh: ${response.message()}", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.ivAvatar.alpha = 1.0f
                    Toast.makeText(requireContext(), "Lỗi mạng: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun getFileFromUri(uri: android.net.Uri): File {
        val inputStream = requireContext().contentResolver.openInputStream(uri)
        val file = File(requireContext().cacheDir, "temp_avatar_${System.currentTimeMillis()}.jpg")
        val outputStream = FileOutputStream(file)
        inputStream?.use { input ->
            outputStream.use { output ->
                input.copyTo(output)
            }
        }
        return file
    }

    private fun updateProfile(newName: String, newPhone: String) {
        val user = sessionManager.getUser() ?: return
        val token = "Bearer ${sessionManager.getToken()}"
        
        lifecycleScope.launch {
            try {
                // Update local session immediately for responsiveness
                val updatedUser = user.copy(fullName = newName, phone = newPhone)
                sessionManager.updateUser(updatedUser)
                binding.tvName.text = newName
                
                Toast.makeText(requireContext(), "Đã cập nhật thông tin", Toast.LENGTH_SHORT).show()
                
                // Call API in background
                val response = RetrofitClient.apiService.updateProfile(token, updatedUser)
                if (!response.isSuccessful) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(requireContext(), "Lỗi đồng bộ lên server", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(requireContext(), "Lỗi mạng: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun setupLogout() {
        binding.btnLogout.setOnClickListener {
            android.app.AlertDialog.Builder(requireContext())
                .setTitle("Đăng xuất")
                .setMessage("Bạn có chắc muốn đăng xuất không?")
                .setPositiveButton("Đăng xuất") { _, _ ->
                    sessionManager.clearSession()
                    startActivity(Intent(requireContext(), AuthActivity::class.java).apply {
                        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    })
                }
                .setNegativeButton("Hủy", null)
                .show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
