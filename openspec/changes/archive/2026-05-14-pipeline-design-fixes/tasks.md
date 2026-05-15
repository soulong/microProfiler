## 1. Conversion drops masks

- [x] 1.1 Remove mask PNG copy loop (lines 191-216) from `convert_measurement()` in `preprocessing/converter.py`

## 2. Z-projection explicit grouping

- [x] 2.1 Make `group_cols` explicit with `["well", "field", "timepoint"]` instead of subtractive column exclusion in `preprocessing/z_projection.py`

## 3. Single-channel segmentation shape

- [x] 3.1 In `build_cellpose_image()` in `segmentation/cellpose.py`, return `c1[np.newaxis, ...]` (shape `(1, H, W)`) when `chan2` is `None`

## 4. Profiling column naming, defaults, and ordering

- [x] 4.1 Lowercase prefixes in `_intensity_fns()` in `object_profiler.py`: `Intensity_` → `intensity_`
- [x] 4.2 Lowercase prefix in `measure_objects()` in `object_profiler.py`: `Parent_` → `parent_`
- [x] 4.3 Lowercase prefix in `make_radial_distribution()` in `extras.py`: `RadialDistribution_` → `radial_`
- [x] 4.4 Lowercase prefix in `make_granularity()` in `extras.py`: `Granularity_` → `granularity_`
- [x] 4.5 Lowercase prefix in `make_glcm()` in `extras.py`: `GLCM_` → `glcm_`
- [x] 4.6 Lowercase prefix in `measure_channel_correlation()` in `extras.py`: `Correlation_` → `correlation_`
- [x] 4.7 Change granularity default from `list(range(16))` to `list(range(5))` in `profile_objects()` in `object_profiler.py`
- [x] 4.8 Reorder columns in `measure_objects()`: `label`, `is_boundary`, `parent_*` first

## 5. Database output to measurement root

- [x] 5.1 Change `db_path` in `pipeline.py` from `unified_dir / db_name` to `cfg.input_dir / db_name`

## 6. Tile capture group in regex

- [x] 6.1 Add `(?P<tile>_tile\d+)?` to `UNIFIED_IMAGE_PATTERN` in `io/dataset.py`
- [x] 6.2 Add `(?P<tile>_tile\d+)?` to `UNIFIED_MASK_PATTERN` in `io/dataset.py`

## 7. Verify

- [x] 7.1 Copy test data to test_result directories
- [x] 7.2 Run `pytest tests/test_pipeline.py -v` and confirm all tests pass
- [x] 7.3 Run `ruff check .` and confirm no new lint errors
