"""QApplication bootstrap for the microProfiler GUI."""
from __future__ import annotations

import sys
from importlib.resources import files

from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from microProfiler.logging_utils import _ensure_std_streams, setup_logging


def _resource(name: str) -> str | None:
    """Return the path to a bundled resource file, or *None*."""
    try:
        return str(files("microProfiler.resources") / name)
    except Exception:
        return None


def main() -> None:
    """Launch the microProfiler desktop application."""
    _ensure_std_streams()
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("microProfiler")
    app.setOrganizationName("microProfiler")

    # Dark palette for title bar and system dialogs
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 46))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.Base, QColor(30, 30, 46))
    palette.setColor(QPalette.AlternateBase, QColor(37, 37, 54))
    palette.setColor(QPalette.ToolTipBase, QColor(45, 45, 68))
    palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    palette.setColor(QPalette.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.Button, QColor(45, 45, 68))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.BrightText, QColor(240, 71, 112))
    palette.setColor(QPalette.Highlight, QColor(76, 201, 240))
    palette.setColor(QPalette.HighlightedText, QColor(30, 30, 46))
    app.setPalette(palette)

    icon_path = _resource("icon.ico")
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    qss_path = _resource("style.qss")
    if qss_path:
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    from microProfiler.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
