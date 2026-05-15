"""Vendor-specific converters that produce unified file naming.

Unified filename pattern (strict):
    {well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff

Supported vendors:
    - operetta:  r{row}c{col}f{field}p{stack}-ch{channel}sk{timepoint}fk1fl1.tiff
    - mica:      {row}/{col}/Pos{field}.tif  →  {well}_f{field}_z1_t1_ch1.tiff
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
from scipy.ndimage import zoom as ndi_zoom

from microProfiler.io.loaders import read_image, write_image

log = logging.getLogger(__name__)

# ── Operetta pattern ─────────────────────────────────────────────────────
OPERETTA_PATTERN = re.compile(
    r"r(?P<row>\d+)c(?P<column>\d+)f(?P<field>\d+)p(?P<stack>\d+)-ch(?P<channel>\d+)"
    r"sk(?P<timepoint>\d+)fk1fl1\.tiff"
)

# ── MICA patterns ────────────────────────────────────────────────────────
MICA_POS_PATTERN = re.compile(r"Pos(\d+)\.(tif|tiff|lof)$", re.IGNORECASE)


def _build_unified_name(
    well: str,
    field: int,
    stack: int = 0,
    timepoint: int = 0,
    channel: int = 0,
) -> str:
    """Build a unified filename from its components.

    Pattern: ``{well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff``

    Parameters
    ----------
    well : str
        Well identifier (e.g. ``"A1"``).
    field : int
        Field index.
    stack : int
        Stack index.
    timepoint : int
        Timepoint index.
    channel : int
        Channel index.

    Returns
    -------
    str
        Unified filename.
    """
    return f"{well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff"


def _resize_if_needed(img: np.ndarray, resize_factor: float) -> np.ndarray:
    """Resize a 2-D image if factor != 1.0, otherwise return as-is."""
    if resize_factor == 1.0:
        return img
    h, w = img.shape[:2]
    target = (int(round(h * resize_factor)), int(round(w * resize_factor)))
    zoom = (target[0] / h, target[1] / w)
    return ndi_zoom(img, zoom, order=1).astype(img.dtype)


def _convert_operetta_file(
    src: Path,
    match: re.Match,
    output_dir: Path,
    resize_factor: float = 1.0,
) -> Optional[Path]:
    """Convert a single Operetta-format file to unified naming.

    Parameters
    ----------
    src : Path
        Source image path.
    match : re.Match
        Regex match from ``OPERETTA_PATTERN``.
    output_dir : Path
        Target directory for the converted file.
    resize_factor : float
        Resize scale factor (1.0 = no resize).

    Returns
    -------
    Path or None
        Path to the converted file, or ``None`` if skipped.
    """
    row = match.group("row")
    col = match.group("column")
    raw_well = f"{chr(64 + int(row))}{str(int(col))}"  # 1→A, 2→B, etc.
    field = int(match.group("field"))
    stack = int(match.group("stack"))
    channel = int(match.group("channel"))
    timepoint = int(match.group("timepoint"))

    out_name = _build_unified_name(
        well=raw_well, field=field, stack=stack, timepoint=timepoint, channel=channel,
    )
    dst = output_dir / out_name
    if dst.exists():
        return dst  # already converted

    img = read_image(src)
    img = _resize_if_needed(img, resize_factor)
    write_image(dst, img)
    return dst


def _find_mica_root(path: Path, _max_depth: int = 10) -> Path:
    """Auto-detect MICA root directory by walking up the tree.

    MICA structure: ``{row}/{col}/PosNNN.ext`` where row directories are
    single letters (``A``, ``B``, etc.).  Walks up parent directories
    until a directory with single-letter subdirectories is found.

    Parameters
    ----------
    path : Path
        Path to a directory within the MICA tree.
    _max_depth : int
        Maximum levels to walk up (prevents infinite loops).

    Returns
    -------
    Path
        The detected root directory.
    """
    current = path
    for _ in range(_max_depth):
        if current.is_dir():
            subdirs = [
                x.name for x in current.iterdir()
                if x.is_dir() and x.name != "Metadata"
            ]
            row_dirs = [s for s in subdirs if len(s) == 1 and s.isalpha()]
            if row_dirs:
                return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return path


def _convert_mica_file(
    src: Path,
    match: re.Match,
    output_dir: Path,
    row_letter: str,
    col_num: str,
    resize_factor: float = 1.0,
) -> List[Path]:
    """Convert a single MICA file to unified naming.

    Parameters
    ----------
    src : Path
        Source image path.
    match : re.Match
        Regex match from ``MICA_POS_PATTERN``.
    output_dir : Path
        Target directory for converted files.
    row_letter : str
        Row letter (e.g. ``"A"``, ``"B"``).
    col_num : str
        Column number (e.g. ``"1"``, ``"2"``).
    resize_factor : float
        Resize scale factor (1.0 = no resize).

    Returns
    -------
    list of Path
        One path per channel.  Single-channel TIFFs produce one file (ch1);
        multi-channel TIFFs are split into ch1..chN.
    """
    ext = match.group(2).lower()
    if ext == "lof":
        raise NotImplementedError(
            "MICA .lof conversion requires the 'liffile' package which is not "
            "included in microProfiler.  Convert .lof files to .tif manually first."
        )

    field = int(match.group(1))
    well = f"{row_letter}{str(int(col_num))}"
    img = read_image(src)

    if img.ndim == 2:
        channel_count = 1
    elif img.ndim == 3:
        channel_count = img.shape[2]
    else:
        raise ValueError(f"Unexpected image dimensions: {img.ndim}")

    results: List[Path] = []
    for c in range(channel_count):
        out_name = _build_unified_name(
            well=well, field=field, stack=1, timepoint=1, channel=c + 1,
        )
        dst = output_dir / out_name
        if dst.exists():
            results.append(dst)
            continue
        data = img if img.ndim == 2 else img[..., c]
        data = _resize_if_needed(data, resize_factor)
        write_image(dst, data)
        results.append(dst)

    return results


def convert_measurement(
    input_dir: Union[str, Path],
    vendor_format: str = "operetta",
    root_dir: Optional[Union[str, Path]] = None,
    resize_factor: float = 1.0,
    output_name: str = "unified",
) -> List[Path]:
    """Convert a vendor-format measurement directory to unified naming.

    Parameters
    ----------
    input_dir : str or Path
        Raw measurement directory.
    vendor_format : str
        ``"operetta"`` or ``"mica"``.
    root_dir : str or Path, optional
        Root directory for output (defaults to ``input_dir``).
    resize_factor : float
        Resize scale factor (1.0 = no resize).
    output_name : str
        Output subdirectory name under ``root_dir`` (default ``"unified"``).

    Returns
    -------
    list of Path
        Paths to the converted files.
    """
    input_dir = Path(input_dir)
    root_dir = Path(root_dir) if root_dir else input_dir
    output_dir = root_dir / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    converted: List[Path] = []

    if vendor_format == "operetta":
        img_dir = input_dir / "Images"
        if not img_dir.is_dir():
            raise NotADirectoryError(
                f"Operetta images subdirectory not found: {img_dir}"
            )

        tiff_files = sorted(img_dir.glob("*.tiff"))
        if not tiff_files:
            raise FileNotFoundError(f"No .tiff files found in {img_dir}")

        for src in tiff_files:
            m = OPERETTA_PATTERN.match(src.name)
            if m is None:
                continue
            dst = _convert_operetta_file(src, m, output_dir, resize_factor)
            if dst:
                converted.append(dst)

        log.info("Converted %d Operetta files → %s", len(converted), output_dir)

    elif vendor_format == "mica":
        root = _find_mica_root(input_dir)

        row_dirs = sorted(
            d for d in root.iterdir()
            if d.is_dir() and len(d.name) == 1 and d.name.isalpha() and d.name != "Metadata"
        )
        for row_dir in row_dirs:
            row_letter = row_dir.name
            col_dirs = sorted(
                d for d in row_dir.iterdir()
                if d.is_dir() and d.name not in ("Metadata", "Images")
            )
            for col_dir in col_dirs:
                col_num = col_dir.name
                for src in sorted(col_dir.iterdir()):
                    m = MICA_POS_PATTERN.match(src.name)
                    if m is None:
                        continue
                    dsts = _convert_mica_file(
                        src, m, output_dir, row_letter, col_num, resize_factor,
                    )
                    converted.extend(dsts)

        log.info("Converted %d MICA files → %s", len(converted), output_dir)

    else:
        raise ValueError(f"Unknown vendor format: {vendor_format}")

    if not converted:
        raise RuntimeError(f"No files converted from {input_dir} ({vendor_format})")

    return converted
