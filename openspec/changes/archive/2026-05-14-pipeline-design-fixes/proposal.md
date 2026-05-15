## Why

The pipeline has accumulated several design inconsistencies and correctness issues across preprocessing, segmentation, and profiling stages — masks leak into the conversion step, z-projection grouping is implicit, segmentation input/output shapes are inconsistent with single-channel models, profiling column naming is mixed-case and unordered, tile metadata lacks an explicit capture group, and the database output path is buried inside a subdirectory.

## What Changes

1. **Conversion drops masks** (`converter.py`): Remove mask PNG copy during vendor conversion. Masks should only appear after segmentation, never during format conversion.

2. **Explicit z-projection grouping** (`z_projection.py`): Add `channel` to the group-by columns so grouping by `(well, field, timepoint, channel)` is explicit. Remove the inner channel loop.

3. **Segmentation supports single-channel input** (`segmentation/cellpose.py`): `build_cellpose_image()` returns `(1, H, W)` when `chan2` is `None`, instead of padding with zeros to `(2, H, W)`.

4. **Profiling column naming cleanup** (`profiling/extras.py`, `profiling/object_profiler.py`):
   - All object-level feature columns use lowercase prefixes: `intensity_*`, `radial_*`, `granularity_*`, `glcm_*`, `correlation_*`, `parent_*`
   - Granularity default reduced from 16 scales to 5
   - Column ordering: `label`, `is_boundary`, `parent_*` moved to the front

5. **Database output to measurement root** (`pipeline.py`): Write `results.db` to `cfg.input_dir` (parent of `unified/`) rather than inside `unified/`.

6. **Tile capture group in regex** (`io/dataset.py`): Add explicit `(?P<tile>_tile\d+)?` named group to `UNIFIED_IMAGE_PATTERN` and `UNIFIED_MASK_PATTERN`.

## Capabilities

### New Capabilities

None. All changes are bug fixes and design cleanups within existing capabilities.

### Modified Capabilities

None. No spec-level behavior contracts change — existing requirements still hold.

## Impact

- **`microProfiler/preprocessing/converter.py`**: Remove Operetta mask copy (lines 191-216)
- **`microProfiler/preprocessing/z_projection.py`**: Group-by logic restructured
- **`microProfiler/segmentation/cellpose.py`**: `build_cellpose_image()` output shape changes from `(2, H, W)` to `(1, H, W)` when single-channel
- **`microProfiler/profiling/extras.py`**: Column name prefixes in 4 factory functions
- **`microProfiler/profiling/object_profiler.py`**: Intensity prefix, parent prefix, column reordering, granularity default
- **`microProfiler/pipeline.py`**: DB path changed from `unified/db_name` to `input_dir/db_name`
- **`microProfiler/io/dataset.py`**: Both regex patterns gain a `tile` named group
