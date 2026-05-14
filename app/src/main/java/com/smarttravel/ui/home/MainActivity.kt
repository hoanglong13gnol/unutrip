package com.smarttravel.ui.home

import android.content.Context
import android.content.res.Configuration
import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.interpolator.view.animation.FastOutSlowInInterpolator
import androidx.navigation.NavDestination
import androidx.navigation.NavOptions
import androidx.annotation.IdRes
import androidx.navigation.fragment.NavHostFragment
import com.smarttravel.R
import com.smarttravel.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    /** True while updating bottom-nav `selectedItemId` from NavController — avoids re-entering the item listener (infinite loop). */
    private var syncingBottomNavSelection = false

    override fun attachBaseContext(newBase: Context) {
        val config = Configuration(newBase.resources.configuration)
        config.fontScale = 1.0f
        val context = newBase.createConfigurationContext(config)
        super.attachBaseContext(context)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController

        val fullScreenDestinations = setOf(
            R.id.aiItineraryRequestFragment,
            R.id.aiItineraryOptionsFragment,
            R.id.aiItineraryEditorFragment,
        )

        val hideBottomNavDestinations = fullScreenDestinations + setOf(
            R.id.destinationDetailFragment,
            R.id.mapFragment,
            R.id.itineraryDetailFragment,
            R.id.aiSuggestFragment,
            R.id.settingsFragment,
        )

        navController.addOnDestinationChangedListener { _, destination, _ ->
            val showBottomNav = destination.id !in hideBottomNavDestinations
            animateBottomNavVisibility(showBottomNav)
            syncBottomNavSelection(destination)
        }

        binding.bottomNavigation.setOnItemSelectedListener { item ->
            if (syncingBottomNavSelection) {
                return@setOnItemSelectedListener true
            }
            val opts = NavOptions.Builder()
                .setLaunchSingleTop(true)
                .setRestoreState(true)
                .setPopUpTo(navController.graph.startDestinationId, false, true)
                .setEnterAnim(R.anim.nav_tab_enter)
                .setExitAnim(R.anim.nav_tab_exit)
                .setPopEnterAnim(R.anim.nav_tab_pop_enter)
                .setPopExitAnim(R.anim.nav_tab_pop_exit)
                .build()
            try {
                navController.navigate(item.itemId, null, opts)
                true
            } catch (_: IllegalArgumentException) {
                false
            }
        }

        binding.bottomNavigation.setOnItemReselectedListener { item ->
            val currentDest = navController.currentDestination?.id

            when (item.itemId) {
                R.id.homeFragment -> {
                    if (currentDest == R.id.homeDestinationListFragment) {
                        navController.popBackStack(R.id.homeFragment, false)
                    }
                }
                R.id.profileFragment -> {
                    if (currentDest == R.id.profileFavoriteListFragment ||
                        currentDest == R.id.profileItineraryListFragment
                    ) {
                        navController.popBackStack(R.id.profileFragment, false)
                    }
                }
            }
        }
    }

    private fun syncBottomNavSelection(destination: NavDestination) {
        val menu = binding.bottomNavigation.menu
        for (i in 0 until menu.size()) {
            val item = menu.getItem(i)
            if (destinationMatchesMenuItem(destination, item.itemId)) {
                applyBottomNavSelectedItemId(item.itemId)
                return
            }
        }
        val fallbackTab = when (destination.id) {
            R.id.homeDestinationListFragment -> R.id.homeFragment
            R.id.profileFavoriteListFragment, R.id.profileItineraryListFragment -> R.id.profileFragment
            else -> null
        }
        if (fallbackTab != null) {
            applyBottomNavSelectedItemId(fallbackTab)
        }
    }

    private fun applyBottomNavSelectedItemId(@IdRes itemId: Int) {
        if (binding.bottomNavigation.selectedItemId == itemId) return
        syncingBottomNavSelection = true
        try {
            binding.bottomNavigation.selectedItemId = itemId
        } finally {
            syncingBottomNavSelection = false
        }
    }

    /** Mirrors androidx.navigation.ui.NavigationUI.matchDestination for bottom-nav highlighting. */
    private fun destinationMatchesMenuItem(destination: NavDestination, @IdRes menuItemId: Int): Boolean {
        var current: NavDestination? = destination
        while (current != null) {
            if (current.id == menuItemId) return true
            current = current.parent
        }
        return false
    }

    private fun animateBottomNavVisibility(visible: Boolean) {
        val nav = binding.bottomNavigation
        val slidePx = 28f * resources.displayMetrics.density

        nav.animate().cancel()

        if (visible) {
            if (nav.visibility == View.VISIBLE && nav.alpha >= 0.99f && nav.translationY == 0f) {
                return
            }
            nav.visibility = View.VISIBLE
            nav.alpha = 0f
            nav.translationY = slidePx
            nav.animate()
                .alpha(1f)
                .translationY(0f)
                .setDuration(240)
                .setInterpolator(FastOutSlowInInterpolator())
                .withEndAction {
                    nav.translationY = 0f
                    nav.alpha = 1f
                }
                .start()
        } else {
            if (nav.visibility == View.GONE) return
            nav.animate()
                .alpha(0f)
                .translationY(slidePx)
                .setDuration(200)
                .setInterpolator(FastOutSlowInInterpolator())
                .withEndAction {
                    nav.visibility = View.GONE
                }
                .start()
        }
    }
}
