"""Filter tab — narrow the dataset by metadata columns before segmentation."""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

from natsort import natsorted
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from microProfiler.gui.state import PipelineState

log = logging.getLogger(__name__)

_DIFF_TRUNCATE = 200


class FilterPanel(QWidget):
    """Dataset filter panel with before/after comparison.

    Applies ``ImageDataset.filter_metadata`` on a copy of the original
    dataset so the original is preserved for reset.
    """

    filter_changed = Signal()

    def __init__(self, state: PipelineState, parent=None):
        super().__init__(parent)
        self._state = state
        self._updating = False
        self._filter_widgets: List[Tuple[QComboBox, QLineEdit, QPushButton]] = []
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._apply_filters)
        self._build_ui()

    # ── UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Before / After info ─────────────────────────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        before_group = QGroupBox("Before (Original)")
        bl = QVBoxLayout(before_group)
        self._before_stats = QLabel("No dataset loaded.")
        self._before_stats.setWordWrap(True)
        self._before_stats.setProperty("class", "placeholder")
        bl.addWidget(self._before_stats)
        info_row.addWidget(before_group, 1)

        after_group = QGroupBox("After (Filtered)")
        al = QVBoxLayout(after_group)
        self._after_stats = QLabel("No dataset loaded.")
        self._after_stats.setWordWrap(True)
        self._after_stats.setProperty("class", "placeholder")
        al.addWidget(self._after_stats)
        info_row.addWidget(after_group, 1)

        root.addLayout(info_row)

        # ── Filter rows ─────────────────────────────────────────────────
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_group)
        filters_layout.setSpacing(6)

        self._filters_container = QWidget()
        self._filters_layout = QVBoxLayout(self._filters_container)
        self._filters_layout.setContentsMargins(0, 0, 0, 0)
        self._filters_layout.setSpacing(4)
        self._filters_layout.setAlignment(Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._filters_container)
        filters_layout.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Filter")
        self._add_btn.setProperty("class", "secondary")
        self._add_btn.clicked.connect(self._add_filter_row)
        self._reset_btn = QPushButton("Reset All")
        self._reset_btn.setProperty("class", "secondary")
        self._reset_btn.clicked.connect(self._reset_filters)
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch()
        filters_layout.addLayout(btn_row)

        root.addWidget(filters_group, 1)

    # ── Dataset update ──────────────────────────────────────────────────

    def update_dataset(self) -> None:
        """Refresh info panels from current state.dataset."""
        ds = self._state.dataset
        if ds is None:
            self._before_stats.setText("No dataset loaded.")
            self._before_stats.setProperty("class", "placeholder")
            self._after_stats.setText("No dataset loaded.")
            self._after_stats.setProperty("class", "placeholder")
            return

        self._before_stats.setProperty("class", "")
        self._after_stats.setProperty("class", "")
        self._before_stats.style().polish(self._before_stats)
        self._after_stats.style().polish(self._after_stats)

        orig = self._state.original_dataset
        self._before_stats.setText(
            self._build_stats_text(orig if orig is not None else ds)
        )
        self._after_stats.setText(self._build_stats_text(ds))

    # ── Stats ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_stats_text(ds) -> str:
        n = len(ds)
        meta = ds.metadata
        lines = [f"Image groups: {n}"]

        if meta is not None and "well" in meta.columns:
            n_wells = meta["well"].nunique()
            _M = _DIFF_TRUNCATE
            wells = ", ".join(natsorted(meta["well"].astype(str).unique()))
            if len(wells) > _M:
                wells = wells[:_M] + "…"
            lines.append(f"Wells: {n_wells} ({wells})")

        if meta is not None and "field" in meta.columns:
            n_fields = meta["field"].nunique()
            lines.append(f"Fields: {n_fields}")

        ch = ", ".join(ds.intensity_colnames)
        lines.append(f"Channels: {ch}")

        if ds.img_shape:
            lines.append(f"Dimensions: {ds.img_shape[0]}×{ds.img_shape[1]}")
        if ds.img_dtype is not None:
            lines.append(f"Data type: {ds.img_dtype}")
        if ds.mask_colnames:
            lines.append(f"Masks: {', '.join(ds.mask_colnames)}")

        return "\n".join(lines)

    # ── Filter rows ─────────────────────────────────────────────────────

    def _add_filter_row(self, column: str = "", pattern: str = "") -> None:
        meta_cols = self._get_filterable_columns()

        row = QHBoxLayout()
        col_combo = QComboBox()
        col_combo.addItems(meta_cols)
        if column and column in meta_cols:
            col_combo.setCurrentText(column)
        col_combo.setMaximumWidth(160)

        pat_edit = QLineEdit(pattern)
        pat_edit.setPlaceholderText("regex pattern…")
        pat_edit.setClearButtonEnabled(True)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(28, 28)
        remove_btn.setProperty("class", "danger")

        row.addWidget(col_combo)
        row.addWidget(pat_edit, 1)
        row.addWidget(remove_btn)

        widgets = (col_combo, pat_edit, remove_btn)
        self._filter_widgets.append(widgets)
        self._filters_layout.addLayout(row)

        col_combo.currentTextChanged.connect(self._on_filter_changed)
        pat_edit.textChanged.connect(self._on_filter_changed)
        remove_btn.clicked.connect(lambda: self._remove_filter_row(widgets, row))

        if not self._updating:
            self._apply_filters()

    def _remove_filter_row(
        self,
        widgets: Tuple[QComboBox, QLineEdit, QPushButton],
        row_layout: QHBoxLayout,
    ) -> None:
        if widgets not in self._filter_widgets:
            return
        self._filter_widgets.remove(widgets)
        while row_layout.count():
            item = row_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._filters_layout.removeItem(row_layout)
        if not self._updating:
            self._apply_filters()

    def _clear_filter_rows(self) -> None:
        for combo, edit, btn in self._filter_widgets:
            combo.deleteLater()
            edit.deleteLater()
            btn.deleteLater()
        self._filter_widgets.clear()
        while self._filters_layout.count():
            item = self._filters_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    w = sub.widget()
                    if w:
                        w.deleteLater()

    def _get_filterable_columns(self) -> List[str]:
        ds = self._state.original_dataset or self._state.dataset
        if ds is None or ds.metadata is None:
            return []
        skip = {"directory"}
        return [
            c for c in ds.metadata.columns
            if c not in skip and not c.startswith("ch") and not c.startswith("mask_")
        ]

    # ── Apply / Reset ───────────────────────────────────────────────────

    def _on_filter_changed(self, *_args) -> None:
        if not self._updating:
            self._debounce_timer.start()

    def _apply_filters(self) -> None:
        if self._updating:
            return
        orig = self._state.original_dataset
        if orig is None:
            return
        ds = orig.from_copy()
        for combo, edit, _btn in self._filter_widgets:
            col = combo.currentText()
            pat = edit.text().strip()
            if col and pat:
                try:
                    ds.filter_metadata(col, pat)
                except re.error as e:
                    log.warning("Invalid regex '%s' for column '%s': %s", pat, col, e)
        self._state.dataset = ds
        self.update_dataset()
        self.filter_changed.emit()

    def _reset_filters(self) -> None:
        self._debounce_timer.stop()
        if self._state.original_dataset is not None:
            self._state.dataset = self._state.original_dataset.from_copy()
        self._updating = True
        self._clear_filter_rows()
        self._updating = False
        self.update_dataset()
        self.filter_changed.emit()

    # ── Session persistence ─────────────────────────────────────────────

    def save_to_settings(self, settings) -> dict:
        filters = []
        for combo, edit, _btn in self._filter_widgets:
            col = combo.currentText()
            pat = edit.text().strip()
            if col:
                filters.append({"column": col, "pattern": pat})
        params = {"filters": filters}
        settings.save_params("filter", params)
        return params

    def load_from_settings(self, settings) -> None:
        self._debounce_timer.stop()
        stored = settings.load_params("filter")
        if not stored:
            return
        filters = stored.get("filters", [])
        self._updating = True
        self._clear_filter_rows()
        for f in filters:
            self._add_filter_row(
                column=f.get("column", ""),
                pattern=f.get("pattern", ""),
            )
        self._updating = False
        self._apply_filters()
