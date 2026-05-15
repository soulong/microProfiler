"""Z-stack projection — collapse the Z (stack) dimension."""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image, write_image


def _project_group(
    image_paths: List[Path],
    method: str = "max",
) -> np.ndarray:
    """Compute the projection of a Z-stack group.

    Parameters
    ----------
    image_paths : list of Path
        Z-stack images in slice order.
    method : str
        ``"max"``, ``"mean"``, or ``"min"``.

    Returns
    -------
    np.ndarray
        Projected image.
    """
    images = [read_image(p) for p in image_paths]
    stacked = np.stack(images, axis=0)

    if method == "max":
        return np.max(stacked, axis=0)
    elif method == "mean":
        return np.mean(stacked, axis=0).astype(np.float32)
    elif method == "min":
        return np.min(stacked, axis=0)
    else:
        raise ValueError(f"Unknown projection method: {method}")


log = logging.getLogger(__name__)


def z_project_dataset(
    ds: ImageDataset,
    method: str = "max",
    delete_original: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
) -> ImageDataset:
    """Perform Z-projection on a dataset.

    Groups images by all metadata columns except ``stack``, then projects
    each group.

    Parameters
    ----------
    ds : ImageDataset
        Input dataset with a ``stack`` column.
    method : str
        ``"max"``, ``"mean"``, or ``"min"``.
    delete_original : bool
        Delete original Z-stack files after projection.
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).

    Returns
    -------
    ImageDataset
        New dataset with projected images.
    """
    metadata = ds.metadata

    if "stack" not in metadata.columns:
        raise ValueError("Metadata must contain a 'stack' column for Z-projection")

    # Compute group columns dynamically: all non-data columns except stack
    exclude = set(ds.intensity_colnames) | set(ds.mask_colnames) | {"stack", "directory"}
    group_cols = [c for c in metadata.columns if c not in exclude]
    if not group_cols:
        raise ValueError("No group columns found for Z-projection (all columns excluded)")
    log.info("Z-projection group columns: %s", group_cols)

    root = Path(root_dir) if root_dir else ds.measurement_dir.parent
    proj_dir = root / f"zproject_{method}"
    proj_dir.mkdir(parents=True, exist_ok=True)

    grouped = metadata.groupby(group_cols, sort=False)

    for group_key, group_df in tqdm(grouped, desc="Z-projection", unit="group"):
        if len(group_df) <= 1:
            continue  # no Z-stack to project

        for ch in ds.intensity_colnames:
            paths = [
                Path(row["directory"]) / row[ch]
                for _, row in group_df.iterrows()
                if pd.notna(row[ch])
            ]
            paths = [p for p in paths if p.exists()]
            if not paths:
                continue

            projected = _project_group(paths, method)

            out_name = re.sub(r'_z\d+', '_z0', paths[0].name)
            write_image(proj_dir / out_name, projected)

    if delete_original:
        all_sources = set()
        grouped = metadata.groupby(group_cols, sort=False)
        for _, group_df in grouped:
            if len(group_df) <= 1:
                continue
            for ch in ds.intensity_colnames:
                for _, row in group_df.iterrows():
                    p = Path(row["directory"]) / row[ch]
                    if p.exists():
                        all_sources.add(p)
        for p in all_sources:
            p.unlink()

    return ImageDataset(proj_dir)
