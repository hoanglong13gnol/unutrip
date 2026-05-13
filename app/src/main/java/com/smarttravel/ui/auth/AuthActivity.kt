package com.smarttravel.ui.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModelProvider
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.repository.AuthRepository
import com.smarttravel.databinding.ActivityAuthBinding
import com.smarttravel.ui.home.MainActivity
import com.smarttravel.R
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.AuthViewModel

class AuthActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAuthBinding
    private lateinit var viewModel: AuthViewModel
    private lateinit var sessionManager: SessionManager
    private var isLoginMode = true

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sessionManager = SessionManager.getInstance(this)

        // Nếu đã đăng nhập, chuyển thẳng vào app
        if (sessionManager.isLoggedIn()) {
            goToMain()
            return
        }

        binding = ActivityAuthBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val repo = AuthRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, AuthViewModelFactory(repo))[AuthViewModel::class.java]

        setupUI()
        observeViewModel()
    }

    private fun setupUI() {
        // Toggle login/register
        binding.tvSwitchMode.setOnClickListener {
            isLoginMode = !isLoginMode
            updateUIMode()
        }

        binding.btnSubmit.setOnClickListener {
            if (isLoginMode) {
                viewModel.login(
                    binding.etEmail.text.toString(),
                    binding.etPassword.text.toString()
                )
            } else {
                viewModel.register(
                    binding.etFullName.text.toString(),
                    binding.etEmail.text.toString(),
                    binding.etPassword.text.toString(),
                    binding.etPhone.text.toString().takeIf { it.isNotBlank() }
                )
            }
        }
    }

    private fun updateUIMode() {
        if (isLoginMode) {
            binding.tvTitle.text = getString(R.string.login)
            binding.layoutFullName.visibility = View.GONE
            binding.layoutPhone.visibility = View.GONE
            binding.btnSubmit.text = getString(R.string.login)
            binding.tvSwitchMode.text = android.text.Html.fromHtml(getString(R.string.no_account), android.text.Html.FROM_HTML_MODE_COMPACT)
        } else {
            binding.tvTitle.text = getString(R.string.register)
            binding.layoutFullName.visibility = View.VISIBLE
            binding.layoutPhone.visibility = View.VISIBLE
            binding.btnSubmit.text = getString(R.string.register)
            binding.tvSwitchMode.text = android.text.Html.fromHtml(getString(R.string.has_account), android.text.Html.FROM_HTML_MODE_COMPACT)
        }
    }

    private fun observeViewModel() {
        viewModel.loginResult.observe(this) { result ->
            when (result) {
                is Resource.Loading -> showLoading(true)
                is Resource.Success -> {
                    showLoading(false)
                    if (result.data.success && result.data.token != null && result.data.user != null) {
                        sessionManager.saveSession(result.data.token, result.data.user)
                        goToMain()
                    } else {
                        showError(result.data.message)
                    }
                }
                is Resource.Error -> {
                    showLoading(false)
                    showError(result.message)
                }
            }
        }

        viewModel.registerResult.observe(this) { result ->
            when (result) {
                is Resource.Loading -> showLoading(true)
                is Resource.Success -> {
                    showLoading(false)
                    if (result.data.success && result.data.token != null && result.data.user != null) {
                        sessionManager.saveSession(result.data.token, result.data.user)
                        goToMain()
                    } else {
                        showError(result.data.message)
                    }
                }
                is Resource.Error -> {
                    showLoading(false)
                    showError(result.message)
                }
            }
        }
    }

    private fun showLoading(show: Boolean) {
        binding.progressBar.visibility = if (show) View.VISIBLE else View.GONE
        binding.btnSubmit.isEnabled = !show
    }

    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
    }

    private fun goToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}

class AuthViewModelFactory(private val repo: AuthRepository) :
    androidx.lifecycle.ViewModelProvider.Factory {
    override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
        @Suppress("UNCHECKED_CAST")
        return AuthViewModel(repo) as T
    }
}
