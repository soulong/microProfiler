"""Segmentation step panel — multi-segmentation with add/remove blocks."""
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
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
from microProfiler.gui.image_widgets import ImageViewer



class SegmentBlockWidget(QWidget):
    """A single segmentation block with controls and preview."""

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
        self._syncing = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Separator line
        sep_row = QHBoxLayout()
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep_row.addWidget(sep)
        layout.addLayout(sep_row)

        # Row 1: Object name + Model + Browse + Remove
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Object name:"))
        self._object_name = QLineEdit("cell")
        row1.addWidget(self._object_name)
        row1.addWidget(QLabel("Model:"))
        self._model_name = QComboBox()
        self._model_name.setEditable(True)
        self._model_name.addItems(["cpsam"])
        self._model_name.setCurrentText("cpsam")
        row1.addWidget(self._model_name)
        self._model_browse = QPushButton("Browse...")
        self._model_browse.setProperty("class", "secondary")
        self._model_browse.clicked.connect(self._browse_model)
        row1.addWidget(self._model_browse)
        row1.addStretch()
        self._remove_btn = QPushButton("✕ Remove")
        self._remove_btn.setProperty("class", "danger")
        row1.addWidget(self._remove_btn)
        if self._on_remove:
            self._remove_btn.clicked.connect(self._on_remove)
        layout.addLayout(row1)

        # Row 2: Diameter + thresholds
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Diameter:"))
        self._diameter = QSpinBox()
        self._diameter.setRange(0, 10000)
        self._diameter.setValue(0)
        self._diameter.setSpecialValueText("Auto")
        row2.addWidget(self._diameter)
        row2.addWidget(QLabel("Flow thresh:"))
        self._flow_threshold = QDoubleSpinBox()
        self._flow_threshold.setRange(0.0, 10.0)
        self._flow_threshold.setValue(0.4)
        self._flow_threshold.setSingleStep(0.1)
        row2.addWidget(self._flow_threshold)
        row2.addWidget(QLabel("Cell prob:"))
        self._cellprob_threshold = QDoubleSpinBox()
        self._cellprob_threshold.setRange(0.0, 10.0)
        self._cellprob_threshold.setValue(0.0)
        self._cellprob_threshold.setSingleStep(0.1)
        row2.addWidget(self._cellprob_threshold)
        row2.addStretch()
        layout.addLayout(row2)

        # Row 3: Chan1 + Merge1
        row3 = QHBoxLayout()
        self._chan1_row = row3
        row3.addWidget(QLabel("Chan1:"))
        self._chan1_checkboxes: List[QCheckBox] = []
        self._chan1_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                cb.setChecked(True)
                self._chan1_checkboxes.append(cb)
                row3.addWidget(cb)
        else:
            self._chan1_placeholder = QLabel("Load a dataset to configure")
            self._chan1_placeholder.setProperty("class", "placeholder")
            row3.addWidget(self._chan1_placeholder)
        row3.addWidget(QLabel("Merge1:"))
        self._merge1 = QComboBox()
        self._merge1.addItems(["mean", "max", "min"])
        row3.addWidget(self._merge1)
        row3.addStretch()
        layout.addLayout(row3)

        # Row 4: Chan2 + Merge2
        row4 = QHBoxLayout()
        self._chan2_row = row4
        row4.addWidget(QLabel("Chan2:"))
        self._chan2_checkboxes: List[QCheckBox] = []
        self._chan2_placeholder: Optional[QLabel] = None
        if self._channels:
            for ch in self._channels:
                cb = QCheckBox(ch)
                self._chan2_checkboxes.append(cb)
                row4.addWidget(cb)
        else:
            self._chan2_placeholder = QLabel("Load a dataset to configure")
            self._chan2_placeholder.setProperty("class", "placeholder")
            row4.addWidget(self._chan2_placeholder)
        row4.addWidget(QLabel("Merge2:"))
        self._merge2 = QComboBox()
        self._merge2.addItems(["mean", "max", "min"])
        row4.addWidget(self._merge2)
        row4.addStretch()
        layout.addLayout(row4)

        # Row 5: Right-aligned Pick Random and Preview Segment
        row4 = QHBoxLayout()
        row4.addStretch()
        self._pick_btn = QPushButton("Pick Random")
        self._pick_btn.setProperty("class", "secondary")
        self._preview_btn = QPushButton("Preview Segment")
        self._preview_btn.setProperty("class", "secondary")
        row4.addWidget(self._pick_btn)
        row4.addWidget(self._preview_btn)
        self._mask_toggle_btn = QPushButton("Show Mask")
        self._mask_toggle_btn.setCheckable(True)
        self._mask_toggle_btn.setChecked(True)
        self._mask_toggle_btn.setProperty("class", "secondary")
        self._mask_toggle_btn.setEnabled(False)
        self._mask_toggle_btn.clicked.connect(self._on_mask_toggle)
        row4.addWidget(self._mask_toggle_btn)
        self._mask_toggle_btn.setMinimumWidth(
            self.fontMetrics().horizontalAdvance(self._pick_btn.text()) + 32
        )
        layout.addLayout(row4)

        # Preview row — centered C1/C2 images, tightly packed
        preview_row = QHBoxLayout()
        preview_row.setSpacing(0)
        preview_row.setContentsMargins(0, 0, 0, 0)

        preview_row.addStretch()

        c1_col = QVBoxLayout()
        c1_col.setSpacing(0)
        c1_col.setAlignment(Qt.AlignTop)
        c1_label = QLabel("C1 (merged):")
        c1_label.setAlignment(Qt.AlignCenter)
        c1_label.setContentsMargins(0, 0, 0, 2)
        c1_col.addWidget(c1_label)
        self._c1_view = ImageViewer()
        self._c1_view.setFixedSize(300, 300)
        c1_col.addWidget(self._c1_view)
        preview_row.addLayout(c1_col)

        c2_col = QVBoxLayout()
        c2_col.setSpacing(0)
        c2_col.setAlignment(Qt.AlignTop)
        c2_label = QLabel("C2 (merged):")
        c2_label.setAlignment(Qt.AlignCenter)
        c2_label.setContentsMargins(0, 0, 0, 2)
        c2_col.addWidget(c2_label)
        self._c2_view = ImageViewer()
        self._c2_view.setFixedSize(300, 300)
        c2_col.addWidget(self._c2_view)
        preview_row.addLayout(c2_col)

        preview_row.addStretch()

        layout.addLayout(preview_row)

        # Sync zoom/pan/reset across viewers
        self._c1_view.zoomed.connect(lambda: self._sync_views(self._c1_view))
        self._c1_view.panned.connect(lambda: self._sync_views(self._c1_view))
        self._c2_view.zoomed.connect(lambda: self._sync_views(self._c2_view))
        self._c2_view.panned.connect(lambda: self._sync_views(self._c2_view))
        self._c1_view.view_reset.connect(self._reset_all_views)
        self._c2_view.view_reset.connect(self._reset_all_views)

    def get_chan1(self) -> List[str]:
        return [cb.text() for cb in self._chan1_checkboxes if cb.isChecked()]

    def get_chan2(self) -> List[str]:
        return [cb.text() for cb in self._chan2_checkboxes if cb.isChecked()]

    def rebuild_channels(self, channels: List[str]) -> None:
        """Replace Chan1/Chan2 checkboxes with new channel names."""
        self._channels = channels
        self._chan1_checkboxes.clear()
        self._chan2_checkboxes.clear()

        # Helper to rebuild one channel row
        def _rebuild_row(row, placeholder_attr, checkbox_list, checked_default):
            placeholder = getattr(self, placeholder_attr, None)
            if placeholder is not None:
                for i in range(row.count() - 1, -1, -1):
                    item = row.itemAt(i)
                    if item and item.widget() is placeholder:
                        row.removeItem(item)
                        placeholder.deleteLater()
                        setattr(self, placeholder_attr, None)
                        break

            # Remove all QCheckBox widgets from the row (iterate backwards)
            for i in range(row.count() - 1, -1, -1):
                item = row.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QCheckBox):
                    w = item.widget()
                    row.removeItem(item)
                    w.deleteLater()

            # Find insertion point: right after the label
            insert_at = -1
            for i in range(row.count()):
                w = row.itemAt(i).widget()
                if isinstance(w, QLabel) and w.text().startswith("Chan"):
                    insert_at = i + 1
                    break

            # Insert checkboxes
            for ch in channels:
                cb = QCheckBox(ch)
                cb.setChecked(checked_default)
                row.insertWidget(insert_at, cb)
                checkbox_list.append(cb)
                insert_at += 1

        _rebuild_row(self._chan1_row, "_chan1_placeholder", self._chan1_checkboxes, True)
        _rebuild_row(self._chan2_row, "_chan2_placeholder", self._chan2_checkboxes, False)

    def build_config_section(self) -> dict:
        chan1 = self.get_chan1()
        if not chan1:
            chan1 = self._channels[:1] if self._channels else []
        chan2 = self.get_chan2() or None
        return {
            "object_name": self._object_name.text().strip(),
            "model_name": self._model_name.currentText(),
            "chan1": chan1,
            "chan2": chan2,
            "merge1": self._merge1.currentText(),
            "merge2": self._merge2.currentText(),
            "diameter": self._diameter.value() if self._diameter.value() > 0 else None,
            "flow_threshold": self._flow_threshold.value(),
            "cellprob_threshold": self._cellprob_threshold.value(),
        }

    def set_locked(self, locked: bool) -> None:
        for w in (
            self._object_name, self._model_name, self._model_browse,
            self._diameter, self._flow_threshold, self._cellprob_threshold,
            self._merge1, self._merge2, self._pick_btn, self._preview_btn,
            self._remove_btn,
        ):
            w.setEnabled(not locked)
        for cb in self._chan1_checkboxes + self._chan2_checkboxes:
            cb.setEnabled(not locked)
        for placeholder in (self._chan1_placeholder, self._chan2_placeholder):
            if placeholder is not None:
                placeholder.setEnabled(not locked)

    def _browse_model(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Cellpose Model",
            "", "Model files (*.pt *.torch);;All files (*)",
        )
        if path:
            self._model_name.setCurrentText(path)

    def _on_mask_toggle(self) -> None:
        """Show or hide the mask overlay on C1/C2 previews."""
        visible = self._mask_toggle_btn.isChecked()
        self._mask_toggle_btn.setText("Hide Mask" if visible else "Show Mask")
        self._c1_view.set_overlay_visible(visible)
        self._c2_view.set_overlay_visible(visible)

    def _sync_views(self, source: ImageViewer) -> None:
        """Copy zoom, pan, and internal state to the other two viewers."""
        if self._syncing:
            return
        self._syncing = True
        try:
            t = source.transform()
            h = source.horizontalScrollBar().value()
            v_bar = source.verticalScrollBar().value()
            for view in (self._c1_view, self._c2_view):
                if view is not source:
                    view.setTransform(t)
                    view.horizontalScrollBar().setValue(h)
                    view.verticalScrollBar().setValue(v_bar)
                    view._fit_to_view = source._fit_to_view
                    view._zoom_level = source._zoom_level
        finally:
            self._syncing = False

    def _reset_all_views(self) -> None:
        """Reset zoom/pan on all preview viewers."""
        for v in (self._c1_view, self._c2_view):
            v._reset_view()


