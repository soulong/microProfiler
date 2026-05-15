### Requirement: ImageDataset auto-detects intensity image extension

The system SHALL detect the image file extension in a dataset directory automatically and use it for regex-based filename parsing.

#### Scenario: Single extension detected

- **WHEN** the dataset directory contains only `.tiff` files
- **THEN** the metadata is built using `.tiff` as the intensity suffix
- **THEN** all `.tiff` files matching the unified naming pattern are included

#### Scenario: `.tif` extension is used

- **WHEN** the dataset directory contains only `.tif` files
- **THEN** the metadata is built using `.tif` as the intensity suffix
- **THEN** all `.tif` files matching the unified naming pattern are included

#### Scenario: `.jpg` extension is used

- **WHEN** the dataset directory contains only `.jpg` files
- **THEN** the metadata is built using `.jpg` as the intensity suffix
- **THEN** all `.jpg` files matching the unified naming pattern are included

#### Scenario: Mixed extensions raise an error

- **WHEN** the dataset directory contains both `.tiff` and `.jpg` files
- **THEN** a `ValueError` is raised indicating multiple extensions found

#### Scenario: No image files found

- **WHEN** the dataset directory contains no `.tif`, `.tiff`, `.jpg`, or `.jpeg` files
- **THEN** a `FileNotFoundError` is raised

### Requirement: Metadata excludes pipeline-internal groups

The metadata DataFrame SHALL NOT include columns for `im_suffix` or `tile` that are only used for filename matching, not as meaningful metadata.

#### Scenario: No `im_suffix` column in metadata

- **WHEN** `build_metadata()` completes
- **THEN** the metadata DataFrame SHALL NOT contain an `im_suffix` column

#### Scenario: No `tile` column before tiling

- **WHEN** `build_metadata()` completes on a pre-tiling dataset
- **THEN** the metadata DataFrame SHALL NOT contain a `tile` column

### Requirement: Tile column appears after tiling

The `tile_dataset` function SHALL add a `tile` column (integer index) to the returned dataset's metadata.

#### Scenario: Tile index in metadata after tiling

- **WHEN** `tile_dataset()` returns a new `ImageDataset`
- **THEN** the metadata DataFrame SHALL contain a `tile` column of integer type
- **THEN** the `tile` column values SHALL be the 0-based tile index for each row

### Requirement: Filter parameter uses idiomatic name

The `ImageDataset.__init__` parameter SHALL be named `filters` (plural dict of column→pattern filters).

#### Scenario: Init with `filters=` keyword

- **WHEN** constructing `ImageDataset(..., filters={"well": r"A\d+"})`
- **THEN** only rows matching the well pattern are kept
