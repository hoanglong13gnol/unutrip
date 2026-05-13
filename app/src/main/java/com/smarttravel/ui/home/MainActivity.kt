package com.smarttravel.ui.home

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.smarttravel.R
import com.smarttravel.databinding.ActivityMainBinding
import android.view.View
import android.content.Context
import android.content.res.Configuration

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
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
        val fullScreenDestinations = setOf(
            R.id.aiItineraryRequestFragment,
            R.id.aiItineraryOptionsFragment,
            R.id.aiItineraryEditorFragment
        )
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController
        navController.addOnDestinationChangedListener { _, destination, _ ->
            binding.bottomNavigation.visibility =
                if (destination.id in fullScreenDestinations) {
                    View.GONE
                } else {
                    View.VISIBLE
                }
        }


        // Setup bottom navigation với NavController
        binding.bottomNavigation.setupWithNavController(navController)

        // Ẩn bottom nav khi ở các màn detail
        navController.addOnDestinationChangedListener { _, destination, _ ->
            when (destination.id) {
                R.id.destinationDetailFragment,
                R.id.mapFragment,
                R.id.itineraryDetailFragment,
                R.id.aiSuggestFragment,
                R.id.settingsFragment -> {
                    binding.bottomNavigation.visibility = android.view.View.GONE
                }
                else -> {
                    binding.bottomNavigation.visibility = android.view.View.VISIBLE
                }
            }
        }

        // Handle re-selection of tabs to return to root
        binding.bottomNavigation.setOnItemReselectedListener { item ->
            val navController = (supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment).navController
            val currentDest = navController.currentDestination?.id
            
            when (item.itemId) {
                R.id.homeFragment -> {
                    if (currentDest == R.id.homeDestinationListFragment) {
                        navController.popBackStack(R.id.homeFragment, false)
                    }
                }
                R.id.profileFragment -> {
                    if (currentDest == R.id.profileFavoriteListFragment || currentDest == R.id.profileItineraryListFragment) {
                        navController.popBackStack(R.id.profileFragment, false)
                    }
                }
            }
        }
    }
}