class SegmentStepPanel(BaseStepPanel):
    """Multi-segmentation panel with dynamic block add/remove."""

    step_name = "segment"

    pick_requested = Signal(int)
    preview_requested = Signal(int)

    @staticmethod
    def _compact_block(block: SegmentBlockWidget) -> None:
        from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QSpinBox, QDoubleSpinBox
        for child in block.findChildren(QSpinBox):
            child.setMaximumWidth(200)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in block.findChildren(QDoubleSpinBox):
            child.setMaximumWidth(200)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in block.findChildren(QComboBox):
            child.setMaximumWidth(200)

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.setTitle("Segmentation")
        self._blocks: List[SegmentBlockWidget] = []
        # Wrap controls in scroll area since blocks can be numerous
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._blocks_layout = QVBoxLayout(self._container)
        self._blocks_layout.setContentsMargins(0, 0, 0, 0)

        # Add button — stored in layout member so we can move it to bottom dynamically
        self._add_btn = QPushButton("+ Add New Segmentation")
        self._add_btn.clicked.connect(self._add_block)
        self._add_btn_layout = QHBoxLayout()
        self._add_btn_layout.addWidget(self._add_btn)
        self._add_btn_layout.addStretch()
        self._blocks_layout.addLayout(self._add_btn_layout)

        self._scroll.setWidget(self._container)
        self._controls_layout.addWidget(self._scroll)

        self._channels: List[str] = []
        # Start with one default block so the panel isn't empty
        self._add_block([])

    def _wire_block_signals(self, block: SegmentBlockWidget) -> None:
        """Wire all parameter-change signals on a block to trigger mask sync / auto-save."""
        self._wire_param_signal(block._object_name)
        self._wire_param_signal(block._diameter)
        self._wire_param_signal(block._flow_threshold)
        self._wire_param_signal(block._cellprob_threshold)
        self._wire_param_signal(block._model_name)
        self._wire_param_signal(block._merge1)
        self._wire_param_signal(block._merge2)
        for cb in block._chan1_checkboxes + block._chan2_checkboxes:
            self._wire_param_signal(cb)

    def _add_block(self, channels: Optional[List[str]] = None):
        channels = channels or self._channels
        idx = len(self._blocks)
        block = SegmentBlockWidget(
            idx, channels,
            on_remove=lambda: self._remove_block(block),
            parent=self._container,
        )
        block._pick_btn.clicked.connect(lambda: self.pick_requested.emit(block.block_index))
        block._preview_btn.clicked.connect(lambda: self.preview_requested.emit(block.block_index))
        self._wire_block_signals(block)
        self._compact_block(block)
        # Move add button to bottom: remove it, add spacing+block, re-add add button
        self._blocks_layout.removeItem(self._add_btn_layout)
        if self._blocks:
            self._blocks_layout.addSpacing(14)
        self._blocks.append(block)
        self._blocks_layout.addWidget(block)
        self._blocks_layout.addLayout(self._add_btn_layout)

    def _remove_block(self, block: SegmentBlockWidget):
        if len(self._blocks) <= 1:
            return  # keep at least one block
        self._blocks.remove(block)
        self._blocks_layout.removeWidget(block)
        block.deleteLater()
        # Re-index surviving blocks so block_index matches list position
        for i, b in enumerate(self._blocks):
            b.block_index = i
        self.parameter_changed.emit()

    def populate_channels(self, channels: List[str]) -> None:
        self._channels = channels
        # Save current channel selections before rebuild resets them
        saved_chan1 = {}
        saved_chan2 = {}
        for block in self._blocks:
            if block._channels:  # only preserve if block already had channels
                saved_chan1[block] = [cb.text() for cb in block._chan1_checkboxes if cb.isChecked()]
                saved_chan2[block] = [cb.text() for cb in block._chan2_checkboxes if cb.isChecked()]

        if not self._blocks:
            self._add_block(channels)
        else:
            for block in self._blocks:
                block.rebuild_channels(channels)
                for cb in block._chan1_checkboxes + block._chan2_checkboxes:
                    self._wire_param_signal(cb)

        # Restore channel selections that survived rebuild (same channel names)
        for block in self._blocks:
            if block in saved_chan1:
                for cb in block._chan1_checkboxes:
                    cb.setChecked(cb.text() in saved_chan1[block])
            if block in saved_chan2:
                for cb in block._chan2_checkboxes:
                    cb.setChecked(cb.text() in saved_chan2[block])

        # Trigger initial mask sync so profiling panel sees segmentation object names
        self.parameter_changed.emit()

    def validate_object_names(self) -> Optional[str]:
        """Check all blocks have unique non-empty names. Return error msg or None."""
        names = []
        for block in self._blocks:
            name = block._object_name.text().strip()
            if not name:
                return "Object name cannot be empty in one of the blocks."
            if name in names:
                return f"Duplicate object name: '{name}'. Each block must have a unique name."
            names.append(name)
        return None

    def get_object_names(self) -> List[str]:
        return [b._object_name.text().strip() for b in self._blocks if b._object_name.text().strip()]

    def build_config_section(self) -> List[dict]:
        return [block.build_config_section() for block in self._blocks]

    def set_locked(self, locked: bool) -> None:
        for block in self._blocks:
            block.set_locked(locked)

    def set_blocks_enabled(self, enabled: bool) -> None:
        """Temporarily enable/disable block action buttons (for running state)."""
        for block in self._blocks:
            block._pick_btn.setEnabled(enabled)
            block._preview_btn.setEnabled(enabled)
            block._remove_btn.setEnabled(enabled)

    def save_to_settings(self, settings) -> dict:
        params = {}
        for i, block in enumerate(self._blocks):
            cfg = block.build_config_section()
            for key, val in cfg.items():
                params[f"block_{i}_{key}"] = val
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        # Remove all existing blocks before loading stored
        for block in list(self._blocks):
            self._blocks.remove(block)
            self._blocks_layout.removeWidget(block)
            block.deleteLater()
        # Remove add button layout so blocks go before it
        self._blocks_layout.removeItem(self._add_btn_layout)
        # Count how many blocks we have from settings
        import re
        block_indices = set()
        for key in stored:
            m = re.match(r"block_(\d+)_", key)
            if m:
                block_indices.add(int(m.group(1)))
        for idx in sorted(block_indices):
            if self._blocks:
                self._blocks_layout.addSpacing(14)
            prefix = f"block_{idx}_"
            cfg = {}
            for key, val in stored.items():
                if key.startswith(prefix):
                    cfg[key[len(prefix):]] = val
            # Populate channels for this block
            channels = self._channels
            block = SegmentBlockWidget(
                idx, channels,
                parent=self._container,
            )
            # Wire remove/pick/preview after creation so closures capture the right block
            # Note: QPushButton.clicked emits checked(bool), so accept it as first arg
            block._remove_btn.clicked.connect(lambda checked, b=block: self._remove_block(b))
            block._pick_btn.clicked.connect(lambda checked, b=block: self.pick_requested.emit(b.block_index))
            block._preview_btn.clicked.connect(lambda checked, b=block: self.preview_requested.emit(b.block_index))
            self._wire_block_signals(block)
            if "object_name" in cfg:
                block._object_name.setText(str(cfg["object_name"]))
            if "model_name" in cfg:
                idx2 = block._model_name.findText(str(cfg["model_name"]))
                if idx2 >= 0:
                    block._model_name.setCurrentIndex(idx2)
            if "diameter" in cfg:
                try:
                    block._diameter.setValue(int(cfg["diameter"]))
                except (ValueError, TypeError):
                    pass
            if "flow_threshold" in cfg:
                try:
                    block._flow_threshold.setValue(float(cfg["flow_threshold"]))
                except (ValueError, TypeError):
                    pass
            if "cellprob_threshold" in cfg:
                try:
                    block._cellprob_threshold.setValue(float(cfg["cellprob_threshold"]))
                except (ValueError, TypeError):
                    pass
            if "merge1" in cfg:
                idx3 = block._merge1.findText(str(cfg["merge1"]))
                if idx3 >= 0:
                    block._merge1.setCurrentIndex(idx3)
            if "merge2" in cfg:
                idx4 = block._merge2.findText(str(cfg["merge2"]))
                if idx4 >= 0:
                    block._merge2.setCurrentIndex(idx4)
            # Restore channel checkbox selections (stored as JSON string)
            import json as _json
            if "chan1" in cfg and cfg["chan1"]:
                try:
                    chan1_list = _json.loads(cfg["chan1"])
                    chan1_set = set(chan1_list)
                    for cb in block._chan1_checkboxes:
                        cb.setChecked(cb.text() in chan1_set)
                except (_json.JSONDecodeError, TypeError):
                    pass
            if "chan2" in cfg and cfg["chan2"]:
                try:
                    chan2_list = _json.loads(cfg["chan2"])
                    chan2_set = set(chan2_list)
                    for cb in block._chan2_checkboxes:
                        cb.setChecked(cb.text() in chan2_set)
                except (_json.JSONDecodeError, TypeError):
                    pass
            self._compact_block(block)
            self._blocks.append(block)
            self._blocks_layout.addWidget(block)

        # Re-add add button at end
        self._blocks_layout.addLayout(self._add_btn_layout)
        # Fallback: if no blocks were restored, create a default one
        if not self._blocks:
            self._add_block(self._channels)

    def set_preview_c1(self, block_index: int, arr: np.ndarray):
        if block_index < len(self._blocks):
            block = self._blocks[block_index]
            block._c1_view.set_image(arr)

    def set_preview_c2(self, block_index: int, arr: np.ndarray):
        if block_index < len(self._blocks):
            block = self._blocks[block_index]
            block._c2_view.set_image(arr)

    def set_preview_mask(self, block_index: int, mask: np.ndarray):
        if block_index < len(self._blocks):
            block = self._blocks[block_index]
            block._c1_view.overlay_mask(mask)
            if block._c2_view._base_array is not None:
                block._c2_view.overlay_mask(mask)
            block._mask_toggle_btn.setEnabled(True)
            block._mask_toggle_btn.setChecked(True)
            block._mask_toggle_btn.setText("Hide Mask")

    def load_config_section(self, sections: list) -> None:
        """Restore from a list of SegmentationConfig dicts."""
        if not sections:
            return
        # Remove all existing blocks
        for block in list(self._blocks):
            self._blocks.remove(block)
            self._blocks_layout.removeWidget(block)
            block.deleteLater()
        self._blocks_layout.removeItem(self._add_btn_layout)

        for cfg in sections:
            if not isinstance(cfg, dict):
                continue
            if self._blocks:
                self._blocks_layout.addSpacing(14)
            block = SegmentBlockWidget(
                len(self._blocks), self._channels,
                parent=self._container,
            )
            block._remove_btn.clicked.connect(
                lambda checked, b=block: self._remove_block(b)
            )
            block._pick_btn.clicked.connect(
                lambda checked, b=block: self.pick_requested.emit(b.block_index)
            )
            block._preview_btn.clicked.connect(
                lambda checked, b=block: self.preview_requested.emit(b.block_index)
            )
            self._wire_block_signals(block)

            if "object_name" in cfg:
                block._object_name.setText(str(cfg["object_name"]))
            if "model_name" in cfg:
                idx = block._model_name.findText(str(cfg["model_name"]))
                if idx >= 0:
                    block._model_name.setCurrentIndex(idx)
            if "diameter" in cfg and cfg["diameter"] is not None:
                block._diameter.setValue(int(cfg["diameter"]))
            if "flow_threshold" in cfg:
                block._flow_threshold.setValue(float(cfg["flow_threshold"]))
            if "cellprob_threshold" in cfg:
                block._cellprob_threshold.setValue(float(cfg["cellprob_threshold"]))
            if "merge1" in cfg:
                idx = block._merge1.findText(str(cfg["merge1"]))
                if idx >= 0:
                    block._merge1.setCurrentIndex(idx)
            if "merge2" in cfg:
                idx = block._merge2.findText(str(cfg["merge2"]))
                if idx >= 0:
                    block._merge2.setCurrentIndex(idx)

            # Restore channel checkbox selections
            if "chan1" in cfg and cfg["chan1"]:
                chan1_set = set(cfg["chan1"])
                for cb in block._chan1_checkboxes:
                    cb.setChecked(cb.text() in chan1_set)
            if "chan2" in cfg and cfg["chan2"]:
                chan2_set = set(cfg["chan2"])
                for cb in block._chan2_checkboxes:
                    cb.setChecked(cb.text() in chan2_set)

            self._compact_block(block)
            self._blocks.append(block)
            self._blocks_layout.addWidget(block)

        self._blocks_layout.addLayout(self._add_btn_layout)
