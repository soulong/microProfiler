## 1. zslice → stack rename (cross-cutting)

- [x] 1.1 Rename regex capture groups `zslice` → `stack` in `io/dataset.py` (both `UNIFIED_IMAGE_PATTERN` and `UNIFIED_MASK_PATTERN`)
- [x] 1.2 Update `build_metadata()` dtype_cols from `"zslice"` to `"stack"` in `io/dataset.py`
- [x] 1.3 Rename parameter `zslice` → `stack` in `preprocessing/converter.py` (`_build_unified_name` and callers)
- [x] 1.4 Update `preprocessing/z_projection.py`: rename column refs, group_cols, and docstrings (`zslice` → `stack`)
- [x] 1.5 Update `preprocessing/tile_splitter.py`: rename variable `zslice` → `stack`
- [x] 1.6 Update `tests/test_pipeline.py`: rename all `zslice` references in test assertions and print statements
- [x] 1.7 Update `tests/test_full_pipeline.py`: rename any `zslice` references
- [x] 1.8 Verify no remaining `zslice` references: `grep -rn "zslice" microProfiler/ tests/`

## 2. GLCM naming and entropy

- [x] 2.1 In `profiling/extras.py`: rename `"ASM"` → `"asm"` in `_GLCM_PROPS` and update the special-case key at line 197
- [x] 2.2 Add `"entropy"` to `_GLCM_PROPS`
- [x] 2.3 Update `tests/test_pipeline.py` GLCM test to assert lowercase column names and entropy presence (test_pipeline.py no longer exists — covered by test_full_pipeline.py)

## 3. Fix is_boundary algorithm

- [x] 3.1 Replace pixel-fraction-threshold logic in `profiling/object_profiler.py` `_is_boundary()` with bounding-box edge-touch check
- [x] 3.2 Update the `boundary_threshold` parameter docstring to reflect new behavior (removed parameter)

## 4. Fix column ordering in profiling output

- [x] 4.1 In `profiling/object_profiler.py` `measure_objects()` Step 8: reorder so metadata columns appear first, then `label`/`is_boundary`/`parent_*`, then measurement columns

## 5. Reduce converter verbosity

- [x] 5.1 In `preprocessing/converter.py`: remove `tqdm` progress bar, add a counter, log a one-line summary per vendor at the end

## 6. Add ImageDataset.filter_metadata

- [x] 6.1 Add `filter_metadata(self, column, pattern)` method to `io/dataset.py` that filters `_metadata` in-place and returns `self`
- [x] 6.2 Add optional `filter_metadata` parameter to `__init__` for construction-time filtering

## 7. Change segment_dataset return type to ImageDataset

- [x] 7.1 In `segmentation/cellpose.py`: change `segment_dataset()` return type from `Dict` to `ImageDataset`; call `ds.build_metadata()` before returning `ds`
- [x] 7.2 Update `pipeline.py`: adapt to new return type (`ds = segment_dataset(ds, ...)` instead of `segment_dataset(ds, ...); ds.build_metadata()`)
- [x] 7.3 Update `tests/test_full_pipeline.py`: adapt to new return type and remove explicit `ds.build_metadata()` call after segmentation

## 8. Update all docstrings and comments

- [x] 8.1 Update docstrings in all modified files to reflect renamed columns and changed APIs
- [x] 8.2 Remove or update stale comments (e.g., references to old column names)

## 9. Verify and lint

- [x] 9.1 Run `ruff check .` and fix any lint issues
- [x] 9.2 Skip — test_pipeline.py no longer exists, coverage handled by test_full_pipeline.py
- [x] 9.3 Run `pytest tests/test_full_pipeline.py -v -m slow` — 2 passed ✓
