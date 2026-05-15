## Why

The project lacks a conda environment file for easy environment reproduction, and the API reference (`docs/api.md`) is too concise for complex pipeline functions — users have to read source code to understand all parameters. A hand-curated `micro.yml` and a deeper API reference lower the barrier for new users.

## What Changes

- **micro.yml**: New hand-curated conda environment file at repo root, mirroring `pyproject.toml` dependencies with loose version pinning (conda-forge channels for most, pip for packages with lagging conda versions — `natsort`, `pydantic`, `ruff`)
- **docs/api.md**: Expanded with full parameter tables (D1) for complex pipeline functions (convert, segment, profile, measure) while keeping simple IO functions concise (D2)
- **README.md**: Updated references to reflect new `micro.yml` workflow

## Capabilities

### New Capabilities
- `env-setup`: Conda environment file (`micro.yml`) with curated dependencies matching `pyproject.toml`, split between conda-forge and pip packages
- `api-documentation`: API reference with tiered detail — full parameter tables for complex functions, concise signatures for simple utilities

### Modified Capabilities
- *(none — no existing specs cover environment setup or documentation depth)*

## Impact

| File | Change |
|------|--------|
| `micro.yml` (new) | Hand-curated conda environment file |
| `docs/api.md` | Full parameter tables for segment_dataset, measure_objects, profile_objects, convert_measurement, etc. |
| `README.md` | Reference `micro.yml` in installation section |
