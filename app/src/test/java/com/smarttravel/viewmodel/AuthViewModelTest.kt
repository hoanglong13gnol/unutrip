package com.smarttravel.viewmodel

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import com.smarttravel.data.model.AuthResponse
import com.smarttravel.data.repository.AuthRepository
import com.smarttravel.utils.Resource
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class AuthViewModelTest {

    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun login_invalidEmail_doesNotCallRepository() = runTest(dispatcher) {
        val repo = mockk<AuthRepository>(relaxed = true)
        val vm = AuthViewModel(repo)
        vm.login("not-an-email", "secret12")
        advanceUntilIdle()
        coVerify(exactly = 0) { repo.login(any(), any()) }
        val res = vm.loginResult.value
        assertTrue(res is Resource.Error)
        assertEquals("Email không hợp lệ", (res as Resource.Error).message)
    }

    @Test
    fun login_shortPassword_doesNotCallRepository() = runTest(dispatcher) {
        val repo = mockk<AuthRepository>(relaxed = true)
        val vm = AuthViewModel(repo)
        vm.login("user@test.com", "short")
        advanceUntilIdle()
        coVerify(exactly = 0) { repo.login(any(), any()) }
        assertEquals("Mật khẩu phải ít nhất 6 ký tự", (vm.loginResult.value as Resource.Error).message)
    }

    @Test
    fun login_validInput_callsRepositoryAndEmitsSuccess() = runTest(dispatcher) {
        val repo = mockk<AuthRepository>()
        val body = AuthResponse(success = true, message = "ok", token = "t", user = null)
        coEvery { repo.login("user@test.com", "secret12") } returns Resource.Success(body)
        val vm = AuthViewModel(repo)
        vm.login("user@test.com", "secret12")
        advanceUntilIdle()
        coVerify(exactly = 1) { repo.login("user@test.com", "secret12") }
        assertTrue(vm.loginResult.value is Resource.Success)
        assertEquals(body, (vm.loginResult.value as Resource.Success).data)
    }

    @Test
    fun register_blankFullName_doesNotCallRepository() = runTest(dispatcher) {
        val repo = mockk<AuthRepository>(relaxed = true)
        val vm = AuthViewModel(repo)
        vm.register("   ", "user@test.com", "secret12", null)
        advanceUntilIdle()
        coVerify(exactly = 0) { repo.register(any(), any(), any(), any()) }
        assertEquals("Vui lòng nhập họ tên", (vm.registerResult.value as Resource.Error).message)
    }

    @Test
    fun register_validInput_callsRepository() = runTest(dispatcher) {
        val repo = mockk<AuthRepository>()
        val body = AuthResponse(success = true, message = "created", token = null, user = null)
        coEvery {
            repo.register("Nguyen Van A", "user@test.com", "secret12", "090")
        } returns Resource.Success(body)
        val vm = AuthViewModel(repo)
        vm.register("Nguyen Van A", "user@test.com", "secret12", "090")
        advanceUntilIdle()
        coVerify(exactly = 1) {
            repo.register("Nguyen Van A", "user@test.com", "secret12", "090")
        }
        assertTrue(vm.registerResult.value is Resource.Success)
    }
}
