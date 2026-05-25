"""Image-level profiling — whole-image features.

Computes per-channel intensity statistics (mean, sum, percentiles) and
optionally object-area statistics via thresholding.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from skimage.measure import label, regionprops_table
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.database import Database

log = logging.getLogger(__name__)
ProgressCB = Callable[[str, int, int, str], None]


def measure_single_image(
    image_data: np.ndarray,
    channel_names: List[str],
    intensity_channels: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Profile a single image stack at the whole-image level.

    Parameters
    ----------
    image_data : np.ndarray
        Shape ``(Y, X, C)``.
    channel_names : list of str
        Names matching the C axis.
    intensity_channels : list of str, optional
        Subset to profile.  ``None`` = all channels.
    thresholds : dict, optional
        Per-channel thresholds for object detection, e.g.
        ``{"ch1": 500.0}``.

    Returns
    -------
    dict
        Flat dict with ``{metric}_{channel}`` keys.
    """
    if image_data.ndim != 3:
        raise ValueError(f"image_data must be (Y, X, C), got {image_data.shape}")
    if len(channel_names) != image_data.shape[2]:
        raise ValueError(
            f"Got {len(channel_names)} names for {image_data.shape[2]} channels"
        )

    if intensity_channels is None:
        intensity_channels = channel_names
    thresholds = thresholds or {}

    result: Dict[str, Any] = {}

    for ch_name in intensity_channels:
        ch_idx = channel_names.index(ch_name)
        img = image_data[:, :, ch_idx]

        if img.size == 0 or np.all(img == 0):
            result[f"intensity_mean_{ch_name}"] = 0.0
            result[f"intensity_sum_{ch_name}"] = 0.0
            for q in [0.1, 1, 25, 75, 99, 99.9]:
                result[f"intensity_q{q}_{ch_name}"] = 0.0
        else:
            result[f"intensity_mean_{ch_name}"] = float(np.mean(img))
            result[f"intensity_sum_{ch_name}"] = float(np.sum(img))
            for q in [0.1, 1, 25, 75, 99, 99.9]:
                result[f"intensity_q{q}_{ch_name}"] = float(np.percentile(img, q))

        threshold = thresholds.get(ch_name)
        if threshold is not None:
            binary = img >= threshold
            labeled = label(binary)
            if labeled.max() > 0:
                props = regionprops_table(labeled, properties=["area", "label"])
                result[f"shape_area_{ch_name}"] = int(np.sum(props["area"]))
                result[f"shape_n_object_{ch_name}"] = len(props["label"])
                result[f"shape_mean_object_area_{ch_name}"] = float(np.mean(props["area"]))
            else:
                result[f"shape_area_{ch_name}"] = 0
                result[f"shape_n_object_{ch_name}"] = 0
                result[f"shape_mean_object_area_{ch_name}"] = 0.0

    return result


def _process_one_image(
    ds: ImageDataset,
    idx: int,
    channels: List[str],
    thresholds: Optional[Dict[str, float]],
) -> pd.DataFrame:
    """Profile a single image — extracted for parallel execution."""
    image_data, _ = ds.get_imageset(idx)
    row = ds.metadata.iloc[idx]
    excluded = set(ds.intensity_colnames) | set(ds.mask_colnames)
    meta = {k: v for k, v in row.to_dict().items() if k not in excluded}
    measures = measure_single_image(image_data, ds.intensity_colnames, channels, thresholds)
    return pd.DataFrame([{**meta, **measures}])


def _profile_image_worker(args):
    """ProcessPoolExecutor worker — receives only serializable types."""
    image_data, channel_names, channels, thresholds, meta = args
    measures = measure_single_image(image_data, channel_names, channels, thresholds)
    return pd.DataFrame([{**meta, **measures}])


def profile_images(
    ds: ImageDataset,
    channels: Optional[List[str]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    db_path: Union[str, Path, None] = None,
    table_name: str = "image",
    progress_cb: Optional[ProgressCB] = None,
    n_workers: int = 1,
) -> Optional[pd.DataFrame]:
    """Profile all images in a dataset at the whole-image level.

    Parameters
    ----------
    ds : ImageDataset
        Dataset to profile.
    channels : list of str, optional
        Channels to profile.  ``None`` = all.
    thresholds : dict, optional
        Per-channel thresholds.
    db_path : str or Path, optional
        SQLite output path.  ``None`` returns a DataFrame.
    table_name : str
        Table name for DB output.
    n_workers : int
        Number of worker threads (1 = sequential).

    Returns
    -------
    pd.DataFrame or None
        Results DataFrame if ``db_path`` is ``None``.
    """
    channels = channels or ds.intensity_colnames
    log.debug(
        "profile_images: channels=%s, thresholds=%s, db=%s, table=%s, count=%d, workers=%d",
        channels, thresholds, db_path, table_name, len(ds), n_workers,
    )
    results: List[pd.DataFrame] = []
    n_total = len(ds)

    if n_workers == 1:
        for idx in tqdm(range(n_total), desc="Image profiling", unit="img"):
            if progress_cb:
                progress_cb("Profile Image", idx, n_total, f"Row {idx}")
            results.append(_process_one_image(ds, idx, channels, thresholds))
    else:
        # Pre-read all image data (serializable) for ProcessPoolExecutor
        tasks = []
        for idx in range(n_total):
            image_data, _ = ds.get_imageset(idx)
            row = ds.metadata.iloc[idx]
            excluded = set(ds.intensity_colnames) | set(ds.mask_colnames)
            meta = {k: v for k, v in row.to_dict().items() if k not in excluded}
            tasks.append((image_data, ds.intensity_colnames, channels, thresholds, meta))

        completed = 0
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = {
                executor.submit(_profile_image_worker, t): idx
                for idx, t in enumerate(tasks)
            }
            for future in tqdm(as_completed(futures), total=n_total, desc="Image profiling", unit="img"):
                idx = futures[future]
                try:
                    results.append(future.result())
                    completed += 1
                    if progress_cb:
                        progress_cb("Profile Image", completed, n_total, f"Row {idx}")
                except Exception:
                    log.exception("Image profiling failed for row %d — skipping", idx)
                    completed += 1

    if not results:
        return None

    combined = pd.concat(results, ignore_index=True)

    if db_path:
        db = Database(db_path)
        try:
            db.save_table(combined, table_name, if_exists="append")
        finally:
            db.close()
        return None

    return combined
