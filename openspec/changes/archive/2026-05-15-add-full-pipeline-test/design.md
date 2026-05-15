## Context

The `microProfiler` pipeline has 21 existing tests, but the two heaviest modules — Cellpose segmentation (`segmentation/cellpose.py`, 243 lines) and object profiling on real data (`profiling/object_profiler.py`) — have zero integration coverage. The existing `test_cli_run` exercises conversion → z-projection → tiling → image profiling → DB, but skips segmentation and object profiling entirely. This means regressions in mask I/O, Cellpose model loading, DB schema construction from profiling results, and the interaction between pipeline stages go undetected until manual release testing.

The project has two vendor-specific test datasets (Operetta, MICA) in `tests/test_dataset/` that are copied to `tests/test_dataset/test_result/` before test runs. The conda `cellpose` environment has GPU available.

## Goals / Non-Goals

**Goals:**
- Add one integration test function (parameterized over Operetta and MICA) that runs: convert → segment → image profile → object profile (all extras) → verify DB
- Validate the DB contains the correct 3 tables (metadata, image, mask) with expected column schemas
- Handle zero-object segmentation gracefully (skip object assertions, keep image assertions)
- Mark the test so it runs before releases, not on every commit

**Non-Goals:**
- No changes to existing application code, test infrastructure, test data, or existing 21 tests
- No conversion of existing tests to the new parameterized approach
- No speed optimization of existing tests
- No GPU-free fallback path (test requires GPU)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test location | New file `tests/test_full_pipeline.py` | Keeps the existing 21 tests untouched; no risk of breaking CI cadence. |
| Parameterization | `@pytest.mark.parametrize("vendor", ["operetta", "mica"])` | Single test body, maximum coverage per LOC. |
| Release gating | `@pytest.mark.slow` marker | `pytest -m "not slow"` for daily CI, `pytest -m slow` or full suite before release. |
| Segmentation default | First intensity channel, no resize, auto-diameter | Matches common user workflow; tests the default code path. |
| Image profiling | No thresholds (intensity stats only) | User explicitly requested this; simpler assertion (just check columns exist). |
| Object extras | Enable all: radial (5 bins), granularity (scales 0-4), GLCM (distances [1,2,3]), correlation (ch1↔ch2 if 2+ channels) | Tests every extra property factory in a real pipeline context. |
| Zero objects | Soft skip — assert image profiling succeeded, log warning, skip object assertions | Pipeline handles this in production; the test should not fail on empty but valid output. |
| DB verification | Check file exists, read tables via `Database` API, assert column names | Tests both the write path and the `Database` read API. |
| DB table name for objects | Uses the mask name as table name (e.g., `"cell"`) | This is what `profile_objects` does by default — validates the naming convention end-to-end. |

## Risks / Trade-offs

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cellpose model download fails (no internet) | Low (release env has network) | Fail with clear error message; release blocker. |
| Segmentation finds zero objects on test data | Medium | Test handles gracefully — skips object assertions, logs warning. |
| GPU OOM on large Cellpose model | Low (test images are small, ~512×512) | Not mitigated; would be caught during manual testing. |
| Test becomes slow as test data grows | Low (test data is fixed) | PR review should flag data additions. |
| Test bitrots (always passes vacuously) | Low | DB schema assertions fail if any step silently no-ops. |
