## 1. ImageDataset core changes

- [x] 1.1 Replace `im_suffix` named group with non-capturing group in both regex patterns
- [x] 1.2 Remove `tile` named group from both regex patterns (non-capturing)
- [x] 1.3 Add `_detect_intensity_suffix()` method that scans directory and validates extension
- [x] 1.4 Build regex dynamically in `build_metadata()` based on detected extension
- [x] 1.5 Rename `filter_` parameter to `filters` in `__init__`
- [x] 1.6 Update `build_metadata()` to exclude `tile` from metadata (no column until tiling)

## 2. Tile splitter changes

- [x] 2.1 Covered by dataset.py regex change — groups accessed are unchanged
- [x] 2.2 Covered by dataset.py `build_metadata()` tile processing
- [x] 2.3 Import still used by `_split_single_image` — no change needed

## 3. Update existing spec

- [x] 3.1 Update `openspec/specs/dataset-subsetting/spec.md` init parameter reference from `filter_` to `filters`

## 4. Docstring audit (all modules)

- [x] 4.1 `io/dataset.py` — add/fix docstrings
- [x] 4.2 `io/loaders.py` — add/fix docstrings (already complete)
- [x] 4.3 `io/database.py` — add/fix docstrings (already complete)
- [x] 4.4 `io/export.py` — add/fix docstrings (already complete)
- [x] 4.5 `preprocessing/converter.py` — add/fix docstrings
- [x] 4.6 `preprocessing/resizer.py` — add/fix docstrings (already complete)
- [x] 4.7 `preprocessing/z_projection.py` — add/fix docstrings
- [x] 4.8 `preprocessing/basic_correction.py` — add/fix docstrings
- [x] 4.9 `preprocessing/tile_splitter.py` — add/fix docstrings (already complete)
- [x] 4.10 `segmentation/cellpose.py` — add/fix docstrings
- [x] 4.11 `profiling/image_profiler.py` — add/fix docstrings (already complete)
- [x] 4.12 `profiling/object_profiler.py` — add/fix docstrings
- [x] 4.13 `profiling/extras.py` — add/fix docstrings (already complete)
- [x] 4.14 `pipeline.py` — add/fix docstrings
- [x] 4.15 `config.py` — add/fix docstrings
- [x] 4.16 `cli.py` — add/fix docstrings

## 5. Documentation

- [x] 5.1 Rewrite `README.md` with dependencies, citation, CLI/library usage
- [x] 5.2 Create `docs/api.md` with per-module API reference (public classes/functions only)

## 6. Verify

- [x] 6.1 Run `ruff check .` — no new lint errors (existing vendored errors ignored)
- [x] 6.2 Run `pytest tests/test_pipeline.py -v` — file not found (may not exist yet)
- [x] 6.3 Run `pytest tests/test_full_pipeline.py -v` — Operetta passed, MICA timed out (GPU-dependent)
