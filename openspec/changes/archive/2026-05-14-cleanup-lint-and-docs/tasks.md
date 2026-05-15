## 1. Unused imports

- [x] 1.1 Run `ruff check --fix` to auto-remove all 15 unused imports
- [x] 1.2 Run `pytest` to verify no breakage after auto-fix

## 2. Long lines

- [x] 2.1 Wrap long lines in `cli.py` (8 lines, lines 29-37)
- [x] 2.2 Wrap long lines in `config.py` (6 lines, lines 33,34,37,78,79,84,87)
- [x] 2.3 Wrap long lines in `io/dataset.py` (3 lines, lines 135,148,150)
- [x] 2.4 Wrap long lines in `preprocessing/basic_correction.py` (3 lines, lines 110,167,205)
- [x] 2.5 Wrap long lines in `profiling/image_profiler.py` (1 line, line 125)
- [x] 2.6 Wrap long lines in `tests/test_pipeline.py` (1 line, line 65)

## 3. Field numeric conversion

- [x] 3.1 Add `"field"` to `dtype_cols` list in `io/dataset.py:build_metadata()`

## 4. Docstring fixes

- [x] 4.1 Fix docstring in `segmentation/cellpose.py:79` — `(2, H, W)` → `(2, H, W) or (1, H, W)`
- [x] 4.2 Fix docstring in `profiling/extras.py:72` — `RadialDistribution_` → `radial_`
- [x] 4.3 Fix docstring in `profiling/extras.py:140` — `Granularity_` → `granularity_`
- [x] 4.4 Fix docstring in `profiling/extras.py:214` — `GLCM_` → `glcm_`

## 5. CLI run integration test

- [x] 5.1 Add `test_cli_run` to `tests/test_pipeline.py` that runs `microprofiler run` with `--format operetta --z-projection max --tile 256 256 --profile-image` and verifies exit code 0 + `results.db` created

## 6. Verify

- [x] 6.1 Copy test data to test_result directories
- [x] 6.2 Run `pytest tests/test_pipeline.py -v` and confirm all tests pass
- [x] 6.3 Run `ruff check .` and confirm no new lint errors in non-vendored code
