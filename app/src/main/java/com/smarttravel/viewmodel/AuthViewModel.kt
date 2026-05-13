package com.smarttravel.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smarttravel.data.model.AuthResponse
import com.smarttravel.data.repository.AuthRepository
import com.smarttravel.utils.Resource
import kotlinx.coroutines.launch

class AuthViewModel(private val repository: AuthRepository) : ViewModel() {

    private val _loginResult = MutableLiveData<Resource<AuthResponse>>()
    val loginResult: LiveData<Resource<AuthResponse>> = _loginResult

    private val _registerResult = MutableLiveData<Resource<AuthResponse>>()
    val registerResult: LiveData<Resource<AuthResponse>> = _registerResult

    fun login(email: String, password: String) {
        if (!validateLoginInput(email, password)) return

        viewModelScope.launch {
            _loginResult.value = Resource.Loading
            _loginResult.value = repository.login(email.trim(), password)
        }
    }

    fun register(fullName: String, email: String, password: String, phone: String?) {
        if (!validateRegisterInput(fullName, email, password)) return

        viewModelScope.launch {
            _registerResult.value = Resource.Loading
            _registerResult.value = repository.register(fullName.trim(), email.trim(), password, phone?.trim())
        }
    }

    private fun validateLoginInput(email: String, password: String): Boolean {
        if (email.isBlank() || !android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            _loginResult.value = Resource.Error("Email không hợp lệ")
            return false
        }
        if (password.length < 6) {
            _loginResult.value = Resource.Error("Mật khẩu phải ít nhất 6 ký tự")
            return false
        }
        return true
    }

    private fun validateRegisterInput(fullName: String, email: String, password: String): Boolean {
        if (fullName.isBlank()) {
            _registerResult.value = Resource.Error("Vui lòng nhập họ tên")
            return false
        }
        if (email.isBlank() || !android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            _registerResult.value = Resource.Error("Email không hợp lệ")
            return false
        }
        if (password.length < 6) {
            _registerResult.value = Resource.Error("Mật khẩu phải ít nhất 6 ký tự")
            return false
        }
        return true
    }
}
