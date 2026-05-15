## Context

Each preprocessing step currently creates its output directory under `ds.measurement_dir`, which is the previous step's output. This creates recursive nesting:

```
unified/resized_0.5/zproject_max/tiles_540x540/
```

The converter writes to `unified/`, then resize creates `unified/resized_0.5/`, then z-projection creates `unified/resized_0.5/zproject_max/`, etc.

Separately, resize is a simple `scipy.ndimage.zoom` call that adds a full I/O pass. And z-projection's group columns (`["well", "field", "timepoint"]`) are hard-coded.

## Goals / Non-Goals

**Goals:**
- All preprocessing step outputs live as siblings under the measurement root dir
- Resize is foldable into conversion (optional `resize_factor` param)
- Z-projection derives group columns dynamically from metadata schema
- CLI reflects new capabilities (`--resize` on convert, `--output-name`)
- Docs updated

**Non-Goals:**
- No change to segmentation or profiling steps (they write alongside source files)
- No change to the vendored BaSiC algorithm
- No change to database schema or profiling output format

## Decisions

### 1. How each step gets the root directory

**Chosen: Pass `root_dir` as an explicit parameter to each preprocessing function**

Each step's public API gains a `root_dir: Path` parameter. The pipeline passes `cfg.input_dir` (the measurement root).

**Alternatives considered:**
- Store `root_dir` on `ImageDataset` → couples data representation to pipeline context
- Compute from `ds.measurement_dir` by walking up → fragile, breaks if InputDataset ever points elsewhere

Signature pattern:
```python
def z_project_dataset(
    ds: ImageDataset,
    root_dir: Path,
    method: str = "max",
    delete_original: bool = False,
) -> ImageDataset:
    output_dir = root_dir / f"zproject_{method}"
```

### 2. Resize integration strategy

**Chosen: `convert_measurement` gains `resize_factor: float = 1.0`**

When `resize_factor != 1.0`, each image is resized via `scipy.ndimage.zoom` before writing to the output directory. The filename stays the same — the resized file replaces what would have been the full-resolution file.

The standalone `resize_dataset` in `resizer.py` is kept (not removed) for users who want to resize an already-converted dataset without re-converting.

In `run_pipeline`, the standalone resize step is removed. If `cfg.resize` is set, its value is passed as `resize_factor` to `convert_measurement` instead.

### 3. Dynamic group columns for z-projection

**Chosen: Compute from metadata columns minus intensity/mask columns and `stack`**

```python
exclude = set(ds.intensity_colnames) | set(ds.mask_colnames) | {"stack", "directory"}
group_cols = [c for c in ds.metadata.columns if c not in exclude]
```

This handles any metadata schema automatically. If `tile` is present, it's included in group_cols (each tile's stacks are projected independently).

### 4. Converter output directory naming

**Chosen: default `"unified"`, configurable via `output_name` parameter**

`convert_measurement` gains an `output_name: str = "unified"` parameter. The output path becomes `root_dir / output_name`. This replaces the current `output_dir` parameter.

**Alternative considered:**
- Keep `output_dir` and add `output_name` → confusing having both
- Simpler to just have `output_name: str = "unified"` and construct path from `root_dir / output_name`

### 5. Pipeline `root_dir` flow

```
run_pipeline(cfg):
    root_dir = cfg.input_dir
    
    # Convert + optional resize
    convert_measurement(root_dir=root_dir, ..., resize_factor=cfg.resize)
    
    ds = ImageDataset(root_dir / "unified")
    
    # BaSiC
    ds = apply_basic(ds, root_dir=root_dir, ...)
    
    # Z-projection
    ds = z_project_dataset(ds, root_dir=root_dir, ...)
    
    # Tile
    ds = tile_dataset(ds, root_dir=root_dir, ...)
    
    # Segment & Profile (unchanged)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Existing scripts rely on nested path structure | This is a **BREAKING** change — document clearly in changelog |
| `root_dir` adds complexity to function signatures | Keeps stateless API design; pipeline orchestrator manages the wiring |
| Removing standalone resize from pipeline surprises users | Keep `resizer.py` module and `resize_dataset()` function, just remove the pipeline step call |
| Dynamic group_cols could pull in unexpected columns | Add a warning log showing the computed group columns |
