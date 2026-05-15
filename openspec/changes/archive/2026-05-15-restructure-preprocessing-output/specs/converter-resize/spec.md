## ADDED Requirements

### Requirement: Converter supports optional resize during conversion

The `convert_measurement` function SHALL accept a `resize_factor` parameter. When set to a value other than `1.0`, images SHALL be resized during the conversion write step.

#### Scenario: Default resize factor produces full-resolution output

- **WHEN** `convert_measurement(...)` is called (no resize_factor specified)
- **THEN** images are written at their original resolution

#### Scenario: Custom resize factor resizes during conversion

- **WHEN** `convert_measurement(..., resize_factor=0.5)` is called
- **THEN** each image is resized to 50% of its original dimensions before writing
- **THEN** the output filename is identical to the full-resolution version

### Requirement: Converter output directory name is configurable

The `convert_measurement` function SHALL accept an `output_name` parameter that controls the output subdirectory name under the root.

#### Scenario: Default output name

- **WHEN** `convert_measurement(root_dir="/meas/")` is called
- **THEN** output files are written to `/meas/unified/`

#### Scenario: Custom output name

- **WHEN** `convert_measurement(root_dir="/meas/", output_name="myoutput")` is called
- **THEN** output files are written to `/meas/myoutput/`
