"""High-level pipeline orchestrator for microProfiler."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from microProfiler.config import PipelineConfig
from microProfiler.logging_utils import setup_logging


def run_pipeline(
    cfg: PipelineConfig,
    db_name: str = "results.db",
    log_file: Optional[Path] = None,
) -> None:
    """Run the full microProfiler pipeline.

    Executes the configured pipeline steps in order:
    Convert[+resize] → Resize → BaSiC → Z-projection → Tile → Segment → Profile.

    Parameters
    ----------
    cfg : PipelineConfig
        Complete pipeline configuration.
    db_name : str
        Filename for the output SQLite database.
    log_file : Path or None
        Optional path for log output.
    """
    log = setup_logging(log_file=log_file)
    log.info("Pipeline start — input: %s", cfg.input_dir)

    root_dir = cfg.output_dir or cfg.input_dir

    # ── Step 0: Convert vendor format to unified naming ────────────────
    from microProfiler.preprocessing.converter import convert_measurement

    output_name = cfg.convert.output_name if cfg.convert else "image"
    conv_resize = cfg.convert.resize_factor if cfg.convert else 1.0
    convert_delete_original = cfg.convert.delete_original if cfg.convert else False
    ds = convert_measurement(
        input_dir=cfg.input_dir,
        vendor_format=cfg.format,
        root_dir=root_dir,
        resize_factor=conv_resize,
        output_name=output_name,
        delete_original=convert_delete_original,
    )
    log.info("Conversion complete → %s/%s", root_dir, output_name)
    log.info("Dataset loaded: %d rows, channels=%s", len(ds), ds.intensity_colnames)

    # ── Step 1: Standalone resize (optional) ──────────────────────────
    if cfg.resize and cfg.resize.scale_factor != 1.0:
        from microProfiler.preprocessing.resizer import resize_dataset

        ds = resize_dataset(
            ds,
            scale_factor=cfg.resize.scale_factor,
            root_dir=root_dir,
            inplace=cfg.resize.inplace,
        )
        log.info("Resize applied: factor=%s, inplace=%s", cfg.resize.scale_factor, cfg.resize.inplace)

    # ── Step 2: BaSiC shading correction (optional) ────────────────────
    if cfg.basic_correction:
        from microProfiler.preprocessing.basic_correction import apply_basic

        ds = apply_basic(
            ds,
            mode=cfg.basic_correction.mode,
            n_image=cfg.basic_correction.n_image,
            working_size=cfg.basic_correction.working_size,
            enable_darkfield=cfg.basic_correction.enable_darkfield,
            root_dir=root_dir,
            inplace=cfg.basic_correction.inplace,
        )
        log.info("BaSiC correction applied: mode=%s", cfg.basic_correction.mode)

    # ── Step 3: Z-projection (optional) ────────────────────────────────
    if cfg.z_projection:
        from microProfiler.preprocessing.z_projection import z_project_dataset

        ds = z_project_dataset(
            ds,
            method=cfg.z_projection.method,
            root_dir=root_dir,
            inplace=cfg.z_projection.inplace,
        )
        log.info("Z-projection applied: method=%s", cfg.z_projection.method)

    # ── Step 4: Tile splitting (optional) ──────────────────────────────
    if cfg.tile:
        from microProfiler.preprocessing.tile_splitter import tile_dataset

        ds = tile_dataset(
            ds,
            tile_w=cfg.tile.tile_width,
            tile_h=cfg.tile.tile_height,
            root_dir=root_dir,
            inplace=cfg.tile.inplace,
        )
        log.info("Tiling applied: %dx%d", cfg.tile.tile_width, cfg.tile.tile_height)

    # ── Step 5: Cellpose segmentation (optional) ───────────────────────
    if cfg.segmentation:
        from microProfiler.segmentation.cellpose import segment_dataset

        seg_cfg = cfg.segmentation
        ds = segment_dataset(
            ds,
            object_name=seg_cfg.object_name,
            chan1=seg_cfg.chan1 or ds.intensity_colnames[:1],
            chan2=seg_cfg.chan2,
            merge1=seg_cfg.merge1,
            merge2=seg_cfg.merge2,
            model_name=seg_cfg.model_name,
            diameter=seg_cfg.diameter,
            flow_threshold=seg_cfg.flow_threshold,
            cellprob_threshold=seg_cfg.cellprob_threshold,
        )
        log.info("Segmentation complete: object=%s", seg_cfg.object_name)

    # ── Step 6: Profiling ─────────────────────────────────────────────
    profiling = cfg.profiling
    if profiling is None:
        log.info("No profiling requested — done.")
        return

    db_path = (cfg.output_dir or cfg.input_dir) / db_name
    intensity_cols = ds.intensity_colnames

    if profiling.image_channels is not None:
        from microProfiler.profiling.image_profiler import profile_images

        channels = profiling.image_channels or intensity_cols
        log.info("Image profiling on channels: %s", channels)
        profile_images(ds, channels=channels, db_path=db_path, table_name="image")

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

        log.info("Object profiling on mask=%s, channels=%s", mask_name, ic)
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
        )

    log.info("Pipeline complete — results written to %s", db_path)
