## ADDED Requirements

### Requirement: Hand-curated conda environment file

The repository SHALL provide a `micro.yml` file at the root that defines a conda environment matching the project's dependencies from `pyproject.toml`.

#### Scenario: Environment file exists

- **WHEN** a user runs `conda env create -f micro.yml`
- **THEN** a conda environment named `cellpose` is created
- **THEN** all runtime dependencies are installed (numpy, pandas, scipy, scikit-image, tifffile, cellpose, torch, jax, pyyaml, tqdm, natsort, pydantic>=2.0)
- **THEN** the `microProfiler` package is NOT installed by the environment file (requires `pip install -e .`)

#### Scenario: Install instructions reference micro.yml

- **WHEN** a user reads the README installation section
- **THEN** the first option SHALL use `conda env create -f micro.yml`
- **THEN** the second step SHALL be `conda activate cellpose` followed by `pip install -e .`

### Requirement: Dependencies split by conda availability

Packages available on conda-forge SHALL be listed as conda dependencies. Packages where conda versions lag (`natsort`, `pydantic`, `ruff`) SHALL be listed as pip dependencies.

#### Scenario: Pip section for conda-lagging packages

- **WHEN** a user runs `conda env create -f micro.yml`
- **THEN** `natsort` and `pydantic>=2.0` SHALL be installed via pip, not conda
- **THEN** all other dependencies SHALL be installed via conda-forge
