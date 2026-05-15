## Context

The repo currently has no conda environment file. Users must read `pyproject.toml` to know what to install, or rely on `pip install -e .` which doesn't handle conda-specific setups (torch with CUDA, jax, etc.).

`docs/api.md` was created as a concise reference. After the last two implementation cycles, it's been updated for new signatures but still lacks depth on complex functions. A user reading it can't tell what all the parameters of `segment_dataset` or `measure_objects` do without reading source code.

## Goals / Non-Goals

**Goals:**
- `micro.yml` at repo root that mirrors `pyproject.toml` dependencies, with conda-forge for most packages and pip for lagging ones
- Expanded `docs/api.md` with parameter tables for all pipeline-orchestrating functions
- README updated to reference `micro.yml`

**Non-Goals:**
- No change to actual package dependencies or code
- No generated docs (Sphinx, MkDocs) — markdown only
- No `requirements.txt` — conda is the target

## Decisions

### 1. micro.yml structure

**Chosen: Hand-curated, loose version pins, split conda-forge/pip**

The file follows standard conda `environment.yml` format with two sections:
- `dependencies` (conda-forge): `python>=3.10, numpy, pandas, scipy, scikit-image, tifffile, cellpose, torch, jax, pyyaml, tqdm, pytest, pytest-cov`
- `pip`: `natsort, pydantic>=2.0, ruff` (packages where conda version often lags or don't exist on conda-forge)

Post-install step: `pip install -e .` to register the local package.

**Alternative considered:** `conda env export --from-history` — too minimal (only 6 packages). Full `conda env export` — too verbose and platform-specific.

### 2. API docs tiering (D1 vs D2)

**Chosen: D1 table format for complex functions, D2 inline for simple ones**

D1 format (parameter table):
```
#### `function_name`(param1, param2=default)

Description paragraph.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| param1 | type | — | Description |
| param2 | type | value | Description |

**Returns:** type — description
```

D2 format (inline):
```
#### `function_name`(param1, param2=default)

Description. Returns type — description.
```

**Which functions get which:**

| Level | Functions |
|-------|-----------|
| D1 (table) | ImageDataset.__init__, get_imageset, build_metadata, convert_measurement, resize_dataset, z_project_dataset, tile_dataset, fit_models, transform_images, apply_basic, segment_dataset, measure_single_image, profile_images, measure_objects, profile_objects |
| D2 (inline) | read_image, write_image, IntensityNormalizer, Database, write_results_to_db, write_dataloader, make_radial_distribution, make_granularity, make_glcm, measure_channel_correlation, _detect_intensity_suffix |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| micro.yml drifts from pyproject.toml over time | Keep it minimal — only the 12 direct deps. Review during dependency updates. |
| Parameter tables make api.md very long | Use clear section headers and collapsible structure. Complex functions are worth the space. |
