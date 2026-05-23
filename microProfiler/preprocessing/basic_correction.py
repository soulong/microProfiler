"""BaSiC shading correction — thin wrapper around the basic/ folder.

The actual BaSiC algorithm lives in ``microProfiler.preprocessing.basic``
(copied verbatim from the original image_profiler).
"""

from __future__ import annotations

import logging
import pickle
import random
from pathlib import Path
from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import read_image, write_image
from microProfiler.preprocessing._swap import TempSwap
from microProfiler.preprocessing.basic.basic import BaSiC

ProgressCB = Callable[[str, int, int, str], None]


def basic_fit(
    image_paths: List[Path],
    n_image: int = 50,
    enable_darkfield: bool = False,
    working_size: int = 64,
) -> BaSiC:
    """Fit BaSiC model on a set of images.

    Parameters
    ----------
    image_paths : list of Path
        Image file paths for fitting.
    n_image : int
        Max number of images to use.
    enable_darkfield : bool
        Enable darkfield estimation.
    working_size : int
        Working size for the BaSiC model.

    Returns
    -------
    BaSiC
        Fitted BaSiC model.
    """
    if len(image_paths) > n_image:
        image_paths = random.sample(image_paths, k=n_image)

    imgs = [read_image(p) for p in image_paths]
    shapes = {img.shape for img in imgs}
    if len(shapes) > 1:
        raise ValueError(
            f"BaSiC fit requires uniform image shapes, got {len(shapes)} different shapes: {shapes}"
        )
    imgs = np.stack(imgs)
    basic = BaSiC(
        get_darkfield=enable_darkfield,
        smoothness_flatfield=1,
        smoothness_darkfield=1,
        working_size=working_size,
        max_workers=8,
    )
    basic.fit(imgs)
    return basic


def basic_transform(
    image_paths: List[Path],
    model: BaSiC,
    target_dir: Path,
) -> int:
    """Apply BaSiC model to correct images and save to target_dir.

    Parameters
    ----------
    image_paths : list of Path
        Image file paths to correct.
    model : BaSiC
        Fitted BaSiC model.
    target_dir : Path
        Directory to write corrected images.

    Returns
    -------
    int
        Number of images written.
    """
    imgs = np.stack([read_image(p) for p in image_paths])
    dtype_in = imgs.dtype
    corrected = model.transform(imgs)

    if dtype_in == np.uint16:
        corrected = np.clip(corrected, 0, 65535)
    elif dtype_in == np.uint8:
        corrected = np.clip(corrected, 0, 255)
    corrected = corrected.astype(dtype_in)

    n = 0
    for src, corr in zip(image_paths, corrected):
        dst = target_dir / src.name
        write_image(dst, corr)
        n += 1
    return n


def fit_models(
    ds: ImageDataset,
    channels: Optional[List[str]] = None,
    n_image: int = 50,
    working_size: int = 64,
    enable_darkfield: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
    progress_cb: Optional[ProgressCB] = None,
) -> Path:
    """Fit BaSiC models for specified channels.

    Parameters
    ----------
    ds : ImageDataset
        Dataset to fit from.
    channels : list of str, optional
        Channels to fit.  Defaults to all intensity channels.
    n_image : int
        Number of images to use for fitting.
    working_size : int
        Working size for BaSiC model.
    enable_darkfield : bool
        Enable darkfield estimation.
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).

    Returns
    -------
    Path
        Directory containing the saved model files.
    """
    channels = channels or ds.intensity_colnames
    metadata = ds.metadata
    root = Path(root_dir) if root_dir else ds.measurement_dir.parent

    model_dir = root / "BaSiC_model"
    model_dir.mkdir(parents=True, exist_ok=True)

    for ci, chan in enumerate(channels):
        if progress_cb:
            progress_cb("BaSiC Fit", ci, len(channels), f"Fitting channel {chan}")
        logging.getLogger("microProfiler").info("BaSiC fitting channel %s (%d/%d)", chan, ci + 1, len(channels))
        paths = [
            Path(metadata.iloc[i]["directory"]) / metadata.iloc[i][chan]
            for i in range(len(metadata))
        ]
        paths = [p for p in paths if p.exists()]
        if not paths:
            continue

        model = basic_fit(paths, n_image, enable_darkfield, working_size)
        logging.getLogger("microProfiler").info("BaSiC finished fitting channel %s", chan)

        with open(model_dir / f"model_{chan}.pkl", "wb") as f:
            pickle.dump(model, f)

        write_image(
            model_dir / f"model_{chan}_flatfield.tiff",
            model.flatfield.astype(np.float32),
        )
        if enable_darkfield:
            write_image(
                model_dir / f"model_{chan}_darkfield.tiff",
                model.darkfield.astype(np.float32),
            )

    if progress_cb:
        progress_cb("BaSiC Fit", len(channels), len(channels), "Fit complete")
    return model_dir


