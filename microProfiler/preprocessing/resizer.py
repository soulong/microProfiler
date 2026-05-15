"""Resize images to a target scale factor.

This is the FIRST step in the preprocessing pipeline (when enabled).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from scipy.ndimage import zoom as ndi_zoom
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image, write_image


def resize_dataset(
    ds: ImageDataset,
    scale_factor: float = 1.0,
    root_dir: Optional[Union[str, Path]] = None,
) -> ImageDataset:
    """Resize all images in a dataset by a scale factor.

    The dataset metadata is rebuilt after resizing so that filenames reflect
    the new (resized) files.  Original files are **not** deleted.

    Parameters
    ----------
    ds : ImageDataset
        Dataset whose images should be resized.
    scale_factor : float
        Resize factor (e.g., 0.5 halves both dimensions).
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).

    Returns
    -------
    ImageDataset
        New dataset pointing to the resized files.
    """
    if scale_factor == 1.0:
        return ds

    root = Path(root_dir) if root_dir else ds.measurement_dir.parent
    resize_dir = root / f"resized_{scale_factor:.2f}"
    resize_dir.mkdir(parents=True, exist_ok=True)

    metadata = ds.metadata
    bar = tqdm(range(len(metadata)), desc="Resizing", unit="img")

    for idx in bar:
        row = metadata.iloc[idx]
        img_dir = row["directory"]

        for ch in ds.intensity_colnames:
            src = Path(img_dir) / row[ch]
            img = read_image(src)
            h, w = img.shape[:2]
            target = (int(round(h * scale_factor)), int(round(w * scale_factor)))
            zoom = (target[0] / h, target[1] / w)
            resized = ndi_zoom(img, zoom, order=1).astype(img.dtype)

            dst = resize_dir / src.name
            write_image(dst, resized)

    return ImageDataset(resize_dir)
