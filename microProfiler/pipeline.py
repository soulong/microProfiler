"""High-level pipeline orchestrator for microProfiler."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from microProfiler.config import PipelineConfig
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
        return

    db_path = root_dir / db_name
    intensity_cols = ds.intensity_colnames
    log.debug(
        "Profile: image_channels=%s, object_mask=%s, db=%s",
        profiling.image_channels,
        profiling.object_mask_name,
        db_path,
    )

    if profiling.image_channels is not None:
        from microProfiler.profiling.image_profiler import profile_images

        channels = profiling.image_channels or intensity_cols
        img_kwargs = {"db_path": db_path, "table_name": "image", "progress_cb": progress_cb}
        if profiling.image_thresholds:
            img_kwargs["thresholds"] = profiling.image_thresholds
        if progress_cb:
            progress_cb("Profile Image", 0, 1, "Image profiling...")
        profile_images(ds, channels=channels, **img_kwargs)
        if progress_cb:
            progress_cb("Profile Image", 1, 1, "Image profiling complete")

    if profiling.object_mask_name:
        from microProfiler.profiling.object_profiler import profile_objects

        mask_name = profiling.object_mask_name
        ic = profiling.object_intensity_channels or intensity_cols
        rc = profiling.object_radial_channels
        gc = profiling.object_granularity_channels
        glcm_c = profiling.object_glcm_channels
        glcm_d = profiling.object_glcm_distances
        corr = profiling.correlation_pairs
        corr_tuples = None
        if corr:
            corr_tuples = [(tuple(p) if isinstance(p, list) else p) for p in corr]

        obj_kwargs = {}
        if profiling.parent_mask_name:
            obj_kwargs["parent_mask_name"] = profiling.parent_mask_name
        if gc and profiling.object_granularity_scales:
            obj_kwargs["granularity_kwargs"] = {
                "scales": [
                    int(s.strip()) for s in
                    profiling.object_granularity_scales.split(",") if s.strip()
                ],
                "subsample_size": profiling.object_granularity_subsample or 0.25,
                "element_size": profiling.object_granularity_element_size or 10,
            }
        if glcm_c:
            obj_kwargs["glcm_kwargs"] = {"distances": glcm_d or [1, 2, 3]}
            if profiling.object_glcm_levels:
                obj_kwargs["glcm_kwargs"]["levels"] = profiling.object_glcm_levels
            if profiling.object_glcm_angles:
                obj_kwargs["glcm_kwargs"]["angles"] = [
                    float(a.strip()) for a in profiling.object_glcm_angles.split(",") if a.strip()
                ]
        if rc and profiling.object_radial_bins != 5:
            obj_kwargs["radial_kwargs"] = {"nbins": profiling.object_radial_bins}

        if progress_cb:
            progress_cb("Profile Object", 0, 1, f"Object profiling on {mask_name}...")
        profile_objects(
            ds,
            mask_name=mask_name,
            intensity_channels=ic,
            radial_channels=rc,
            radial_n_bins=profiling.object_radial_bins,
            granularity_channels=gc,
            glcm_channels=glcm_c,
            glcm_distances=glcm_d,
            correlation_pairs=corr_tuples,
            db_path=db_path,
            table_name=mask_name,
            progress_cb=progress_cb,
            **obj_kwargs,
        )
        if progress_cb:
            progress_cb("Profile Object", 1, 1, "Object profiling complete")


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

    Pass a pre-loaded ``ds`` to skip the disk load.
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
        pass
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
