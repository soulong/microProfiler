# microProfiler

Microscopy image preprocessing, segmentation, and profiling pipeline for multi-well plate data.

Converts vendor-specific formats (Operetta, MICA) into a unified file structure, then provides a chainable preprocessing pipeline followed by cell segmentation and feature profiling.

## Requirements

- **Python**: >= 3.10
- **Conda** (recommended) or `pip`

### Quick setup (conda)

```bash
# Create environment from curated file
conda env create -f micro.yml
conda activate micro

# Install microProfiler
pip install -e .

# With dev extras (testing, linting)
pip install -e ".[dev]"
```

### Manual setup (conda or pip)

```bash
# Conda
conda create -n micro python=3.10
conda activate micro
conda install -c conda-forge cellpose numpy pandas scipy scikit-image tifffile torch jax pyyaml tqdm
pip install natsort "pydantic>=2.0"
pip install -e .
```

## Pipeline Order

```
Input → Convert → BaSiC correction → Z-projection → Tile → Segment → Profile
```

1. **Convert** — Vendor-format files → `{well}_f{field}_z{z}_t{t}_ch{ch}.tiff`
2. **BaSiC correction** (optional) — Flatfield/darkfield shading correction
3. **Z-projection** (optional) — Max/mean/min projection of Z-stacks
4. **Tile splitting** (optional) — Non-overlapping tiles
5. **Segmentation** (optional) — Cellpose-SAM object detection
6. **Profiling** — Image-level and object-level feature extraction

## Quick Start (CLI)

```bash
# Run full pipeline on Operetta format (with resize during conversion)
microprofiler run /path/to/Measurement\ 1 --format operetta \
  --resize 0.5 \
  --basic fit-transform \
  --z-projection max \
  --tile 540 540 \
  --segment cell --segment-channels ch1 \
  --profile-image \
  --profile-object cell

# Run full pipeline on MICA format
microprofiler run /path/to/Sequence\ 002 --format mica \
  --segment cell --segment-channels ch1 \
  --profile-object cell --db results.db

# Convert only (with optional resize and custom output name)
microprofiler convert /path/to/Measurement\ 1 --format operetta --resize 0.5 --output-name myoutput
```

## Library Usage

```python
from pathlib import Path
from microProfiler import ImageDataset
from microProfiler.preprocessing.converter import convert_measurement
from microProfiler.preprocessing.z_projection import z_project_dataset
from microProfiler.preprocessing.tile_splitter import tile_dataset
from microProfiler.segmentation.cellpose import segment_dataset
from microProfiler.profiling.image_profiler import profile_images
from microProfiler.profiling.object_profiler import profile_objects

root = Path(r"/path/to/Measurement 1")

# 1. Convert to unified naming (optional resize during conversion)
convert_measurement(root, vendor_format="operetta", resize_factor=0.5)

# 2. Load dataset (auto-detects .tiff/.tif/.jpg/.jpeg)
ds = ImageDataset(root / "unified")

# 3. Preprocess (output directories are siblings under root)
ds = z_project_dataset(ds, root_dir=root, method="max")
ds = tile_dataset(ds, root_dir=root, tile_w=540, tile_h=540)

# 4. Segment
ds = segment_dataset(ds, object_name="cell", chan1=["ch1"])

# 5. Profile
profile_images(ds, db_path=root / "results.db", table_name="image")
profile_objects(ds, mask_name="cell",
                intensity_channels=["ch1", "ch2"],
                db_path=root / "results.db")
```

## Supported Vendor Formats

| Format | Input Pattern | Output Pattern |
|--------|---------------|----------------|
| Operetta | `r{row}c{col}f{field}p{stack}-ch{channel}sk{timepoint}fk1fl1.tiff` | `{well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff` |
| MICA | `{row}/{col}/Pos{field}.tif` | `{well}_f{field}_z1_t1_ch{channel}.tiff` |

## Key Modules

| Module | Purpose |
|--------|---------|
| `io.dataset` | Metadata management, filename parsing, image loading |
| `io.database` | Thread-safe SQLite (WAL mode, per-thread connections) |
| `io.loaders` | Unified TIFF I/O + lazy intensity normalization |
| `preprocessing.converter` | Vendor → unified naming |
| `preprocessing.z_projection` | Z-stack projection |
| `preprocessing.tile_splitter` | Image tiling |
| `preprocessing.basic_correction` | BaSiC shading correction wrapper |
| `segmentation.cellpose` | Cellpose-SAM segmentation |
| `profiling.image_profiler` | Whole-image features |
| `profiling.object_profiler` | Per-object features (shape, intensity, texture) |
| `profiling.extras` | Radial distribution, granularity, GLCM, correlation |

## API Documentation

See [`docs/api.md`](docs/api.md) for the full API reference including class and function signatures, parameters, and return types.

## Citation

If you use microProfiler in your research, please cite the repository:

```
@software{microProfiler,
  author = {Hao He},
  title = {microProfiler: Microscopy Image Preprocessing, Segmentation, and Profiling Pipeline},
  year = {2026},
  url = {https://github.com/soulong/microProfiler}
}
```

## License

MIT
