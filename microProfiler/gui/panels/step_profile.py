"""Profiling step panel — image and object profiling parameter controls."""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


class ProfileStepPanel(BaseStepPanel):
    """Profiling panel with Image-level and Object-level sub-sections."""

    step_name = "profile"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Profiling")
        self._build_controls()
        self.setChecked(True)

    def _build_controls(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)

        # ── Image-level Profiling ────────────────────────────────────
        image_group = QGroupBox("Image-level Profiling")
        image_layout = QVBoxLayout(image_group)

        self._image_ch_group = QWidget()
        self._image_ch_layout = QHBoxLayout(self._image_ch_group)
        self._image_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._image_ch_layout.addWidget(QLabel("Channels:"))
        self._image_ch_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._image_ch_layout.addWidget(self._image_ch_placeholder)
        self._image_ch_cbs: List[QCheckBox] = []
        image_layout.addWidget(self._image_ch_group)

        self._threshold_group = QWidget()
        self._threshold_layout = QHBoxLayout(self._threshold_group)
        self._threshold_layout.setContentsMargins(0, 0, 0, 0)
        self._threshold_layout.addWidget(QLabel("Thresholds:"))
        self._threshold_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._threshold_layout.addWidget(self._threshold_placeholder)
        self._threshold_spins: Dict[str, QDoubleSpinBox] = {}
        image_layout.addWidget(self._threshold_group)

        inner_layout.addWidget(image_group)

        # ── separator helper ──
        def _hsep():
            s = QFrame()
            s.setFrameShape(QFrame.HLine)
            s.setFrameShadow(QFrame.Sunken)
            return s

        # ── Object-level Profiling (compact two-row sections) ────────
        obj_group = QGroupBox("Object-level Profiling")
        obj_group.setCheckable(True)
        obj_group.setChecked(True)
        self._obj_group = obj_group
        obj_layout = QVBoxLayout(obj_group)

        mask_form = QFormLayout()
        self._object_mask = QComboBox()
        self._object_mask.setEditable(True)
        self._parent_mask = QComboBox()
        self._parent_mask.setEditable(True)
        self._parent_mask.addItems(["None"])
        mask_form.addRow("Mask name:", self._object_mask)
        mask_form.addRow("Parent mask:", self._parent_mask)
        obj_layout.addLayout(mask_form)

        # -- Intensity --
        obj_layout.addWidget(_hsep())
        self._intensity_ch_layout = QHBoxLayout()
        self._intensity_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._intensity_ch_layout.addWidget(QLabel("Intensity:"))
        self._intensity_cbs: List[QCheckBox] = []
        self._intensity_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._intensity_ch_layout.addWidget(self._intensity_placeholder)
        obj_layout.addLayout(self._intensity_ch_layout)

        # -- Radial --
        obj_layout.addWidget(_hsep())
        self._radial_ch_layout = QHBoxLayout()
        self._radial_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._radial_ch_layout.addWidget(QLabel("Radial:"))
        self._radial_cbs: List[QCheckBox] = []
        self._radial_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._radial_ch_layout.addWidget(self._radial_placeholder)
        obj_layout.addLayout(self._radial_ch_layout)
        rad_params = QHBoxLayout()
        rad_params.addWidget(QLabel("Bins:"))
        self._radial_bins = QSpinBox()
        self._radial_bins.setRange(1, 50)
        self._radial_bins.setValue(5)
        rad_params.addWidget(self._radial_bins)
        rad_params.addStretch()
        obj_layout.addLayout(rad_params)

        # -- Granularity --
        obj_layout.addWidget(_hsep())
        self._gran_ch_layout = QHBoxLayout()
        self._gran_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._gran_ch_layout.addWidget(QLabel("Granularity:"))
        self._gran_cbs: List[QCheckBox] = []
        self._gran_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._gran_ch_layout.addWidget(self._gran_placeholder)
        obj_layout.addLayout(self._gran_ch_layout)
        gran_params = QHBoxLayout()
        gran_params.addWidget(QLabel("Scales:"))
        self._gran_scales = QLineEdit("0,1,2,3,4")
        gran_params.addWidget(self._gran_scales)
        gran_params.addWidget(QLabel("Subsample:"))
        self._gran_subsample = QDoubleSpinBox()
        self._gran_subsample.setRange(0.01, 1.0)
        self._gran_subsample.setValue(0.25)
        self._gran_subsample.setSingleStep(0.05)
        gran_params.addWidget(self._gran_subsample)
        gran_params.addWidget(QLabel("Element:"))
        self._gran_element = QSpinBox()
        self._gran_element.setRange(1, 100)
        self._gran_element.setValue(10)
        gran_params.addWidget(self._gran_element)
        gran_params.addStretch()
        obj_layout.addLayout(gran_params)

        # -- GLCM --
        obj_layout.addWidget(_hsep())
        self._glcm_ch_layout = QHBoxLayout()
        self._glcm_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._glcm_ch_layout.addWidget(QLabel("GLCM:"))
        self._glcm_cbs: List[QCheckBox] = []
        self._glcm_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._glcm_ch_layout.addWidget(self._glcm_placeholder)
        obj_layout.addLayout(self._glcm_ch_layout)
        glcm_params = QHBoxLayout()
        glcm_params.addWidget(QLabel("Distances:"))
        self._glcm_distances = QLineEdit("1,2,3")
        glcm_params.addWidget(self._glcm_distances)
        glcm_params.addWidget(QLabel("Levels:"))
        self._glcm_levels = QSpinBox()
        self._glcm_levels.setRange(2, 256)
        self._glcm_levels.setValue(8)
        glcm_params.addWidget(self._glcm_levels)
        glcm_params.addWidget(QLabel("Angles:"))
        self._glcm_angles = QLineEdit("0,0.785,1.571,2.356")
        glcm_params.addWidget(self._glcm_angles)
        glcm_params.addStretch()
        obj_layout.addLayout(glcm_params)

        # -- Correlation --
        obj_layout.addWidget(_hsep())
        self._corr_layout = QHBoxLayout()
        self._corr_layout.setContentsMargins(0, 0, 0, 0)
        self._corr_layout.addWidget(QLabel("Correlation:"))
        self._corr_cbs: List[QCheckBox] = []
        self._corr_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._corr_layout.addWidget(self._corr_placeholder)
        obj_layout.addLayout(self._corr_layout)
        obj_layout.addWidget(_hsep())

        inner_layout.addWidget(obj_group)
        inner_layout.addStretch()
        scroll.setWidget(inner)
        self._controls_layout.addWidget(scroll)

        for w in (self._radial_bins, self._gran_scales, self._gran_subsample,
                  self._gran_element, self._glcm_distances, self._glcm_levels,
                  self._glcm_angles, self._object_mask, self._parent_mask):
            self._wire_param_signal(w)

    def _remove_placeholder(self, layout, placeholder_attr):
        old = getattr(self, placeholder_attr, None)
        if old is not None:
            layout.removeWidget(old)
            old.deleteLater()
            setattr(self, placeholder_attr, None)

    def _re_add_placeholder(self, placeholder_attr, layout):
        placeholder = QLabel("Load a dataset to configure")
        layout.addWidget(placeholder)
        setattr(self, placeholder_attr, placeholder)

    def _restore_channel_checks(self, stored, section_key):
        """Return a set of channel names that should be checked from stored settings."""
        if stored and section_key in stored:
            raw = stored.get(section_key, "")
            return {ch for ch in raw.split(",") if ch}
        return set()

    def populate_channels(self, channels: List[str]) -> None:
        saved_thresholds = {
            ch: spin.value() for ch, spin in self._threshold_spins.items()
        }
        stored = getattr(self, "_stored_channel_settings", {})
        self._remove_placeholder(self._intensity_ch_layout, "_intensity_placeholder")
        self._remove_placeholder(self._radial_ch_layout, "_radial_placeholder")
        self._remove_placeholder(self._gran_ch_layout, "_gran_placeholder")
        self._remove_placeholder(self._glcm_ch_layout, "_glcm_placeholder")
        self._remove_placeholder(self._corr_layout, "_corr_placeholder")
        self._remove_placeholder(self._image_ch_layout, "_image_ch_placeholder")
        self._remove_placeholder(self._threshold_layout, "_threshold_placeholder")
        self._clear_channel_section(self._image_ch_layout, self._image_ch_cbs)
        self._clear_channel_section(self._intensity_ch_layout, self._intensity_cbs)
        self._clear_channel_section(self._radial_ch_layout, self._radial_cbs)
        self._clear_channel_section(self._gran_ch_layout, self._gran_cbs)
        self._clear_channel_section(self._glcm_ch_layout, self._glcm_cbs)
        self._clear_channel_section(self._corr_layout, self._corr_cbs)
        self._clear_thresholds()
        if not channels:
            self._re_add_placeholder("_image_ch_placeholder", self._image_ch_layout)
            self._re_add_placeholder("_threshold_placeholder", self._threshold_layout)
            self._re_add_placeholder("_intensity_placeholder", self._intensity_ch_layout)
            self._re_add_placeholder("_radial_placeholder", self._radial_ch_layout)
            self._re_add_placeholder("_gran_placeholder", self._gran_ch_layout)
            self._re_add_placeholder("_glcm_placeholder", self._glcm_ch_layout)
            self._re_add_placeholder("_corr_placeholder", self._corr_layout)
            return

        saved_image = self._restore_channel_checks(stored, "image_channels")
        saved_intensity = self._restore_channel_checks(stored, "intensity_channels")
        saved_radial = self._restore_channel_checks(stored, "radial_channels")
        saved_gran = self._restore_channel_checks(stored, "granularity_channels")
        saved_glcm = self._restore_channel_checks(stored, "glcm_channels")

        for ch in channels:
            cb = QCheckBox(ch)
            cb.setChecked(ch in saved_image)
            self._image_ch_layout.addWidget(cb)
            self._image_ch_cbs.append(cb)
            self._wire_param_signal(cb)

            cb2 = QCheckBox(ch)
            cb2.setChecked(ch in saved_intensity)
            self._intensity_ch_layout.addWidget(cb2)
            self._intensity_cbs.append(cb2)
            self._wire_param_signal(cb2)

            cb3 = QCheckBox(ch)
            cb3.setChecked(ch in saved_radial)
            self._radial_ch_layout.addWidget(cb3)
            self._radial_cbs.append(cb3)
            self._wire_param_signal(cb3)

            cb4 = QCheckBox(ch)
            cb4.setChecked(ch in saved_gran)
            self._gran_ch_layout.addWidget(cb4)
            self._gran_cbs.append(cb4)
            self._wire_param_signal(cb4)

            cb5 = QCheckBox(ch)
            cb5.setChecked(ch in saved_glcm)
            self._glcm_ch_layout.addWidget(cb5)
            self._glcm_cbs.append(cb5)
            self._wire_param_signal(cb5)

            # Threshold spinbox per channel
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 100000.0)
            spin.setDecimals(1)
            spin.setMinimumWidth(90)
            th_key = f"threshold_{ch}"
            if th_key in stored:
                try:
                    spin.setValue(float(stored[th_key]))
                except (ValueError, TypeError):
                    spin.setValue(0.0)
            elif ch in saved_thresholds:
                spin.setValue(saved_thresholds[ch])
            else:
                spin.setValue(0.0)
            self._threshold_layout.addWidget(spin)
            self._threshold_spins[ch] = spin
            self._wire_param_signal(spin)

            # Correlation pair checkboxes
            for other in channels:
                if other > ch:
                    pair_cb = QCheckBox(f"{ch}-{other}")
                    self._corr_layout.addWidget(pair_cb)
                    self._corr_cbs.append(pair_cb)

        # Clear stored settings after applying
        if hasattr(self, "_stored_channel_settings"):
            del self._stored_channel_settings

    def load_config_section(self, section: dict) -> None:
        """Restore profiling panel from a ProfilingConfig dict."""
        if not section:
            return

        # Scalar params
        if "object_radial_bins" in section:
            self._radial_bins.setValue(int(section["object_radial_bins"]))
        if "object_granularity_scales" in section and section["object_granularity_scales"]:
            self._gran_scales.setText(str(section["object_granularity_scales"]))
        if "object_granularity_subsample" in section and section["object_granularity_subsample"] is not None:
            self._gran_subsample.setValue(float(section["object_granularity_subsample"]))
        if "object_granularity_element_size" in section and section["object_granularity_element_size"] is not None:
            self._gran_element.setValue(int(section["object_granularity_element_size"]))
        if "object_glcm_distances" in section and section["object_glcm_distances"]:
            self._glcm_distances.setText(",".join(str(d) for d in section["object_glcm_distances"]))
        if "object_glcm_levels" in section and section["object_glcm_levels"] is not None:
            self._glcm_levels.setValue(int(section["object_glcm_levels"]))
        if "object_glcm_angles" in section and section["object_glcm_angles"]:
            self._glcm_angles.setText(str(section["object_glcm_angles"]))
        if "object_mask_name" in section:
            idx = self._object_mask.findText(str(section["object_mask_name"]))
            if idx >= 0:
                self._object_mask.setCurrentIndex(idx)
        if "parent_mask_name" in section and section["parent_mask_name"]:
            idx = self._parent_mask.findText(str(section["parent_mask_name"]))
            if idx >= 0:
                self._parent_mask.setCurrentIndex(idx)

        # Channel checkboxes (widgets exist if populate_channels was called)
        self._set_checked_states(self._image_ch_cbs, section.get("image_channels"))
        self._set_checked_states(self._intensity_cbs, section.get("object_intensity_channels"))
        self._set_checked_states(self._radial_cbs, section.get("object_radial_channels"))
        self._set_checked_states(self._gran_cbs, section.get("object_granularity_channels"))
        self._set_checked_states(self._glcm_cbs, section.get("object_glcm_channels"))

        # Thresholds
        thresholds = section.get("image_thresholds") or {}
        for ch, spin in self._threshold_spins.items():
            if ch in thresholds:
                spin.setValue(float(thresholds[ch]))

        # Correlation pairs
        corr_pairs = section.get("correlation_pairs") or []
        for cb in self._corr_cbs:
            pair = cb.text().split("-")
            cb.setChecked(pair in corr_pairs)

    @staticmethod
    def _set_checked_states(cbs, channels):
        if channels is None:
            return
        channel_set = set(channels)
        for cb in cbs:
            cb.setChecked(cb.text() in channel_set)

    def get_checked(self, cbs: List[QCheckBox]) -> List[str]:
        return [cb.text() for cb in cbs if cb.isChecked()]

    @staticmethod
    def _clear_channel_section(layout, checkbox_list):
        i = 0
        while i < layout.count():
            item = layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QCheckBox):
                layout.removeItem(item)
                w.deleteLater()
            else:
                i += 1
        checkbox_list.clear()

    def _clear_thresholds(self):
        for spin in self._threshold_spins.values():
            self._threshold_layout.removeWidget(spin)
            spin.deleteLater()
        self._threshold_spins.clear()

    def populate_masks(self, mask_names: List[str]) -> None:
        # Strip "mask_" prefix — get_imageset() uses bare names as keys
        stripped = [n.removeprefix("mask_") for n in mask_names]
        current = self._object_mask.currentText()
        self._object_mask.clear()
        for name in stripped:
            self._object_mask.addItem(name)
        if stripped and current in stripped:
            self._object_mask.setCurrentText(current)
        current_parent = self._parent_mask.currentText()
        self._parent_mask.clear()
        self._parent_mask.addItems(["None"] + stripped)
        if current_parent in (["None"] + stripped):
            self._parent_mask.setCurrentText(current_parent)

    def save_to_settings(self, settings) -> dict:
        params = {
            "radial_bins": self._radial_bins.value(),
            "gran_scales": self._gran_scales.text(),
            "gran_subsample": self._gran_subsample.value(),
            "gran_element": self._gran_element.value(),
            "glcm_distances": self._glcm_distances.text(),
            "glcm_levels": self._glcm_levels.value(),
            "glcm_angles": self._glcm_angles.text(),
            "object_mask_name": self._object_mask.currentText(),
            "parent_mask_name": self._parent_mask.currentText(),
            "object_level_enabled": self._obj_group.isChecked(),
            "image_channels": ",".join(self.get_checked(self._image_ch_cbs)),
            "intensity_channels": ",".join(self.get_checked(self._intensity_cbs)),
            "radial_channels": ",".join(self.get_checked(self._radial_cbs)),
            "granularity_channels": ",".join(self.get_checked(self._gran_cbs)),
            "glcm_channels": ",".join(self.get_checked(self._glcm_cbs)),
        }
        # Thresholds per channel
        for ch, spin in self._threshold_spins.items():
            params[f"threshold_{ch}"] = spin.value()
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        if "radial_bins" in stored:
            try:
                self._radial_bins.setValue(int(stored["radial_bins"]))
            except (ValueError, TypeError):
                pass
        if "gran_scales" in stored:
            self._gran_scales.setText(stored["gran_scales"])
        if "gran_subsample" in stored:
            try:
                self._gran_subsample.setValue(float(stored["gran_subsample"]))
            except (ValueError, TypeError):
                pass
        if "gran_element" in stored:
            try:
                self._gran_element.setValue(int(stored["gran_element"]))
            except (ValueError, TypeError):
                pass
        if "glcm_distances" in stored:
            self._glcm_distances.setText(stored["glcm_distances"])
        if "glcm_levels" in stored:
            try:
                self._glcm_levels.setValue(int(stored["glcm_levels"]))
            except (ValueError, TypeError):
                pass
        if "glcm_angles" in stored:
            self._glcm_angles.setText(stored["glcm_angles"])
        if "object_mask_name" in stored:
            idx = self._object_mask.findText(stored["object_mask_name"])
            if idx >= 0:
                self._object_mask.setCurrentIndex(idx)
        if "parent_mask_name" in stored:
            idx = self._parent_mask.findText(stored["parent_mask_name"])
            if idx >= 0:
                self._parent_mask.setCurrentIndex(idx)
        if "object_level_enabled" in stored:
            self._obj_group.setChecked(stored["object_level_enabled"] in ("1", "True", "true"))
        # Channel selections and thresholds are restored in populate_channels
        # after the dynamic widgets are created
        self._stored_channel_settings = stored

    def get_thresholds(self) -> Optional[Dict[str, float]]:
        result = {}
        for ch, spin in self._threshold_spins.items():
            val = spin.value()
            if val > 0:
                result[ch] = val
        return result or None

    def get_object_mask_name(self) -> str:
        return self._object_mask.currentText()

    def get_parent_mask_name(self) -> Optional[str]:
        txt = self._parent_mask.currentText()
        return None if txt == "None" else txt

    def get_correlation_pairs(self) -> Optional[List[List[str]]]:
        pairs = []
        for cb in self._corr_cbs:
            if cb.isChecked():
                a, b = cb.text().split("-")
                pairs.append([a, b])
        return pairs or None

    def build_config_section(self) -> dict:
        image_ch = self.get_checked(self._image_ch_cbs) or None
        result = {
            "image_channels": image_ch,
            "image_thresholds": self.get_thresholds(),
        }

        if not self._obj_group.isChecked():
            return result

        intensity_ch = self.get_checked(self._intensity_cbs) or None
        radial_ch = self.get_checked(self._radial_cbs) or None
        gran_ch = self.get_checked(self._gran_cbs) or None
        glcm_ch = self.get_checked(self._glcm_cbs) or None

        glcm_d_str = self._glcm_distances.text().strip()
        glcm_d = None
        if glcm_d_str:
            glcm_d = [int(x.strip()) for x in glcm_d_str.split(",") if x.strip()]

        result.update({
            "object_mask_name": self.get_object_mask_name(),
            "parent_mask_name": self.get_parent_mask_name(),
            "object_intensity_channels": intensity_ch,
            "object_radial_channels": radial_ch,
            "object_radial_bins": self._radial_bins.value(),
            "object_granularity_channels": gran_ch,
            "object_granularity_scales": self._gran_scales.text().strip() or None,
            "object_granularity_subsample": self._gran_subsample.value(),
            "object_granularity_element_size": self._gran_element.value(),
            "object_glcm_channels": glcm_ch,
            "object_glcm_distances": glcm_d,
            "object_glcm_levels": self._glcm_levels.value(),
            "object_glcm_angles": self._glcm_angles.text().strip() or None,
            "correlation_pairs": self.get_correlation_pairs(),
        })
        return result
