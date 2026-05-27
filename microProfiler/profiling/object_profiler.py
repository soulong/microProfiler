"""Object-level profiling — shape, intensity, and texture per labeled object."""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from scipy.ndimage import find_objects
from skimage.measure import regionprops_table
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.database import Database
from microProfiler.profiling.extras import (
    make_glcm,
    make_granularity,
    make_radial_distribution,
    measure_channel_correlation,
)

log = logging.getLogger(__name__)
ProgressCB = Callable[[str, int, int, str], None]

# ── Shape properties ─────────────────────────────────────────────────────
_SHAPE_PROPS: Tuple[str, ...] = (
    "label",
    "area",
    "eccentricity",
    "equivalent_diameter_area",
    "extent",
    "feret_diameter_max",
    "major_axis_length",
    "minor_axis_length",
    "perimeter",
    "solidity",
)

_SHAPE_RENAMES: Dict[str, str] = {
    "area": "shape_area",
    "eccentricity": "shape_eccentricity",
    "equivalent_diameter_area": "shape_equivalent_diameter_area",
    "extent": "shape_extent",
    "feret_diameter_max": "shape_feret_diameter_max",
    "major_axis_length": "shape_major_axis_length",
    "minor_axis_length": "shape_minor_axis_length",
    "perimeter": "shape_perimeter",
    "solidity": "shape_solidity",
}


# ── Helpers ──────────────────────────────────────────────────────────────

def _named(fn, name: str):
    fn.__name__ = name
    fn.__qualname__ = name
    return fn


def _resolve_indices(
    requested: Optional[Sequence[str]],
    channel_names: List[str],
    param_name: str,
) -> List[int]:
    if not requested:
        return []
    unknown = [c for c in requested if c not in channel_names]
    if unknown:
        raise ValueError(
            f"'{param_name}' unknown channels: {unknown}. "
            f"Available: {channel_names}"
        )
    return [channel_names.index(c) for c in requested]


def _intensity_fns(ch_name: str) -> list:
    def _mean(mask, intensity):
        p = intensity[mask.astype(bool)]
        return float(p.mean()) if p.size > 0 else 0.0

    def _median(mask, intensity):
        p = intensity[mask.astype(bool)]
        return float(np.median(p)) if p.size > 0 else 0.0

    def _std(mask, intensity):
        p = intensity[mask.astype(bool)]
        return float(p.std()) if p.size > 0 else 0.0

    def _sum(mask, intensity):
        p = intensity[mask.astype(bool)]
        return float(p.sum()) if p.size > 0 else 0.0

    return [
        _named(_mean, f"intensity_mean_{ch_name}"),
        _named(_median, f"intensity_median_{ch_name}"),
        _named(_std, f"intensity_std_{ch_name}"),
        _named(_sum, f"intensity_sum_{ch_name}"),
    ]



def _relate_masks(
    child: np.ndarray,
    parent: np.ndarray,
) -> Dict[int, int]:
    """Assign each child object to the parent containing most of its pixels."""
    if child.shape != parent.shape:
        raise ValueError("child and parent mask shapes must match")
    child_labels = np.unique(child)
    child_labels = child_labels[child_labels != 0]
    mapping: Dict[int, int] = {}
    slices = find_objects(child)

    for lbl in child_labels:
        sl = slices[lbl - 1]
        if sl is None:
            mapping[int(lbl)] = 0
            continue
        roi_child = child[sl] == lbl
        roi_parent = parent[sl]
        vals = roi_parent[roi_child]
        vals = vals[vals != 0]
        if vals.size == 0:
            mapping[int(lbl)] = 0
        else:
            unique, counts = np.unique(vals, return_counts=True)
            mapping[int(lbl)] = int(unique[np.argmax(counts)])
    return mapping


