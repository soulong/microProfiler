"""Z-projection step panel — compact controls without preview."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


class ZProjectStepPanel(BaseStepPanel):
    step_name = "zproject"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Z-Projection")
        self._build_controls()

    def _build_controls(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("Method:"))
        self._method = QComboBox()
        self._method.addItems(["max", "mean", "min"])
        row.addWidget(self._method)
        row.addStretch()
        self._apply_btn = QPushButton("▶ Apply")
        self._apply_btn.setStyleSheet("font-weight: bold; padding: 4px 16px;")
        row.addWidget(self._apply_btn)
        self._controls_layout.addLayout(row)

        for w in (self._method,):
            self._wire_param_signal(w)

    def save_to_settings(self, settings) -> dict:
        params = {
            "method": self._method.currentText(),
        }
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "method" in stored:
            idx = self._method.findText(stored["method"])
            if idx >= 0:
                self._method.setCurrentIndex(idx)

    def load_config_section(self, section: dict) -> None:
        if not section:
            return
        if "method" in section:
            idx = self._method.findText(str(section["method"]))
            if idx >= 0:
                self._method.setCurrentIndex(idx)

    def build_config_section(self) -> dict:
        return {
            "method": self._method.currentText(),
        }
