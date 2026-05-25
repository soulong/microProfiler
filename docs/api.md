# microProfiler API Reference

## `microProfiler.io`

### `microProfiler.io.dataset`

#### `ImageDataset`

```python
class ImageDataset(
    measurement_dir: Union[str, Path],
    image_pattern: Optional[Union[str, re.Pattern]] = None,
    mask_pattern: Optional[Union[str, re.Pattern]] = None,
    filters: Optional[Dict[str, str]] = None,
    image_subdir_pattern: Optional[str] = None,
)
```

Lightweight metadata manager for a directory of microscopy images. Scans the directory, auto-detects the image file extension (`.tiff`, `.tif`, `.jpg`, `.jpeg`), and builds a metadata DataFrame by parsing filenames against a regex pattern. Checks `image/` subdirectory first for converted data; falls back to `image_subdir_pattern` or auto-detection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `measurement_dir` | `str` or `Path` | — | Directory containing `image/`, `Images/`, or unified image files. |
| `image_pattern` | `str` or `Pattern` | `UNIFIED_IMAGE_PATTERN` | Regex with named groups to parse filenames. Extension auto-detected if default. |
| `mask_pattern` | `str` or `Pattern` | `UNIFIED_MASK_PATTERN` | Regex with named groups to parse mask filenames. |
| `filters` | `dict[str, str]` | `None` | Column → regex patterns applied after metadata build (AND logic). |
| `image_subdir_pattern` | `str` | `None` | Glob pattern for raw vendor files. `None` = auto (checks `Images/` for operetta, `[A-P]/` for mica). Set to `"Images/"` (operetta) or `"[A-P]/"` (mica) to force a specific raw layout. |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `metadata` | `pd.DataFrame` | Full metadata table with columns: `directory`, `well`, `field`, `stack`, `timepoint`, `tile` (after tiling), `ch0`, `ch1`, ... `mask_cell`, etc. |
| `intensity_colnames` | `list[str]` | Channel names (e.g. `["ch1", "ch2"]`). |
| `mask_colnames` | `list[str]` | Mask column names (e.g. `["mask_cell"]`). |
| `img_shape` | `tuple` or `None` | `(H, W)` from the first intensity image. |
| `img_dtype` | `np.dtype` or `None` | Data type from the first intensity image. |

**Methods:**

##### `build_metadata() -> None`

Scan directory and rebuild metadata. Handles tile column cleanup (drops if all NaN, converts to int if present). Called automatically during `__init__`, but must be called again after segmentation to pick up new mask files.

##### `filter_metadata(column: str, pattern: str) -> ImageDataset`

Keep only rows where *column* matches regex *pattern*. Modifies in-place, returns `self` for chaining.

| Parameter | Type | Description |
|-----------|------|-------------|
| `column` | `str` | Name of the metadata column to filter on. |
| `pattern` | `str` | Regex pattern to match against column values. |

**Returns:** `ImageDataset` — self with rows filtered in-place.

##### `get_imageset(row_idx: int, channels=None, masks=None) -> tuple`

Load the image stack and masks for a given metadata row.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `row_idx` | `int` | — | Row index in the metadata DataFrame. |
| `channels` | `list[str]` | all intensity cols | Channel names to load. |
| `masks` | `list[str]` | all mask columns | Mask column names to load. |

**Returns:** `tuple[np.ndarray, dict]` — `image_data` as `(H, W, C)` channels-last array, `mask_data` as `{mask_name: (H, W) uint16}`.

##### `export_metadata(write_db=True, table_name="metadata")`

Write metadata to an SQLite database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `write_db` | `bool`, `str`, or `None` | `True` | `True` → `results.db` in measurement dir. `str` → filename. `None`/`False` → skip. |
| `table_name` | `str` | `"metadata"` | Target table name. |

**Constants:**

| Constant | Value | Description |
|----------|-------|-------------|
| `KNOWN_IMAGE_EXTS` | `(".tiff", ".tif", ".jpg", ".jpeg")` | Supported image extensions for auto-detection. |
| `UNIFIED_IMAGE_PATTERN` | compiled regex | Default pattern matching `{well}_f{field}_z{z}_t{t}_ch{ch}...tiff`. |
| `UNIFIED_MASK_PATTERN` | compiled regex | Default pattern matching `{well}_f{field}_z{z}_t{t}_ch{ch}..._cp_masks_{name}.png`. |

#### `_detect_intensity_suffix(directory: Path) -> str`

Scan a directory and determine the single image extension in use. Raises `FileNotFoundError` or `ValueError` if zero or multiple extensions found.

---

### `microProfiler.io.loaders`