def _is_boundary(mask: np.ndarray) -> Dict[int, bool]:
    """Flag objects whose bounding box touches the image edge.

    An object whose bounding box touches the image boundary is truncated
    and its full morphology is not captured.
    """
    H, W = mask.shape
    labels = np.unique(mask)
    labels = labels[labels != 0]
    result: Dict[int, bool] = {}
    slices = find_objects(mask)

    for lbl in labels:
        sl = slices[lbl - 1]
        if sl is None:
            result[int(lbl)] = False
        else:
            touches = (
                sl[0].start == 0 or sl[0].stop == H
                or sl[1].start == 0 or sl[1].stop == W
            )
            result[int(lbl)] = touches

    return result


def _run_per_channel_regionprops(
    mask: np.ndarray,
    img: np.ndarray,
    channel_names: List[str],
    groups: Dict[int, list],
) -> pd.DataFrame:
    """Run regionprops_table once per channel slice and merge on label.

    Parameters
    ----------
    mask : np.ndarray
        Labeled segmentation mask of shape ``(H, W)``.
    img : np.ndarray
        Multichannel image of shape ``(H, W, C)``.
    channel_names : list of str
        Names matching the C axis.
    groups : dict of int → list
        Map from channel index to list of extra property callables.

    Returns
    -------
    pd.DataFrame
        Merged regionprops with one row per label.
    """
    dfs: List[pd.DataFrame] = []
    for ch_idx, fns in groups.items():
        if not fns:
            continue
        props = regionprops_table(
            mask, img[..., ch_idx],
            properties=["label"],
            extra_properties=fns,
        )
        dfs.append(pd.DataFrame(props))
    if not dfs:
        return pd.DataFrame()
    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on="label", how="outer")
    return result


# ── Public API ───────────────────────────────────────────────────────────

