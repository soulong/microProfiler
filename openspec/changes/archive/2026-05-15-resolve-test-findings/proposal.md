## Why

Running the full pipeline integration test on real Operetta and MICA data revealed 9 issues spanning profiling correctness, column naming, boundary detection, API conventions, and usability. These accumulate as technical debt and cause downstream confusion in analysis results.

## What Changes

- **BREAKING** Rename `zslice` column → `stack` throughout the entire pipeline (regex, metadata, preprocessing, profiling)
- **BREAKING** `segment_dataset()` now returns `ImageDataset` instead of `Dict`
- Fix `glcm_ASM_*` → lowercase `glcm_asm_*` and add `glcm_entropy_*` columns
- Fix `is_boundary` algorithm to flag objects whose bounding box touches the image edge (current 0.25 fraction threshold lets edge objects through)
- Fix column order in profiling output: attributes → label/is_boundary → measurements
- Suppress per-file `tqdm` progress in converter — log a one-line summary instead
- Add `ImageDataset.filter_metadata(column, pattern)` method for regex-based row subsetting
- Update `pipeline.py` and tests for the new `segment_dataset` return type
- Update all docstrings and comments to reflect renamed columns

## Capabilities

### New Capabilities
- `dataset-subsetting`: Filter `ImageDataset` rows by regex pattern on any metadata column, callable at init or after init for flexible per-subset processing

### Modified Capabilities

None. All changes are internal fixes and API improvements within existing capabilities.

## Impact

- `profiling/extras.py` — GLCM property naming and entropy addition
- `profiling/object_profiler.py` — boundary algorithm, column ordering
- `io/dataset.py` — regex group names, dtype_cols, new filter_metadata method
- `preprocessing/converter.py` — tqdm → summary log, parameter rename
- `preprocessing/z_projection.py` — `zslice` → `stack` string references
- `preprocessing/tile_splitter.py` — variable rename
- `segmentation/cellpose.py` — **BREAKING** return type change
- `pipeline.py` — adapt to new segment_dataset return type
- `cli.py` — no changes expected (pipeline handles the new API)
- `tests/test_pipeline.py` — update zslice/glcm_ASM references
- `tests/test_full_pipeline.py` — adapt to new segment_dataset return type and column names
