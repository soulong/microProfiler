"""Progress bar widget for pipeline execution."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget


class ProgressPanel(QWidget):
    """Real-time progress bar with step label, percentage, and cancel button."""

    cancel_requested = Signal()

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self._label = QLabel("")
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setFormat("%p%")
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("class", "danger")
        self._cancel_btn.clicked.connect(self.cancel_requested)
        self._cancel_btn.setVisible(False)

        if compact:
            self._bar.setFixedHeight(16)
            self._bar.setMinimumWidth(200)
            self._bar.setMaximumWidth(350)
            self._label.setMaximumWidth(280)
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
            layout.addWidget(self._label)
            layout.addWidget(self._bar)
            layout.addWidget(self._cancel_btn)
        else:
            self._bar.setFixedHeight(22)
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
        self._bar.setProperty("class", "")
        self._bar.style().polish(self._bar)

    def show_status(self, message: str, pct: int) -> None:
        self._label.setText(message)
        self._bar.setRange(0, 100)
        self._bar.setValue(pct)
        self._cancel_btn.setVisible(False)
        self._bar.setProperty("class", "")
        self._bar.style().polish(self._bar)

    def show_error(self, message: str) -> None:
        self._label.setText(f"Error: {message}")
        self._bar.setProperty("class", "error")
        self._bar.style().polish(self._bar)
        self._cancel_btn.setVisible(False)

    def reset(self) -> None:
        self._label.setText("")
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._cancel_btn.setVisible(False)
        self._bar.setProperty("class", "")
        self._bar.style().polish(self._bar)

    def finished(self) -> None:
        self._bar.setValue(self._bar.maximum())
        self._cancel_btn.setVisible(False)
        self._label.setText("Complete")
        self._bar.setProperty("class", "success")
        self._bar.style().polish(self._bar)


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
