"""Image display widgets for the GUI preview panels."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def _array_to_pixmap(arr: np.ndarray, lo: float = 0.1, hi: float = 99.9) -> QPixmap:
    """Convert a 2-D numpy array to QPixmap with percentile-based contrast stretch.

    Parameters
    ----------
    arr : np.ndarray
        Input image array.
    lo, hi : float
        Percentile values for contrast clipping (default: 0.1th and 99.9th).
    """
    arr = arr.astype(np.float64)
    if arr.max() > arr.min():
        vmin, vmax = np.percentile(arr, (lo, hi))
        if vmax > vmin:
            arr = (arr - vmin) / (vmax - vmin)
        arr = arr.clip(0, 1)
    arr = (arr * 255).round().clip(0, 255).astype(np.uint8)
    h, w = arr.shape
    img = QImage(arr.data, w, h, w, QImage.Format_Grayscale8)
    return QPixmap.fromImage(img)


class ImageViewer(QGraphicsView):
    """Single image viewer with mouse-wheel zoom and click-drag pan.

    Emits ``zoomed``, ``panned``, and ``view_reset`` signals for
    synchronizing multiple viewers.
    """

    zoomed = Signal()
    panned = Signal()
    view_reset = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._fit_to_view = True
        self._zoom_level = 0
        self.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        self._reloading = False
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumSize(100, 100)

    def set_image(self, arr: np.ndarray | QImage) -> None:
        self._reloading = True
        self._scene.clear()
        if isinstance(arr, QImage):
            pixmap = QPixmap.fromImage(arr)
        else:
            pixmap = _array_to_pixmap(arr)
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._fit_to_view = True
        self._zoom_level = 0
        self._reloading = False

    def _reset_view(self) -> None:
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
            self._fit_to_view = True
            self._zoom_level = 0

    def mouseDoubleClickEvent(self, event):
        self._reset_view()
        self.view_reset.emit()
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scale(1.15, 1.15)
            self._zoom_level += 1
            self._fit_to_view = False
            self.zoomed.emit()
        elif delta < 0 and self._zoom_level > 0:
            self.scale(1 / 1.15, 1 / 1.15)
            self._zoom_level -= 1
            self.zoomed.emit()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if not getattr(self, "_reloading", False):
            self.panned.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item and self._fit_to_view:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)


class ChannelTile(QWidget):
    """Single channel image tile with label."""

    def __init__(self, label: str, arr: np.ndarray | QImage | None = None, parent=None):
        super().__init__(parent)
        self._label_widget = QLabel(label)
        self._label_widget.setAlignment(Qt.AlignCenter)
        self._viewer = ImageViewer()
        self._viewer.setMinimumSize(120, 120)
        if arr is not None:
            self._viewer.set_image(arr)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._label_widget)
        layout.addWidget(self._viewer)

    def set_image(self, arr: np.ndarray | QImage) -> None:
        self._viewer.set_image(arr)


