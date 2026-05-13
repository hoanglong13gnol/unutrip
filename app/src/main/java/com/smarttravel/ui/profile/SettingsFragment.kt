package com.smarttravel.ui.profile

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.smarttravel.R
import com.smarttravel.databinding.FragmentSettingsBinding

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnBack.setOnClickListener {
            findNavController().navigateUp()
        }

        setupMenu()
    }

    private fun setupMenu() {
        // Language
        binding.settingLanguage.ivIcon.setImageResource(R.drawable.ic_map)
        binding.settingLanguage.tvLabel.text = "Ngôn ngữ"
        binding.settingLanguage.root.setOnClickListener {
            Toast.makeText(context, "Tính năng đang phát triển", Toast.LENGTH_SHORT).show()
        }

        // Notification
        binding.settingNotification.ivIcon.setImageResource(R.drawable.ic_nav_chat)
        binding.settingNotification.tvLabel.text = "Thông báo"
        binding.settingNotification.root.setOnClickListener {
            Toast.makeText(context, "Tính năng đang phát triển", Toast.LENGTH_SHORT).show()
        }

        // Theme
        binding.settingTheme.ivIcon.setImageResource(R.drawable.ic_nav_home)
        binding.settingTheme.tvLabel.text = "Giao diện"
        binding.settingTheme.root.setOnClickListener {
            Toast.makeText(context, "Tính năng đang phát triển", Toast.LENGTH_SHORT).show()
        }

        // Help
        binding.settingHelp.ivIcon.setImageResource(R.drawable.ic_nav_chat)
        binding.settingHelp.tvLabel.text = "Trợ giúp & Hỗ trợ"
        binding.settingHelp.root.setOnClickListener {
            Toast.makeText(context, "Tính năng đang phát triển", Toast.LENGTH_SHORT).show()
        }

        // About
        binding.settingAbout.ivIcon.setImageResource(R.drawable.ic_more_vertical)
        binding.settingAbout.tvLabel.text = "Về SmartTravel"
        binding.settingAbout.root.setOnClickListener {
            Toast.makeText(context, "SmartTravel v1.0.0", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