def measure_objects(
    mask: np.ndarray,
    img: np.ndarray,
    channel_names: List[str],
    metadata_row: Optional[Dict[str, Any]] = None,
    parent_mask: Optional[np.ndarray] = None,
    parent_mask_name: str = "Parent",
    intensity_channels: Optional[Sequence[str]] = None,
    radial_channels: Optional[Sequence[str]] = None,
    radial_kwargs: Optional[Dict] = None,
    granularity_channels: Optional[Sequence[str]] = None,
    granularity_kwargs: Optional[Dict] = None,
    glcm_channels: Optional[Sequence[str]] = None,
    glcm_kwargs: Optional[Dict] = None,
    correlation_pairs: Optional[Sequence[Tuple[str, str]]] = None,
) -> pd.DataFrame:
    """Measure shape, intensity, and texture for every labeled object.

    Parameters
    ----------
    mask : (Y, X) int
        Labeled segmentation mask.
    img : (Y, X, C) numeric
        Multichannel intensity image.
    channel_names : list of str
        Names matching the C axis.
    metadata_row : dict, optional
        Prepended to every row.
    parent_mask : (Y, X) int, optional
        Parent mask for child→parent assignment.
    parent_mask_name : str
        Column name suffix for parent.
    intensity_channels : list of str, optional
        Channels for mean/median/std/sum.  ``None`` = all.
    radial_channels : list of str, optional
        Channels for radial distribution.
    radial_kwargs : dict, optional
        ``{"nbins": int}``.
    granularity_channels : list of str, optional
        Channels for granularity spectrum.
    granularity_kwargs : dict, optional
        ``{"radii": ..., "subsample_size": ...}``.
    glcm_channels : list of str, optional
        Channels for GLCM texture.
    glcm_kwargs : dict, optional
        ``{"distances": ..., "levels": ...}``.
    correlation_pairs : list of (str, str), optional
        Channel pairs for Pearson correlation.

    Returns
    -------
    pd.DataFrame
        One row per object.
    """
    if img.ndim != 3:
        raise ValueError(f"img must be (Y, X, C), got {img.shape}")
    if mask.shape != img.shape[:2]:
        raise ValueError("mask and img spatial shapes must match")
    if len(channel_names) != img.shape[2]:
        raise ValueError(f"Got {len(channel_names)} names for {img.shape[2]} channels")

    if intensity_channels is None:
        intensity_channels = list(channel_names)

    intensity_idx = _resolve_indices(intensity_channels, channel_names, "intensity_channels")
    radial_idx = _resolve_indices(radial_channels, channel_names, "radial_channels")
    granularity_idx = _resolve_indices(granularity_channels, channel_names, "granularity_channels")
    glcm_idx = _resolve_indices(glcm_channels, channel_names, "glcm_channels")

    corr_pairs: List[Tuple[int, int]] = []
    if correlation_pairs:
        for a, b in correlation_pairs:
            if a not in channel_names or b not in channel_names:
                raise ValueError(f"Correlation pair ({a}, {b}) not in {channel_names}")
            corr_pairs.append((channel_names.index(a), channel_names.index(b)))

    # Step 1: Shape
    shape_props = regionprops_table(mask, properties=_SHAPE_PROPS)
    df = pd.DataFrame(shape_props).rename(
        columns={k: v for k, v in _SHAPE_RENAMES.items() if k in shape_props}
    )

    # Step 2: Boundary
    boundary_map = _is_boundary(mask)
    df["is_boundary"] = df["label"].map(boundary_map)

    # Step 3: Parent relationship
    if parent_mask is not None:
        parent_map = _relate_masks(mask, parent_mask)
        df[f"parent_{parent_mask_name}"] = df["label"].map(parent_map).fillna(0).astype(int)

    # Step 4: Build per-channel extra property groups
    groups: Dict[int, list] = {}

    def _add(ch_idx: int, fns: list) -> None:
        groups.setdefault(ch_idx, []).extend(fns)

    for idx in intensity_idx:
        _add(idx, _intensity_fns(channel_names[idx]))

    rd_kw = dict(radial_kwargs or {})
    for idx in radial_idx:
        fns = make_radial_distribution(ch_name=channel_names[idx], **rd_kw)
        _add(idx, fns)

    gr_kw = dict(granularity_kwargs or {})
    for idx in granularity_idx:
        fns = make_granularity(ch_name=channel_names[idx], **gr_kw)
        _add(idx, fns)

    gl_kw = dict(glcm_kwargs or {})
    for idx in glcm_idx:
        fns = make_glcm(ch_name=channel_names[idx], **gl_kw)
        _add(idx, fns)

    # Step 5: Per-channel regionprops
    if groups:
        extra = _run_per_channel_regionprops(mask, img, channel_names, groups)
        df = df.merge(extra, on="label", how="left")

    # Step 6: Pearson correlation
    if corr_pairs:
        corr_dict = measure_channel_correlation(mask, img, corr_pairs)
        renamed: Dict[str, Any] = {"label": corr_dict["label"]}
        for a, b in corr_pairs:
            old_key = f"correlation_pearson_ch{a}_ch{b}"
            new_key = f"correlation_pearson_{channel_names[a]}_{channel_names[b]}"
            renamed[new_key] = corr_dict[old_key]
        df = df.merge(pd.DataFrame(renamed), on="label", how="left")

    # Step 7: Prepend metadata
    if metadata_row:
        df = pd.concat([pd.DataFrame([metadata_row] * len(df)), df], axis=1)

    # Step 8: Reorder — attributes first, then label/is_boundary/parent, then measurements
    cols = df.columns.tolist()
    meta_cols = list(metadata_row.keys()) if metadata_row else []
    priority_labels = ["label", "is_boundary"] + sorted(c for c in cols if c.startswith("parent_"))
    priority = meta_cols + [c for c in priority_labels if c not in meta_cols]
    rest = [c for c in cols if c not in priority]
    df = df[priority + rest]

    return df


