"""Base class for collapsible pipeline step panels."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal
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
        self.setStyleSheet("QGroupBox { font-weight: bold; }")

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: green; font-weight: normal;")

        top = QHBoxLayout()
        top.addStretch()
        top.addWidget(self._status_label)

        self._controls_widget = QWidget()
        self._controls_layout = QVBoxLayout(self._controls_widget)
        self._controls_layout.setContentsMargins(0, 0, 0, 0)

        self._preview_widget = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_widget)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)

        body = QVBoxLayout(self)
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
            self.setCheckable(False)
            self._status_label.setText("✓ Completed")
        else:
            self.setCheckable(True)
            self.setChecked(self._was_checked)
            self._status_label.setText("")

    def _wire_param_signal(self, widget: QObject) -> None:
        """Connect common widget value-change signals to ``parameter_changed``."""
        if isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox)):
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self.parameter_changed)
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self.parameter_changed)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self.parameter_changed)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self.parameter_changed)

    def _collect_widgets(self) -> List[QObject]:
        """Return all parameter widgets. Override in subclasses."""
        return []

    def save_to_settings(self, settings) -> Dict[str, Any]:
        """Persist widget values to ``settings`` (a QSettingsPersistence instance).

        Subclasses should override to provide step-specific params,
        then call the inherited version.
        """
        params: Dict[str, Any] = {}
        for w in self._collect_widgets():
            if isinstance(w, QLineEdit):
                params[w.objectName() or f"widget_{id(w)}"] = w.text()
            elif isinstance(w, QSpinBox):
                params[w.objectName() or f"widget_{id(w)}"] = w.value()
            elif isinstance(w, QDoubleSpinBox):
                params[w.objectName() or f"widget_{id(w)}"] = w.value()
            elif isinstance(w, QCheckBox):
                params[w.objectName() or f"widget_{id(w)}"] = w.isChecked()
            elif isinstance(w, QComboBox):
                params[w.objectName() or f"widget_{id(w)}"] = w.currentText()
        settings.save_params(self.step_name, params)
        return params

    def load_from_settings(self, settings) -> None:
        """Restore widget values from ``settings`` (a QSettingsPersistence instance).

        Subclasses should override to provide step-specific params,
        then call the inherited version.
        """
        stored = settings.load_params(self.step_name)
        if not stored:
            return
        for w in self._collect_widgets():
            key = w.objectName() or ""
            if not key or key not in stored:
                continue
            val = stored[key]
            if isinstance(w, QLineEdit):
                w.setText(val)
            elif isinstance(w, QSpinBox):
                try:
                    w.setValue(int(val))
                except (ValueError, TypeError):
                    pass
            elif isinstance(w, QDoubleSpinBox):
                try:
                    w.setValue(float(val))
                except (ValueError, TypeError):
                    pass
            elif isinstance(w, QCheckBox):
                w.setChecked(val in ("1", "True", "true"))
            elif isinstance(w, QComboBox):
                idx = w.findText(val)
                if idx >= 0:
                    w.setCurrentIndex(idx)

    def save_to_state(self) -> None:
        """Update state from widget values. Override in subclasses."""

    def load_from_state(self) -> None:
        """Update widget values from state. Override in subclasses."""

    def build_config_section(self) -> Optional[dict]:
        """Return a dict for PipelineConfig or None if disabled."""
        return None
