"""Resize images to a target scale factor.

Runs as a standalone step after conversion (when enabled).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional, Union

import numpy as np
from scipy.ndimage import zoom as ndi_zoom
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image, write_image
from microProfiler.preprocessing._swap import TempSwap

log = logging.getLogger(__name__)

ProgressCB = Callable[[str, int, int, str], None]


def resize_single(img: np.ndarray, scale_factor: float) -> np.ndarray:
    """Resize a single 2-D image by a scale factor.

    Parameters
    ----------
    img : np.ndarray
        Input 2-D image.
    scale_factor : float
        Resize factor (e.g., 0.5 halves both dimensions).

    Returns
    -------
    np.ndarray
        Resized image with same dtype as input.
    """
    h, w = img.shape[:2]
    target = (int(round(h * scale_factor)), int(round(w * scale_factor)))
    zoom = (target[0] / h, target[1] / w)
    log.debug("resize_single: %s -> %s (factor=%s)", (h, w), target, scale_factor)
    return ndi_zoom(img, zoom, order=1).astype(img.dtype)


def resize_dataset(
    ds: ImageDataset,
    scale_factor: float = 1.0,
    root_dir: Optional[Union[str, Path]] = None,
    inplace: bool = True,
    delete_original: bool = False,
    progress_cb: Optional[ProgressCB] = None,
) -> ImageDataset:
    """Resize all images in a dataset by a scale factor.

    Parameters
    ----------
    ds : ImageDataset
        Dataset whose images should be resized.
    scale_factor : float
        Resize factor (e.g., 0.5 halves both dimensions).
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).
    inplace : bool
        If True, resize images in-place (overwrite source directory).
    delete_original : bool
        Delete original files after resizing (only when not inplace).

    Returns
    -------
    ImageDataset
        New dataset pointing to the resized files.
    """
    if scale_factor == 1.0:
        return ds

    root = Path(root_dir) if root_dir else ds.measurement_dir.parent
    log.debug("resize_dataset: scale_factor=%s, inplace=%s", scale_factor, inplace)

    if inplace:
        target_dir = ds.measurement_dir
        effective_delete = False
    else:
        target_dir = root / f"resized_{scale_factor:.2f}"
        target_dir.mkdir(parents=True, exist_ok=True)
        effective_delete = delete_original

    # Fail-fast: check first image exists and is readable
    _validate_first_image(ds)

    metadata = ds.metadata
    all_paths = []
    for _, row in metadata.iterrows():
        img_dir = row["directory"]
        for ch in ds.intensity_colnames:
            all_paths.append(Path(img_dir) / row[ch])

    with TempSwap(target_dir, "resize") as swap:
        for i, src in enumerate(tqdm(all_paths, desc="Resizing", unit="img")):
            if progress_cb:
                progress_cb("Resize", i, len(all_paths), f"Image {src.name}")
            if not src.exists():
                continue
            img = read_image(src)
            resized = resize_single(img, scale_factor)

            dst = swap.temp_dir / src.name
            write_image(dst, resized)

            if inplace or effective_delete:
                swap.mark_original(src)

    if progress_cb:
        progress_cb("Resize", len(all_paths), len(all_paths), "Resize complete")

    if effective_delete and not inplace:
        for src in all_paths:
            if src.exists():
                src.unlink()

    return ImageDataset(target_dir)


def _validate_first_image(ds: ImageDataset) -> None:
    """Check that at least one image exists before processing.

    The first image is read again in the main processing loop —
    this function only verifies existence to fail fast before
    entering the TempSwap context.
    """
    if ds.metadata.empty:
        raise ValueError("Dataset is empty — no images to resize")
    row = ds.metadata.iloc[0]
    chs = ds.intensity_colnames
    if not chs:
        raise ValueError("Dataset has no intensity channels")
    img_path = Path(row["directory"]) / row[chs[0]]
    if not img_path.exists():
        raise FileNotFoundError(
            f"First image not found: {img_path}. "
            "Cannot proceed with resize."
        )
