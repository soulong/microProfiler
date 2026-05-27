"""Convert step panel — vendor format to unified naming."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
)

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


class ConvertStepPanel(BaseStepPanel):
    step_name = "convert"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Convert")
        self._build_controls()
        self.setChecked(True)

    def _build_controls(self):
        form = QFormLayout()
        self._output_name = QLineEdit("image")
        self._resize_factor = QDoubleSpinBox()
        self._resize_factor.setRange(0.1, 4.0)
        self._resize_factor.setValue(1.0)
        self._resize_factor.setSingleStep(0.1)
        self._delete_orig = QCheckBox("Delete original vendor files")
        form.addRow("Output name:", self._output_name)
        form.addRow("Resize factor:", self._resize_factor)
        form.addRow("", self._delete_orig)
        self._controls_layout.addLayout(form)

        self._apply_btn = QPushButton("▶ Apply")
        self._apply_btn.setProperty("class", "primary")
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._apply_btn)
        self._controls_layout.addLayout(btn_row)

        for w in (self._output_name, self._resize_factor, self._delete_orig):
            self._wire_param_signal(w)

    def save_to_settings(self, settings) -> dict:
        params = {
            "output_name": self._output_name.text(),
            "resize_factor": self._resize_factor.value(),
            "delete_original": self._delete_orig.isChecked(),
        }
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "output_name" in stored:
            self._output_name.setText(stored["output_name"])
        if "resize_factor" in stored:
            try:
                self._resize_factor.setValue(float(stored["resize_factor"]))
            except (ValueError, TypeError):
                pass
        if "delete_original" in stored:
            self._delete_orig.setChecked(stored["delete_original"] in ("1", "True", "true"))

    def load_config_section(self, section: dict) -> None:
        if not section:
            return
        if "output_name" in section:
            self._output_name.setText(str(section["output_name"]))
        if "resize_factor" in section:
            self._resize_factor.setValue(float(section["resize_factor"]))
        if "delete_original" in section:
            self._delete_orig.setChecked(bool(section["delete_original"]))

    def build_config_section(self) -> dict:
        return {
            "output_name": self._output_name.text(),
            "resize_factor": self._resize_factor.value(),
            "delete_original": self._delete_orig.isChecked(),
        }
