"""ImageDataset — lightweight metadata manager for the pipeline.

This is a stripped-down replacement of the original god-class ImageDataset.
It handles metadata discovery, pattern-based filename parsing, and image
loading.  Processing logic (preprocessing, segmentation, profiling) lives
in dedicated modules that accept an ImageDataset as input.
"""

from __future__ import annotations

import logging
import re
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from natsort import natsorted

from microProfiler.io.loaders import read_image

log = logging.getLogger(__name__)

# ── Supported intensity image extensions ─────────────────────────────────
KNOWN_IMAGE_EXTS = (".tiff", ".tif", ".jpg", ".jpeg")


def _detect_intensity_suffix(directory: Path) -> str:
    """Scan a directory and determine the single image extension in use.

    Parameters
    ----------
    directory : Path
        Directory to scan recursively.

    Returns
    -------
    str
        Detected extension (e.g. ``".tiff"``, ``".jpg"``).

    Raises
    ------
    FileNotFoundError
        If no files with known extensions are found.
    ValueError
        If multiple different image extensions are present.
    """
    counts: Dict[str, int] = {}
    for ext in KNOWN_IMAGE_EXTS:
        counts[ext] = len(list(directory.rglob(f"*{ext}")))
    present = {k: v for k, v in counts.items() if v > 0}
    if not present:
        raise FileNotFoundError(
            f"No image files with extensions {KNOWN_IMAGE_EXTS} found in {directory}"
        )
    if len(present) > 1:
        raise ValueError(
            f"Multiple image extensions found in {directory}: {list(present.keys())}. "
            "All intensity images must use the same extension."
        )
    return list(present.keys())[0]


def _has_row_subdirs(directory: Path) -> bool:
    """Check if *directory* contains single-letter subdirectories (mica raw layout)."""
    try:
        for entry in directory.iterdir():
            if entry.is_dir() and entry.name.isalpha() and len(entry.name) == 1:
                return True
    except OSError:
        pass
    return False


# ── Default regex patterns ──────────────────────────────────────────────
# Unified naming: {well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff
# Non-capturing suffix group allows transformation steps (z-projection,
# tiling) to append extra identifiers without breaking metadata parsing.
_UNIFIED_IMAGE_BASE = (
    r"(?P<well>[A-Z]\d+)_f(?P<field>[\d-]+)_z(?P<stack>\d+)_t(?P<timepoint>\d+)_ch(?P<channel>\d+)"
    r"(?P<tile>_tile\d+)?"
    r"(?:.*?)"
)

UNIFIED_IMAGE_PATTERN = re.compile(_UNIFIED_IMAGE_BASE + r"\.tiff")
UNIFIED_MASK_PATTERN = re.compile(
    _UNIFIED_IMAGE_BASE + r"_cp_masks_(?P<mask_name>.+)\.png"
)


