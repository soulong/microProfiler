"""Progress bar widget for pipeline execution."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget


class ProgressPanel(QWidget):
    """Real-time progress bar with step label, percentage, and cancel button."""

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("")
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(30)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.cancel_requested)
        self._cancel_btn.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(self._label)
        top.addStretch()
        top.addWidget(self._cancel_btn)
        layout.addLayout(top)
        layout.addWidget(self._bar)

    def update_progress(self, step: str, current: int, total: int, message: str) -> None:
        self._label.setText(f"{step}: {message}")
        if total > 0:
            self._bar.setRange(0, total)
            self._bar.setValue(min(current, total))
        else:
            self._bar.setRange(0, 0)
        self._cancel_btn.setVisible(True)
        # Reset bar style — clear any error state
        self._bar.setStyleSheet("")

    def show_status(self, message: str, pct: int) -> None:
        """Update with a percentage status (e.g. for preview or non-step progress)."""
        self._label.setText(message)
        self._bar.setRange(0, 100)
        self._bar.setValue(pct)
        self._cancel_btn.setVisible(False)
        self._bar.setStyleSheet("")

    def show_error(self, message: str) -> None:
        """Display error state on the progress bar."""
        self._label.setText(f"Error: {message}")
        self._bar.setStyleSheet(
            "QProgressBar { border: 1px solid #d00; }"
            "QProgressBar::chunk { background-color: #d00; }"
        )
        self._cancel_btn.setVisible(False)

    def reset(self) -> None:
        self._label.setText("")
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._cancel_btn.setVisible(False)
        self._bar.setStyleSheet("")

    def finished(self) -> None:
        self._bar.setValue(self._bar.maximum())
        self._cancel_btn.setVisible(False)
        self._label.setText("Complete")
        self._bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #090; }"
        )


class QtLogHandler(QObject, logging.Handler):
    """Logging handler that emits a Qt signal for in-app display."""

    log_received = Signal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        from microProfiler.logging_utils import setup_logging  # avoid circular import

    def emit(self, record):
        msg = self.format(record)
        try:
            self.log_received.emit(msg)
        except RuntimeError:
            pass  # application shutting down
