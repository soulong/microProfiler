## Why

ImageDataset's metadata layer has accrued inconsistencies (polluting columns, hardcoded suffix, awkward parameter name) that make the API harder to use and maintain. The repo also lacks proper API documentation and has uneven docstring coverage, creating a barrier for new users.

## What Changes

- **ImageDataset regex**: Replace `im_suffix` named group with non-capturing group (remove column); remove `tile` from initial metadata — added only after tiling step
- **Extension auto-detection**: ImageDataset scans directory and auto-detects `.tif` / `.tiff` / `.jpg` / `.jpeg` (enforces one extension per dataset)
- **`filter_` renamed to `filters`**: More idiomatic parameter name
- **Docstrings**: Add/fix function descriptions, parameters, and return types across the entire repo
- **README.md**: Rewrite with dependencies, citation, richer CLI/library usage
- **docs/api.md**: New dedicated API reference file

## Capabilities

### New Capabilities
- `dataset-metadata-improvements`: Extension auto-detection from directory listing; correct column set in metadata (no `im_suffix`, `tile` appears only post-tiling); `filters` parameter name

### Modified Capabilities
- `dataset-subsetting`: The `ImageDataset` init parameter name changes from `filter_` to `filters`

## Impact

| File | Change |
|------|--------|
| `io/dataset.py` | Regex, extension detection, param rename, docstrings |
| `preprocessing/tile_splitter.py` | Add `tile` (int) column after constructing dataset, docstrings |
| `preprocessing/converter.py` | Docstrings |
| `preprocessing/resizer.py` | Docstrings |
| `preprocessing/z_projection.py` | Docstrings |
| `preprocessing/basic_correction.py` | Docstrings |
| `segmentation/cellpose.py` | Docstrings |
| `profiling/image_profiler.py` | Docstrings |
| `profiling/object_profiler.py` | Docstrings |
| `profiling/extras.py` | Docstrings |
| `io/database.py` | Docstrings |
| `io/loaders.py` | Docstrings |
| `pipeline.py` | Docstrings (if missing) |
| `config.py` | Docstrings (if missing) |
| `cli.py` | Docstrings (if missing) |
| `README.md` | Rewrite with deps, citation, usage |
| `docs/api.md` | New file with full API reference |
| `openspec/specs/dataset-subsetting/spec.md` | Update parameter name from `filter_` to `filters` |
