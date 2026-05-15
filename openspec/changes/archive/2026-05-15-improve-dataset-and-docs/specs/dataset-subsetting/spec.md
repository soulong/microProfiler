## MODIFIED Requirements

### Requirement: ImageDataset supports regex-based row filtering

The `ImageDataset` class SHALL provide a method to filter its metadata rows by regex pattern on any metadata column.

#### Scenario: Filter by well pattern at initialization
- **WHEN** constructing an `ImageDataset` with `filters={"well": r"B\d+"}` kwarg
- **THEN** only rows where `well` matches the regex `B\d+` are kept in the dataset
- **THEN** subsequent calls to `__len__` reflect only matching rows

#### Scenario: Filter after initialization
- **WHEN** calling `ds.filter_metadata("well", r"B\d+")` on an existing `ImageDataset`
- **THEN** the dataset is modified in-place
- **THEN** only rows matching the regex remain
- **THEN** the method returns `self` for chaining

#### Scenario: Multiple filters can be applied sequentially
- **WHEN** calling `ds.filter_metadata("field", r"[12]").filter_metadata("stack", r"[12]")`
- **THEN** only rows matching all filters remain (AND logic)

#### Scenario: No match produces an empty dataset
- **WHEN** the pattern matches no rows
- **THEN** the dataset has `len() == 0`
- **THEN** no error is raised

**Reason**: Parameter renamed from `filter_` to `filters` for idiomatic consistency.
**Migration**: Replace `filter_={"col": pat}` with `filters={"col": pat}`.
