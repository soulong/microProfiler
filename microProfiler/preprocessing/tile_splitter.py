"""Tile splitting — split images into non-overlapping tiles.

This is the LAST step in the preprocessing pipeline (when enabled).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset, UNIFIED_IMAGE_PATTERN
from microProfiler.io.loaders import read_image, write_image
from microProfiler.preprocessing._swap import TempSwap

log = logging.getLogger(__name__)


def _split_single_image(
    src: Path,
    tile_w: int,
    tile_h: int,
    output_dir: Path,
) -> int:
    """Split a single 2-D image into tiles with unified naming.

    Parameters
    ----------
    src : Path
        Source image path.
    tile_w : int
        Tile width in pixels.
    tile_h : int
        Tile height in pixels.
    output_dir : Path
        Directory to save tiles.

    Returns
    -------
    int
        Number of tiles created.
    """
    m = UNIFIED_IMAGE_PATTERN.match(src.name)
    if m is None:
        return 0
    well = m.group("well")
    field = m.group("field")
    stack = m.group("stack")
    timepoint = m.group("timepoint")
    channel = m.group("channel")

    img = read_image(src)
    if img.ndim != 2:
        log.warning("Skipping non-2D image (ndim=%d): %s", img.ndim, src.name)
        return 0

    h, w = img.shape
    tile_idx = 0
    n_kept = 0
    for y in range(0, h, tile_h):
        for x in range(0, w, tile_w):
            if y + tile_h <= h and x + tile_w <= w:
                tile = img[y : y + tile_h, x : x + tile_w]
                out_name = f"{well}_f{field}_z{stack}_t{timepoint}_ch{channel}_tile{tile_idx}.tiff"
                write_image(output_dir / out_name, tile)
                n_kept += 1
            tile_idx += 1

    return n_kept


def tile_dataset(
    ds: ImageDataset,
    tile_w: int = 1024,
    tile_h: int = 1024,
    delete_original: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
    inplace: bool = True,
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
        for src in tqdm(all_paths, desc="Tiling", unit="img"):
            if not src.exists():
                continue
            n = _split_single_image(src, tile_w, tile_h, swap.temp_dir)
            if inplace or effective_delete:
                swap.mark_original(src)
            _ = n  # total count not critical for correctness

    if effective_delete and not inplace:
        for src in all_paths:
            if src.exists():
                src.unlink()

    return ImageDataset(target_dir)
