## 1. Create test file scaffold

- [x] 1.1 Create `tests/test_full_pipeline.py` with imports, marker registration, test data path constants, and cleanup helper (reuse `_clean_output_dir` pattern from existing tests)
- [x] 1.2 Register the `slow` marker in `pyproject.toml` under `[tool.pytest.ini_options]`

## 2. Implement the parameterized test function

- [x] 2.1 Define `@pytest.mark.slow` + `@pytest.mark.parametrize("vendor", ["operetta", "mica"])` test function
- [x] 2.2 Implement vendor-specific setup: copy test data to `test_result/`, handle vendor-specific directory structures
- [x] 2.3 Run `convert_measurement` with the vendor format and verify converted files exist
- [x] 2.4 Load `ImageDataset` from converted output and assert non-zero rows
- [x] 2.5 Run `segment_dataset` with default settings (first channel as chan1, auto-diameter)
- [x] 2.6 Reload `ImageDataset` to pick up mask columns; handle zero-mask case gracefully

## 3. Add profiling and DB verification

- [x] 3.1 Run `profile_images` with no thresholds; assert DataFrame result columns
- [x] 3.2 Run `profile_objects` with all extras enabled: radial (5 bins), granularity (scales 0-4), GLCM (distances [1,2,3]), correlation (all channel pairs)
- [x] 3.3 Write profiling results to `results.db` (image → `image` table, objects → mask name table)
- [x] 3.4 Verify `results.db` exists and is non-empty using `Database` API
- [x] 3.5 Assert `image` table contains expected intensity columns for each channel
- [x] 3.6 If objects exist: assert mask table contains shape, intensity, radial, granularity, GLCM, and correlation columns; verify correlation columns only present when vendor has 2+ channels

## 4. Verify and lint

- [x] 4.1 Run `ruff check .` and fix any lint issues in the new test file
- [x] 4.2 Run `pytest tests/test_full_pipeline.py -v -m slow` to confirm the test passes end-to-end on both vendors
- [x] 4.3 Run `pytest tests/test_pipeline.py -v` to confirm existing tests are unaffected
