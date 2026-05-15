"""Tile splitting — split images into non-overlapping tiles.

This is the LAST step in the preprocessing pipeline (when enabled).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from tqdm import tqdm

from microProfiler.io.dataset import ImageDataset, UNIFIED_IMAGE_PATTERN
from microProfiler.io.loaders import read_image, write_image


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
        return 0

    h, w = img.shape
    tile_idx = 0
    for y in range(0, h, tile_h):
        for x in range(0, w, tile_w):
            tile = img[y : y + tile_h, x : x + tile_w]
            out_name = f"{well}_f{field}_z{stack}_t{timepoint}_ch{channel}_tile{tile_idx}.tiff"
            write_image(output_dir / out_name, tile)
            tile_idx += 1

    return tile_idx


def tile_dataset(
    ds: ImageDataset,
    tile_w: int = 1024,
    tile_h: int = 1024,
    delete_original: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
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
    root_dir : str or Path, optional
        Root directory for output (defaults to ``ds.measurement_dir.parent``).

    Returns
    -------
    ImageDataset
        New dataset with tiled images.
    """
    root = Path(root_dir) if root_dir else ds.measurement_dir.parent
    tile_dir = root / f"tiles_{tile_w}x{tile_h}"
    tile_dir.mkdir(parents=True, exist_ok=True)

    metadata = ds.metadata
    all_paths = []
    for _, row in metadata.iterrows():
        img_dir = row["directory"]
        for ch in ds.intensity_colnames:
            all_paths.append(Path(img_dir) / row[ch])

    total_tiles = 0
    for src in tqdm(all_paths, desc="Tiling", unit="img"):
        if not src.exists():
            continue
        n = _split_single_image(src, tile_w, tile_h, tile_dir)
        total_tiles += n

    if delete_original:
        for src in all_paths:
            if src.exists():
                src.unlink()

    return ImageDataset(tile_dir)
