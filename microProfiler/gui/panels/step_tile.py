"""Tile splitting step panel — compact controls."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
)

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


class TileStepPanel(BaseStepPanel):
    step_name = "tile"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Tile Splitting")
        self._build_controls()

    def _build_controls(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("W:"))
        self._tile_w = QSpinBox()
        self._tile_w.setRange(64, 65536)
        self._tile_w.setValue(1024)
        self._tile_w.setSingleStep(256)
        row.addWidget(self._tile_w)
        row.addWidget(QLabel("H:"))
        self._tile_h = QSpinBox()
        self._tile_h.setRange(64, 65536)
        self._tile_h.setValue(1024)
        self._tile_h.setSingleStep(256)
        row.addWidget(self._tile_h)
        row.addStretch()
        self._apply_btn = QPushButton("▶ Apply")
        self._apply_btn.setStyleSheet("font-weight: bold; padding: 4px 16px;")
        row.addWidget(self._apply_btn)
        self._controls_layout.addLayout(row)

        for w in (self._tile_w, self._tile_h):
            self._wire_param_signal(w)

    def save_to_settings(self, settings) -> dict:
        params = {
            "tile_width": self._tile_w.value(),
            "tile_height": self._tile_h.value(),
        }
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "tile_width" in stored:
            try:
                self._tile_w.setValue(int(stored["tile_width"]))
            except (ValueError, TypeError):
                pass
        if "tile_height" in stored:
            try:
                self._tile_h.setValue(int(stored["tile_height"]))
            except (ValueError, TypeError):
                pass

    def load_config_section(self, section: dict) -> None:
        if not section:
            return
        if "tile_width" in section:
            self._tile_w.setValue(int(section["tile_width"]))
        if "tile_height" in section:
            self._tile_h.setValue(int(section["tile_height"]))

    def build_config_section(self) -> dict:
        return {
            "tile_width": self._tile_w.value(),
            "tile_height": self._tile_h.value(),
        }
