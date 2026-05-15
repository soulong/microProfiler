## 1. Converter resize integration

- [x] 1.1 Change `convert_measurement` signature: replace `output_dir` with `root_dir: Path` + `output_name: str = "unified"`; add `resize_factor: float = 1.0`
- [x] 1.2 Resize images during conversion write loop when `resize_factor != 1.0`
- [x] 1.3 Update `_build_unified_name` callers to use new `root_dir / output_name` path

## 2. Flat output structure — all preprocessing steps

- [x] 2.1 Add `root_dir` parameter to `resize_dataset`; use `root_dir / f"resized_{scale}"` instead of `ds.measurement_dir / ...`
- [x] 2.2 Add `root_dir` parameter to `apply_basic`, `fit_models`, `transform_images`; use `root_dir / "BaSiC_model"` and `root_dir / "BaSiC_corrected"`
- [x] 2.3 Add `root_dir` parameter to `z_project_dataset`; use `root_dir / f"zproject_{method}"`
- [x] 2.4 Add `root_dir` parameter to `tile_dataset`; use `root_dir / f"tiles_{W}x{H}"`

## 3. Dynamic group columns in z-projection

- [x] 3.1 In `z_project_dataset`, compute group_cols dynamically: all metadata columns minus intensity/mask/stack/directory
- [x] 3.2 Add log message showing computed group columns for transparency

## 4. Pipeline orchestrator updates

- [x] 4.1 Pass `cfg.input_dir` as `root_dir` through all preprocessing steps
- [x] 4.2 Remove standalone resize step from `run_pipeline`; pass `cfg.resize.scale_factor` to `convert_measurement` instead
- [x] 4.3 Update `ImageDataset(unified_dir)` to use `root_dir / "unified"` path

## 5. Config and CLI updates

- [x] 5.1 Add `ConvertConfig` pydantic model with `output_name` and `resize_factor` fields
- [x] 5.2 Add `ConvertConfig` field to `PipelineConfig`
- [x] 5.3 Add `--resize` flag to `convert` subcommand in CLI
- [x] 5.4 Add `--output-name` flag to both `run` and `convert` subcommands
- [x] 5.5 Update `main()` to wire new CLI flags to config

## 6. Documentation

- [x] 6.1 Update `README.md` pipeline diagram, CLI examples, and description
- [x] 6.2 Update `docs/api.md` signatures for changed functions
- [x] 6.3 Add changelog or breaking-change note for path restructuring

## 7. Verify

- [x] 7.1 Run `ruff check .` — no new lint errors (only vendored basic/ errors remain)
- [x] 7.2 Run `pytest tests/test_full_pipeline.py -v -k operetta` — PASSED
- [x] 7.3 Verify flat output layout manually against a test run
