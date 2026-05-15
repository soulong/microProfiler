## Context

After two rounds of pipeline bug fixes, 37 lint issues remain in non-vendored code (15 unused imports, 22 long lines). Several docstrings are stale after the column rename and segmentation shape changes. The `field` metadata column is the only identifier column not converted to numeric. The `microprofiler run` command has zero end-to-end test coverage.

## Goals / Non-Goals

**Goals:**
- Zero F401 (unused import) errors in non-vendored code
- No E501 (line too long) errors exceeding 100 chars in non-vendored code
- `field` column is numeric in metadata (consistent with `zslice`/`timepoint`)
- Docstrings match actual behavior for column names and shapes
- At least one end-to-end test for `microprofiler run`

**Non-Goals:**
- No changes to vendored BaSiC code (any errors there are preserved)
- No changes to W293/W291/F841/F822 errors in vendored code
- No behavior changes to any module
- No new features

## Decisions

### 1. Unused imports (F401)

Use `ruff check --fix` (auto-fix). This handles all 15 F401 errors in one pass. Manual verification after.

**Files affected**: `examples/quickstart.py`, `io/database.py`, `io/dataset.py`, `preprocessing/basic_correction.py`, `preprocessing/converter.py`, `preprocessing/resizer.py`, `preprocessing/tile_splitter.py`, `preprocessing/z_projection.py`, `segmentation/cellpose.py`, `tests/test_pipeline.py`

### 2. Long lines (E501)

Wrap manually. No auto-fix available. Each file should be checked individually and lines over 100 chars broken at logical boundaries (argument lists, list comprehensions, string concatenations).

**Files affected**: `cli.py`, `config.py`, `io/dataset.py`, `preprocessing/basic_correction.py`, `profiling/image_profiler.py`, `tests/test_pipeline.py`

### 3. Field numeric conversion

Add `"field"` to the `dtype_cols` list in `dataset.py:build_metadata()`:

```python
dtype_cols = ["zslice", "timepoint", "field"]
```

**Rationale**: `field` is parsed from regex as a digit string and should be numeric for sorting and comparison, consistent with the other identifier columns.

### 4. Docstring fixes

| File | Line | Current | Correct |
|------|------|---------|---------|
| `segmentation/cellpose.py` | 79 | `(2, H, W)` | `(2, H, W) or (1, H, W)` |
| `profiling/extras.py` | 72 | `RadialDistribution_bin{i}_ch{channel}` | `radial_bin{i}_ch{channel}` |
| `profiling/extras.py` | 140 | `Granularity_scale{s}_ch{channel}` | `granularity_scale{s}_ch{channel}` |
| `profiling/extras.py` | 214 | `GLCM_{prop}_d{distance}_ch{channel}` | `glcm_{prop}_d{distance}_ch{channel}` |

### 5. CLI run test

Add `test_cli_run` to `tests/test_pipeline.py` that:
1. Converts Operetta test data to unified format (via a helper that reuses the existing convert logic)
2. Runs `microprofiler run` with `--format operetta --z-projection max --tile 256 256 --profile-image`
3. Verifies exit code 0 and checks that `results.db` was created at the measurement root

**Rationale**: This exercises the full CLI argument parsing → config building → pipeline orchestration path, which is currently completely untested. Operetta test data is used because it has Z-stacks (enabling z-projection) and is small enough for fast test execution.

**Note**: The test skips `--segment` since Cellpose-SAM requires GPU and model download. The `--profile-object` path is also skipped since no masks exist at conversion time.

## Risks / Trade-offs

- **[CLI Run Test]**: Creates a `results.db` file in the test data directory during the test. `_clean_output_dir` fixture cleanup handles this. Risk: if the test crashes before cleanup, a stale DB remains. Mitigation: clean up in `try/finally` block.
- **[Auto-fix imports]**: `ruff check --fix` may remove imports that are used only via `__all__` re-exports. Mitigation: run `pytest` after to confirm no breakage.
