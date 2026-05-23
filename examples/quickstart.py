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
DATA_DIR = Path(r"C:\Users\haohe\GitHub\microProfiler\tests\test_result\mica\Sequence 002")
VENDOR_FORMAT = "mica"

OUTPUT_DB = DATA_DIR / "result.db"

# ── Step 1: Convert vendor format to unified naming ─────────────────────
print("Converting vendor format → unified naming")
ds = convert_measurement(DATA_DIR, vendor_format=VENDOR_FORMAT, delete_original=False)
print(ds)
print(ds.metadata)

# ── Step 2: Converted dataset is already loaded ─────────────────────────
# The converter writes to DATA_DIR / "image" by default.
print(f"Dataset measurement dir: {ds.measurement_dir}")

# subset to rows for quick testing
# ds.filter_metadata("well", r"B[2]").filter_metadata("field", r"[13]")
# ds.filter_metadata("tile", r"0")
# print(ds)

# ── Step 3: Z-projection (collapse stacks) ──────────────────────────────
ds = z_project_dataset(ds, method="max", inplace=True)
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
