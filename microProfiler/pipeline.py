"""High-level pipeline orchestrator for microProfiler."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from microProfiler.config import ObjectProfilingConfig, PipelineConfig
from microProfiler.io.dataset import ImageDataset
from microProfiler.logging_utils import setup_logging

log = logging.getLogger(__name__)
ProgressCB = Callable[[str, int, int, str], None]


def _run_convert(
    cfg: PipelineConfig,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the convert step or load existing dataset from disk."""
    if cfg.convert is None:
        return ImageDataset(root_dir)

    from microProfiler.preprocessing.converter import convert_measurement

    if progress_cb:
        progress_cb("Convert", 0, 1, "Starting conversion...")
    log.debug(
        "Convert: vendor=%s, resize=%s, output_name=%s, delete_original=%s",
        cfg.format,
        cfg.convert.resize_factor,
        cfg.convert.output_name,
        cfg.convert.delete_original,
    )
    ds = convert_measurement(
        input_dir=cfg.input_dir,
        vendor_format=cfg.format,
        root_dir=root_dir,
        resize_factor=cfg.convert.resize_factor,
        output_name=cfg.convert.output_name,
        delete_original=cfg.convert.delete_original,
    )
    if progress_cb:
        progress_cb("Convert", 1, 1, "Conversion complete")
    return ds