def _process_one_object(
    ds: ImageDataset,
    idx: int,
    mask_name: str,
    parent_mask_name: Optional[str],
    intensity_channels: Optional[List[str]],
    correlation_pairs: Optional[List[Tuple[str, str]]],
    measure_kwargs: Dict[str, Any],
) -> Optional[pd.DataFrame]:
    """Profile objects in a single image — extracted for parallel execution."""
    row = ds.metadata.iloc[idx]
    meta = {
        k: v for k, v in row.to_dict().items()
        if k not in ds.intensity_colnames and k not in ds.mask_colnames
    }
    image_data, mask_data = ds.get_imageset(idx)
    mask = mask_data.get(mask_name)
    if mask is None:
        return None
    parent_mask = None
    if parent_mask_name is not None:
        parent_mask = mask_data.get(parent_mask_name)
    return measure_objects(
        mask=mask,
        img=image_data,
        channel_names=ds.intensity_colnames,
        metadata_row=meta,
        parent_mask=parent_mask,
        parent_mask_name=parent_mask_name or "Parent",
        intensity_channels=intensity_channels,
        correlation_pairs=correlation_pairs,
        **measure_kwargs,
    )


def _profile_object_worker(args):
    """ProcessPoolExecutor worker — receives only serializable types."""
    (image_data, mask_data, channel_names, meta, mask_name,
     parent_mask_name, intensity_channels, correlation_pairs, measure_kwargs) = args

    mask = mask_data.get(mask_name)
    if mask is None:
        return None
    parent_mask = None
    if parent_mask_name is not None:
        parent_mask = mask_data.get(parent_mask_name)
    return measure_objects(
        mask=mask,
        img=image_data,
        channel_names=channel_names,
        metadata_row=meta,
        parent_mask=parent_mask,
        parent_mask_name=parent_mask_name or "Parent",
        intensity_channels=intensity_channels,
        correlation_pairs=correlation_pairs,
        **measure_kwargs,
    )