def transform_images(
    ds: ImageDataset,
    channels: Optional[List[str]] = None,
    root_dir: Optional[Union[str, Path]] = None,
    inplace: bool = True,
    progress_cb: Optional[ProgressCB] = None,
) -> ImageDataset:
    """Apply fitted BaSiC models to correct images.

    Parameters
    ----------
    ds : ImageDataset
        Dataset with saved BaSiC models in ``BaSiC_model/`` subdirectory.
    channels : list of str, optional
        Channels to transform.  Defaults to all intensity channels.
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).
    inplace : bool
        If True, write corrected images into the dataset directory (in-place).

    Returns
    -------
    ImageDataset
        New dataset with corrected images.
    """
    channels = channels or ds.intensity_colnames
    metadata = ds.metadata
    root = Path(root_dir) if root_dir else ds.measurement_dir.parent

    if inplace:
        target_dir = ds.measurement_dir
    else:
        target_dir = root / "BaSiC_corrected"
        target_dir.mkdir(parents=True, exist_ok=True)

    total_items = sum(
        1 for chan in channels
        if (root / "BaSiC_model" / f"model_{chan}.pkl").exists()
    )
    item_idx = 0

    with TempSwap(target_dir, "basic") as swap:
        for chan in channels:
            model_path = root / "BaSiC_model" / f"model_{chan}.pkl"
            if not model_path.exists():
                continue

            if progress_cb:
                progress_cb("BaSiC Transform", item_idx, total_items, f"Channel {chan}")
            logging.getLogger("microProfiler").info("BaSiC transforming channel %s", chan)
            item_idx += 1

            with open(model_path, "rb") as f:
                model = pickle.load(f)

            paths = [
                Path(metadata.iloc[i]["directory"]) / metadata.iloc[i][chan]
                for i in range(len(metadata))
            ]
            paths = [p for p in paths if p.exists()]

            for batch_start in range(0, len(paths), 50):
                batch = paths[batch_start : batch_start + 50]
                basic_transform(batch, model, swap.temp_dir)

            if inplace:
                swap.mark_originals(paths)
            logging.getLogger("microProfiler").info("BaSiC finished transforming channel %s", chan)

    if progress_cb:
        progress_cb("BaSiC Transform", total_items, total_items, "Transform complete")

    return ImageDataset(target_dir)


def _validate_shapes(ds: ImageDataset, n_image: int = 50) -> None:
    """Pre-validate that all channel images have consistent shapes.

    Raises ``ValueError`` if sampled images across channels have
    differing dimensions.
    """
    channels = ds.intensity_colnames
    metadata = ds.metadata
    sample_paths: List[Path] = []
    for chan in channels:
        paths = [
            Path(metadata.iloc[i]["directory"]) / metadata.iloc[i][chan]
            for i in range(len(metadata))
            if pd.notna(metadata.iloc[i].get(chan))
        ]
        paths = [p for p in paths if p.exists()]
        if paths:
            sample_paths.extend(paths[:n_image])
    if sample_paths:
        first_shape = read_image(sample_paths[0]).shape
        for p in sample_paths[1:]:
            img = read_image(p)
            if img.shape != first_shape:
                raise ValueError(
                    f"BaSiC requires uniform image shapes across all channels. "
                    f"Got {first_shape} and {img.shape} for {p.name}. "
                    "This is checked before any processing begins."
                )


def apply_basic(
    ds: ImageDataset,
    mode: str = "fit-transform",
    n_image: int = 50,
    working_size: int = 64,
    enable_darkfield: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
    inplace: bool = True,
    progress_cb: Optional[ProgressCB] = None,
) -> ImageDataset:
    """End-to-end BaSiC correction: fit, transform, or both.

    Parameters
    ----------
    ds : ImageDataset
        Input dataset.
    mode : str
        ``"fit"``, ``"transform"``, or ``"fit-transform"``.
    n_image : int
        Number of images for fitting.
    working_size : int
        BaSiC working size.
    enable_darkfield : bool
        Enable darkfield estimation.
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).
    inplace : bool
        If True, write corrected images into the dataset directory (in-place).

    Returns
    -------
    ImageDataset
        Dataset with corrected images (or the original if only fitting).
    """
    if mode in ("fit", "fit-transform"):
        # Fail-fast: validate image shape consistency before any I/O
        _validate_shapes(ds, n_image)
        fit_models(
            ds,
            n_image=n_image,
            working_size=working_size,
            enable_darkfield=enable_darkfield,
            root_dir=root_dir,
            progress_cb=progress_cb,
        )

    if mode in ("transform", "fit-transform"):
        return transform_images(ds, root_dir=root_dir, inplace=inplace, progress_cb=progress_cb)

    return ds
