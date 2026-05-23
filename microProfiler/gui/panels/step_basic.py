"""BaSiC shading correction step panel — compact controls with per-channel preview."""
from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from microProfiler.gui.panels.base_step_panel import BaseStepPanel
from microProfiler.gui.image_widgets import ChannelTile


class BaSiCStepPanel(BaseStepPanel):
    step_name = "basic"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("BaSiC Shading Correction")
        self._build_controls()
        self._build_preview()

    def _build_controls(self):
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Mode:"))
        self._mode = QComboBox()
        self._mode.addItems(["fit-transform", "fit", "transform"])
        row1.addWidget(self._mode)
        row1.addWidget(QLabel("Fit images:"))
        self._n_image = QSpinBox()
        self._n_image.setRange(1, 1000)
        self._n_image.setValue(50)
        row1.addWidget(self._n_image)
        row1.addWidget(QLabel("Working size:"))
        self._working_size = QSpinBox()
        self._working_size.setRange(16, 512)
        self._working_size.setValue(64)
        row1.addWidget(self._working_size)
        self._darkfield = QCheckBox("Darkfield")
        row1.addWidget(self._darkfield)
        self._inplace = QCheckBox("In-place")
        self._inplace.setChecked(True)
        row1.addWidget(self._inplace)
        row1.addStretch()
        self._controls_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addStretch()
        self._fit_btn = QPushButton("Fit Model")
        row2.addWidget(self._fit_btn)
        self._pick_btn = QPushButton("Pick Random")
        row2.addWidget(self._pick_btn)
        self._preview_btn = QPushButton("Preview Transform")
        row2.addWidget(self._preview_btn)
        self._apply_btn = QPushButton("▶ Apply")
        self._apply_btn.setStyleSheet("font-weight: bold; padding: 4px 16px;")
        row2.addWidget(self._apply_btn)
        self._controls_layout.addLayout(row2)

        for w in (self._mode, self._n_image, self._working_size, self._darkfield, self._inplace):
            self._wire_param_signal(w)

    def _build_preview(self):
        # Per-channel preview container: each row is chN: [raw] | [corrected] | [flatfield]
        self._preview_container = QVBoxLayout()
        self._preview_container.addWidget(QLabel("Load a dataset and click Pick Random to preview"))
        self._preview_layout.addLayout(self._preview_container)

    def set_preview_channels(self, channel_names):
        """Clear and rebuild the per-channel preview rows."""
        self._clear_preview()
        if not channel_names:
            self._preview_container.addWidget(
                QLabel("Load a dataset and click Pick Random to preview")
            )
            return
        for ch in channel_names:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{ch}:"))
            raw_tile = ChannelTile("raw", np.zeros((64, 64)))
            corr_tile = ChannelTile("corrected", np.zeros((64, 64)))
            ff_tile = ChannelTile("flatfield", np.zeros((64, 64)))
            row.addWidget(raw_tile)
            row.addWidget(corr_tile)
            row.addWidget(ff_tile)
            # Store refs for later update
            if not hasattr(self, "_channel_tiles"):
                self._channel_tiles = {}
            self._channel_tiles[ch] = (raw_tile, corr_tile, ff_tile)
            self._preview_container.addLayout(row)

    def update_preview_raw(self, channel_data: dict):
        """Update raw image tiles per channel."""
        for ch, arr in channel_data.items():
            if hasattr(self, "_channel_tiles") and ch in self._channel_tiles:
                self._channel_tiles[ch][0].set_image(arr)

    def update_preview_corrected(self, channel_data: dict):
        """Update corrected image tiles per channel."""
        for ch, arr in channel_data.items():
            if hasattr(self, "_channel_tiles") and ch in self._channel_tiles:
                self._channel_tiles[ch][1].set_image(arr)

    def update_preview_flatfield(self, channel_data: dict):
        """Update flatfield image tiles per channel."""
        for ch, arr in channel_data.items():
            if hasattr(self, "_channel_tiles") and ch in self._channel_tiles:
                self._channel_tiles[ch][2].set_image(arr)

    def _clear_preview(self):
        while self._preview_container.count():
            item = self._preview_container.takeAt(0)
            if item.layout():
                self._clear_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()
        if hasattr(self, "_channel_tiles"):
            del self._channel_tiles

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def save_to_settings(self, settings) -> dict:
        params = {
            "mode": self._mode.currentText(),
            "n_image": self._n_image.value(),
            "working_size": self._working_size.value(),
            "enable_darkfield": self._darkfield.isChecked(),
            "inplace": self._inplace.isChecked(),
        }
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "mode" in stored:
            idx = self._mode.findText(stored["mode"])
            if idx >= 0:
                self._mode.setCurrentIndex(idx)
        if "n_image" in stored:
            try:
                self._n_image.setValue(int(stored["n_image"]))
            except (ValueError, TypeError):
                pass
        if "working_size" in stored:
            try:
                self._working_size.setValue(int(stored["working_size"]))
            except (ValueError, TypeError):
                pass
        if "enable_darkfield" in stored:
            self._darkfield.setChecked(stored["enable_darkfield"] in ("1", "True", "true"))
        if "inplace" in stored:
            self._inplace.setChecked(stored["inplace"] in ("1", "True", "true"))

    def load_config_section(self, section: dict) -> None:
        if not section:
            return
        if "mode" in section:
            idx = self._mode.findText(str(section["mode"]))
            if idx >= 0:
                self._mode.setCurrentIndex(idx)
        if "n_image" in section:
            self._n_image.setValue(int(section["n_image"]))
        if "working_size" in section:
            self._working_size.setValue(int(section["working_size"]))
        if "enable_darkfield" in section:
            self._darkfield.setChecked(bool(section["enable_darkfield"]))
        if "inplace" in section:
            self._inplace.setChecked(bool(section["inplace"]))

    def build_config_section(self) -> dict:
        return {
            "mode": self._mode.currentText(),
            "n_image": self._n_image.value(),
            "working_size": self._working_size.value(),
            "enable_darkfield": self._darkfield.isChecked(),
            "inplace": self._inplace.isChecked(),
        }