def profile_objects(
    ds: ImageDataset,
    mask_name: str,
    parent_mask_name: Optional[str] = None,
    intensity_channels: Optional[List[str]] = None,
    radial_channels: Optional[List[str]] = None,
    radial_n_bins: int = 5,
    granularity_channels: Optional[List[str]] = None,
    glcm_channels: Optional[List[str]] = None,
    glcm_distances: Optional[List[int]] = None,
    correlation_pairs: Optional[List[Tuple[str, str]]] = None,
    db_path: Union[str, Path, None] = None,
    table_name: Optional[str] = None,
    progress_cb: Optional[ProgressCB] = None,
    n_workers: int = 1,
    **extra_kwargs,
) -> Optional[pd.DataFrame]:
    """Profile all objects in a dataset for a given mask.

    Iterates over every image in the dataset, loads the image and mask pair,
    runs ``measure_objects()``, and aggregates results. Writes to SQLite if
    ``db_path`` is provided, otherwise returns a DataFrame.

    Parameters
    ----------
    ds : ImageDataset
        Dataset containing intensity images and mask files for ``mask_name``.
    mask_name : str
        Mask to use for object measurements (e.g. ``"cell"``).
    parent_mask_name : str, optional
        Parent mask for hierarchical child-to-parent assignment.
    intensity_channels : list of str, optional
        Channels for mean, median, std, and sum intensity measurements.
        Defaults to all intensity channels.
    radial_channels : list of str, optional
        Channels for radial distribution measurement.
    radial_n_bins : int
        Number of radial bins. Default is 5.
    granularity_channels : list of str, optional
        Channels for granularity spectrum measurement.
    glcm_channels : list of str, optional
        Channels for GLCM texture measurement.
    glcm_distances : list of int, optional
        GLCM pixel distances. Defaults to ``[1, 2, 3]``.
    correlation_pairs : list of (str, str), optional
        Channel pairs for Pearson correlation.
    db_path : str or Path, optional
        SQLite output path. ``None`` returns a DataFrame instead.
    table_name : str, optional
        DB table name. Defaults to ``mask_name``.
    progress_cb : callable or None, optional
        Optional callback ``(step_name, current, total, message)``
        for GUI progress tracking.
    n_workers : int
        Number of worker processes (1 = sequential).
    **extra_kwargs : dict, optional
        Extra keyword arguments forwarded to ``measure_objects()``.
        Use to override ``granularity_kwargs``, ``glcm_kwargs``,
        ``radial_kwargs``, etc.

    Returns
    -------
    pd.DataFrame or None
        Combined object measurements across all images, or ``None``
        if results were written to database via ``db_path``.
    """
    table_name = table_name or mask_name
    log.debug(
        "profile_objects: mask=%s, parent=%s, intensity_channels=%s, db=%s, table=%s, count=%d, workers=%d",
        mask_name, parent_mask_name, intensity_channels, db_path, table_name, len(ds), n_workers,
    )

    # ── Pre-build measure_kwargs (constant across all images) ──
    measure_kwargs: Dict[str, Any] = {}

    if radial_channels is not None:
        measure_kwargs["radial_channels"] = radial_channels
        measure_kwargs["radial_kwargs"] = {"nbins": radial_n_bins}

    if granularity_channels is not None:
        measure_kwargs["granularity_channels"] = granularity_channels
        measure_kwargs["granularity_kwargs"] = {
            "radii": [1, 3, 6, 8, 12],
            "subsample_size": 1.0,
        }

    if glcm_channels is not None:
        measure_kwargs["glcm_channels"] = glcm_channels
        measure_kwargs["glcm_kwargs"] = {
            "distances": glcm_distances or [1, 2, 3],
        }

    for k, v in extra_kwargs.items():
        if k in measure_kwargs and isinstance(measure_kwargs[k], dict) and isinstance(v, dict):
            measure_kwargs[k].update(v)
        else:
            measure_kwargs[k] = v

    BATCH = 100
    results: List[pd.DataFrame] = []
    n_total = len(ds)
    db = Database(db_path) if db_path else None
    first_write = True
    completed = 0

    def _flush_batch(batch, first):
        if not batch:
            return first
        combined = pd.concat(batch, ignore_index=True)
        if db is not None:
            db.save_table(combined, table_name, if_exists="replace" if first else "append")
            return False
        results.extend(batch)
        return first

    try:
        if n_workers == 1:
            batch: List[pd.DataFrame] = []
            for idx in tqdm(range(n_total), desc=f"Profiling {mask_name}", unit="img"):
                if progress_cb:
                    progress_cb(f"Profile {mask_name}", idx, n_total, "")
                result = _process_one_object(
                    ds, idx, mask_name, parent_mask_name,
                    intensity_channels, correlation_pairs, measure_kwargs,
                )
                if result is not None:
                    batch.append(result)
                    completed += 1
                    if len(batch) >= BATCH:
                        first_write = _flush_batch(batch, first_write)
                        batch = []
            first_write = _flush_batch(batch, first_write)
        else:
            # Process in chunks to avoid pre-loading all images into RAM
            for chunk_start in range(0, n_total, BATCH):
                chunk_end = min(chunk_start + BATCH, n_total)
                tasks = []
                for idx in range(chunk_start, chunk_end):
                    row = ds.metadata.iloc[idx]
                    meta = {
                        k: v for k, v in row.to_dict().items()
                        if k not in ds.intensity_colnames and k not in ds.mask_colnames
                    }
                    image_data, mask_data = ds.get_imageset(idx)
                    tasks.append((
                        image_data, mask_data, ds.intensity_colnames, meta,
                        mask_name, parent_mask_name, intensity_channels,
                        correlation_pairs, measure_kwargs,
                    ))

                with ProcessPoolExecutor(max_workers=n_workers) as executor:
                    futures = {
                        executor.submit(_profile_object_worker, t): idx
                        for idx, t in enumerate(tasks)
                    }
                    chunk_batch: List[pd.DataFrame] = []
                    for future in tqdm(as_completed(futures), total=len(tasks),
                                       desc=f"Profiling {mask_name}", unit="img", leave=False):
                        task_idx = futures[future]
                        try:
                            result = future.result()
                            if result is not None:
                                chunk_batch.append(result)
                            completed += 1
                            if progress_cb:
                                progress_cb(f"Profile {mask_name}", completed, n_total, "")
                        except Exception:
                            log.exception("Object profiling failed for row %d — skipping", chunk_start + task_idx)
                            completed += 1
                    first_write = _flush_batch(chunk_batch, first_write)
    finally:
        if db is not None:
            db.close()

    if not results:
        return None

    return pd.concat(results, ignore_index=True)
