# microProfiler

Microscopy image preprocessing, segmentation, and profiling pipeline for multi-well plate data.

## Build / Install

```bash
# Conda (recommended)
conda env create -f micro.yml
conda activate micro
pip install -e .

# Or pip only
pip install -e .
```

The CLI entry point is `microprofiler` (defined in `pyproject.toml` under `[project.scripts]`).

## How to Run

### CLI
```bash
# Convert vendor format only
microprofiler convert /path/to/data --format operetta

# Full pipeline from YAML config
microprofiler run /path/to/data --config pipeline_config.yml

# With individual flags
microprofiler run /path/to/data --output ./results --segment --profile
```

### GUI (no args)
```bash
microprofiler
```

### Library / quickstart
```bash
python examples/quickstart.py
```
The quickstart walks through all 7 steps programmatically using test data under `tests/test_dataset/`.

## Directory Structure

```
microProfiler/
  cli.py                  # argparse CLI (run / convert subcommands)
  config.py               # Pydantic config models (PipelineConfig, etc.)
  pipeline.py             # Orchestrator: run_pipeline(), run_step()
  logging_utils.py        # Logger setup

  io/
    dataset.py            # ImageDataset — metadata manager over image directory
    database.py           # Database — thread-safe SQLite wrapper (WAL mode)
    loaders.py            # read_image / write_image, IntensityNormalizer
    export.py             # CellProfiler CSV export

  preprocessing/
    converter.py          # convert_measurement() — vendor → unified naming
    resizer.py            # resize_dataset()
    basic_correction.py   # apply_basic() — BaSiC flatfield/darkfield correction
    z_projection.py       # z_project_dataset() — max/mean/min projection
    tile_splitter.py      # tile_dataset() — non-overlapping tiles
    _swap.py              # TempSwap — atomic file operations
    basic/                # BaSiC algorithm engine — DO NOT MODIFY

  segmentation/
    cellpose.py           # segment_dataset() — Cellpose-SAM masks

  profiling/
    image_profiler.py     # profile_images() — whole-image features
    object_profiler.py    # profile_objects() — per-object features
    extras.py             # Extra property factories (radial, granularity, GLCM, correlation)

  gui/                    # PySide6 desktop GUI (implementation subject to change)
```

## Key Conventions

- **Pipeline step order**: Convert → Resize → BaSiC → Z-projection → Tile → Segment → Profile
- **Each step** is a function taking `(dataset, **params)` and returning an `ImageDataset`
- **Convert** is a nescessary step to convert various dataset into a unified image file naming structure
- **Resize** **BaSiC** **Z-projection** **Tile** are pre-processing steps. they are all optional steps, any combination of them could subject to run while the running order is still unique
- **`ImageDataset`** is a metadata manager (pandas DataFrame), not a god class — processing logic lives in dedicated modules
- **`TempSwap`** provides crash-safe atomic file writes (writes go to `.tmp_{step}/`, swapped on success)
- **Config** is Pydantic models loaded from YAML (`load_config()`) or built from CLI flags / GUI state
- **SQLite** uses WAL mode + `threading.local()` connections for thread safety
- **`microProfiler/preprocessing/basic/`** is the BaSiC algorithm engine — do not modify

## Test Data & Smoke Test

Test fixture data is at `tests/test_dataset/`:
- `tests/test_dataset/operetta/` — Operetta format samples
- `tests/test_dataset/mica/` — MICA format samples
- when test, in case not to destroy original files, copy `tests/test_dataset/operetta/*` to `tests/test_result/operetta/*` first (take operetta as example, same with mica). and use `tests/test_result/*` as test target to do all tests

Quick smoke test:
```bash
python examples/quickstart.py
```
This runs the full pipeline on MICA test data and writes results to `tests/test_result/mica/Sequence 002/result.db`.

## Dependencies

Core: numpy, pandas, scipy, scikit-image, tifffile, Pillow, cellpose, torch, jax, pydantic>=2.0, pyyaml, PySide6, natsort, tqdm