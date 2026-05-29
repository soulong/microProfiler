"""Base class for collapsible pipeline step panels."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from microProfiler.gui.state import PipelineState


class BaseStepPanel(QGroupBox):
    """Collapsible step panel with enable/disable toggle and status badge.

    Uses QGroupBox built-in ``setCheckable(True)`` as the single enable toggle.
    Subclasses override ``_build_controls()`` and ``_build_preview()``.
    """

    step_name: str = "step"
    parameter_changed = Signal()

    def __init__(self, state: PipelineState, parent=None):
        super().__init__(parent)
        self._state = state
        self._was_checked = False
        self.setCheckable(True)
        self.setChecked(False)
        self.setProperty("class", "card")

        self._status_label = QLabel("")

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addStretch()
        top.addWidget(self._status_label)

        self._controls_widget = QWidget()
        self._controls_layout = QVBoxLayout(self._controls_widget)
        self._controls_layout.setContentsMargins(0, 0, 0, 0)
        self._controls_layout.setSpacing(2)

        self._preview_widget = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_widget)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)

        body = QVBoxLayout(self)
        body.setSpacing(0)
        body.addLayout(top)
        body.addWidget(self._controls_widget)
        body.addWidget(self._preview_widget)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._was_checked = checked

    def is_enabled(self) -> bool:
        return self.isChecked()

    def set_locked(self, locked: bool) -> None:
        self._controls_widget.setEnabled(not locked)
        if locked:
            self._was_checked = self.isChecked()
            super().setChecked(True)
            self.setCheckable(False)
            self._status_label.setText("✓ Completed")
            self._status_label.setProperty("class", "success")
        else:
            self.setCheckable(True)
            self.setChecked(self._was_checked)
            self._status_label.setText("")
            self._status_label.setProperty("class", "")
        self._status_label.style().polish(self._status_label)

    def _wire_param_signal(self, widget: QObject) -> None:
        """Connect common widget value-change signals to ``parameter_changed``."""
        if isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox)):
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.parameter_changed, Qt.UniqueConnection)
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self.parameter_changed, Qt.UniqueConnection)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self.parameter_changed, Qt.UniqueConnection)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self.parameter_changed, Qt.UniqueConnection)

    def save_to_settings(self, settings) -> Dict[str, Any]:
        """Persist widget values to ``settings``. Override in subclasses."""
        return {}

    def load_from_settings(self, settings) -> None:
        """Restore widget values from ``settings``. Override in subclasses."""

    def build_config_section(self) -> Optional[dict]:
        """Return a dict for PipelineConfig or None if disabled."""
        return None