#### `read_image(path: Union[str, Path]) -> np.ndarray`

Read a single image from disk (TIFF or PNG). Returns `(H, W)` 2-D or `(Z, H, W)` multi-page array.

#### `write_image(path: Union[str, Path], data: np.ndarray, **kwargs) -> None`

Write a single TIFF image to disk with zlib compression.

#### `IntensityNormalizer`

```python
class IntensityNormalizer(
    method: Optional[str] = "percentile",
    pmin: float = 1.0,
    pmax: float = 99.8,
    dtype: np.dtype = np.uint16,
)
```

Lazy intensity normalization applied on image read. Methods: `"percentile"`, `"minmax"`, `"zscore"`, or `None`.

---

### `microProfiler.io.database`

#### `Database`

```python
class Database(db_path: Union[str, Path])
```

Thread-safe SQLite database using WAL mode. Each thread gets its own connection.

**Methods:**
- `close()` — Close current thread's connection.
- `save_table(df, table_name, if_exists)` — Write DataFrame to a table.
- `query(sql)` → `pd.DataFrame` — Execute SELECT query.
- `get_tables()` → `list` — List all tables.

#### `write_results_to_db(db_path, table_name, results, if_exists="append")`

Convenience: write results using a one-shot `Database` instance.

---

### `microProfiler.io.export`

#### `write_dataloader(metadata, image_colnames, mask_colnames, out_path) -> pd.DataFrame`

Convert metadata to CellProfiler-compatible CSV format. Writes to file if `out_path` is provided.

---

## `microProfiler.preprocessing`

### `microProfiler.preprocessing.converter`

#### `convert_measurement(input_dir, vendor_format, root_dir=None, resize_factor=1.0, output_name="image", delete_original=False) -> ImageDataset`

