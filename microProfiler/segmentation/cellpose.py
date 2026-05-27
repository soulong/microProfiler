"""Cellpose-SAM segmentation for microscopy images.

Supports:
    1. Single channel  → C1 = image, C2 = 0
    2. Two channel groups → C1 = merge(chan1), C2 = merge(chan2)
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from cellpose import models, io as cp_io
from skimage.morphology import closing
from skimage.transform import rescale
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image

log = logging.getLogger(__name__)
ProgressCB = Callable[[str, int, int, str], None]


def merge_channels(
    paths: List[Path],
    method: str = "mean",
    resize_factor: float = 1.0,
) -> np.ndarray:
    """Read and merge a list of images.

    Parameters
    ----------
    paths : list of Path
        Image file paths.
    method : str
        ``"mean"``, ``"max"``, or ``"min"``.
    resize_factor : float
        Optional resize factor.

    Returns
    -------
    np.ndarray
        Merged 2-D image.
    """
    imgs = [read_image(p) for p in paths]
    stacked = np.stack(imgs, axis=0)

    if stacked.ndim == 4:
        stacked = np.mean(stacked, axis=3, keepdims=False)

    if method == "mean":
        merged = np.mean(stacked, axis=0)
    elif method == "max":
        merged = np.max(stacked, axis=0)
    elif method == "min":
        merged = np.min(stacked, axis=0)
    else:
        raise ValueError(f"Unsupported merge method: {method}")

    if resize_factor != 1.0:
        merged = rescale(
            merged, resize_factor,
            anti_aliasing=True, preserve_range=True,
        ).astype(stacked.dtype)

    return merged


def build_cellpose_image(
    row: pd.Series,
    chan1: List[str],
    chan2: Optional[List[str]],
    merge1: str,
    merge2: str,
    resize_factor: float,
) -> np.ndarray:
    """Build a (C, H, W) image for Cellpose-SAM (C=2 with chan2, C=1 without).

    Parameters
    ----------
    row : pd.Series
        Single row from the metadata DataFrame.
    chan1 : list of str
        Channel names for the first input channel.
    chan2 : list of str or None
        Channel names for the second input channel (optional).
    merge1 : str
        Merge method for chan1 (``"mean"``, ``"max"``, ``"min"``).
    merge2 : str
        Merge method for chan2 (``"mean"``, ``"max"``, ``"min"``).
    resize_factor : float
        Resize factor applied before merging.

    Returns
    -------
    np.ndarray
        Image array of shape ``(1, H, W)`` or ``(2, H, W)``.
    """
    img_dir = Path(row["directory"])

    ch1_paths = [
        img_dir / row[ch] for ch in chan1
        if ch in row and pd.notna(row[ch])
    ]
    if not ch1_paths:
        raise ValueError(f"Missing images for channel group 1: {chan1}")
    c1 = merge_channels(ch1_paths, merge1, resize_factor)

    if chan2:
        ch2_paths = [
            img_dir / row[ch] for ch in chan2
            if ch in row and pd.notna(row[ch])
        ]
        if not ch2_paths:
            raise ValueError(f"Missing images for channel group 2: {chan2}")
        c2 = merge_channels(ch2_paths, merge2, resize_factor)
        return np.stack([c1, c2], axis=0)

    return c1[np.newaxis, ...]


def segment_single(
    row: pd.Series,
    chan1: List[str],
    chan2: Optional[List[str]] = None,
    merge1: str = "mean",
    merge2: str = "mean",
    model_name: str = "cpsam",
    diameter: Optional[float] = None,
    flow_threshold: float = 0.4,
    cellprob_threshold: float = 0.0,
    resize_factor: float = 1.0,
    gpu_batch_size: int = 16,
) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
    """Segment a single image row using Cellpose-SAM.

    Parameters
    ----------
    row : pd.Series
        Single row from the metadata DataFrame.
    chan1 : list of str
        First channel group names.
    chan2 : list of str or None
        Second channel group names (optional).
    merge1, merge2 : str
        Merge method (``"mean"``, ``"max"``, ``"min"``).
    model_name : str
        Cellpose model name or path.
    diameter : float or None
        Object diameter in pixels (None = auto).
    flow_threshold : float
        Cellpose flow threshold.
    cellprob_threshold : float
        Cell probability threshold.
    resize_factor : float
        Resize factor before segmentation.

    Returns
    -------
    tuple of (np.ndarray or None, np.ndarray or None, np.ndarray)
        ``(chan1_merged, chan2_merged_or_None, mask)``.
    """
    device = _get_device()
    model = models.CellposeModel(device=device, pretrained_model=model_name)
    img = build_cellpose_image(row, chan1, chan2, merge1, merge2, resize_factor)
    diameter_val = None if diameter is None or diameter <= 0 else int(diameter * resize_factor)
    masks, flows, _ = model.eval(
        img,
        normalize={"percentile": [0.1, 99.9]},
        diameter=diameter_val,
        flow_threshold=flow_threshold,
        cellprob_threshold=cellprob_threshold,
        batch_size=gpu_batch_size,
    )
    if resize_factor != 1.0:
        masks = rescale(masks, 1.0 / resize_factor, order=0).astype(np.uint16)
    masks = closing(masks)

    c1_img = img[0] if img.shape[0] >= 1 else None
    c2_img = img[1] if img.shape[0] >= 2 else None
    return c1_img, c2_img, masks


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    log.debug("Device selected: %s", device)
    return device


def segment_dataset(
    ds: ImageDataset,
    object_name: str = "cell",
    chan1: Optional[List[str]] = None,
    chan2: Optional[List[str]] = None,
    merge1: str = "mean",
    merge2: str = "mean",
    model_name: str = "cpsam",
    diameter: Optional[float] = None,
    normalize: Optional[Dict] = None,
    resize_factor: float = 1.0,
    overwrite_mask: bool = False,
    flow_threshold: float = 0.4,
    cellprob_threshold: float = 0.0,
    gpu_batch_size: int = 16,
    progress_cb: Optional[ProgressCB] = None,
) -> ImageDataset:
    """Run Cellpose-SAM segmentation on every image in the dataset.

    Parameters
    ----------
    ds : ImageDataset
        Dataset to segment.
    object_name : str
        Suffix for mask filenames (e.g., ``"cell"``).
    chan1 : list of str, optional
        First channel group.  Defaults to first intensity channel.
    chan2 : list of str, optional
        Second channel group.  ``None`` means C2 = zeros.
    merge1, merge2 : str
        Merge method: ``"mean"``, ``"max"``, or ``"min"``.
    model_name : str
        Cellpose model name or path.
    diameter : float, optional
        Object diameter in pixels (``None`` = auto).
    normalize : dict, optional
        Normalization params, e.g. ``{"percentile": [0.1, 99.9]}``.
    resize_factor : float
        Resize factor before segmentation.
    overwrite_mask : bool
        Overwrite existing mask files.
    flow_threshold : float
        Cellpose flow threshold.
    cellprob_threshold : float
        Cell probability threshold.
    gpu_batch_size : int
        GPU patch batch size for Cellpose ``model.eval`` (number of patches
        processed in parallel on the GPU, not the number of images).

    Returns
    -------
    ImageDataset
        The input dataset with mask columns populated.
    """
    summary: Dict = {
        "success": False,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "masks_saved": 0,
        "errors": [],
    }

    chan1 = chan1 or ds.intensity_colnames[:1]
    if isinstance(chan1, str):
        chan1 = [chan1]
    if isinstance(chan2, str):
        chan2 = [chan2]

    log.debug(
        "segment_dataset: object=%s, model=%s, diameter=%s, chan1=%s, chan2=%s, resize=%s",
        object_name, model_name, diameter, chan1, chan2, resize_factor,
    )

    missing = [ch for ch in (chan1 + (chan2 or [])) if ch not in ds.intensity_colnames]
    if missing:
        log.error("Channels not found in dataset: %s", missing)
        return ds

    device = _get_device()
    normalize = normalize or {"percentile": [0.1, 99.9]}

    if progress_cb:
        progress_cb("Segment", 0, 1, "Loading Cellpose model...")
    log.info("Loading Cellpose model '%s'...", model_name)
    model = models.CellposeModel(device=device, pretrained_model=model_name)
    diameter_val = None if diameter is None or diameter <= 0 else int(diameter * resize_factor)

    metadata = ds.metadata
    for idx in tqdm(range(len(metadata)), desc="Cellpose", unit="img"):
        if progress_cb:
            progress_cb("Segment", idx, len(metadata), f"Image {idx}")
        row = metadata.iloc[idx]
        stem_ch = chan1[0]
        src_path = Path(row["directory"]) / row[stem_ch]
        if not src_path.exists():
            summary["skipped"] += 1
            summary["errors"].append(f"Source not found: {src_path.name}")
            continue

        save_stem = src_path.parent / f"{src_path.stem}_cp_masks"
        mask_path = save_stem.with_name(f"{save_stem.name}_{object_name}.png")

        if mask_path.exists() and not overwrite_mask:
            summary["skipped"] += 1
            continue

        try:
            img = build_cellpose_image(row, chan1, chan2, merge1, merge2, resize_factor)

            masks, flows, _ = model.eval(
                img,
                batch_size=gpu_batch_size,
                normalize=normalize,
                diameter=diameter_val,
                flow_threshold=flow_threshold,
                cellprob_threshold=cellprob_threshold,
            )

            if resize_factor != 1.0:
                masks = rescale(masks, 1.0 / resize_factor, order=0).astype(np.uint16)

            n_objects = len(np.unique(masks)) - 1
            if n_objects <= 0:
                summary["processed"] += 1
                summary["errors"].append(f"No objects in {src_path.name}")
                continue

            cp_io.save_masks(
                img[0],
                closing(masks),
                flows,
                file_names=str(save_stem),
                suffix=f"_{object_name}",
            )
            summary["processed"] += 1
            summary["masks_saved"] += 1

        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            summary["failed"] += 1
            summary["errors"].append(f"GPU OOM on {src_path.name}")
        except Exception as e:
            summary["failed"] += 1
            summary["errors"].append(f"Error on {src_path.name}: {e}")

        if idx % 200 == 0:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif torch.backends.mps.is_available():
                torch.mps.empty_cache()
            gc.collect()

    log.info(
        "Segmentation complete: %d processed, %d skipped, %d failed, %d masks saved",
        summary["processed"], summary["skipped"], summary["failed"], summary["masks_saved"],
    )
    if summary["errors"]:
        log.warning("Segmentation errors: %s", summary["errors"])

    ds.build_metadata()
    return ds
