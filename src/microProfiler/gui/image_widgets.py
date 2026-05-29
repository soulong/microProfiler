"""Image display widgets for the GUI preview panels."""
from __future__ import annotations

from typing import Optional

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
        self._base_array: Optional[np.ndarray] = None
        self._overlay_mask: Optional[np.ndarray] = None
        self._overlay_visible = False
        self._overlay_alpha = 0.4
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumSize(100, 100)

    def set_image(self, arr: np.ndarray | QImage) -> None:
        self._base_array = arr if isinstance(arr, np.ndarray) else None
        self._overlay_mask = None
        self._overlay_visible = False
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

    def overlay_mask(self, mask: np.ndarray, alpha: float = 0.7) -> None:
        """Overlay a colored label mask on top of the current base image.

        Parameters
        ----------
        mask : np.ndarray
            uint16 label mask (0 = background, non-zero = objects).
        alpha : float
            Opacity of the mask overlay (0 = invisible, 1 = opaque).
        """
        if self._base_array is None:
            return
        self._overlay_mask = mask
        self._overlay_alpha = alpha
        self._overlay_visible = True
        self._apply_overlay()

    def set_overlay_visible(self, visible: bool) -> None:
        """Show or hide the mask overlay without losing the base image or mask data."""
        self._overlay_visible = visible
        if visible and self._overlay_mask is not None:
            self._apply_overlay()
        elif not visible and self._base_array is not None:
            self._reloading = True
            self._scene.clear()
            pixmap = _array_to_pixmap(self._base_array)
            self._pixmap_item = QGraphicsPixmapItem(pixmap)
            self._scene.addItem(self._pixmap_item)
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
            self._fit_to_view = True
            self._zoom_level = 0
            self._reloading = False

    def _apply_overlay(self) -> None:
        """Recompute and display the composited base + mask overlay."""
        if self._base_array is None or self._overlay_mask is None:
            return
        base = self._base_array.astype(np.float64)
        vmin, vmax = np.percentile(base[base > 0] if (base > 0).any() else base, (0.1, 99.9))
        if vmax > vmin:
            base = (base - vmin) / (vmax - vmin)
        base = base.clip(0, 1)

        mask = self._overlay_mask
        labels = np.unique(mask)
        h, w = mask.shape
        overlay = np.zeros((h, w, 4), dtype=np.float64)
        for lbl in labels:
            if lbl == 0:
                continue
            rnd = np.random.RandomState(int(lbl) * 7 + 13)
            color = np.array([rnd.randint(60, 256) for _ in range(3)], dtype=np.float64) / 255.0
            overlay[mask == lbl, :3] = color
            overlay[mask == lbl, 3] = self._overlay_alpha

        base_rgb = np.stack([base] * 3, axis=-1)
        a = overlay[..., 3:4]
        composited = overlay[..., :3] * a + base_rgb * (1 - a)
        composited = (composited.clip(0, 1) * 255).astype(np.uint8)

        qimg = QImage(composited.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self._reloading = True
        self._scene.clear()
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


