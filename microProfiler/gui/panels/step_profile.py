"""Profiling step panel — image and object profiling parameter controls."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from microProfiler.gui.panels.base_step_panel import BaseStepPanel


def _hsep():
    s = QFrame()
    s.setFrameShape(QFrame.HLine)
    s.setFrameShadow(QFrame.Sunken)
    return s


def _hint(text: str) -> QLabel:
    """Small, muted explanatory label for parameter rows."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "QLabel { color: #888; font-size: 11px; font-style: italic; padding-left: 4px; }"
    )
    return lbl


class ObjectProfileBlockWidget(QWidget):
    """A single object-level profiling block with mask, channels, and extras."""

    def __init__(
        self,
        block_index: int,
        channels: List[str],
        on_remove: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.block_index = block_index
        self._on_remove = on_remove
        self._channels = channels
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # Row: Mask name + Parent mask + Remove button (all in one row)
        row_top = QHBoxLayout()
        row_top.addWidget(QLabel("Mask name:"))
        self._object_mask = QComboBox()
        self._object_mask.setEditable(True)
        row_top.addWidget(self._object_mask)
        row_top.addWidget(QLabel("Parent mask:"))
        self._parent_mask = QComboBox()
        self._parent_mask.setEditable(True)
        self._parent_mask.addItems(["None"])
        row_top.addWidget(self._parent_mask)
        row_top.addWidget(QLabel("Output table:"))
        self._output_table = QLineEdit()
        self._output_table.setMaximumWidth(150)
        self._table_synced = True
        self._object_mask.currentTextChanged.connect(self._sync_output_table)
        self._output_table.textEdited.connect(self._on_output_table_edited)
        row_top.addWidget(self._output_table)
        row_top.addStretch()
        self._remove_btn = QPushButton("✕ Remove")
        self._remove_btn.setProperty("class", "danger")
        row_top.addWidget(self._remove_btn)
        if self._on_remove:
            self._remove_btn.clicked.connect(self._on_remove)
        layout.addLayout(row_top)

        # -- Intensity --
        layout.addWidget(_hsep())
        self._intensity_ch_layout = QHBoxLayout()
        self._intensity_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._intensity_ch_layout.addWidget(QLabel("Intensity:"))
        self._intensity_cbs: List[QCheckBox] = []
        self._intensity_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                self._intensity_ch_layout.addWidget(cb)
                self._intensity_cbs.append(cb)
        else:
            self._intensity_placeholder = QLabel("Load a dataset to configure")
            self._intensity_ch_layout.addWidget(self._intensity_placeholder)
        layout.addLayout(self._intensity_ch_layout)

        # -- Radial --
        layout.addWidget(_hsep())
        self._radial_ch_layout = QHBoxLayout()
        self._radial_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._radial_ch_layout.addWidget(QLabel("Radial:"))
        self._radial_cbs: List[QCheckBox] = []
        self._radial_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                self._radial_ch_layout.addWidget(cb)
                self._radial_cbs.append(cb)
        else:
            self._radial_placeholder = QLabel("Load a dataset to configure")
            self._radial_ch_layout.addWidget(self._radial_placeholder)
        layout.addLayout(self._radial_ch_layout)
        self._rad_params_layout = QHBoxLayout()
        self._rad_params_layout.addWidget(QLabel("Bins:"))
        self._radial_bins = QSpinBox()
        self._radial_bins.setRange(1, 50)
        self._radial_bins.setValue(5)
        self._rad_params_layout.addWidget(self._radial_bins)
        layout.addLayout(self._rad_params_layout)
        layout.addWidget(_hint("Number of concentric rings from object edge to center"))

        # -- Granularity --
        layout.addWidget(_hsep())
        self._gran_ch_layout = QHBoxLayout()
        self._gran_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._gran_ch_layout.addWidget(QLabel("Granularity:"))
        self._gran_cbs: List[QCheckBox] = []
        self._gran_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                self._gran_ch_layout.addWidget(cb)
                self._gran_cbs.append(cb)
        else:
            self._gran_placeholder = QLabel("Load a dataset to configure")
            self._gran_ch_layout.addWidget(self._gran_placeholder)
        layout.addLayout(self._gran_ch_layout)
        self._gran_params_layout = QHBoxLayout()
        self._gran_params_layout.addWidget(QLabel("Radii (px):"))
        self._gran_radii = QLineEdit("1,3,6,8,12")
        self._gran_params_layout.addWidget(self._gran_radii)
        self._gran_params_layout.addWidget(QLabel("Subsample:"))
        self._gran_subsample = QDoubleSpinBox()
        self._gran_subsample.setRange(0.01, 1.0)
        self._gran_subsample.setValue(1.0)
        self._gran_subsample.setSingleStep(0.05)
        self._gran_params_layout.addWidget(self._gran_subsample)
        layout.addLayout(self._gran_params_layout)
        layout.addWidget(_hint(
            "Radii: pixel sizes of features to measure (before subsampling), "
            "e.g. '1,2,4,8,16'. Each radius defines a morphological closing disk; "
            "the effective disk size is scaled by the subsample ratio."
        ))
        layout.addWidget(_hint(
            "Subsample: fraction of object pixels to process for speed "
            "(0.25 = quarter resolution, 1.0 = full resolution)."
        ))

        # -- GLCM --
        layout.addWidget(_hsep())
        self._glcm_ch_layout = QHBoxLayout()
        self._glcm_ch_layout.setContentsMargins(0, 0, 0, 0)
        self._glcm_ch_layout.addWidget(QLabel("GLCM:"))
        self._glcm_cbs: List[QCheckBox] = []
        self._glcm_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                self._glcm_ch_layout.addWidget(cb)
                self._glcm_cbs.append(cb)
        else:
            self._glcm_placeholder = QLabel("Load a dataset to configure")
            self._glcm_ch_layout.addWidget(self._glcm_placeholder)
        layout.addLayout(self._glcm_ch_layout)
        self._glcm_params_layout = QHBoxLayout()
        self._glcm_params_layout.addWidget(QLabel("Distances:"))
        self._glcm_distances = QLineEdit("1,3")
        self._glcm_params_layout.addWidget(self._glcm_distances)
        self._glcm_params_layout.addWidget(QLabel("Levels:"))
        self._glcm_levels = QSpinBox()
        self._glcm_levels.setRange(2, 256)
        self._glcm_levels.setValue(256)
        self._glcm_params_layout.addWidget(self._glcm_levels)
        self._glcm_params_layout.addWidget(QLabel("Angles:"))
        self._glcm_angles = QLineEdit("0,90,180,270")
        self._glcm_params_layout.addWidget(self._glcm_angles)
        layout.addLayout(self._glcm_params_layout)
        layout.addWidget(_hint(
            "Distances: pixel offsets for co-occurrence pairs (comma-sep). "
            "Levels: grayscale quantization bins (fewer = coarser texture). "
            "Angles: GLCM analysis directions in degrees (comma-sep)"
        ))

        # -- Correlation --
        layout.addWidget(_hsep())
        self._corr_layout = QHBoxLayout()
        self._corr_layout.setContentsMargins(0, 0, 0, 0)
        self._corr_layout.addWidget(QLabel("Correlation:"))
        self._corr_cbs: List[QCheckBox] = []
        self._corr_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                for other in self._channels:
                    if other > ch:
                        pair_cb = QCheckBox(f"{ch}-{other}")
                        self._corr_layout.addWidget(pair_cb)
                        self._corr_cbs.append(pair_cb)
        else:
            self._corr_placeholder = QLabel("Load a dataset to configure")
            self._corr_layout.addWidget(self._corr_placeholder)
        layout.addLayout(self._corr_layout)
        layout.addWidget(_hint(
            "Select channel pairs to measure Pearson correlation of intensities "
            "within each segmented object"
        ))

        # Ensure content left-aligns (stretch at end of each row)
        self._left_align_content()

    def _left_align_content(self):
        """Force left alignment on every content row so widgets hug the left edge."""
        for lyt in [
            self._intensity_ch_layout, self._radial_ch_layout, self._gran_ch_layout,
            self._glcm_ch_layout, self._corr_layout,
            self._rad_params_layout, self._gran_params_layout, self._glcm_params_layout,
        ]:
            lyt.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # Remove ALL existing spacers (not just last — placeholders removal
            # can leave a stray spacer in the middle of the layout)
            for i in range(lyt.count() - 1, -1, -1):
                item = lyt.itemAt(i)
                if item and item.spacerItem():
                    lyt.removeItem(item)
            lyt.addStretch()

    # ── channel helpers ────────────────────────────────────────────────

    @staticmethod
    def _remove_placeholder(layout, placeholder_attr, obj):
        old = getattr(obj, placeholder_attr, None)
        if old is not None:
            layout.removeWidget(old)
            old.deleteLater()
            setattr(obj, placeholder_attr, None)

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

    def _checked(self, cbs: List[QCheckBox]) -> List[str]:
        return [cb.text() for cb in cbs if cb.isChecked()]

    def get_object_mask_name(self) -> str:
        return self._object_mask.currentText()

    def get_parent_mask_name(self) -> Optional[str]:
        txt = self._parent_mask.currentText()
        return None if txt == "None" else txt

    def get_output_table_name(self) -> str:
        return self._output_table.text().strip() or self.get_object_mask_name()

    def _sync_output_table(self, text: str) -> None:
        if self._table_synced:
            self._output_table.setText(text)

    def _on_output_table_edited(self) -> None:
        self._table_synced = False
        # Re-sync if user clears the field
        if not self._output_table.text().strip():
            self._table_synced = True
            self._output_table.setText(self._object_mask.currentText())

    def populate_channels(self, channels: List[str], stored: Optional[dict] = None) -> None:
        """Rebuild channel checkboxes for all sections."""
        self._channels = channels
        prefix = f"block_{self.block_index}_"
        get_saved = lambda key: set(
            (stored or {}).get(f"{prefix}{key}", "").split(",")
        ) - {""} if stored else set()

        saved_intensity = get_saved("intensity_channels")
        saved_radial = get_saved("radial_channels")
        saved_gran = get_saved("granularity_channels")
        saved_glcm = get_saved("glcm_channels")

        # Remove placeholders and existing checkboxes
        self._remove_placeholder(self._intensity_ch_layout, "_intensity_placeholder", self)
        self._remove_placeholder(self._radial_ch_layout, "_radial_placeholder", self)
        self._remove_placeholder(self._gran_ch_layout, "_gran_placeholder", self)
        self._remove_placeholder(self._glcm_ch_layout, "_glcm_placeholder", self)
        self._remove_placeholder(self._corr_layout, "_corr_placeholder", self)
        self._clear_channel_section(self._intensity_ch_layout, self._intensity_cbs)
        self._clear_channel_section(self._radial_ch_layout, self._radial_cbs)
        self._clear_channel_section(self._gran_ch_layout, self._gran_cbs)
        self._clear_channel_section(self._glcm_ch_layout, self._glcm_cbs)
        self._clear_channel_section(self._corr_layout, self._corr_cbs)

        if not channels:
            self._intensity_placeholder = QLabel("Load a dataset to configure")
            self._intensity_ch_layout.addWidget(self._intensity_placeholder)
            self._radial_placeholder = QLabel("Load a dataset to configure")
            self._radial_ch_layout.addWidget(self._radial_placeholder)
            self._gran_placeholder = QLabel("Load a dataset to configure")
            self._gran_ch_layout.addWidget(self._gran_placeholder)
            self._glcm_placeholder = QLabel("Load a dataset to configure")
            self._glcm_ch_layout.addWidget(self._glcm_placeholder)
            self._corr_placeholder = QLabel("Load a dataset to configure")
            self._corr_layout.addWidget(self._corr_placeholder)
            self._left_align_content()
            return

        has_saved = bool(stored)
        for ch in channels:
            cb = QCheckBox(ch)
            cb.setChecked(ch in saved_intensity if has_saved else False)
            self._intensity_ch_layout.addWidget(cb)
            self._intensity_cbs.append(cb)

            cb = QCheckBox(ch)
            cb.setChecked(ch in saved_radial if has_saved else False)
            self._radial_ch_layout.addWidget(cb)
            self._radial_cbs.append(cb)

            cb = QCheckBox(ch)
            cb.setChecked(ch in saved_gran if has_saved else False)
            self._gran_ch_layout.addWidget(cb)
            self._gran_cbs.append(cb)

            cb = QCheckBox(ch)
            cb.setChecked(ch in saved_glcm if has_saved else False)
            self._glcm_ch_layout.addWidget(cb)
            self._glcm_cbs.append(cb)

            for other in channels:
                if other > ch:
                    pair_cb = QCheckBox(f"{ch}-{other}")
                    self._corr_layout.addWidget(pair_cb)
                    self._corr_cbs.append(pair_cb)

        self._left_align_content()

    def populate_masks(self, mask_names: List[str]) -> None:
        stripped = [n.removeprefix("mask_") for n in mask_names]
        current = self._object_mask.currentText()
        self._object_mask.clear()
        for name in stripped:
            self._object_mask.addItem(name)
        if stripped:
            if current in stripped:
                self._object_mask.setCurrentText(current)
            else:
                self._object_mask.setCurrentIndex(0)
        current_parent = self._parent_mask.currentText()
        self._parent_mask.clear()
        self._parent_mask.addItems(["None"] + stripped)
        if current_parent in (["None"] + stripped):
            self._parent_mask.setCurrentText(current_parent)
        elif stripped:
            self._parent_mask.setCurrentIndex(0)

    def get_correlation_pairs(self) -> Optional[List[List[str]]]:
        pairs = []
        for cb in self._corr_cbs:
            if cb.isChecked():
                a, b = cb.text().split("-")
                pairs.append([a, b])
        return pairs or None

    def build_config_section(self) -> dict:
        glcm_d_str = self._glcm_distances.text().strip()
        glcm_d = None
        if glcm_d_str:
            glcm_d = [int(x.strip()) for x in glcm_d_str.split(",") if x.strip()]

        return {
            "object_mask_name": self.get_object_mask_name() or None,
            "parent_mask_name": self.get_parent_mask_name(),
            "output_table_name": self.get_output_table_name() or None,
            "object_intensity_channels": self._checked(self._intensity_cbs) or None,
            "object_radial_channels": self._checked(self._radial_cbs) or None,
            "object_radial_bins": self._radial_bins.value(),
            "object_granularity_channels": self._checked(self._gran_cbs) or None,
            "object_granularity_radii": self._gran_radii.text().strip() or None,
            "object_granularity_subsample": self._gran_subsample.value(),
            "object_glcm_channels": self._checked(self._glcm_cbs) or None,
            "object_glcm_distances": glcm_d,
            "object_glcm_levels": self._glcm_levels.value(),
            "object_glcm_angles": self._glcm_angles.text().strip() or None,
            "correlation_pairs": self.get_correlation_pairs(),
        }


class ProfileStepPanel(BaseStepPanel):
    """Profiling panel with Image-level and Object-level sub-sections."""

    step_name = "profile"

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Profiling")
        self._blocks: List[ObjectProfileBlockWidget] = []
        self._build_controls()
        self.setChecked(True)

    def _build_controls(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)

        # ── General profiling settings ───────────────────────────────
        general_layout = QHBoxLayout()
        general_layout.setContentsMargins(0, 0, 0, 0)
        general_layout.addWidget(QLabel("Worker Threads:"))
        self._n_workers = QSpinBox()
        self._n_workers.setRange(1, 64)
        n_cpu = __import__('os').cpu_count() or 1
        half_cores = max(1, n_cpu // 2)
        self._n_workers.setValue(half_cores)
        self._n_workers.setToolTip(
            "Number of worker processes for parallel profiling (default: half of CPU cores)"
        )
        general_layout.addWidget(self._n_workers)
        self._worker_hint = QLabel(f"(½ of {n_cpu} cores)")
        self._worker_hint.setProperty("class", "placeholder")
        general_layout.addWidget(self._worker_hint)
        general_layout.addStretch()

        # ── Image-level Profiling ────────────────────────────────────
        image_group = QGroupBox("Image-level Profiling")
        image_layout = QVBoxLayout(image_group)

        self._image_grid = QWidget()
        self._image_grid_layout = QGridLayout(self._image_grid)
        self._image_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._image_grid_layout.setHorizontalSpacing(4)
        self._image_grid_layout.setVerticalSpacing(2)
        self._image_ch_label = QLabel("Channels:")
        self._image_grid_layout.addWidget(self._image_ch_label, 0, 0)
        self._threshold_label = QLabel("Thresholds:")
        self._image_grid_layout.addWidget(self._threshold_label, 1, 0)
        self._image_ch_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._image_grid_layout.addWidget(self._image_ch_placeholder, 0, 1, 1, -1)
        self._threshold_placeholder: Optional[QLabel] = QLabel("Load a dataset to configure")
        self._image_grid_layout.addWidget(self._threshold_placeholder, 1, 1, 1, -1)
        self._image_ch_cbs: List[QCheckBox] = []
        self._threshold_spins: Dict[str, QLineEdit] = {}
        image_layout.addWidget(self._image_grid)

        inner_layout.addWidget(image_group)

        # ── Object-level Profiling (dynamic blocks) ──────────────────
        obj_group = QGroupBox("Object-level Profiling")
        obj_group.setCheckable(True)
        obj_group.setChecked(True)
        self._obj_group = obj_group
        self._obj_layout = QVBoxLayout(obj_group)

        # Add button — stored in layout member so we can move it to bottom
        self._obj_layout.addSpacing(8)
        self._add_btn = QPushButton("+ Add New Object Profiling")
        self._add_btn.clicked.connect(self._add_block)
        self._add_btn_layout = QHBoxLayout()
        self._add_btn_layout.addWidget(self._add_btn)
        self._add_btn_layout.addStretch()
        self._obj_layout.addLayout(self._add_btn_layout)

        inner_layout.addWidget(obj_group)
        inner_layout.addLayout(general_layout)
        inner_layout.addStretch()
        scroll.setWidget(inner)
        self._controls_layout.addWidget(scroll)

        # Wire n_workers signal
        self._wire_param_signal(self._n_workers)

        # Start with one default block
        self._add_block([])

    # ── Block management ──────────────────────────────────────────────

    @staticmethod
    def _compact_block(block: ObjectProfileBlockWidget) -> None:
        """Strip spinbox button symbols and set max width matching _apply_compact_widths."""
        from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox
        for child in block.findChildren(QLineEdit):
            child.setMaximumWidth(200)
        for child in block.findChildren(QSpinBox):
            child.setMaximumWidth(200)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in block.findChildren(QDoubleSpinBox):
            child.setMaximumWidth(200)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in block.findChildren(QComboBox):
            child.setMaximumWidth(200)

    def _wire_block_signals(self, block: ObjectProfileBlockWidget) -> None:
        self._wire_param_signal(block._object_mask)
        self._wire_param_signal(block._parent_mask)
        self._wire_param_signal(block._output_table)
        self._wire_param_signal(block._radial_bins)
        self._wire_param_signal(block._gran_radii)
        self._wire_param_signal(block._gran_subsample)
        self._wire_param_signal(block._glcm_distances)
        self._wire_param_signal(block._glcm_levels)
        self._wire_param_signal(block._glcm_angles)
        for cb_list in (block._intensity_cbs, block._radial_cbs, block._gran_cbs,
                        block._glcm_cbs, block._corr_cbs):
            for cb in cb_list:
                self._wire_param_signal(cb)

    def _add_block(self, channels: Optional[List[str]] = None):
        # Use first block's channels so new block is identical (not empty placeholders).
        # Use `or` to also catch False from QPushButton.clicked signal.
        channels = channels or (list(self._blocks[0]._channels) if self._blocks else [])
        idx = len(self._blocks)
        block = ObjectProfileBlockWidget(
            idx, channels,
            on_remove=lambda: self._remove_block(block),
            parent=self,
        )
        self._wire_block_signals(block)
        # Strip spinbox button symbols so new blocks match the first one
        self._compact_block(block)
        # Clone settings from existing first block: masks, channels, scalar params
        if self._blocks:
            src = self._blocks[0]
            block._object_mask.clear()
            for i in range(src._object_mask.count()):
                block._object_mask.addItem(src._object_mask.itemText(i))
            block._object_mask.setCurrentIndex(src._object_mask.currentIndex())
            block._parent_mask.clear()
            for i in range(src._parent_mask.count()):
                block._parent_mask.addItem(src._parent_mask.itemText(i))
            block._parent_mask.setCurrentIndex(src._parent_mask.currentIndex())
            block._output_table.setText(src._output_table.text())
            block._table_synced = src._table_synced
            # Clone channel checkbox states
            for src_cbs, dst_cbs in [
                (src._intensity_cbs, block._intensity_cbs),
                (src._radial_cbs, block._radial_cbs),
                (src._gran_cbs, block._gran_cbs),
                (src._glcm_cbs, block._glcm_cbs),
                (src._corr_cbs, block._corr_cbs),
            ]:
                checked = {cb.text() for cb in src_cbs if cb.isChecked()}
                for cb in dst_cbs:
                    cb.setChecked(cb.text() in checked)
            # Clone scalar params
            block._radial_bins.setValue(src._radial_bins.value())
            block._gran_radii.setText(src._gran_radii.text())
            block._gran_subsample.setValue(src._gran_subsample.value())
            block._glcm_distances.setText(src._glcm_distances.text())
            block._glcm_levels.setValue(src._glcm_levels.value())
            block._glcm_angles.setText(src._glcm_angles.text())
        # Move add button to bottom: remove it, add spacing+block, re-add add button
        self._obj_layout.removeItem(self._add_btn_layout)
        if self._blocks:
            self._obj_layout.addSpacing(42)
        self._blocks.append(block)
        self._obj_layout.addWidget(block)
        self._obj_layout.addLayout(self._add_btn_layout)

    def _remove_block(self, block: ObjectProfileBlockWidget):
        if len(self._blocks) <= 1:
            return  # keep at least one block
        self._blocks.remove(block)
        self._obj_layout.removeWidget(block)
        block.deleteLater()
        self.parameter_changed.emit()

    # ── Image-level helpers ───────────────────────────────────────────

    @staticmethod
    def _clear_grid_section(layout, checkbox_list, row):
        i = 0
        while i < layout.count():
            item = layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QCheckBox):
                r, _, _, _ = layout.getItemPosition(i)
                if r == row:
                    layout.removeItem(item)
                    w.deleteLater()
                    continue
            i += 1
        checkbox_list.clear()

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
        for w in self._threshold_spins.values():
            self._image_grid_layout.removeWidget(w)
            w.deleteLater()
        self._threshold_spins.clear()

    def _remove_placeholder(self, layout, placeholder_attr):
        old = getattr(self, placeholder_attr, None)
        if old is not None:
            layout.removeWidget(old)
            old.deleteLater()
            setattr(self, placeholder_attr, None)

    def _re_add_placeholder(self, placeholder_attr, layout, row=0, col=0, rowspan=1, colspan=1):
        placeholder = QLabel("Load a dataset to configure")
        if isinstance(layout, type(self._image_grid_layout)):
            layout.addWidget(placeholder, row, col, rowspan, colspan)
        else:
            layout.addWidget(placeholder)
        setattr(self, placeholder_attr, placeholder)

    def _restore_channel_checks(self, stored, section_key):
        if stored and section_key in stored:
            raw = stored.get(section_key, "")
            return {ch for ch in raw.split(",") if ch}
        return set()

    @staticmethod
    def _set_checked_states(cbs, channels):
        if channels is None:
            return
        channel_set = set(channels)
        for cb in cbs:
            cb.setChecked(cb.text() in channel_set)

    def _get_checked(self, cbs: List[QCheckBox]) -> List[str]:
        return [cb.text() for cb in cbs if cb.isChecked()]

    def get_thresholds(self) -> Optional[Dict[str, float]]:
        result = {}
        for ch, w in self._threshold_spins.items():
            try:
                val = float(w.text())
            except (ValueError, TypeError):
                val = 0.0
            if val > 0:
                result[ch] = val
        return result or None

    # ── Channel / mask population ─────────────────────────────────────

    def populate_channels(self, channels: List[str]) -> None:
        saved_thresholds = {}
        for ch, w in self._threshold_spins.items():
            try:
                saved_thresholds[ch] = float(w.text())
            except (ValueError, TypeError):
                saved_thresholds[ch] = 0.0
        stored = getattr(self, "_stored_channel_settings", {})

        # Rebuild image-level channel checkboxes
        self._remove_placeholder(self._image_grid_layout, "_image_ch_placeholder")
        self._remove_placeholder(self._image_grid_layout, "_threshold_placeholder")
        self._clear_grid_section(self._image_grid_layout, self._image_ch_cbs, 0)
        self._clear_thresholds()

        if not channels:
            self._re_add_placeholder("_image_ch_placeholder", self._image_grid_layout, 0, 1, 1, -1)
            self._re_add_placeholder("_threshold_placeholder", self._image_grid_layout, 1, 1, 1, -1)
        else:
            saved_image = self._restore_channel_checks(stored, "image_channels")
            image_has_saved = stored and "image_channels" in stored
            for col_idx, ch in enumerate(channels):
                col = col_idx + 1
                cb = QCheckBox(ch)
                cb.setChecked(ch in saved_image if image_has_saved else True)
                self._image_grid_layout.addWidget(cb, 0, col)
                self._image_ch_cbs.append(cb)
                self._wire_param_signal(cb)

                th_widget = QLineEdit("0.0")
                th_widget.setMinimumWidth(70)
                th_widget.setMaximumWidth(90)
                th_key = f"threshold_{ch}"
                if th_key in stored:
                    th_widget.setText(str(stored[th_key]))
                elif ch in saved_thresholds:
                    th_widget.setText(str(saved_thresholds[ch]))
                self._image_grid_layout.addWidget(th_widget, 1, col)
                self._threshold_spins[ch] = th_widget
                self._wire_param_signal(th_widget)

            # Push image-level channel columns to the left
            self._image_grid_layout.setColumnStretch(len(channels) + 1, 1)

        # Rebuild object-level channels in all blocks
        for block in self._blocks:
            block.populate_channels(channels, stored)
            self._wire_block_signals(block)

        if hasattr(self, "_stored_channel_settings"):
            del self._stored_channel_settings

    def populate_masks(self, mask_names: List[str]) -> None:
        for block in self._blocks:
            block.populate_masks(mask_names)

    # ── Accessors ─────────────────────────────────────────────────────

    def get_object_mask_name(self) -> str:
        if self._blocks:
            return self._blocks[0].get_object_mask_name()
        return ""

    def get_parent_mask_name(self) -> Optional[str]:
        if self._blocks:
            return self._blocks[0].get_parent_mask_name()
        return None

    def get_object_mask_names(self) -> List[str]:
        return [b.get_object_mask_name() for b in self._blocks]

    def get_parent_mask_names(self) -> List[Optional[str]]:
        return [b.get_parent_mask_name() for b in self._blocks]

    # ── Config building ───────────────────────────────────────────────

    def build_config_section(self) -> dict:
        image_ch = self._get_checked(self._image_ch_cbs) or None
        result = {
            "n_workers": self._n_workers.value(),
            "image_channels": image_ch,
            "image_thresholds": self.get_thresholds(),
        }

        if self._obj_group.isChecked():
            result["object_profilings"] = [b.build_config_section() for b in self._blocks]
        else:
            result["object_profilings"] = []

        return result

    # ── Settings persistence ──────────────────────────────────────────

    def save_to_settings(self, settings) -> dict:
        params = {
            "n_workers": self._n_workers.value(),
            "object_level_enabled": self._obj_group.isChecked(),
            "image_channels": ",".join(self._get_checked(self._image_ch_cbs)),
        }
        for ch, w in self._threshold_spins.items():
            params[f"threshold_{ch}"] = w.text()
        # Per-block params
        for i, block in enumerate(self._blocks):
            cfg = block.build_config_section()
            for key, val in cfg.items():
                if isinstance(val, list):
                    params[f"block_{i}_{key}"] = ",".join(str(v) for v in val if v is not None)
                elif val is not None:
                    params[f"block_{i}_{key}"] = str(val) if not isinstance(val, (int, float, bool)) else val
                else:
                    params[f"block_{i}_{key}"] = ""
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return

        if "n_workers" in stored:
            try:
                self._n_workers.setValue(int(stored["n_workers"]))
            except (ValueError, TypeError):
                pass
        if "object_level_enabled" in stored:
            self._obj_group.setChecked(stored["object_level_enabled"] in ("1", "True", "true"))

        # Count blocks from stored settings
        import re
        block_indices = set()
        for key in stored:
            m = re.match(r"block_(\d+)_", key)
            if m:
                block_indices.add(int(m.group(1)))

        if block_indices:
            # Remove existing blocks
            for block in list(self._blocks):
                self._blocks.remove(block)
                self._obj_layout.removeWidget(block)
                block.deleteLater()
            self._obj_layout.removeItem(self._add_btn_layout)

            for idx in sorted(block_indices):
                if self._blocks:
                    self._obj_layout.addSpacing(42)
                prefix = f"block_{idx}_"
                block = ObjectProfileBlockWidget(idx, [], parent=self)
                block._remove_btn.clicked.connect(lambda checked, b=block: self._remove_block(b))
                self._wire_block_signals(block)
                self._load_block_from_stored(block, stored, prefix)
                self._compact_block(block)
                self._blocks.append(block)
                self._obj_layout.addWidget(block)

            self._obj_layout.addLayout(self._add_btn_layout)
        else:
            # Backward compat: load legacy flat object params into first block
            if self._blocks:
                block = self._blocks[0]
                if "object_mask_name" in stored:
                    idx = block._object_mask.findText(stored["object_mask_name"])
                    if idx >= 0:
                        block._object_mask.setCurrentIndex(idx)
                if "parent_mask_name" in stored:
                    idx = block._parent_mask.findText(stored["parent_mask_name"])
                    if idx >= 0:
                        block._parent_mask.setCurrentIndex(idx)
                self._load_legacy_block_params(block, stored)

        # Channel selections and thresholds are restored in populate_channels
        self._stored_channel_settings = stored

    @staticmethod
    def _load_legacy_block_params(block: ObjectProfileBlockWidget, stored: dict) -> None:
        """Restore legacy flat object params into a block."""
        if "radial_bins" in stored:
            try:
                block._radial_bins.setValue(int(stored["radial_bins"]))
            except (ValueError, TypeError):
                pass
        if "gran_radii" in stored:
            block._gran_radii.setText(stored["gran_radii"])
        if "gran_subsample" in stored:
            try:
                block._gran_subsample.setValue(float(stored["gran_subsample"]))
            except (ValueError, TypeError):
                pass
        if "glcm_distances" in stored:
            block._glcm_distances.setText(stored["glcm_distances"])
        if "glcm_levels" in stored:
            try:
                block._glcm_levels.setValue(int(stored["glcm_levels"]))
            except (ValueError, TypeError):
                pass
        if "glcm_angles" in stored:
            block._glcm_angles.setText(stored["glcm_angles"])

    @staticmethod
    def _load_block_from_stored(block: ObjectProfileBlockWidget, stored: dict, prefix: str) -> None:
        """Restore a single block from stored settings with prefix."""
        def _get(key):
            return stored.get(f"{prefix}{key}")

        if _get("object_mask_name"):
            idx = block._object_mask.findText(str(_get("object_mask_name")))
            if idx >= 0:
                block._object_mask.setCurrentIndex(idx)
        if _get("parent_mask_name"):
            idx = block._parent_mask.findText(str(_get("parent_mask_name")))
            if idx >= 0:
                block._parent_mask.setCurrentIndex(idx)
        if _get("output_table_name"):
            block._output_table.setText(str(_get("output_table_name")))
            block._table_synced = False
        if _get("object_radial_bins"):
            try:
                block._radial_bins.setValue(int(_get("object_radial_bins")))
            except (ValueError, TypeError):
                pass
        if _get("object_granularity_radii"):
            block._gran_radii.setText(str(_get("object_granularity_radii")))
        if _get("object_granularity_subsample"):
            try:
                block._gran_subsample.setValue(float(_get("object_granularity_subsample")))
            except (ValueError, TypeError):
                pass
        if _get("object_glcm_distances"):
            block._glcm_distances.setText(str(_get("object_glcm_distances")))
        if _get("object_glcm_levels"):
            try:
                block._glcm_levels.setValue(int(_get("object_glcm_levels")))
            except (ValueError, TypeError):
                pass
        if _get("object_glcm_angles"):
            block._glcm_angles.setText(str(_get("object_glcm_angles")))

    # ── Config section loading ────────────────────────────────────────

    def load_config_section(self, section) -> None:
        """Restore profiling panel from a config dict or list."""
        if not section:
            return

        # Support new format (dict with object_profilings) and legacy single dict
        if isinstance(section, dict):
            if "n_workers" in section:
                self._n_workers.setValue(int(section["n_workers"]))

            # Image-level
            self._set_checked_states(self._image_ch_cbs, section.get("image_channels"))
            thresholds = section.get("image_thresholds") or {}
            for ch, w in self._threshold_spins.items():
                if ch in thresholds:
                    w.setText(str(thresholds[ch]))

            obj_profilings = section.get("object_profilings", [])
            if not obj_profilings:
                # Legacy: single-object fields on the top-level dict
                if "object_mask_name" in section:
                    obj_profilings = [section]
                else:
                    return

            # Rebuild blocks from object_profilings list
            for block in list(self._blocks):
                self._blocks.remove(block)
                self._obj_layout.removeWidget(block)
                block.deleteLater()
            self._obj_layout.removeItem(self._add_btn_layout)

            for cfg in obj_profilings:
                if not isinstance(cfg, dict):
                    continue
                if self._blocks:
                    self._obj_layout.addSpacing(42)
                block = ObjectProfileBlockWidget(len(self._blocks), [], parent=self)
                block._remove_btn.clicked.connect(lambda checked, b=block: self._remove_block(b))
                self._wire_block_signals(block)

                if "object_mask_name" in cfg:
                    idx = block._object_mask.findText(str(cfg["object_mask_name"]))
                    if idx >= 0:
                        block._object_mask.setCurrentIndex(idx)
                if "parent_mask_name" in cfg and cfg["parent_mask_name"]:
                    idx = block._parent_mask.findText(str(cfg["parent_mask_name"]))
                    if idx >= 0:
                        block._parent_mask.setCurrentIndex(idx)
                if "output_table_name" in cfg and cfg["output_table_name"]:
                    block._output_table.setText(str(cfg["output_table_name"]))
                    block._table_synced = False
                if "object_radial_bins" in cfg:
                    block._radial_bins.setValue(int(cfg["object_radial_bins"]))
                if "object_granularity_radii" in cfg and cfg["object_granularity_radii"]:
                    block._gran_radii.setText(str(cfg["object_granularity_radii"]))
                if "object_granularity_subsample" in cfg and cfg["object_granularity_subsample"] is not None:
                    block._gran_subsample.setValue(float(cfg["object_granularity_subsample"]))
                if "object_glcm_distances" in cfg and cfg["object_glcm_distances"]:
                    block._glcm_distances.setText(",".join(str(d) for d in cfg["object_glcm_distances"]))
                if "object_glcm_levels" in cfg and cfg["object_glcm_levels"] is not None:
                    block._glcm_levels.setValue(int(cfg["object_glcm_levels"]))
                if "object_glcm_angles" in cfg and cfg["object_glcm_angles"]:
                    block._glcm_angles.setText(str(cfg["object_glcm_angles"]))

                # Channel checkboxes (restored after widgets exist)
                self._set_checked_states(block._intensity_cbs, cfg.get("object_intensity_channels"))
                self._set_checked_states(block._radial_cbs, cfg.get("object_radial_channels"))
                self._set_checked_states(block._gran_cbs, cfg.get("object_granularity_channels"))
                self._set_checked_states(block._glcm_cbs, cfg.get("object_glcm_channels"))

                corr_pairs = cfg.get("correlation_pairs") or []
                for cb in block._corr_cbs:
                    pair = cb.text().split("-")
                    cb.setChecked(pair in corr_pairs)

                self._compact_block(block)
                self._blocks.append(block)
                self._obj_layout.addWidget(block)

            self._obj_layout.addLayout(self._add_btn_layout)
