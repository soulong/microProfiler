"""QApplication bootstrap for the microProfiler GUI."""
import sys

from PySide6.QtWidgets import QApplication

from microProfiler.logging_utils import setup_logging


def main() -> None:
    """Launch the microProfiler desktop application."""
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("microProfiler")
    app.setOrganizationName("microProfiler")
    app.setApplicationVersion("0.8.1")

    from microProfiler.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