Convert a vendor-format measurement directory to unified naming. Supports `"operetta"` and `"mica"`. Optionally resizes images during conversion via `resize_factor`. Writes to `root_dir / output_name`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_dir` | `str` or `Path` | — | Raw measurement directory containing vendor-format files. |
| `vendor_format` | `str` | `"operetta"` | `"operetta"` or `"mica"`. |
| `root_dir` | `str` or `Path` | `input_dir` | Root directory for output. |
| `resize_factor` | `float` | `1.0` | Resize scale factor applied during conversion write. `1.0` = no resize. |
| `output_name` | `str` | `"image"` | Output subdirectory name under `root_dir`. |
| `delete_original` | `bool` | `False` | Delete original vendor files after successful conversion. |

**Returns:** `ImageDataset` — dataset pointing to the converted files.

**Vendor patterns:**

| Vendor | Input pattern | Output pattern |
|--------|---------------|----------------|
| Operetta | `r{row}c{col}f{field}p{stack}-ch{channel}sk{timepoint}fk1fl1.tiff` | `{well}_f{field}_z{stack}_t{timepoint}_ch{channel}.tiff` |
| MICA | `{row}/{col}/Pos{field}.tif` | `{well}_f{field}_z1_t1_ch{channel}.tiff` |

---

### `microProfiler.preprocessing.resizer`

#### `resize_dataset(ds: ImageDataset, scale_factor: float, root_dir=None, inplace=True, delete_original=False) -> ImageDataset`

Resize all images in a dataset by a scale factor using spline interpolation (order 1). When `inplace=True` (default), resized images replace originals in the dataset directory via temp→swap atomicity. When `inplace=False`, creates a `resized_{scale}/` subdirectory under `root_dir`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset whose images should be resized. |
| `scale_factor` | `float` | `1.0` | Resize factor (e.g. `0.5` halves both dimensions). |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory for output. |
| `inplace` | `bool` | `True` | Resize in-place (overwrite source directory). |
| `delete_original` | `bool` | `False` | Delete original files after resizing (only when not inplace). |

**Returns:** `ImageDataset` — new dataset pointing to the resized files.

---

### `microProfiler.preprocessing.z_projection`

#### `z_project_dataset(ds: ImageDataset, method: str, delete_original=False, root_dir=None, inplace=True) -> ImageDataset`

Collapse the Z dimension using `"max"`, `"mean"`, or `"min"` projection. Group columns are dynamically derived from metadata (all non-data columns except `stack`). When `inplace=True` (default), projected images replace Z-stacks in the dataset directory via temp→swap atomicity. When `inplace=False`, creates a `zproject_{method}/` subdirectory under `root_dir`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Input dataset with a `stack` column. |
| `method` | `str` | `"max"` | `"max"`, `"mean"`, or `"min"`. |
| `delete_original` | `bool` | `False` | Delete original Z-stack files after projection (only when not inplace). |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory for output. |
| `inplace` | `bool` | `True` | Project in-place (replace source directory). |

**Returns:** `ImageDataset` — new dataset with projected images.

---

### `microProfiler.preprocessing.tile_splitter`

#### `tile_dataset(ds: ImageDataset, tile_w: int, tile_h: int, delete_original=False, root_dir=None, inplace=True) -> ImageDataset`

Split all images into non-overlapping tiles. Each source image is split into `ceil(H / tile_h) * ceil(W / tile_w)` tiles. The returned dataset includes a `tile` column (integer index). When `inplace=True` (default), tiles replace originals in the dataset directory via temp→swap atomicity. When `inplace=False`, creates a `tiles_{W}x{H}/` subdirectory under `root_dir`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Input dataset. |
| `tile_w` | `int` | `1024` | Tile width in pixels. |
| `tile_h` | `int` | `1024` | Tile height in pixels. |
| `delete_original` | `bool` | `False` | Delete original files after tiling (only when not inplace). |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory for output. |
| `inplace` | `bool` | `True` | Tile in-place (replace source directory). |

**Returns:** `ImageDataset` — new dataset with tiled images.

---

### `microProfiler.preprocessing.basic_correction`

#### `fit_models(ds, channels=None, n_image=50, working_size=64, enable_darkfield=False, root_dir=None) -> Path`

Fit BaSiC models for specified channels. Saves pickled models and flatfield/darkfield images to `root_dir/.microprofiler/BaSiC_model/`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset to fit from. |
| `channels` | `list[str]` | all intensity cols | Channels to fit. |
| `n_image` | `int` | `50` | Number of images to use for fitting. |
| `working_size` | `int` | `64` | Working size for BaSiC model. |
| `enable_darkfield` | `bool` | `False` | Enable darkfield estimation. |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory for output. |

**Returns:** `Path` — directory containing the saved model files.

#### `transform_images(ds, channels=None, root_dir=None, inplace=True) -> ImageDataset`

Apply fitted BaSiC models to correct images. Models are loaded from `root_dir/.microprofiler/BaSiC_model/`. When `inplace=True` (default), corrected images replace originals in the dataset directory via temp→swap atomicity. When `inplace=False`, corrected images are written to `root_dir/BaSiC_corrected/`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset with saved BaSiC models. |
| `channels` | `list[str]` | all intensity cols | Channels to transform. |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory (same as used during fit). |
| `inplace` | `bool` | `True` | Correct in-place (replace source directory). |

**Returns:** `ImageDataset` — new dataset with corrected images.

#### `apply_basic(ds, mode="fit-transform", n_image=50, working_size=64, enable_darkfield=False, root_dir=None, inplace=True) -> ImageDataset`

End-to-end BaSiC correction: fit, transform, or both.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Input dataset. |
| `mode` | `str` | `"fit-transform"` | `"fit"`, `"transform"`, or `"fit-transform"`. |
| `n_image` | `int` | `50` | Number of images for fitting. |
| `working_size` | `int` | `64` | BaSiC working size. |
| `enable_darkfield` | `bool` | `False` | Enable darkfield estimation. |
| `root_dir` | `str` or `Path` | `ds.measurement_dir.parent` | Root directory for output. |
| `inplace` | `bool` | `True` | Correct in-place (replace source directory). |

**Returns:** `ImageDataset` — dataset with corrected images (or the original if only fitting).

---

## `microProfiler.segmentation`

### `microProfiler.segmentation.cellpose`

#### `segment_dataset(ds, object_name="cell", chan1=None, chan2=None, merge1="mean", merge2="mean", model_name="cpsam", diameter=None, normalize=None, resize_factor=1.0, overwrite_mask=False, flow_threshold=0.4, cellprob_threshold=0.0, gpu_batch_size=16) -> ImageDataset`

Run Cellpose-SAM segmentation on every image in the dataset. Produces `_cp_masks_{object_name}.png` files alongside the source images.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset to segment. |
| `object_name` | `str` | `"cell"` | Suffix for mask filenames. |
| `chan1` | `list[str]` | first intensity col | First channel group (C1 in Cellpose). |
| `chan2` | `list[str]` | `None` | Second channel group (C2 in Cellpose). `None` = C2 is zeros. |
| `merge1` | `str` | `"mean"` | Merge method for chan1: `"mean"`, `"max"`, or `"min"`. |
| `merge2` | `str` | `"mean"` | Merge method for chan2: `"mean"`, `"max"`, or `"min"`. |
| `model_name` | `str` | `"cpsam"` | Cellpose model name or path. |
| `diameter` | `float` | `None` | Object diameter in pixels. `None` = auto-detect. |
| `normalize` | `dict` | `{"percentile": [0.1, 99.9]}` | Normalization parameters for Cellpose. |
| `resize_factor` | `float` | `1.0` | Resize factor applied before segmentation (not written to disk). |
| `overwrite_mask` | `bool` | `False` | Re-run segmentation even if mask file exists. |
| `flow_threshold` | `float` | `0.4` | Cellpose flow threshold (lower = more masks). |
| `cellprob_threshold` | `float` | `0.0` | Cell probability threshold (lower = more masks). |
| `gpu_batch_size` | `int` | `16` | GPU batch size for Cellpose eval. |

**Returns:** `ImageDataset` — the input dataset with mask columns populated (call `ds.build_metadata()` to refresh).

---

## `microProfiler.profiling`

### `microProfiler.profiling.image_profiler`

#### `measure_single_image(image_data, channel_names, intensity_channels=None, thresholds=None) -> dict`

Profile a single image stack at the whole-image level.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_data` | `np.ndarray` | — | Shape `(Y, X, C)` channels-last array. |
| `channel_names` | `list[str]` | — | Names matching the C axis. |
| `intensity_channels` | `list[str]` | all channels | Subset of channels to profile. |
| `thresholds` | `dict[str, float]` | `None` | Per-channel thresholds for object detection, e.g. `{"ch1": 500.0}`. |

