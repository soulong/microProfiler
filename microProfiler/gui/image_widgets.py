"""Image display widgets for the GUI preview panels."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
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
    """Single image viewer with mouse-wheel zoom and click-drag pan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._fit_to_view = True
        self.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMinimumSize(200, 200)

    def set_image(self, arr: np.ndarray | QImage) -> None:
        self._scene.clear()
        if isinstance(arr, QImage):
            pixmap = QPixmap.fromImage(arr)
        else:
            pixmap = _array_to_pixmap(arr)
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._fit_to_view = True

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        self._fit_to_view = False

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


