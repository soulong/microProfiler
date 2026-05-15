## ADDED Requirements

### Requirement: API reference uses tiered detail

The `docs/api.md` file SHALL provide full parameter tables (D1) for complex pipeline functions and concise inline signatures (D2) for simple utility functions.

#### Scenario: D1 functions have parameter tables

- **WHEN** a user reads the API reference for `convert_measurement`, `segment_dataset`, `measure_objects`, `profile_objects`, `z_project_dataset`, `tile_dataset`, `resize_dataset`, `apply_basic`, `fit_models`, `transform_images`, or `profile_images`
- **THEN** the entry SHALL include a table with columns: Parameter, Type, Default, Description
- **THEN** the entry SHALL include a Returns section with type and description

#### Scenario: D2 functions have concise inline signatures

- **WHEN** a user reads the API reference for `read_image`, `write_image`, `IntensityNormalizer`, `Database`, `write_results_to_db`, `write_dataloader`, or extras factory functions
- **THEN** the entry SHALL use a compact inline format (one-liner signature + short description)
- **THEN** the entry SHALL NOT include full parameter tables
