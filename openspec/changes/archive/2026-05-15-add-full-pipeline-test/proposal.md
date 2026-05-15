## Why

The pipeline's two most critical modules — Cellpose segmentation and object-level profiling — have zero integration test coverage. Existing tests exercise these in isolation (synthetic data) or skip them entirely. Without a real-data end-to-end test, regressions in mask file I/O, model loading, DB schema, or the interaction between segmentation and downstream profiling go undetected until release time.

## What Changes

- Add a single new integration test file `tests/test_full_pipeline.py` that runs the full pipeline (convert → segment → image profile → object profile → DB) against both Operetta and MICA test datasets
- No changes to existing application code, test infrastructure, or test data
- Test is marked as a release-level smoke test, not a per-commit test

## Capabilities

### New Capabilities
- `full-pipeline-integration`: End-to-end smoke test that exercises conversion, Cellpose segmentation (real model, GPU), image-level profiling, object-level profiling with all extra features enabled, and SQLite database writing — verified on both Operetta and MICA vendor formats

### Modified Capabilities

None. No existing specs or requirements change.

## Impact

- New test file: `tests/test_full_pipeline.py`
- No changes to existing application code (`microProfiler/`), test data, or existing tests
- Test requires the `cellpose` conda environment (GPU available), runs before releases only
- Existing 21 tests remain untouched; no regressions expected
