## ADDED Requirements

### Requirement: Preprocessing output directories are flat under measurement root

All preprocessing steps SHALL write their output to sibling directories directly under the measurement root directory, not nested under the previous step's output directory.

#### Scenario: Resize outputs to root sibling

- **WHEN** `resize_dataset()` is called with `root_dir=Path("/meas/")` and `scale_factor=0.5`
- **THEN** output files are written to `/meas/resized_0.50/`
- **THEN** the returned `ImageDataset` has `measurement_dir=/meas/resized_0.50/`

#### Scenario: Z-projection outputs to root sibling

- **WHEN** `z_project_dataset()` is called with `root_dir=Path("/meas/")` and `method="max"`
- **THEN** output files are written to `/meas/zproject_max/`

#### Scenario: Tile output to root sibling

- **WHEN** `tile_dataset()` is called with `root_dir=Path("/meas/")`, `tile_w=512`, `tile_h=512`
- **THEN** output files are written to `/meas/tiles_512x512/`

#### Scenario: BaSiC model output to root sibling

- **WHEN** `fit_models()` is called with `root_dir=Path("/meas/")`
- **THEN** model files are written to `/meas/BaSiC_model/`

#### Scenario: BaSiC correction output to root sibling

- **WHEN** `transform_images()` is called with `root_dir=Path("/meas/")`
- **THEN** corrected images are written to `/meas/BaSiC_corrected/`
