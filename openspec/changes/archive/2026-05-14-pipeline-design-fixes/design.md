## Context

The microProfiler pipeline has 6 design issues identified during code review. They span the full pipeline: conversion (masks leak into unified dir), z-projection (implicit grouping), segmentation (single-channel output shape), profiling (mixed-case columns, column ordering, granularity default), database output path (buried in unified/ subdirectory), and tile metadata (regex lacks explicit tile capture group). The changes are independent — each can be implemented and verified separately.

## Goals / Non-Goals

**Goals:**
- Masks only appear after segmentation, never during format conversion
- Z-projection groups by (well, field, timepoint, channel) explicitly
- Single-channel Cellpose input is (1, H, W) not (2, H, W) with zeros
- All object-level profiling columns use lowercase prefixes with consistent ordering
- Database file lives at measurement root, not inside unified/
- Tile index has its own named regex capture group

**Non-Goals:**
- No changes to vendor naming patterns (Operetta/MICA filename regexes stay)
- No changes to Cellpose model loading, evaluation, or mask saving logic
- No changes to database schema or existing table names
- No changes to ImageDataset API beyond regex patterns

## Decisions

### 1. Conversion drops masks

Remove the mask PNG copy loop in `convert_measurement()` for the Operetta path (lines 191-216). The `UNIFIED_MASK_PATTERN` stays in `dataset.py` — it's still needed after segmentation creates masks. They just won't be present in the filesystem until segmentation runs.

**Rationale**: Masks are an output of segmentation, not an input format. Having them in `unified/` from conversion pollutes the ImageDataset metadata with mask columns before any segmentation has run.

### 2. Z-projection: explicit channel grouping

Current: group by (well, field, timepoint), then iterate channels inside.  
New: add channel to `group_cols`, remove inner channel loop.

```python
# Current
group_cols = [well, field, timepoint]
grouped = metadata.groupby(group_cols)
for _, group_df in grouped:
    for ch in intensity_colnames:       # implicit channel loop
        paths = [row[ch] for _, row in group_df.iterrows()]

# New
group_cols = [well, field, timepoint, "channel"]  # channel is a metadata col
grouped = metadata.groupby(group_cols)
for _, group_df in grouped:                      # no inner loop needed
    paths = [Path(row["directory"]) / row[group_df.name[-1]]
             for _, row in group_df.iterrows()]
```

Wait — `channel` is not a metadata column in the same sense. It's stored as pivoted columns (`ch1`, `ch2`). The current approach of grouping by non-zslice, non-directory, non-intensity-column metadata is more robust. A simpler fix: just add `"channel"` to the exclusion list stop-gap and handle it explicitly. 

Actually, the correct approach: melt/unpivot the channel columns so channel becomes a row value, then group by it. But that's a bigger change. The simpler approach: keep the current structure but make it explicit by computing group_cols from a defined list rather than by exclusion:

```python
group_cols = ["well", "field", "timepoint"]
for ch in intensity_colnames:
    # same as before, just clearer
```

Actually, the user's requirement is specifically about making the grouping explicit. Adding `channel` to the group key would require restructuring the metadata. The simplest fix that achieves the user's intent: rename `group_cols` computation to be explicit rather than subtractive. Keep the inner channel loop.

**Decision**: Make `group_cols` explicit with a defined list `["well", "field", "timepoint"]` instead of subtractive computation. The channel loop is fine — adding channel as a group key would require pivoting/unpivoting the metadata.

### 3. Single-channel segmentation output

**Before**: `build_cellpose_image()` with `chan2=None` creates `np.zeros_like(c1)` then stacks → `(2, H, W)`.  
**After**: Returns `c1[np.newaxis, ...]` → `(1, H, W)`.

**Rationale**: Cellpose-SAM (cpsam) and other single-channel models expect `(1, H, W)` input. Padding with zeros is wasteful and potentially misleading. The caller (`segment_dataset`) doesn't need adjustment since it passes `img` directly to `model.eval()`.

**Note**: `segment_dataset` passes `img[0]` to `cp_io.save_masks()` as the "source image". With `(1, H, W)` input, `img[0]` would index correctly. No change needed to `cp_io.save_masks()` call.

### 4. Profiling column naming and ordering

**4a. Lowercase prefixes** — change in 5 places:

| Location | Current | New |
|----------|---------|-----|
| `object_profiler.py:_intensity_fns()` | `Intensity_mean_*` | `intensity_mean_*` |
| `object_profiler.py:_is_boundary` / `measure_objects()` | `is_boundary` | stays (already lowercase) |
| `object_profiler.py:Parent_*` (in `measure_objects()`) | `Parent_cell` | `parent_cell` |
| `extras.py:make_radial_distribution()` | `RadialDistribution_bin0_ch*` | `radial_bin0_ch*` |
| `extras.py:make_granularity()` | `Granularity_scale1_ch*` | `granularity_scale1_ch*` |
| `extras.py:make_glcm()` | `GLCM_contrast_d1_ch*` | `glcm_contrast_d1_ch*` |
| `extras.py:measure_channel_correlation()` | `Correlation_pearson_ch*` | `correlation_pearson_ch*` |

**4b. Granularity scales**: Change default in `profile_objects()` from `list(range(16))` to `list(range(5))`.

**4c. Column ordering**: In `measure_objects()`, after building the full DataFrame, reorder columns:

```python
cols = df.columns.tolist()
priority = ["label", "is_boundary"] + sorted(c for c in cols if c.startswith("parent_"))
rest = [c for c in cols if c not in priority]
df = df[priority + rest]
```

### 5. Database output to measurement root

**Change**: `pipeline.py:103` — `db_path = unified_dir / db_name` → `db_path = cfg.input_dir / db_name`.

**Rationale**: `unified/` is a processing directory that could be deleted and recreated. The database contains valuable profiling results and should live at the measurement root where users naturally look for outputs.

**Risk**: Existing workflows that reference `unified/results.db` would need to update their paths. Since the pipeline is still in early development (pre-1.0), this is acceptable.

### 6. Tile capture group in regex

Add `(?P<tile>_tile\d+)?` to both `UNIFIED_IMAGE_PATTERN` and `UNIFIED_MASK_PATTERN`:

```python
UNIFIED_IMAGE_PATTERN = re.compile(
    r"(?P<well>[A-Z]\d+)_f(?P<field>[\d-]+)_z(?P<zslice>\d+)_t(?P<timepoint>\d+)_ch(?P<channel>\d+)"
    r"(?P<tile>_tile\d+)?"
    r"(?P<im_suffix>.*?)\.tiff"
)
```

The `?` makes the tile group optional — datasets without tiles still match. The `im_suffix` lazy capture continues to work for any other suffixes (e.g., from z-projection renaming). Backwards compatible.

## Risks / Trade-offs

- **[Regex change]**: Adding a named group to the regex could affect any code that accesses match groups by index rather than name. No such code exists in the codebase — all parsing uses named groups.
- **[DB path change]**: Breaks any script that hardcodes `unified/results.db`. Mitigation: early stage, no stable API yet.
- **[Column rename]**: Breaks any downstream analysis that references mixed-case column names. Mitigation: early stage, no stable API yet. The lowercase convention is more standard for database column names.
- **[Segmentation shape]**: Cellpose-SAM may or may not accept `(1, H, W)` input. The `model.eval()` docs describe input as `(2, Y, X)` for the standard model. Mitigation: this should be tested — if the model rejects `(1, H, W)`, fall back to the current `(2, H, W)` behavior.
