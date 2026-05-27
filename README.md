# microProfiler

[![PyPI version](https://img.shields.io/pypi/v/microProfiler)](https://pypi.org/project/microProfiler/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/pypi/pyversions/microProfiler)

Microscopy image preprocessing, segmentation, and profiling pipeline for multi-well plate data.

Converts vendor-specific formats (Operetta, MICA) into a unified file structure, then provides a chainable preprocessing pipeline followed by cell segmentation and feature profiling.

## Requirements

- **Python** >= 3.10
- **OS**: Windows 10/11 (64-bit) recommended; CLI works cross-platform
- **GPU** (optional): NVIDIA GPU with CUDA 12+ for faster segmentation

## Installation

### Quick Install (CPU)

Works out of the box — no GPU required:

```bash
pip install microProfiler
```

### GPU-Accelerated Install (Recommended)

For significantly faster Cellpose segmentation, install GPU-enabled PyTorch **before** installing microProfiler.

**Step 1 — Install PyTorch with CUDA**

Go to [pytorch.org/get-started](https://pytorch.org/get-started/locally/) and select your CUDA version. Example for CUDA 12.6:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
```

**Step 2 — Install JAX with CUDA** (used by BaSiC shading correction)

```bash
pip install jax[cuda12]
```

> See [jax.readthedocs.io](https://jax.readthedocs.io/en/latest/installation.html) for other CUDA versions.

**Step 3 — Install microProfiler**

```bash
pip install microProfiler
```

This installs cellpose and all remaining dependencies automatically.

### Conda Install

```bash
conda env create -f micro.yml
conda activate micro
```

### Development Install

```bash
git clone https://github.com/soulong/microProfiler.git
cd microProfiler
pip install -e ".[dev]"
```

## Pipeline Order

```
Input → Convert[+resize] → Resize → BaSiC → Z-projection → Tile → Segment → Profile
```

1. **Convert** — Vendor-format files → `{well}_f{field}_z{z}_t{t}_ch{ch}.tiff` (optional resize during write)
2. **Resize** (optional) — Standalone resize step (after conversion if `--resize` is set)
3. **BaSiC correction** (optional) — Flatfield/darkfield shading correction
4. **Z-projection** (optional) — Max/mean/min projection of Z-stacks
5. **Tile splitting** (optional) — Non-overlapping tiles
6. **Segmentation** (optional) — Cellpose-SAM object detection
7. **Profiling** — Image-level and object-level feature extraction. Supports multi-object profiling (profile multiple masks with different channel/feature settings in a single run via `object_profilings` list).

## Quick Start (CLI)

```bash
# Run full pipeline using a YAML config file
microprofiler run /path/to/Measurement\ 1 --config examples/pipeline_config.yml

# Run full pipeline on Operetta format (with resize during conversion and standalone resize)
microprofiler run /path/to/Measurement\ 1 --format operetta \
  --convert-resize 0.5 \
  --resize 0.5 \
  --basic fit-transform \
  --z-projection max \
  --tile 540 540 \
  --segment cell --segment-channels ch1 \
  --profile-image \
  --profile-object cell \
  --workers 4 \
  --output /path/to/output \
  --config examples/pipeline_config.yml

# Run full pipeline on MICA format
microprofiler run /path/to/Sequence\ 002 --format mica \
  --segment cell --segment-channels ch1 \
  --profile-object cell --db results.db

# Convert only (with optional resize and custom output name)
microprofiler convert /path/to/Measurement\ 1 --format operetta --convert-resize 0.5 --output-name myoutput

# Use a YAML config for full control over all profiling and segmentation parameters
microprofiler run /path/to/Measurement\ 1 --config examples/pipeline_config.yml
```

A complete YAML config with all parameters is at [`examples/pipeline_config.yml`](examples/pipeline_config.yml).

## Library Usage

```python
from pathlib import Path
from microProfiler.preprocessing.converter import convert_measurement
from microProfiler.preprocessing.resizer import resize_dataset
from microProfiler.preprocessing.basic_correction import apply_basic
from microProfiler.preprocessing.z_projection import z_project_dataset
from microProfiler.preprocessing.tile_splitter import tile_dataset
from microProfiler.segmentation.cellpose import segment_dataset
from microProfiler.profiling.image_profiler import profile_images
from microProfiler.profiling.object_profiler import profile_objects, measure_objects

root = Path(r"/path/to/Measurement 1")

# 1. Convert to unified naming (optional resize during conversion)
ds = convert_measurement(root, vendor_format="operetta", resize_factor=0.5)

# 2. Preprocess (in-place by default)
ds = resize_dataset(ds, scale_factor=0.5, root_dir=root)
ds = apply_basic(ds, mode="fit-transform", root_dir=root)
ds = z_project_dataset(ds, root_dir=root, method="max")
ds = tile_dataset(ds, root_dir=root, tile_w=540, tile_h=540)

# 3. Segment
ds = segment_dataset(ds, object_name="cell", chan1=["ch1"])

# 4. Profile — image-level + object-level with extras
profile_images(ds, db_path=root / "results.db", table_name="image")
profile_objects(
    ds,
    mask_name="cell",
    intensity_channels=["ch1", "ch2"],
    radial_channels=["ch1"],
    radial_n_bins=5,
    granularity_channels=["ch1"],
    glcm_channels=["ch1"],
    glcm_distances=[1, 3],
    correlation_pairs=[("ch1", "ch2")],
    # override granularity defaults via extra_kwargs
    granularity_kwargs={"radii": [1, 3, 6, 8, 12], "subsample_size": 1.0},
    db_path=root / "results.db",
)

# Or measure a single image/mask pair directly
row = ds.metadata.iloc[0]
img, masks = ds.get_imageset(0)
df = measure_objects(
    masks["cell"], img,
    channel_names=ds.intensity_colnames,
    intensity_channels=ds.intensity_colnames,
    granularity_channels=ds.intensity_colnames,
)
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

## Desktop GUI

microProfiler includes a PySide6 desktop GUI that wraps the full pipeline with step-by-step image preview, parameter configuration, progress bars, and a log console.

### System Requirements

- **OS**: Windows 10/11 (64-bit) — GUI is Windows-optimized; CLI works cross-platform
- **RAM**: 16 GB minimum (32 GB recommended for large datasets)
- **GPU**: NVIDIA GPU with CUDA 12+ (recommended for segmentation speed; CPU fallback works)

### Running the GUI

```bash
microprofiler
```

The `microprofiler` command launches the GUI when called with no arguments. The CLI pipeline is accessible via subcommands:

| Command | Action |
|---------|--------|
| `microprofiler` | Launch desktop GUI |
| `microprofiler run ...` | Run pipeline from CLI |
| `microprofiler convert ...` | Convert vendor format via CLI |
| `microprofiler --version` | Print version |
| `microprofiler --help` | Show CLI help |

### Cellpose Model

microProfiler does **not** bundle Cellpose model weights. On first use:
- Leave the **Model** field empty to use the built-in `cpsam` model (downloaded automatically by Cellpose).
- Or click **Browse** to select a custom `.pt` model file.

## API Documentation

See [`docs/api.md`](docs/api.md) for the full API reference including class and function signatures, parameters, and return types.

## Acknowledgements

microProfiler uses the following open-source libraries:

- **BaSiCPy** — Flatfield and darkfield shading correction.  
  https://github.com/peng-lab/BaSiCPy
- **Cellpose** — Generalist deep learning model for segmentation.  
  https://github.com/MouseLand/cellpose

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
