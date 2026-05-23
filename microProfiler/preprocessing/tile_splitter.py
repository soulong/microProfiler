"""Tile splitting — split images into non-overlapping tiles.

This is the LAST step in the preprocessing pipeline (when enabled).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

import numpy as np
from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset, UNIFIED_IMAGE_PATTERN
from microProfiler.io.loaders import read_image, write_image
from microProfiler.preprocessing._swap import TempSwap

log = logging.getLogger(__name__)

ProgressCB = Callable[[str, int, int, str], None]


def tile_single(
    img: np.ndarray,
    tile_w: int,
    tile_h: int,
) -> List[Tuple[int, np.ndarray]]:
    """Split a single 2-D image into non-overlapping tiles.

    Parameters
    ----------
    img : np.ndarray
        Input 2-D image.
    tile_w : int
        Tile width in pixels.
    tile_h : int
        Tile height in pixels.

    Returns
    -------
    list of (int, np.ndarray)
        List of ``(tile_index, tile_array)`` tuples.
    """
    h, w = img.shape
    tiles: List[Tuple[int, np.ndarray]] = []
    tile_idx = 0
    for y in range(0, h, tile_h):
        for x in range(0, w, tile_w):
            if y + tile_h <= h and x + tile_w <= w:
                tiles.append((tile_idx, img[y : y + tile_h, x : x + tile_w]))
            tile_idx += 1
    return tiles


def tile_dataset(
    ds: ImageDataset,
    tile_w: int = 1024,
    tile_h: int = 1024,
    delete_original: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
    inplace: bool = True,
    progress_cb: Optional[ProgressCB] = None,
) -> ImageDataset:
    """Split all images in a dataset into tiles.

    Parameters
    ----------
    ds : ImageDataset
        Input dataset.
    tile_w : int
        Tile width in pixels.
    tile_h : int
        Tile height in pixels.
    delete_original : bool
        Delete original files after tiling (only when not inplace).
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).
    inplace : bool
        If True, write tiles into the dataset directory (in-place).

    Returns
    -------
    ImageDataset
        New dataset with tiled images.
    """
    root = Path(root_dir) if root_dir else ds.measurement_dir.parent

    if inplace:
        target_dir = ds.measurement_dir
        effective_delete = False  # TempSwap handles deletion
    else:
        target_dir = root / f"tiles_{tile_w}x{tile_h}"
        target_dir.mkdir(parents=True, exist_ok=True)
        effective_delete = delete_original

    # Validate image size unconditionally
    img_shape = ds.img_shape
    if img_shape is None and not ds.metadata.empty:
        row = ds.metadata.iloc[0]
        img_dir = row["directory"]
        chs = ds.intensity_colnames
        if chs:
            img_path = Path(img_dir) / row[chs[0]]
            if img_path.exists():
                img = read_image(img_path)
                img_shape = img.shape[:2]

    if img_shape is not None and (img_shape[0] < tile_h or img_shape[1] < tile_w):
        raise ValueError(
            f"Images of size {img_shape} are smaller than tile size "
            f"({tile_w}×{tile_h}). All images must be at least as large "
            "as the tile dimensions."
        )

    metadata = ds.metadata
    all_paths = []
    for _, row in metadata.iterrows():
        img_dir = row["directory"]
        for ch in ds.intensity_colnames:
            all_paths.append(Path(img_dir) / row[ch])

    with TempSwap(target_dir, "tile") as swap:
        for i, src in enumerate(tqdm(all_paths, desc="Tiling", unit="img")):
            if progress_cb:
                progress_cb("Tile", i, len(all_paths), f"Image {src.name}")
            if not src.exists():
                continue
            img = read_image(src)
            tiles = tile_single(img, tile_w, tile_h)
            for tile_idx, tile in tiles:
                m = UNIFIED_IMAGE_PATTERN.match(src.name)
                if m is not None:
                    out_name = (
                        f"{m.group('well')}_f{m.group('field')}"
                        f"_z{m.group('stack')}_t{m.group('timepoint')}"
                        f"_ch{m.group('channel')}_tile{tile_idx}.tiff"
                    )
                    write_image(swap.temp_dir / out_name, tile)
            if inplace or effective_delete:
                swap.mark_original(src)

    if progress_cb:
        progress_cb("Tile", len(all_paths), len(all_paths), "Tiling complete")

    if effective_delete and not inplace:
        for src in all_paths:
            if src.exists():
                src.unlink()

    return ImageDataset(target_dir)
