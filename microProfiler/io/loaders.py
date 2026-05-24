"""Unified image I/O with lazy intensity normalization.

Normalization (percentile scaling, min-max, z-score) is applied in-memory
when images are read — not stored to disk as a separate preprocessing step.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import tifffile
from PIL import Image

log = logging.getLogger(__name__)


def read_image(path: Union[str, Path]) -> np.ndarray:
    """Read a single image from disk (TIFF or PNG).

    Parameters
    ----------
    path : str or Path
        Path to the image file.

    Returns
    -------
    np.ndarray
        Image array.  2-D for single-plane, 3-D for multi-page TIFF.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    ext = path.suffix.lower()
    if ext == ".png":
        with Image.open(str(path)) as img:
            return np.array(img)
    return tifffile.imread(str(path))


def write_image(path: Union[str, Path], data: np.ndarray, **kwargs) -> None:
    """Write a single TIFF image to disk with compression.

    Parameters
    ----------
    path : str or Path
        Output file path.
    data : np.ndarray
        Image data to write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(path), data, compression="zlib", **kwargs)


class IntensityNormalizer:
    """Intensity normalization applied lazily on image read.

    Parameters
    ----------
    method : str
        One of ``"percentile"``, ``"minmax"``, ``"zscore"``, or ``None``.
    pmin : float
        Lower percentile (for ``percentile`` method).
    pmax : float
        Upper percentile (for ``percentile`` method).
    dtype : np.dtype
        Target output dtype.
    """

    def __init__(
        self,
        method: Optional[str] = "percentile",
        pmin: float = 1.0,
        pmax: float = 99.8,
        dtype: np.dtype = np.uint16,
    ):
        if method is not None and method not in ("percentile", "minmax", "zscore"):
            raise ValueError(f"Unknown normalization method: {method}")
        self.method = method
        self.pmin = pmin
        self.pmax = pmax
        self.dtype = dtype

    def __call__(self, image: np.ndarray) -> np.ndarray:
        """Apply normalization to the image.

        Parameters
        ----------
        image : np.ndarray
            Input image of any shape.

        Returns
        -------
        np.ndarray
            Normalized image at the target dtype.
        """
        if self.method is None:
            return image.astype(self.dtype)

        image = image.astype(np.float64)
        mask = image > 0
        nonzero = image[mask]

        if nonzero.size == 0:
            return image.astype(self.dtype)

        if self.method == "percentile":
            low = np.percentile(nonzero, self.pmin)
            high = np.percentile(nonzero, self.pmax)
            if high - low > 0:
                normalized = np.clip((image - low) / (high - low), 0, 1)
            else:
                normalized = np.zeros_like(image)

        elif self.method == "minmax":
            mn, mx = nonzero.min(), nonzero.max()
            if mx - mn > 0:
                normalized = (image - mn) / (mx - mn)
            else:
                normalized = np.zeros_like(image)

        elif self.method == "zscore":
            mean, std = nonzero.mean(), nonzero.std()
            if std > 0:
                normalized = (image - mean) / std
            else:
                normalized = np.zeros_like(image)

        if self.method != "zscore":
            max_val = np.iinfo(self.dtype).max if np.issubdtype(self.dtype, np.integer) else 1.0
            normalized = normalized * max_val

        return normalized.astype(self.dtype)
