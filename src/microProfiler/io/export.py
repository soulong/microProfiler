"""Export utilities for CellProfiler-compatible CSV and SQLite."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

log = logging.getLogger(__name__)


def write_dataloader(
    metadata: pd.DataFrame,
    image_colnames: List[str],
    mask_colnames: Optional[List[str]],
    out_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Convert metadata to CellProfiler-compatible CSV format.

    Parameters
    ----------
    metadata : pd.DataFrame
        Metadata DataFrame from ``ImageDataset.metadata``.
    image_colnames : list of str
        Column names for intensity images.
    mask_colnames : list of str or None
        Column names for mask images.
    out_path : str or Path, optional
        Output CSV path.  If None, returns DataFrame without writing.

    Returns
    -------
    pd.DataFrame
        Reformatted DataFrame.
    """
    df = metadata.copy()
    log.debug("write_dataloader: %d rows, image_cols=%s, mask_cols=%s", len(metadata), image_colnames, mask_colnames)

    for ch in image_colnames:
        df[f"Image_PathName_{ch}"] = df["directory"]
        df = df.rename(columns={ch: f"Image_FileName_{ch}"})

    if mask_colnames:
        for m in mask_colnames:
            label = m.replace("mask_", "")
            df[f"Image_ObjectsPathName_mask_{label}"] = df["directory"]
            df = df.rename(columns={m: f"Image_ObjectsFileName_mask_{label}"})

    for col in metadata.columns:
        if col not in image_colnames and (not mask_colnames or col not in mask_colnames):
            df = df.rename(columns={col: f"Metadata_{col}"})

    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)

    return df
