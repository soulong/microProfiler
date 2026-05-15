## Why

Preprocessing steps create outputs nested recursively under the previous step's directory (e.g. `unified/resized_0.5/zproject_max/tiles_540x540/`), making it hard to navigate results and brittle when step order changes. The resize step is a trivial pixel operation that adds an unnecessary I/O pass when it could be folded into conversion. Group columns in z-projection are hard-coded rather than derived from metadata, breaking when metadata schema changes.

## What Changes

- **Flat output structure**: Every preprocessing step writes to a sibling directory under the measurement root (`measurement/zproject_max/`, `measurement/tiles_540x540/`), not nested under the previous output
- **Resize merged into converter**: `convert_measurement` gains a `resize_factor` parameter; resize logic executes during the conversion write. Standalone `--resize` is removed from the run pipeline.
- **Dynamic group columns**: `z_project_dataset` derives group columns dynamically from the metadata schema (all non-data columns except `stack`)
- **Docs & CLI updated**: CLI gains `--resize` on `convert` subcommand; converter output dir name configurable via `--output-name`; all documentation reflects new structure
- **BREAKING**: Preprocessing output directories move from nested to flat paths. Existing scripts referencing nested paths will break.

## Capabilities

### New Capabilities
- `preprocessing-output-structure`: All preprocessing steps (resize, BaSiC, z-projection, tile) write to sibling directories under the measurement root, keyed by a shared root reference
- `converter-resize`: Converter optionally resizes images during the conversion write step via a `resize_factor` parameter
- `pipeline-group-cols`: Z-projection determines group columns dynamically from the metadata schema rather than hard-coding column names

### Modified Capabilities
- *(none — existing specs don't reference output paths or step internals)*

## Impact

| File | Change |
|------|--------|
| `preprocessing/converter.py` | Add `resize_factor` parameter; resize during conversion write |
| `preprocessing/resizer.py` | Deprecate or remove standalone step |
| `preprocessing/z_projection.py` | Dynamic group_cols from metadata; output dir via root + subdir |
| `preprocessing/tile_splitter.py` | Output dir via root + subdir |
| `preprocessing/basic_correction.py` | Output dir via root + subdir (BaSiC_model/, BaSiC_corrected/) |
| `pipeline.py` | Remove standalone resize step; pass root_dir through pipeline |
| `config.py` | Add ConvertConfig with output_name and resize_factor |
| `cli.py` | `--resize` on convert subcommand; `--output-name` option |
| `README.md`, `docs/api.md` | Reflect new structure |
