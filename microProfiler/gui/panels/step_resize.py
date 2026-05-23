"""Resize step panel — compact controls without preview."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


class ResizeStepPanel(BaseStepPanel):
    step_name = "resize"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Resize")
        self._build_controls()

    def _build_controls(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("Scale:"))
        self._scale_factor = QDoubleSpinBox()
        self._scale_factor.setRange(0.1, 4.0)
        self._scale_factor.setValue(0.5)
        self._scale_factor.setSingleStep(0.1)
        row.addWidget(self._scale_factor)
        self._inplace = QCheckBox("In-place")
        self._inplace.setChecked(True)
        row.addWidget(self._inplace)
        row.addStretch()
        self._apply_btn = QPushButton("▶ Apply")
        self._apply_btn.setStyleSheet("font-weight: bold; padding: 4px 16px;")
        row.addWidget(self._apply_btn)
        self._controls_layout.addLayout(row)

        for w in (self._scale_factor, self._inplace):
            self._wire_param_signal(w)

    def save_to_settings(self, settings) -> dict:
        params = {
            "scale_factor": self._scale_factor.value(),
            "inplace": self._inplace.isChecked(),
        }
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "scale_factor" in stored:
            try:
                self._scale_factor.setValue(float(stored["scale_factor"]))
            except (ValueError, TypeError):
                pass
        if "inplace" in stored:
            self._inplace.setChecked(stored["inplace"] in ("1", "True", "true"))

    def load_config_section(self, section: dict) -> None:
        if not section:
            return
        if "scale_factor" in section:
            self._scale_factor.setValue(float(section["scale_factor"]))
        if "inplace" in section:
            self._inplace.setChecked(bool(section["inplace"]))

    def build_config_section(self) -> dict:
        return {
            "scale_factor": self._scale_factor.value(),
            "inplace": self._inplace.isChecked(),
        }
