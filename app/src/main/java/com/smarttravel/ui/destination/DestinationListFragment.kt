package com.smarttravel.ui.destination

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.fragment.findNavController
import com.smarttravel.R
import com.smarttravel.data.api.RetrofitClient
import com.smarttravel.data.repository.DestinationRepository
import com.smarttravel.databinding.FragmentDestinationListBinding
import com.smarttravel.utils.Resource
import com.smarttravel.utils.SessionManager
import com.smarttravel.viewmodel.DestinationViewModel
import com.smarttravel.viewmodel.DestinationViewModelFactory

class DestinationListFragment : Fragment() {

    private var _binding: FragmentDestinationListBinding? = null
    private val binding get() = _binding!!
    private lateinit var viewModel: DestinationViewModel
    private lateinit var sessionManager: SessionManager
    private lateinit var adapter: DestinationListAdapter

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentDestinationListBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        sessionManager = SessionManager.getInstance(requireContext())

        val repo = DestinationRepository(RetrofitClient.apiService)
        viewModel = ViewModelProvider(this, DestinationViewModelFactory(repo))[DestinationViewModel::class.java]
        viewModel.init(sessionManager.getBearerToken())

        setupAdapter()
        setupSearch()
        setupFilters()
        observeViewModel()

        // Check if navigated with a category argument or favorites mode
        val category = arguments?.getString("category")
        val isFavoriteOnly = arguments?.getBoolean("isFavoriteOnly") ?: false
        val currentDestId = findNavController().currentDestination?.id

        if (isFavoriteOnly) {
            binding.tvTitle.text = "Yêu thích"
            binding.layoutSearch.visibility = View.GONE
            binding.scrollFilters.visibility = View.GONE
            binding.btnBack.visibility = View.VISIBLE
            viewModel.loadFavorites()
        } else if (currentDestId == R.id.homeDestinationListFragment) {
            binding.btnBack.visibility = View.VISIBLE
            if (!category.isNullOrBlank()) {
                viewModel.loadDestinations(category = category)
            } else {
                viewModel.loadDestinations()
            }
        } else if (!category.isNullOrBlank()) {
            viewModel.loadDestinations(category = category)
        } else {
            viewModel.loadDestinations()
        }

        binding.btnBack.setOnClickListener {
            findNavController().popBackStack()
        }
    }

    private fun setupAdapter() {
        adapter = DestinationListAdapter(
            onClick = { destination ->
                val bundle = Bundle().apply { putInt("destinationId", destination.id) }
                val currentDest = findNavController().currentDestination?.id
                val actionId = when (currentDest) {
                    R.id.profileFavoriteListFragment -> R.id.action_profileFavoriteListFragment_to_destinationDetailFragment
                    R.id.homeDestinationListFragment -> R.id.action_homeDestinationListFragment_to_destinationDetailFragment
                    else -> R.id.action_destinationListFragment_to_destinationDetailFragment
                }
                findNavController().navigate(actionId, bundle)
            },
            onFavoriteClick = { destination ->
                viewModel.toggleFavorite(destination.id, destination.isFavorite)
                destination.isFavorite = !destination.isFavorite
                adapter.notifyDataSetChanged()
            }
        )
        binding.rvDestinations.adapter = adapter
        
        // Pagination Scroll Listener
        binding.rvDestinations.addOnScrollListener(object : androidx.recyclerview.widget.RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: androidx.recyclerview.widget.RecyclerView, dx: Int, dy: Int) {
                super.onScrolled(recyclerView, dx, dy)
                val layoutManager = recyclerView.layoutManager as androidx.recyclerview.widget.LinearLayoutManager
                val visibleItemCount = layoutManager.childCount
                val totalItemCount = layoutManager.itemCount
                val firstVisibleItemPosition = layoutManager.findFirstVisibleItemPosition()

                if ((visibleItemCount + firstVisibleItemPosition) >= totalItemCount && firstVisibleItemPosition >= 0) {
                    viewModel.loadMoreDestinations()
                }
            }
        })
    }

    private fun setupSearch() {
        binding.etSearch.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) {
                val query = s.toString().trim()
                binding.btnClearSearch.visibility = if (query.isNotEmpty()) View.VISIBLE else View.GONE
                viewModel.search(query)
            }
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        binding.btnClearSearch.setOnClickListener {
            binding.etSearch.text?.clear()
        }
    }

    private fun setupFilters() {
        binding.chipFilterAll.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations()
        }
        binding.chipFilterBeach.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "beach")
        }
        binding.chipFilterMountain.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "mountain")
        }
        binding.chipFilterCity.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "city")
        }
        binding.chipFilterHeritage.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "heritage")
        }
        binding.chipFilterNature.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "nature")
        }
        binding.chipFilterCheckin.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "checkin")
        }
        binding.chipFilterHistorical.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "historical")
        }
        binding.chipFilterFood.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "food")
        }
        binding.chipFilterCulture.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "culture")
        }
        binding.chipFilterReligious.setOnCheckedChangeListener { _, checked ->
            if (checked) viewModel.loadDestinations(category = "religious")
        }
    }

    private fun observeViewModel() {
        viewModel.destinations.observe(viewLifecycleOwner) { result ->
            if (arguments?.getBoolean("isFavoriteOnly") == true) return@observe
            when (result) {
                is Resource.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                }
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    // Create a new list to ensure DiffUtil updates correctly
                    adapter.submitList(result.data.data.toList())
                    binding.tvResultCount.text = "${result.data.total} địa điểm"
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    android.util.Log.e("DestinationList", "Error loading destinations: ${result.message}")
                    android.widget.Toast.makeText(context, "Lỗi: ${result.message}", android.widget.Toast.LENGTH_LONG).show()
                }
            }
        }

        viewModel.favorites.observe(viewLifecycleOwner) { result ->
            if (arguments?.getBoolean("isFavoriteOnly") != true) return@observe
            when (result) {
                is Resource.Loading -> binding.progressBar.visibility = View.VISIBLE
                is Resource.Success -> {
                    binding.progressBar.visibility = View.GONE
                    adapter.submitList(result.data.toList())
                    binding.tvResultCount.text = "${result.data.size} địa điểm"
                }
                is Resource.Error -> {
                    binding.progressBar.visibility = View.GONE
                    android.widget.Toast.makeText(context, "Lỗi: ${result.message}", android.widget.Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
