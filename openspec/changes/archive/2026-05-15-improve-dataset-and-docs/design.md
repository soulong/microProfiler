## Context

ImageDataset constructs metadata by scanning a directory, matching filenames against a regex with named groups (`well`, `field`, `stack`, `timepoint`, `channel`, `im_suffix`, `tile`), and pivoting into a DataFrame. Two issues:

1. **Column pollution**: `im_suffix` and `tile` are meaningful only for file matching, not as metadata. `tile` should appear only after the tiling step, but the regex extracts it unconditionally.
2. **Hardcoded `.tiff`**: The regex ends with `\.tiff`, so pre-converted datasets with `.tif`, `.jpg`, or `.jpeg` extensions fail.
3. **`filter_`**: Uses trailing-underscore convention to avoid shadowing builtin `filter`, but `filters` (plural) is cleaner.

Separately, docstrings across the repo are inconsistent or missing, and the repo has no dedicated API reference.

## Goals / Non-Goals

**Goals:**
- Auto-detect intensity image extension (.tif/.tiff/.jpg/.jpeg) from the directory, enforce consistency
- Remove `im_suffix` and `tile` columns from initial metadata; add `tile` only after tiling
- Rename `filter_` to `filters` in `ImageDataset.__init__`
- Full docstring audit: every public function/class gets Parameters, Returns, and description
- README.md with dependencies, citation, CLI/library usage
- docs/api.md with full API reference

**Non-Goals:**
- No change to mask detection (always `.png`)
- No change to the converter (always writes `.tiff`)
- No change to pipelining logic, profiling, segmentation algorithms
- No Sphinx/MkDocs build setup — markdown is the delivery format

## Decisions

### 1. Extension detection strategy

**Chosen: Scan + validate in `build_metadata()`**

Scan the measurement directory for files matching `*.tif`, `*.tiff`, `*.jpg`, `*.jpeg`. If exactly one extension is present, use it. If none found, error. If multiple found, error with details.

**Alternatives considered:**
- Make the regex match all four extensions simultaneously → possible but creates ambiguity (e.g., `file.tiff` and `file.tif` coexist)
- Accept an explicit `suffix` parameter → defeats "automatic" requirement; users shouldn't need to know the extension

### 2. Regex column control

**Chosen: Remove named groups + post-process tile**

- Convert `(?P<im_suffix>.*?)` to `(?:.*?)` — the value is never needed
- Convert `(?P<tile>_tile\d+)?` to `(?:_tile\d+)?` — the value isn't needed at parse time
- In `tile_dataset`, after creating `ImageDataset(tile_dir)`, parse tile indices from filenames and set `metadata["tile"] = int`

**Why not exclude columns after extraction?**
- `im_suffix` with `.*?` always captures an empty string, which then requires filtering at the column level — noisy
- `tile` with the non-capturing approach makes the metadata cleaner: no NaN column pre-tiling, no column at all until it's meaningful

### 3. `filter_` → `filters`

Renamed because:
- `filters` is idiomatic for `Dict[str, str]` — implies multiple filter rules
- Doesn't shadow Python's `filter()` builtin
- Existing callers (zero in codebase) don't need migration

### 4. Docstring standard

All public functions and methods get:
```python
def func(param1: type, param2: type) -> ReturnType:
    """One-line description.

    Parameters
    ----------
    param1 : type
        Description.
    param2 : type, optional
        Description (default ``value``).

    Returns
    -------
    ReturnType
        Description.
    """
```
Following NumPy-style docstrings (already used in the codebase).

### 5. Documentation structure

```
README.md          ← Install, deps, quick start, CLI examples, citation
docs/api.md        ← Per-module API reference: every public class/function
```

README focuses on "get started in 2 minutes". API.md is the reference you open when you need exact parameter types.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Extension auto-detect might match non-image files (e.g., `.tiff` sidecar files) | Only check for our well-known extension list; if ambiguous data exists, user can still pass explicit `image_pattern` |
| Removing `im_suffix` from regex could break matching for files with unexpected suffixes appended by custom pipeline steps | Non-capturing `(?:.*?)` preserves the same matching flexibility without creating a column |
| Docstring audit is mechanical and may miss edge cases | Review each module's public API; focus on exported names in `__all__` or non-underscore-prefixed functions |
| Existing users relying on `filter_=` keyword (private/internal use) | No known users; the parameter is used in zero call sites in the repo |
