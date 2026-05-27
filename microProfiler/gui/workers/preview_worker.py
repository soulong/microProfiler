"""PreviewWorker — runs single-image preview operations in a background thread."""
from __future__ import annotations

import inspect
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        """Preview BaSiC flatfield correction on a single image.

        Parameters
        ----------
        ds : ImageDataset
            Dataset to pull the image from.
        row_idx : int
            Row index in the dataset metadata.
        channels : list of str
            Channels to apply correction to.
        """
        if self._thread.isRunning():
            return
        self._dataset = ds
        self._row_idx = row_idx
        self._op = "basic"
        self._params = {"channels": channels}
        self._thread.start()

    def preview_segment(self, ds: ImageDataset, row_idx: int, seg_params: dict) -> None:
        """Preview Cellpose segmentation on a single image.

        Parameters
        ----------
        ds : ImageDataset
            Dataset to pull the image from.
        row_idx : int
            Row index in the dataset metadata.
        seg_params : dict
            Segmentation parameters forwarded to ``segment_single()``.
        """
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
                channels = self._params.get("channels", [])
                model_root = self._dataset.measurement_dir.parent
                flatfield_data: Dict[str, np.ndarray] = {}
                for ch, img in before_channels:
                    if ch not in channels:
                        after_channels.append((ch, img))
                        continue
                    model_path = model_root / ".microprofiler" / "BaSiC_model" / f"model_{ch}.pkl"
                    if model_path.exists():
                        with open(model_path, "rb") as f:
                            model = pickle.load(f)
                        ff = model.flatfield.astype(np.float32)
                        df = model.darkfield.astype(np.float32) if hasattr(model, "darkfield") and model.darkfield is not None else 0.0
                        corrected = (img.astype(np.float32) - df) / ff
                        after_channels.append((ch, corrected))
                        flatfield_data[ch] = ff
                    else:
                        after_channels.append((ch, img))
                extra["flatfield"] = flatfield_data

            elif self._op == "segment":
                from microProfiler.segmentation.cellpose import segment_single
                valid = set(inspect.signature(segment_single).parameters) - {"row"}
                c1_img, c2_img, mask = segment_single(
                    row, **{k: v for k, v in self._params.items() if k in valid}
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

    def cancel(self) -> None:
        """Request cancellation of the running preview."""
        if self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(3000):
                self._thread.terminate()
