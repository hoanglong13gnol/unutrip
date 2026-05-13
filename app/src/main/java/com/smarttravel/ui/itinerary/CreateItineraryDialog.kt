package com.smarttravel.ui.itinerary

import android.os.Bundle
import android.view.*
import android.widget.Button
import android.widget.EditText
import androidx.fragment.app.DialogFragment
import com.smarttravel.R

class CreateItineraryDialog(
    private val onSubmit: (String, String?, String, String) -> Unit
) : DialogFragment() {

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return inflater.inflate(R.layout.dialog_create_itinerary, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val etTitle = view.findViewById<EditText>(R.id.etTitle)
        val etDesc = view.findViewById<EditText>(R.id.etDescription)
        val etStartDate = view.findViewById<EditText>(R.id.etStartDate)
        val etEndDate = view.findViewById<EditText>(R.id.etEndDate)
        val btnCreate = view.findViewById<Button>(R.id.btnCreate)
        val btnCancel = view.findViewById<Button>(R.id.btnCancel)

        // Date pickers
        etStartDate.setOnClickListener { showDatePicker(etStartDate, "Ngày đi") }
        etEndDate.setOnClickListener { showDatePicker(etEndDate, "Ngày về") }

        btnCreate.setOnClickListener {
            val title = etTitle.text.toString().trim()
            val desc = etDesc.text.toString().trim().takeIf { it.isNotBlank() }
            val start = etStartDate.text.toString().trim()
            val end = etEndDate.text.toString().trim()

            if (title.isBlank() || start.isBlank() || end.isBlank()) {
                etTitle.error = if (title.isBlank()) "Nhập tên lịch trình" else null
                return@setOnClickListener
            }
            onSubmit(title, desc, start, end)
            dismiss()
        }

        btnCancel.setOnClickListener { dismiss() }
    }

    private fun showDatePicker(target: EditText, title: String) {
        val picker = com.google.android.material.datepicker.MaterialDatePicker.Builder.datePicker()
            .setTitleText(title)
            .build()
        picker.addOnPositiveButtonClickListener { selection ->
            val sdf = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault())
            target.setText(sdf.format(java.util.Date(selection)))
        }
        picker.show(parentFragmentManager, "date_$title")
    }

    override fun onStart() {
        super.onStart()
        dialog?.window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    }
}