**Returns:** `dict` — flat dict with keys like `intensity_mean_{ch}`, `intensity_sum_{ch}`, `intensity_q{q}_{ch}`, and optionally `shape_area_{ch}`, `shape_n_object_{ch}`, `shape_mean_object_area_{ch}`.

#### `profile_images(ds, channels=None, thresholds=None, db_path=None, table_name="image", n_workers=1) -> Optional[pd.DataFrame]`

Profile all images in a dataset at the whole-image level. Uses `ProcessPoolExecutor` when `n_workers > 1`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset to profile. |
| `channels` | `list[str]` | all intensity cols | Channels to profile. |
| `thresholds` | `dict[str, float]` | `None` | Per-channel thresholds. |
| `db_path` | `str` or `Path` | `None` | SQLite output path. `None` = return DataFrame. |
| `table_name` | `str` | `"image"` | Table name for DB output. |
| `n_workers` | `int` | `1` | Number of worker processes (`1` = sequential). Default: half of CPU cores. |

**Returns:** `pd.DataFrame` or `None` — results DataFrame if `db_path` is `None`.

---

### `microProfiler.profiling.object_profiler`

#### `measure_objects(mask, img, channel_names, metadata_row=None, parent_mask=None, parent_mask_name="Parent", intensity_channels=None, radial_channels=None, radial_kwargs=None, granularity_channels=None, granularity_kwargs=None, glcm_channels=None, glcm_kwargs=None, correlation_pairs=None) -> pd.DataFrame`

