## ADDED Requirements

### Requirement: Z-projection derives group columns from metadata schema

The `z_project_dataset` function SHALL dynamically determine which columns to group by, rather than using hard-coded column names. The group columns SHALL be all metadata columns except intensity channel columns, mask columns, the `stack` column, and the `directory` column.

#### Scenario: Basic metadata grouping

- **WHEN** metadata has columns `["directory", "well", "field", "stack", "timepoint", "ch0", "ch1"]`
- **AND** intensity channels are `["ch0", "ch1"]`
- **THEN** group columns are `["well", "field", "timepoint"]`

#### Scenario: Tile column included in groups when present

- **WHEN** metadata has columns `["directory", "well", "field", "stack", "timepoint", "tile", "ch0"]`
- **AND** intensity channels are `["ch0"]`
- **THEN** group columns SHALL include `"tile"`: `["well", "field", "timepoint", "tile"]`
