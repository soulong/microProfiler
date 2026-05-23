"""PreviewWorker — runs single-image preview operations in a background thread."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image

PreviewResult = Dict[str, object]


class PreviewWorker(QObject):
    """Worker that computes previews for a single step in a background thread."""

    preview_ready = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._execute)
        self._dataset: Optional[ImageDataset] = None
        self._row_idx: int = 0

    def preview_basic(self, ds: ImageDataset, row_idx: int, channels: List[str]) -> None:
        if self._thread.isRunning():
            return
        self._dataset = ds
        self._row_idx = row_idx
        self._op = "basic"
        self._params = {"channels": channels}
        self._thread.start()

    def preview_segment(self, ds: ImageDataset, row_idx: int, seg_params: dict) -> None:
        if self._thread.isRunning():
            return
        self._dataset = ds
        self._row_idx = row_idx
        self._op = "segment"
        self._params = seg_params
        self._thread.start()

    def _execute(self) -> None:
        try:
            if self._dataset is None or self._row_idx >= len(self._dataset):
                self.error.emit("Invalid dataset or row index")
                return

            row = self._dataset.metadata.iloc[self._row_idx]
            row_dir = Path(row["directory"])

            # Always collect before images
            before_channels: List[Tuple[str, np.ndarray]] = []
            for ch in self._dataset.intensity_colnames:
                path = row_dir / row[ch]
                before_channels.append((ch, read_image(path)))

            after_channels: List[Tuple[str, np.ndarray]] = []
            extra: dict = {}

            if self._op == "basic":
                for ch, img in before_channels:
                    after_channels.append((ch, img))

            elif self._op == "segment":
                from microProfiler.segmentation.cellpose import segment_single
                c1_img, c2_img, mask = segment_single(
                    row, **self._params
                )
                extra["c1_img"] = c1_img
                extra["c2_img"] = c2_img
                extra["mask"] = mask

            result: PreviewResult = {
                "before": before_channels,
                "after": after_channels,
                "extra": extra,
                "row_idx": self._row_idx,
            }
            self.preview_ready.emit(result)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._thread.quit()
            self._thread.wait()