class ImageDataset:
    """Lightweight manager for a directory of microscopy images.

    Scans the given directory, auto-detects the image file extension
    (``.tiff``, ``.tif``, ``.jpg``, ``.jpeg``), and builds a metadata
    DataFrame by parsing filenames against a regex pattern.

    Parameters
    ----------
    measurement_dir : str or Path
        Directory containing either ``Images/`` or ``image/`` subfolder,
        or unified image files directly.
    image_pattern : str or Pattern, optional
        Regex with named groups to parse image filenames.  Defaults to
        ``UNIFIED_IMAGE_PATTERN`` with auto-detected extension.
    mask_pattern : str or Pattern, optional
        Regex with named groups to parse mask filenames.
    filters : dict of str → str, optional
        Column → regex pattern pairs applied after metadata build.
        Only rows matching all filters are kept (AND logic).
    image_subdir_pattern : str, optional
        Glob pattern relative to ``measurement_dir`` for raw vendor files.
        ``None`` (default) auto-detects: checks ``image/`` first for
        converted data, then ``Images/`` (operetta), then ``[A-P]/`` (mica).
        Set to ``"Images/"`` for operetta or ``"[A-P]/"`` for mica to force
        a specific raw layout.
    """

    def __init__(
        self,
        measurement_dir: Union[str, Path],
        image_pattern: Optional[Union[str, re.Pattern]] = None,
        mask_pattern: Optional[Union[str, re.Pattern]] = None,
        filters: Optional[Dict[str, str]] = None,
        image_subdir_pattern: Optional[str] = None,
    ):
        self.measurement_dir = Path(measurement_dir)
        self._image_pattern = image_pattern or UNIFIED_IMAGE_PATTERN
        self._mask_pattern = mask_pattern or UNIFIED_MASK_PATTERN
        self._image_subdir_pattern = image_subdir_pattern
        self._metadata: Optional[pd.DataFrame] = None
        self._intensity_colnames: List[str] = []
        self._mask_colnames: List[str] = []
        self._img_shape: Optional[tuple] = None
        self._img_dtype: Optional[np.dtype] = None

        log.debug("ImageDataset: dir=%s, filters=%s", self.measurement_dir, filters)
        self.build_metadata()
        if filters:
            for col, pat in filters.items():
                self.filter_metadata(col, pat)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def metadata(self) -> pd.DataFrame:
        """Metadata DataFrame with one row per image."""
        return self._metadata

    @property
    def intensity_colnames(self) -> List[str]:
        """Sorted list of intensity channel names."""
        return list(self._intensity_colnames)

    @property
    def mask_colnames(self) -> List[str]:
        """Sorted list of mask column names."""
        return list(self._mask_colnames)

    @property
    def img_shape(self) -> Optional[tuple]:
        """Spatial dimensions ``(H, W)`` of the first intensity image, or ``None``."""
        return self._img_shape

    @property
    def img_dtype(self) -> Optional[np.dtype]:
        """NumPy dtype of the first intensity image, or ``None``."""
        return self._img_dtype

    def __len__(self) -> int:
        return 0 if self._metadata is None else len(self._metadata)

    def __repr__(self) -> str:
        return (
            f"ImageDataset(dir={self.measurement_dir!r}, "
            f"rows={len(self)}, "
            f"channels={self._intensity_colnames}, "
            f"masks={self._mask_colnames})"
        )

    # ── Metadata discovery ──────────────────────────────────────────────

    def build_metadata(self) -> None:
        """Scan measurement directory and build the metadata DataFrame.

        Auto-detects the image extension when the default pattern is used.
        After building, ``tile`` column is dropped if all null (pre-tiling)
        or converted to integer if present (post-tiling).
        """
        search_dir = self.measurement_dir

        # 1. Always check for converter output first (image/)
        image_subdir = self.measurement_dir / "image"
        if image_subdir.is_dir() and (
            list(image_subdir.glob("*.tiff")) or list(image_subdir.glob("*.tif"))
        ):
            search_dir = image_subdir
            self.measurement_dir = image_subdir
            log.debug("Using converter output directory: %s", search_dir)

        elif self._image_subdir_pattern is not None:
            # 2. Explicit raw vendor pattern — scope glob to this pattern
            pass  # search_dir stays as measurement_dir; glob pattern applied below

        else:
            # 3. Auto-detect raw vendor layout
            images_subdir = self.measurement_dir / "Images"
            if images_subdir.is_dir() and list(images_subdir.glob("*.tiff")):
                search_dir = images_subdir
            elif _has_row_subdirs(self.measurement_dir):
                pass  # mica layout: search_dir stays as measurement_dir

        # Auto-detect extension only within the chosen search_dir
        if self._image_pattern is UNIFIED_IMAGE_PATTERN:
            ext = _detect_intensity_suffix(search_dir)
            self._image_pattern = re.compile(_UNIFIED_IMAGE_BASE + re.escape(ext))
            log.debug("Detected image extension: %s in %s", ext, search_dir)

        # Build the glob pattern
        if search_dir == image_subdir:
            # Converted data: flat directory, simple glob
            all_files = [Path(p) for p in glob(str(search_dir / "*"))]
        elif self._image_subdir_pattern is not None:
            # Raw vendor with explicit pattern
            all_files = [Path(p) for p in glob(
                str(search_dir / self._image_subdir_pattern / "**/*"), recursive=True
            )]
        elif _has_row_subdirs(self.measurement_dir):
            # Mica raw: scope to single-letter row directories
            all_files = [Path(p) for p in glob(
                str(search_dir / "[A-P]" / "**/*"), recursive=True
            )]
        else:
            all_files = [Path(p) for p in glob(str(search_dir / "**/*"), recursive=True)]

        if not all_files:
            raise FileNotFoundError(
                f"No files found in {search_dir}"
            )

        image_paths = [p for p in all_files if re.search(self._image_pattern, p.name)]
        mask_paths = [p for p in all_files if re.search(self._mask_pattern, p.name)]
        log.debug("Found %d intensity images, %d mask images", len(image_paths), len(mask_paths))

        if not image_paths:
            raise FileNotFoundError(
                f"No image files matching pattern found in {self.measurement_dir}"
            )

        image_df = pd.DataFrame({
            "directory": [str(p.parent) for p in image_paths],
            "filename": [p.name for p in image_paths],
        })
        parsed = image_df["filename"].str.extract(self._image_pattern)
        if "channel" in parsed.columns:
            parsed["channel"] = "ch" + parsed["channel"].astype(str)
        else:
            parsed["channel"] = "ch0"

        metadata_cols = [c for c in parsed.columns if c not in ("channel", "ext")]
        combined = pd.concat(
            [image_df.reset_index(drop=True), parsed.reset_index(drop=True)],
            axis=1,
        )
        combined = combined.set_index(["directory"] + metadata_cols)
        channels = natsorted(combined["channel"].unique())
        pivoted = combined.pivot(columns="channel", values="filename")
        self._intensity_colnames = channels

        if mask_paths:
            mask_df = pd.DataFrame({
                "directory": [str(p.parent) for p in mask_paths],
                "filename": [p.name for p in mask_paths],
            })

            mparsed = mask_df["filename"].str.extract(self._mask_pattern)
            mask_meta_cols = [
                c for c in mparsed.columns if c not in ("mask_name", "channel", "ext")
            ]

            mcombined = pd.concat(
                [mask_df.reset_index(drop=True), mparsed.reset_index(drop=True)],
                axis=1,
            )
            mcombined = mcombined.set_index(["directory"] + mask_meta_cols)
            mask_names = natsorted(mcombined["mask_name"].unique())
            mpivoted = mcombined.pivot(columns="mask_name", values="filename")

            # Rename mask columns BEFORE join to avoid duplicated column names
            if pivoted.index.names == mpivoted.index.names:
                mpivoted.columns = [f"mask_{c}" for c in mpivoted.columns]
                pivoted = pivoted.join(mpivoted, how="left")
            else:
                log.debug("intensity_df index: %s", pivoted.index.names)
                log.debug("mask_combined index: %s", mcombined.index.names)

            self._mask_colnames = [f"mask_{n}" for n in mask_names]

        self._metadata = pivoted.reset_index()
        log.debug("Built metadata: %d rows, channels=%s, masks=%s", len(self._metadata), self._intensity_colnames, self._mask_colnames)

        # Tile column: convert to int if present, drop if all NaN (pre-tiling)
        if "tile" in self._metadata.columns:
            if self._metadata["tile"].notna().any():
                self._metadata["tile"] = (
                    self._metadata["tile"].str.replace("_tile", "").astype(int)
                )
            else:
                self._metadata.drop(columns=["tile"], inplace=True)

        dtype_cols = ["stack", "timepoint", "field"]
        existing = [c for c in dtype_cols if c in self._metadata.columns]
        for col in existing:
            try:
                self._metadata[col] = pd.to_numeric(self._metadata[col], errors="coerce")
            except (ValueError, TypeError):
                pass

        self._auto_detect_image_properties()

    def _auto_detect_image_properties(self) -> None:
        """Read the first image to detect shape and dtype.

        Sets ``_img_shape`` and ``_img_dtype`` from the first intensity image.
        Silently returns if the metadata is empty or the image file is missing.
        """
        if self._metadata is None or self._metadata.empty:
            return
        row = self._metadata.iloc[0]
        img_dir = row["directory"]
        ch = self._intensity_colnames[0]
        img_path = Path(img_dir) / row[ch]
        if not img_path.exists():
            return
        img = read_image(img_path)
        self._img_shape = img.shape[:2]
        self._img_dtype = img.dtype

    # ── Filtering ──────────────────────────────────────────────────────

    def filter_metadata(self, column: str, pattern: str) -> ImageDataset:
        """Keep only rows where *column* matches regex *pattern*.

        Filters are applied in-place (AND logic — each call further restricts).
        Returns ``self`` for chaining.

        Parameters
        ----------
        column : str
            Name of the metadata column to filter on.
        pattern : str
            Regex pattern to match against column values.

        Returns
        -------
        ImageDataset
            ``self`` with rows filtered in-place.
        """
        mask = self._metadata[column].astype(str).str.match(pattern)
        self._metadata = self._metadata[mask].reset_index(drop=True)
        return self

    # ── Image loading ──────────────────────────────────────────────────

    def get_imageset(
        self,
        row_idx: int,
        channels: Optional[List[str]] = None,
        masks: Optional[List[str]] = None,
    ) -> tuple:
        """Load the image stack and masks for a given metadata row.

        Parameters
        ----------
        row_idx : int
            Row index in the metadata DataFrame.
        channels : list of str, optional
            Channel names to load.  Defaults to all intensity channels.
        masks : list of str, optional
            Mask column names to load.  Defaults to all mask columns.

        Returns
        -------
        tuple of (np.ndarray, dict)
            image_data : (H, W, C) array in channels-last format.
            mask_data : dict of {mask_name: (H, W) uint16 array}.
        """
        row = self._metadata.iloc[row_idx]
        img_dir = row["directory"]

        channels = channels or self._intensity_colnames
        log.debug("get_imageset: row=%d, channels=%s", row_idx, channels)
        if isinstance(channels, str):
            channels = [channels]

        images = []
        for ch in channels:
            path = Path(img_dir) / row[ch]
            images.append(read_image(path))

        image_data = np.stack(images, axis=-1)

        mask_data = {}
        masks = masks or self._mask_colnames
        if isinstance(masks, str):
            masks = [masks]
        for mc in masks:
            name = mc.replace("mask_", "")
            mask_val = row.get(mc)
            if mask_val and not pd.isna(mask_val):
                path = Path(img_dir) / mask_val
                mask_data[name] = read_image(path)

        return image_data, mask_data

    def export_metadata(
        self,
        write_db: Union[bool, str, None] = True,
        table_name: str = "metadata",
    ):
        """Export metadata to an SQLite database.

        Parameters
        ----------
        write_db : bool, str, or None
            If ``True``, write to ``results.db`` in the measurement directory.
            If a string, use it as the filename.  If ``None`` or ``False``, skip.
        table_name : str
            Target table name in the database.
        """
        from microProfiler.io.database import write_results_to_db

        if isinstance(write_db, str):
            db_path = self.measurement_dir / write_db
        elif write_db:
            db_path = self.measurement_dir / "results.db"
        else:
            return

        write_results_to_db(db_path, table_name, self._metadata, if_exists="replace")
