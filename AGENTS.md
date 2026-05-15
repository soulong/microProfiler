# microProfiler — Agent Guide

## Environment

- **Python**: >= 3.10
- **Conda env**: `cellpose` — always activate before running tests or the CLI
- **Install**: `pip install -e .` (from repo root)
- **Dev extras**: `pip install -e ".[dev]"` (adds pytest, pytest-cov, ruff)

## Test workflow

1. **Copy test data** to the working copy before running tests:
   ```
   Xcopy /E /I /Y tests\test_dataset\operetta tests\test_dataset\test_result\operetta
   Xcopy /E /I /Y tests\test_dataset\mica tests\test_dataset\test_result\mica
   ```
   Never run tests against the original `tests/test_dataset/{operetta,mica}/` — use `test_result/` instead.

2. **Run tests**:
   ```
   conda activate cellpose
   pytest tests/test_pipeline.py -v
   ```
   All test output (unified dirs, .db files, segmentation masks, corrected TIFFs, etc.) is written under `tests/test_dataset/test_result/`, keeping the original data pristine. Pipeline steps intentionally write artifacts (masks, corrected files) alongside source images — this is the expected workflow, and `test_result/` is the sandbox for it.

3. **Lint**:
   ```
   ruff check .
   ```

## Protected directories

Do **not** modify any files under `microProfiler/preprocessing/basic/` — this is the vendored BaSiC algorithm and must remain untouched.

## Architecture

| Path | Role |
|------|------|
| `cli.py` | `microprofiler run` / `microprofiler convert` |
| `pipeline.py` | Orchestrator: Convert → Resize → BaSiC → Z-projection → Tile → Segment → Profile |
| `config.py` | Pydantic `PipelineConfig`; also loadable from YAML |
| `io/dataset.py` | `ImageDataset` — metadata manager, filename parsing, image loading |
| `io/loaders.py` | `read_image`/`write_image` + lazy `IntensityNormalizer` |
| `io/database.py` | Thread-safe SQLite (WAL mode) |
| `preprocessing/converter.py` | Operetta/MICA → unified `{well}_f{field}_z{z}_t{t}_ch{ch}.tiff` |
| `segmentation/cellpose.py` | Cellpose-SAM segmentation (`segment_dataset`) |
| `profiling/image_profiler.py` | Whole-image features |
| `profiling/object_profiler.py` | Per-object shape/intensity/texture |
| `profiling/extras.py` | Radial distribution, granularity, GLCM, correlation |

## Test data layout

```
tests/test_dataset/
├── operetta/2026-05-01_plate_Measurement 1/Images/   ← original (read-only)
├── mica/Sequence 002/{B,G,Metadata}/                  ← original (read-only)
└── test_result/
    ├── operetta/2026-05-01_plate_Measurement 1/Images/ ← working copy
    └── mica/Sequence 002/{B,G,Metadata}/                ← working copy
```

## CLI quick reference

```
microprofiler run <input_dir> --format operetta|mica [--resize N] [--basic fit|transform|fit-transform] [--z-projection max|mean|min] [--tile W H] [--segment NAME --segment-channels ch1 ...] [--profile-image] [--profile-object NAME] [--db results.db]

microprofiler convert <input_dir> --format operetta|mica [--output DIR]
```

## Ruff config

Line length: 100. Lint rules: E, F, W.
