package com.smarttravel.ui.destination

import android.os.Bundle
import android.view.*
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.smarttravel.R
import com.smarttravel.data.model.Itinerary
import com.smarttravel.ui.itinerary.ItineraryAdapter

class SelectItineraryDialog(
    private val itineraries: List<Itinerary>,
    private val onSelect: (Itinerary) -> Unit
) : BottomSheetDialogFragment() {

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return inflater.inflate(R.layout.dialog_select_itinerary, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val rvItineraries = view.findViewById<RecyclerView>(R.id.rvItineraries)
        val tvEmpty = view.findViewById<TextView>(R.id.tvEmpty)
        val btnCancel = view.findViewById<Button>(R.id.btnCancel)

        if (itineraries.isEmpty()) {
            tvEmpty.visibility = View.VISIBLE
            rvItineraries.visibility = View.GONE
        } else {
            tvEmpty.visibility = View.GONE
            rvItineraries.visibility = View.VISIBLE

            val adapter = ItineraryAdapter(
                onClick = {
                    onSelect(it)
                    dismiss()
                },
                onDelete = {}
            )
            rvItineraries.layoutManager = LinearLayoutManager(context)
            rvItineraries.adapter = adapter
            adapter.submitList(itineraries)
        }

        btnCancel.setOnClickListener { dismiss() }
    }
}
