## 1. Environment file

- [x] 1.1 Create `micro.yml` at repo root with conda-forge dependencies (python>=3.10, numpy, pandas, scipy, scikit-image, tifffile, cellpose, torch, jax, pyyaml, tqdm, pytest, pytest-cov)
- [x] 1.2 Add pip section for conda-lagging packages (natsort, pydantic>=2.0, ruff)
- [x] 1.3 Add post-create comment/instruction about `pip install -e .`

## 2. API docs — D1 parameter tables

- [x] 2.1 `ImageDataset` — full table for __init__ params, methods signature cleanup
- [x] 2.2 `convert_measurement` — full parameter table
- [x] 2.3 `resize_dataset` — full parameter table
- [x] 2.4 `z_project_dataset` — full parameter table
- [x] 2.5 `tile_dataset` — full parameter table
- [x] 2.6 `fit_models`, `transform_images`, `apply_basic` — full parameter tables
- [x] 2.7 `segment_dataset` — full parameter table (all 15+ params)
- [x] 2.8 `measure_single_image`, `profile_images` — full parameter tables
- [x] 2.9 `measure_objects` — full parameter table
- [x] 2.10 `profile_objects` — full parameter table

## 3. README update

- [x] 3.1 Update installation section with `conda env create -f micro.yml` workflow
- [x] 3.2 Reference `micro.yml` as the recommended setup method

## 4. Verify

- [x] 4.1 Verify `micro.yml` is valid YAML (conda started resolving it successfully)
- [x] 4.2 Verify `docs/api.md` renders cleanly in markdown
