## Context

The pipeline integration test revealed 9 issues that span 7 source files, 2 test files, and affect everything from column naming to API contracts. Most fixes are isolated, but two are cross-cutting: the `zslice`→`stack` rename (touches regex, metadata, preprocessing, profiling, tests) and the `segment_dataset` return type change (touches callers in pipeline.py and tests).

All fixes are in Python source. No new dependencies, no data migration, no schema changes at the storage level (SQLite schema adapts automatically from DataFrame column names).

## Goals / Non-Goals

**Goals:**
- Fix all 9 issues identified during integration testing
- Maintain backward compatibility for `filter_metadata` (new method, no existing code breaks)
- Column names in profiling output are consistent and predictable
- Boundary detection correctly flags edge-touching objects
- `segment_dataset` returns a ready-to-use dataset (no manual `build_metadata()` call needed)

**Non-Goals:**
- No changes to the unified filename pattern (`_z{number}_` stays in filenames, only the internal column renames)
- No changes to the SQLite schema or file storage format
- No performance optimization beyond the scope of these fixes

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `zslice`→`stack` rename scope | Internal column only, filename pattern stays `_z{number}_` | Renaming files would break reproducibility and require migration. The column rename is the user-facing fix. |
| `is_boundary` algorithm | Bounding-box edge check instead of pixel fraction threshold | Simpler, intuitive — if the object's bounding box touches any image edge, it's truncated. The old 0.25 fraction let edge-touching objects through. |
| `segment_dataset` return type | Returns `ImageDataset` (original + masks loaded) | Eliminates the error-prone manual `build_metadata()` call after segmentation. Callers get a ready-to-use dataset. The summary dict is dropped — callers check `len(ds.mask_colnames)` instead. |
| `filter_metadata` mutability | Modifies `_metadata` in-place, returns `self` | Users can chain calls or assign to new variable. No re-scanning of directory needed — cheap enough to call multiple times for different processing branches. |
| Converter tqdm removal | Replace with simple counter + final log | Pipeline and CLI already log summaries. Per-file tqdm is noise in scripts and test output. |
| GLCM entropy addition | Add `"entropy"` to `_GLCM_PROPS` | Supported by skimage `graycoprops` since 0.22. No compatibility concern given project Python requirements. |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `zslice`→`stack` missed references | `grep -rn "zslice" microProfiler/ tests/` after changes |
| `segment_dataset` return type breaks external code | This is **BREAKING** — documented in proposal. No known external consumers. |
| `filter_metadata` in-place mutation surprises | Documented clearly as in-place. Method name `filter_metadata` implies filtering action. |
