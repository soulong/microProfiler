"""Z-stack projection — collapse the Z (stack) dimension."""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image, write_image
from microProfiler.preprocessing._swap import TempSwap

ProgressCB = Callable[[str, int, int, str], None]


def z_project_single(
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
    inplace: bool = True,
    progress_cb: Optional[ProgressCB] = None,
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
        Delete original Z-stack files after projection (only when not
        inplace).
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).
    inplace : bool
        If True, write projected images into the dataset directory
        (in-place).
    progress_cb : callable, optional
        Progress callback ``fn(step, current, total, message)``.

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

    if inplace:
        target_dir = ds.measurement_dir
        effective_delete = False  # TempSwap handles deletion
    else:
        target_dir = root / f"zproject_{method}"
        target_dir.mkdir(parents=True, exist_ok=True)
        effective_delete = delete_original

    grouped = metadata.groupby(group_cols, sort=False)
    all_groups = list(grouped)
    log.debug("z_project_dataset: method=%s, inplace=%s, groups=%d", method, inplace, len(all_groups))

    all_source_set: set[Path] = set()

    with TempSwap(target_dir, "zproject") as swap:
        for gi, (group_key, group_df) in enumerate(
            tqdm(all_groups, desc="Z-projection", unit="group"),
        ):
            if progress_cb:
                progress_cb("Z-projection", gi, len(all_groups), f"Group {group_key}")
            if len(group_df) <= 1:
                log.warning(
                    "Skipping Z-projection for group %s: only %d slice(s). "
                    "A minimum of 2 Z-slices is required for projection.",
                    group_key, len(group_df),
                )
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

                projected = z_project_single(paths, method)

                out_name = re.sub(r'_z\d+', '_z0', paths[0].name)
                write_image(swap.temp_dir / out_name, projected)

                if inplace or effective_delete:
                    all_source_set.update(paths)

        if inplace:
            swap.mark_originals(list(all_source_set))

    if progress_cb:
        progress_cb("Z-projection", len(all_groups), len(all_groups), "Z-projection complete")

    if effective_delete and not inplace:
        for p in all_source_set:
            if p.exists():
                p.unlink()

    return ImageDataset(target_dir)