def _run_resize(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the resize step if configured."""
    if cfg.resize and cfg.resize.scale_factor != 1.0:
        from microProfiler.preprocessing.resizer import resize_dataset

        log.debug("Resize: scale_factor=%s", cfg.resize.scale_factor)
        if progress_cb:
            progress_cb("Resize", 0, 1, f"Resizing by factor {cfg.resize.scale_factor}...")
        ds = resize_dataset(
            ds,
            scale_factor=cfg.resize.scale_factor,
            root_dir=root_dir,
            inplace=True,
            progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb("Resize", 1, 1, "Resize complete")
    return ds


def _run_basic(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the BaSiC correction step if configured."""
    if cfg.basic_correction:
        from microProfiler.preprocessing.basic_correction import apply_basic

        log.debug(
            "BaSiC: mode=%s, n_image=%d, working_size=%d, darkfield=%s",
            cfg.basic_correction.mode,
            cfg.basic_correction.n_image,
            cfg.basic_correction.working_size,
            cfg.basic_correction.enable_darkfield,
        )
        if progress_cb:
            progress_cb("BaSiC", 0, 1, "Applying BaSiC correction...")
        ds = apply_basic(
            ds,
            mode=cfg.basic_correction.mode,
            n_image=cfg.basic_correction.n_image,
            working_size=cfg.basic_correction.working_size,
            enable_darkfield=cfg.basic_correction.enable_darkfield,
            root_dir=root_dir,
            inplace=True,
            progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb("BaSiC", 1, 1, "BaSiC correction complete")
    return ds


def _run_zproject(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the Z-projection step if configured."""
    if cfg.z_projection:
        from microProfiler.preprocessing.z_projection import z_project_dataset

        log.debug("Z-projection: method=%s", cfg.z_projection.method)
        if progress_cb:
            progress_cb("Z-projection", 0, 1, "Applying Z-projection...")
        ds = z_project_dataset(
            ds,
            method=cfg.z_projection.method,
            root_dir=root_dir,
            inplace=True,
            progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb("Z-projection", 1, 1, "Z-projection complete")
    return ds


def _run_tile(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the tile splitting step if configured."""
    if cfg.tile:
        from microProfiler.preprocessing.tile_splitter import tile_dataset

        log.debug("Tile: %dx%d", cfg.tile.tile_width, cfg.tile.tile_height)
        if progress_cb:
            progress_cb("Tile", 0, 1, "Splitting tiles...")
        ds = tile_dataset(
            ds,
            tile_w=cfg.tile.tile_width,
            tile_h=cfg.tile.tile_height,
            root_dir=root_dir,
            inplace=True,
            progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb("Tile", 1, 1, "Tiling complete")
    return ds


def _run_segment(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    progress_cb: Optional[ProgressCB] = None,
):
    """Run all segmentation configurations sequentially."""
    if not cfg.segmentations:
        return ds

    from microProfiler.segmentation.cellpose import segment_dataset

    for seg_cfg in cfg.segmentations:
        name = seg_cfg.object_name
        if not name:
            continue
        log.debug(
            "Segment: object=%s, model=%s, chan1=%s, chan2=%s, diameter=%s",
            name, seg_cfg.model_name, seg_cfg.chan1, seg_cfg.chan2, seg_cfg.diameter,
        )
        if progress_cb:
            progress_cb(f"Segment ({name})", 0, 1, f"Starting segmentation ({name})...")
        ds = segment_dataset(
            ds,
            object_name=name,
            chan1=seg_cfg.chan1 or ds.intensity_colnames[:1],
            chan2=seg_cfg.chan2,
            merge1=seg_cfg.merge1,
            merge2=seg_cfg.merge2,
            model_name=seg_cfg.model_name,
            diameter=seg_cfg.diameter,
            flow_threshold=seg_cfg.flow_threshold,
            cellprob_threshold=seg_cfg.cellprob_threshold,
            progress_cb=progress_cb,
        )
        if progress_cb:
            progress_cb(f"Segment ({name})", 1, 1, f"Segmentation ({name}) complete")
    return ds


def _run_profile(
    cfg: PipelineConfig,
    ds,
    root_dir: Path,
    db_name: str = "results.db",
    progress_cb: Optional[ProgressCB] = None,
):
    """Run the profiling step if configured."""
    profiling = cfg.profiling
    if profiling is None:
        return ds

    db_path = root_dir / db_name
    intensity_cols = ds.intensity_colnames
    n_workers = profiling.n_workers
    obj_masks = [o.object_mask_name for o in profiling.object_profilings if o.object_mask_name]
    if not obj_masks and profiling.object_mask_name:
        obj_masks = [profiling.object_mask_name]
    log.debug(
        "Profile: image_channels=%s, object_masks=%s, db=%s, workers=%d",
        profiling.image_channels,
        obj_masks,
        db_path,
        n_workers,
    )

    if profiling.image_channels is not None:
        from microProfiler.profiling.image_profiler import profile_images

        channels = profiling.image_channels or intensity_cols
        img_kwargs = {"db_path": db_path, "table_name": "image", "progress_cb": progress_cb}
        if profiling.image_thresholds:
            img_kwargs["thresholds"] = profiling.image_thresholds
        if progress_cb:
            progress_cb("Profile image", 0, 1, "Starting...")
        profile_images(ds, channels=channels, n_workers=n_workers, **img_kwargs)
        if progress_cb:
            progress_cb("Profile image", 1, 1, "Done")

    # Build list of object profiling configs (new multi-block + legacy fallback)
    obj_configs = list(profiling.object_profilings)
    if not obj_configs and profiling.object_mask_name:
        legacy = {
            "object_mask_name": profiling.object_mask_name,
            "parent_mask_name": profiling.parent_mask_name,
            "output_table_name": profiling.output_table_name,
            "object_intensity_channels": profiling.object_intensity_channels,
            "object_radial_channels": profiling.object_radial_channels,
            "object_radial_bins": profiling.object_radial_bins,
            "object_granularity_channels": profiling.object_granularity_channels,
            "object_granularity_radii": profiling.object_granularity_radii,
            "object_granularity_subsample": profiling.object_granularity_subsample,
            "object_glcm_channels": profiling.object_glcm_channels,
            "object_glcm_distances": profiling.object_glcm_distances,
            "object_glcm_levels": profiling.object_glcm_levels,
            "object_glcm_angles": profiling.object_glcm_angles,
            "correlation_pairs": profiling.correlation_pairs,
        }
        obj_configs = [ObjectProfilingConfig(**legacy)]

    for obj_cfg in obj_configs:
        mask_name = getattr(obj_cfg, "object_mask_name", None)
        if not mask_name:
            continue
        from microProfiler.profiling.object_profiler import profile_objects

        ic = getattr(obj_cfg, "object_intensity_channels", None) or intensity_cols
        rc = getattr(obj_cfg, "object_radial_channels", None)
        gc = getattr(obj_cfg, "object_granularity_channels", None)
        glcm_c = getattr(obj_cfg, "object_glcm_channels", None)
        glcm_d = getattr(obj_cfg, "object_glcm_distances", None)
        corr = getattr(obj_cfg, "correlation_pairs", None)
        corr_tuples = None
        if corr:
            corr_tuples = [(tuple(p) if isinstance(p, list) else p) for p in corr]

        obj_kwargs = {}
        parent_mask = getattr(obj_cfg, "parent_mask_name", None)
        if parent_mask:
            obj_kwargs["parent_mask_name"] = parent_mask
        obj_gran_radii = getattr(obj_cfg, "object_granularity_radii", None)
        if gc and obj_gran_radii:
            obj_kwargs["granularity_kwargs"] = {
                "radii": [
                    float(s.strip()) for s in
                    obj_gran_radii.split(",") if s.strip()
                ],
                "subsample_size": getattr(obj_cfg, "object_granularity_subsample", None) or 1.0,
            }
        if glcm_c:
            obj_kwargs["glcm_kwargs"] = {"distances": glcm_d or [1, 2, 3]}
            glcm_levels = getattr(obj_cfg, "object_glcm_levels", None)
            if glcm_levels:
                obj_kwargs["glcm_kwargs"]["levels"] = glcm_levels
            glcm_angles = getattr(obj_cfg, "object_glcm_angles", None)
            if glcm_angles:
                import math
                obj_kwargs["glcm_kwargs"]["angles"] = [
                    math.radians(float(a.strip()))
                    for a in glcm_angles.split(",") if a.strip()
                ]
        obj_radial_bins = getattr(obj_cfg, "object_radial_bins", 5)
        if rc and obj_radial_bins != 5:
            obj_kwargs["radial_kwargs"] = {"nbins": obj_radial_bins}

        if progress_cb:
            progress_cb(f"Profile {mask_name}", 0, 1, "Starting...")
        profile_objects(
            ds,
            mask_name=mask_name,
            intensity_channels=ic,
            radial_channels=rc,
            radial_n_bins=obj_radial_bins,
            granularity_channels=gc,
            glcm_channels=glcm_c,
            glcm_distances=glcm_d,
            correlation_pairs=corr_tuples,
            db_path=db_path,
            table_name=getattr(obj_cfg, "output_table_name", None) or mask_name,
            progress_cb=progress_cb,
            n_workers=n_workers,
            **obj_kwargs,
        )
        if progress_cb:
            progress_cb(f"Profile {mask_name}", 1, 1, "Done")

    return ds


_STEP_FUNCTIONS = {
    "convert": _run_convert,
    "resize": _run_resize,
    "basic": _run_basic,
    "zproject": _run_zproject,
    "tile": _run_tile,
    "segment": _run_segment,
    "profile": _run_profile,
}


def run_step(
    cfg: PipelineConfig,
    step_name: str,
    db_name: str = "results.db",
    log_file: Optional[Path] = None,
    progress_cb: Optional[ProgressCB] = None,
    ds=None,
):
    """Run a single pipeline step independently.

    For ``"convert"``, creates a new ImageDataset from the input directory.
    For all other steps, loads the existing ImageDataset from the output
    directory and runs only the requested step.

    Parameters
    ----------
    cfg : PipelineConfig
        Pipeline configuration.
    step_name : str
        One of ``"convert"``, ``"resize"``, ``"basic"``, ``"zproject"``,
        ``"tile"``, ``"segment"``, ``"profile"``.
    db_name : str
        Filename for the output SQLite database (only used for ``"profile"``).
    log_file : Path or None
        Optional path for log output.
    progress_cb : callable or None
        Optional callback ``(step_name, current, total, message)``
        for GUI progress tracking.
    ds : ImageDataset or None
        Optional pre-loaded dataset. When provided, skips loading from disk.

    Returns
    -------
    ImageDataset or None
        The dataset after the step, or ``None`` for ``"profile"`` step.

    Raises
    ------
    ValueError
        If ``step_name`` is not a recognized pipeline step.
    """
    log = setup_logging(log_file=log_file, clear_existing=False)
    log.info("Running step: %s", step_name)
    root_dir = cfg.output_dir or cfg.input_dir
    log.debug("Step '%s': root_dir=%s, db_name=%s", step_name, root_dir, db_name)

    fn = _STEP_FUNCTIONS.get(step_name)
    if fn is None:
        raise ValueError(
            f"Unknown step: {step_name!r}. Must be one of {list(_STEP_FUNCTIONS)}"
        )

    if step_name == "profile":
        if ds is None:
            ds = ImageDataset(root_dir)
        fn(cfg, ds, root_dir, db_name, progress_cb)
        log.info("Step '%s' complete", step_name)
        return ds

    if ds is not None:
        log.info("Skipping dataset loading from disk — using pre-loaded dataset.")
    elif step_name == "convert":
        ds = fn(cfg, root_dir, progress_cb)
    else:
        ds = ImageDataset(root_dir)

    if step_name == "convert":
        pass
    else:
        ds = fn(cfg, ds, root_dir, progress_cb)

    log.info("Step '%s' complete", step_name)
    return ds


def run_pipeline(
    cfg: PipelineConfig,
    db_name: str = "results.db",
    log_file: Optional[Path] = None,
    progress_cb: Optional[ProgressCB] = None,
    ds=None,
) -> ImageDataset | None:
    """Run the full microProfiler pipeline.

    Executes the configured pipeline steps in order:
    Convert → Resize → BaSiC → Z-projection → Tile → Segment → Profile.

    Parameters
    ----------
    cfg : PipelineConfig
        Complete pipeline configuration.
    db_name : str
        Filename for the output SQLite database.
    log_file : Path or None
        Optional path for log output.
    progress_cb : callable or None
        Optional callback ``(step_name, current, total, message)``
        for GUI progress tracking.
    ds : ImageDataset or None
        Optional pre-loaded dataset. When provided, skips dataset
        loading from disk (convert step).

    Returns
    -------
    ImageDataset or None
        The dataset after the full pipeline run.
    """
    log = setup_logging(log_file=log_file, clear_existing=False)
    log.info("Pipeline start — input: %s", cfg.input_dir)

    root_dir = cfg.output_dir or cfg.input_dir
    log.debug("Output dir: %s, DB: %s", root_dir, db_name)
    log.debug(
        "Steps enabled: convert=%s, resize=%s, basic=%s, zproject=%s, tile=%s, segment=%s, profile=%s",
        cfg.convert is not None,
        cfg.resize is not None,
        cfg.basic_correction is not None,
        cfg.z_projection is not None,
        cfg.tile is not None,
        bool(cfg.segmentations),
        cfg.profiling is not None,
    )

    if ds is None:
        ds = _run_convert(cfg, root_dir, progress_cb)
        if cfg.convert:
            log.info("Conversion complete → %s", root_dir)
            log.info("Dataset loaded: %d rows, channels=%s", len(ds), ds.intensity_colnames)

    ds = _run_resize(cfg, ds, root_dir, progress_cb)
    if cfg.resize:
        log.info("Resize step done")

    ds = _run_basic(cfg, ds, root_dir, progress_cb)
    if cfg.basic_correction:
        log.info("BaSiC step done")

    ds = _run_zproject(cfg, ds, root_dir, progress_cb)
    if cfg.z_projection:
        log.info("Z-projection step done")

    ds = _run_tile(cfg, ds, root_dir, progress_cb)
    if cfg.tile:
        log.info("Tiling step done")

    ds = _run_segment(cfg, ds, root_dir, progress_cb)
    if cfg.segmentations:
        log.info("Segmentation step done")

    _run_profile(cfg, ds, root_dir, db_name, progress_cb)
    if cfg.profiling:
        log.info("Pipeline complete — results written to %s", root_dir / db_name)
    return ds
