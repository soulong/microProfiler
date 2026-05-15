## Why

The codebase has accumulated 37 lint issues (15 unused imports, 22 long lines) in non-vendored code, several stale docstrings that reference old column names, a missing numeric conversion for the `field` metadata column, and a complete absence of end-to-end testing for the `microprofiler run` command. These are all small, independent fixes that improve code quality without changing any behavior.

## What Changes

1. **Remove 15 unused imports** — auto-fixable with `ruff check --fix` across 10 files
2. **Wrap 22 long lines** — manual wrapping to meet the 100-char limit in 6 files
3. **Convert `field` to numeric** in `io/dataset.py:build_metadata()` — consistent with existing `zslice`/`timepoint` conversion
4. **Fix stale docstrings** — `segmentation/cellpose.py:79` (output shape), `profiling/extras.py:72,140,214` (column name prefixes)
5. **Add `microprofiler run` CLI test** — end-to-end test exercising CLI arg parsing and pipeline chaining

## Capabilities

### New Capabilities

None. All changes are code quality and test improvements.

### Modified Capabilities

None. No spec-level behavior changes.

## Impact

- **`microProfiler/io/dataset.py`**: Add `field` to numeric column conversion list
- **`microProfiler/segmentation/cellpose.py`**: Fix docstring
- **`microProfiler/profiling/extras.py`**: Fix 3 docstrings
- **`tests/test_pipeline.py`**: Add `test_cli_run` integration test
- **10 other files**: Unused import removal (`ruff check --fix`); long line wrapping (manual)
