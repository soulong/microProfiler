#!/usr/bin/env python3
"""Quick-start example for the microProfiler library."""

from pathlib import Path

from microProfiler import ImageDataset
from microProfiler.preprocessing.converter import convert_measurement
from microProfiler.preprocessing.z_projection import z_project_dataset
from microProfiler.preprocessing.tile_splitter import tile_dataset
from microProfiler.segmentation.cellpose import segment_dataset
from microProfiler.profiling.image_profiler import profile_images
from microProfiler.profiling.object_profiler import profile_objects

# ── Configuration ────────────────────────────────────────────────────────
DATA_DIR = Path(r"C:\Users\haohe\GitHub\microProfiler\tests\test_dataset\mica\Sequence 002")
VENDOR_FORMAT = "mica"

DATA_DIR = Path(r"C:\Users\haohe\GitHub\microProfiler\tests\test_dataset\operetta\2026-05-01_plate_Measurement 1")
VENDOR_FORMAT = "operetta"

OUTPUT_DB = DATA_DIR / "results.db"

# ── Step 1: Convert vendor format to unified naming ─────────────────────
print("Converting vendor format → unified naming")
converted_filepath = convert_measurement(DATA_DIR, vendor_format=VENDOR_FORMAT)
print(converted_filepath[0])

# ── Step 2: Load the converted dataset ──────────────────────────────────
ds = ImageDataset(DATA_DIR / "unified")
print(ds)

# subset to rows for quick testing
ds.filter_metadata("well", r"B[2]").filter_metadata("field", r"[13]")
print(ds)

# ── Step 3: Z-projection (collapse stacks) ──────────────────────────────
ds = z_project_dataset(ds, method="max")
print(ds)

# ── Step 4: Tile splitting ──────────────────────────────────────────────
ds = tile_dataset(ds, tile_w=1024, tile_h=1024)
print(ds)

# ── Step 5: Cellpose segmentation ───────────────────────────────────────
ds = segment_dataset(ds, object_name="cell", chan1=ds.intensity_colnames[:1])
print(ds)

# ── Step 6: Image-level profiling ───────────────────────────────────────
profile_images(ds, channels=ds.intensity_colnames, db_path=OUTPUT_DB)

# ── Step 7: Object-level profiling ──────────────────────────────────────
profile_objects(
    ds,
    mask_name="cell",
    intensity_channels=ds.intensity_colnames,
    radial_channels=ds.intensity_colnames,
    radial_n_bins=5,
    granularity_channels=ds.intensity_colnames,
    glcm_channels=ds.intensity_colnames,
    glcm_distances=[2],
    correlation_pairs=[(ds.intensity_colnames[0], ds.intensity_colnames[1])]
    if len(ds.intensity_colnames) >= 2 else None,
    db_path=OUTPUT_DB,
)

print(f"\nDone! Results written to: {OUTPUT_DB}")
