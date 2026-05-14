package com.smarttravel.ui.itinerary

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.smarttravel.R
import com.smarttravel.data.model.Itinerary

class EditItineraryDialog(
    private val initial: Itinerary,
    private val onSubmit: (String, String?, String, String, Double?) -> Unit
) : BottomSheetDialogFragment() {

    override fun getTheme(): Int = R.style.BottomSheetSmartTravel

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return inflater.inflate(R.layout.dialog_edit_itinerary, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val etTitle = view.findViewById<TextInputEditText>(R.id.etTitle)
        val etDesc = view.findViewById<TextInputEditText>(R.id.etDescription)
        val etStartDate = view.findViewById<TextInputEditText>(R.id.etStartDate)
        val etEndDate = view.findViewById<TextInputEditText>(R.id.etEndDate)
        val etBudget = view.findViewById<TextInputEditText>(R.id.etBudget)
        val btnSave = view.findViewById<MaterialButton>(R.id.btnSave)
        val btnCancel = view.findViewById<MaterialButton>(R.id.btnCancel)

        etTitle.setText(initial.title)
        etDesc.setText(initial.description ?: "")
        etStartDate.setText(initial.startDate)
        etEndDate.setText(initial.endDate)
        initial.estimatedBudget?.let { etBudget.setText(it.toString()) }

        etStartDate.setOnClickListener { showDatePicker(etStartDate, "Ngày đi") }
        etEndDate.setOnClickListener { showDatePicker(etEndDate, "Ngày về") }

        btnSave.setOnClickListener {
            val title = etTitle.text.toString().trim()
            val desc = etDesc.text.toString().trim().takeIf { it.isNotBlank() }
            val start = etStartDate.text.toString().trim()
            val end = etEndDate.text.toString().trim()
            val budget = etBudget.text.toString().trim().toDoubleOrNull()

            if (title.isBlank() || start.isBlank() || end.isBlank()) {
                etTitle.error = if (title.isBlank()) "Nhập tên lịch trình" else null
                return@setOnClickListener
            }
            onSubmit(title, desc, start, end, budget)
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
        picker.show(parentFragmentManager, "edit_date_$title")
    }

    override fun onStart() {
        super.onStart()
        val dlg = dialog as? BottomSheetDialog ?: return
        val bottomSheet = dlg.findViewById<View>(com.google.android.material.R.id.design_bottom_sheet) ?: return
        bottomSheet.layoutParams.height = ViewGroup.LayoutParams.MATCH_PARENT
        val behavior = BottomSheetBehavior.from(bottomSheet)
        behavior.state = BottomSheetBehavior.STATE_EXPANDED
        behavior.skipCollapsed = true
    }
}
