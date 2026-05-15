### Requirement: Full pipeline integration test

The system SHALL provide a parametrized integration test (`tests/test_full_pipeline.py`) that exercises the complete pipeline on both Operetta and MICA vendor datasets: convert to unified naming → Cellpose segmentation → image-level profiling → object-level profiling with all extra features → SQLite database output.

#### Scenario: Operetta runs end-to-end with all steps
- **WHEN** the test runs with `vendor="operetta"`
- **THEN** the test copies the Operetta dataset to the `test_result/` sandbox
- **THEN** conversion produces unified `.tiff` files
- **THEN** an `ImageDataset` loads the converted files with non-zero rows and at least 2 intensity channels
- **THEN** Cellpose segmentation (`segment_dataset`) runs with default settings using the first channel as `chan1`
- **THEN** segmentation produces at least one mask PNG file (or the test gracefully handles zero objects)
- **THEN** the dataset is reloaded and contains mask columns
- **THEN** image profiling runs with no thresholds and produces intensity statistics for all channels
- **THEN** object profiling runs with all extras enabled: radial (5 bins), granularity (scales 0-4), GLCM (distances [1,2,3]), and correlation (ch1↔ch2)
- **THEN** a `results.db` file exists and is non-empty
- **THEN** the database contains at least 2 tables: `image` and the mask-name table
- **THEN** the `image` table contains intensity statistic columns (`intensity_mean_*`, `intensity_q*_*`, `intensity_sum_*`) for each channel
- **THEN** the mask table (if objects exist) contains shape, intensity, radial, granularity, GLCM, and correlation columns

#### Scenario: MICA runs end-to-end with all steps
- **WHEN** the test runs with `vendor="mica"`
- **THEN** the test copies the MICA dataset to the `test_result/` sandbox
- **THEN** conversion produces unified `.tiff` files with single-channel images
- **THEN** an `ImageDataset` loads with non-zero rows and exactly 1 intensity channel
- **THEN** the same segmentation, profiling, and DB verification steps apply
- **THEN** correlation profiling is skipped (only 1 channel, no pairs to compute)
- **THEN** the mask table (if objects exist) contains shape, intensity, radial, granularity, and GLCM columns (but no correlation columns)

#### Scenario: Zero objects from segmentation is handled gracefully
- **WHEN** the segmentation produces masks but all masks contain zero labeled objects (or no mask files at all)
- **THEN** the test logs a warning that no objects were found
- **THEN** the test still asserts that image profiling ran and produced valid results
- **THEN** the test still asserts that the DB contains an `image` table with correct columns
- **THEN** the test skips object table column assertions (mask table may be absent or empty)

#### Scenario: Test is gated as a slow/release test
- **WHEN** the test is defined
- **THEN** it SHALL be decorated with `@pytest.mark.slow`
- **THEN** it SHALL be runnable via `pytest tests/test_full_pipeline.py -m slow`
- **THEN** daily CI shall use `pytest -m "not slow"` to skip it