Measure shape, intensity, and texture for every labeled object in a mask. Returns one row per object.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mask` | `np.ndarray` | — | Labeled segmentation mask of shape `(Y, X)`. |
| `img` | `np.ndarray` | — | Multichannel intensity image of shape `(Y, X, C)`. |
| `channel_names` | `list[str]` | — | Names matching the C axis. |
| `metadata_row` | `dict` | `None` | Prepended to every row (e.g. well, field info). |
| `parent_mask` | `np.ndarray` | `None` | Parent mask for child→parent assignment. |
| `parent_mask_name` | `str` | `"Parent"` | Column name suffix for parent label. |
| `intensity_channels` | `list[str]` | all channels | Channels for mean/median/std/sum measurements. |
| `radial_channels` | `list[str]` | `None` | Channels for radial distribution. |
| `radial_kwargs` | `dict` | `None` | `{"nbins": int}`. |
| `granularity_channels` | `list[str]` | `None` | Channels for granularity spectrum. |
| `granularity_kwargs` | `dict` | `None` | `{"scales": [...], "subsample_size": ..., "element_size": ...}`. |
| `glcm_channels` | `list[str]` | `None` | Channels for GLCM texture. |
| `glcm_kwargs` | `dict` | `None` | `{"distances": [...], "levels": int}`. |
| `correlation_pairs` | `list[tuple[str,str]]` | `None` | Channel pairs for Pearson correlation. |

**Returns:** `pd.DataFrame` — one row per object. Columns include shape metrics (`shape_area`, `shape_eccentricity`, ..., `is_boundary`), intensity metrics (`intensity_mean_{ch}`, `intensity_median_{ch}`, ...), and optional extra features (radial, granularity, GLCM, correlation).

**Feature columns produced:**

| Group | Column pattern | Description |
|-------|----------------|-------------|
| Shape | `shape_area`, `shape_eccentricity`, `shape_equivalent_diameter_area`, `shape_extent`, `shape_feret_diameter_max`, `shape_major_axis_length`, `shape_minor_axis_length`, `shape_perimeter`, `shape_solidity` | Morphology metrics per object. |
| Boundary | `is_boundary` | `True` if the object touches the image edge. |
| Parent | `parent_{name}` | Parent label for hierarchical segmentation. |
| Intensity | `intensity_mean_{ch}`, `intensity_median_{ch}`, `intensity_std_{ch}`, `intensity_sum_{ch}` | Pixel statistics within object mask. |
| Radial | `radial_bin{i}_{ch}` | Fraction of total object intensity in each radial shell (i=0 → outermost). |
| Granularity | `granularity_scale{s}_{ch}` | Fraction of texture removed at each scale. |
| GLCM | `glcm_{prop}_d{d}_{ch}` | Texture features: contrast, dissimilarity, homogeneity, energy, correlation, ASM, entropy. |
| Correlation | `correlation_pearson_{chA}_{chB}` | Per-object Pearson R between channel pairs. |

#### `profile_objects(ds, mask_name, parent_mask_name=None, intensity_channels=None, radial_channels=None, radial_n_bins=5, granularity_channels=None, glcm_channels=None, glcm_distances=None, correlation_pairs=None, db_path=None, table_name=None, n_workers=1, **extra_kwargs) -> Optional[pd.DataFrame]`

Profile all objects in a dataset for a given mask across all images. Uses `ProcessPoolExecutor` when `n_workers > 1`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `ImageDataset` | — | Dataset containing intensity images and mask files for `mask_name`. |
| `mask_name` | `str` | — | Mask to use (e.g. `"cell"`). |
| `parent_mask_name` | `str` | `None` | Parent mask for hierarchical assignment. |
| `intensity_channels` | `list[str]` | all channels | Channels for intensity stats. |
| `radial_channels` | `list[str]` | `None` | Channels for radial distribution. |
| `radial_n_bins` | `int` | `5` | Number of radial bins. |
| `granularity_channels` | `list[str]` | `None` | Channels for granularity. |
| `glcm_channels` | `list[str]` | `None` | Channels for GLCM texture. |
| `glcm_distances` | `list[int]` | `[1, 2, 3]` | GLCM pixel distances. |
| `correlation_pairs` | `list[tuple[str,str]]` | `None` | Channel pairs for Pearson correlation. |
| `db_path` | `str` or `Path` | `None` | SQLite output path. `None` = return DataFrame. |
| `table_name` | `str` | `mask_name` | DB table name (defaults to mask name). |
| `n_workers` | `int` | `1` | Number of worker processes (`1` = sequential). Default: half of CPU cores. |
| `**extra_kwargs` | `dict` | — | Extra kwargs forwarded to `measure_objects()` (e.g. `granularity_kwargs`, `glcm_kwargs`, `radial_kwargs`). |

**Returns:** `pd.DataFrame` or `None` — results DataFrame if `db_path` is `None`.

---

### `microProfiler.profiling.extras`

Extra property factories for `skimage.measure.regionprops_table`.

| Factory | Parameters | Output columns |
|---------|-----------|----------------|
| `make_radial_distribution(nbins, channel)` | `nbins: int=4`, `channel: int=0` | `radial_bin{i}_ch{c}` — fraction of total intensity per radial shell (i=0 outermost). |
| `make_granularity(scales, channel, subsample_size, element_size)` | `scales: sequence`, `channel: int=0`, `subsample_size: float=256`, `element_size: int=10` | `granularity_scale{s}_ch{c}` — texture removed at each scale. |
| `make_glcm(distances, angles, levels, channel, props)` | `distances: sequence=(1,2,4,8)`, `angles: sequence=(0, π/4, π/2, 3π/4)` radians, `levels: int=8`, `channel: int=0`, `props: sequence=(contrast, dissimilarity, homogeneity, energy, correlation, asm, entropy)` | `glcm_{prop}_d{d}_ch{c}` — texture features. Pipeline accepts angles in **degrees** and converts to radians automatically. |
| `measure_channel_correlation(label_image, multichannel_image, channel_pairs)` | `label_image: (H,W) int`, `multichannel_image: (H,W,C) float`, `channel_pairs: list of (a,b)` | `correlation_pearson_ch{a}_ch{b}` — per-object Pearson R. |
