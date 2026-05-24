"""Sidebar navigation widget replacing QTabWidget."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SidebarItem(QWidget):
    """Single navigation item: icon + label + status dot."""

    clicked = Signal(str)

    def __init__(self, page_id: str, label: str, icon: str, parent=None):
        super().__init__(parent)
        self._page_id = page_id
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setProperty("active", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._icon_label = QLabel(icon)
        self._icon_label.setFixedWidth(28)
        self._icon_label.setProperty("class", "sidebar-icon")
        self._icon_label.setAlignment(Qt.AlignCenter)

        self._text_label = QLabel(label)
        self._text_label.setProperty("class", "sidebar-label")

        self._status_dot = QLabel("")
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setStyleSheet(
            "background-color: #555555; border-radius: 5px;"
        )

        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label, 1)
        layout.addWidget(self._status_dot)

        self._anim: QVariantAnimation | None = None

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().polish(self)
        self._icon_label.style().polish(self._icon_label)
        self._text_label.style().polish(self._text_label)

    def set_status(self, status: str) -> None:
        color_map = {
            "idle": "#555555",
            "running": "#4cc9f0",
            "done": "#06d6a0",
            "error": "#f04770",
        }
        target = color_map.get(status, "#555555")
        self._animate_dot_to(target)

    def _animate_dot_to(self, target_color: str) -> None:
        if self._anim is not None:
            self._anim.stop()
        current = self._status_dot.styleSheet()
        start = "#555555"
        if "background-color:" in current:
            start = current.split("background-color:")[1].split(";")[0].strip()

        self._anim = QVariantAnimation()
        self._anim.setDuration(300)
        self._anim.setStartValue(QColor(start))
        self._anim.setEndValue(QColor(target_color))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_dot_color)
        self._anim.start()

    def _on_dot_color(self, color: QColor) -> None:
        self._status_dot.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 5px;"
        )

    def mousePressEvent(self, event):
        self.clicked.emit(self._page_id)
        super().mousePressEvent(event)


class Sidebar(QWidget):
    """Vertical sidebar with icon+label navigation items and status dots."""

    navigation_changed = Signal(str)

    PAGES = [
        ("convert", "Convert", "▶"),        # ▶
        ("preprocess", "Pre-process", "⚙"),  # ⚙
        ("segment", "Segmentation", "▣"),    # ▣
        ("profile", "Profiling", "⌂"),       # ⌂
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(180)
        self.setObjectName("sidebar")
        self._items: dict[str, SidebarItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(2)

        for page_id, label, icon in self.PAGES:
            item = SidebarItem(page_id, label, icon)
            item.clicked.connect(self._on_item_clicked)
            layout.addWidget(item)
            self._items[page_id] = item

        layout.addStretch()
        self._current_page = "convert"
        self._items["convert"].set_active(True)

    def set_current_page(self, page_id: str) -> None:
        if page_id in self._items:
            for key, item in self._items.items():
                item.set_active(key == page_id)
            self._current_page = page_id

    def set_status(self, page_id: str, status: str) -> None:
        if page_id in self._items:
            self._items[page_id].set_status(status)

    def _on_item_clicked(self, page_id: str) -> None:
        self.set_current_page(page_id)
        self.navigation_changed.emit(page_id)
