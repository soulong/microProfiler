"""QApplication bootstrap for the microProfiler GUI."""
from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from microProfiler.logging_utils import setup_logging


def main() -> None:
    """Launch the microProfiler desktop application."""
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("microProfiler")
    app.setOrganizationName("microProfiler")
    app.setApplicationVersion("0.9.0")

    icon_path = Path(__file__).parent / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from microProfiler.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
