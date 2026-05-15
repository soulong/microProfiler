"""Full pipeline integration test — conversion, segmentation, profiling, DB.

Exercises the complete pipeline on real vendor datasets (Operetta and MICA):
  Convert → Segment → Image profile → Object profile (all extras) → SQLite.

This is a pre-release smoke test, not a per-commit test.
Marked ``@pytest.mark.slow`` — run with ``pytest -m slow``.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.database import Database
from microProfiler.preprocessing.converter import convert_measurement
from microProfiler.preprocessing.resizer import resize_dataset
from microProfiler.profiling.image_profiler import profile_images
from microProfiler.profiling.object_profiler import profile_objects
from microProfiler.segmentation.cellpose import segment_dataset

TEST_DIR = Path(__file__).parent / "test_dataset"
RESULT_DIR = TEST_DIR / "test_result"
OPERETTA_SRC = TEST_DIR / "operetta" / "2026-05-01_plate_Measurement 1"
MICA_SRC = TEST_DIR / "mica" / "Sequence 002"


def _clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _vendor_config(vendor: str):
    if vendor == "operetta":
        return OPERETTA_SRC, "operetta"
    if vendor == "mica":
        return MICA_SRC, "mica"
    raise ValueError(f"Unknown vendor: {vendor}")


@pytest.mark.slow
@pytest.mark.parametrize("vendor", ["operetta", "mica"])
def test_full_pipeline(vendor: str):
    log = logging.getLogger(f"test_full_pipeline.{vendor}")

    src_dir, result_sub = _vendor_config(vendor)
    run_dir = RESULT_DIR / result_sub / vendor
    _clean_output_dir(run_dir)

    dst_dir = run_dir / src_dir.name
    shutil.copytree(src_dir, dst_dir)

    # Remove stale artifacts from previous runs that may have old schema
    for stale in dst_dir.glob("results.db"):
        stale.unlink()
    for stale in dst_dir.glob("unified"):
        shutil.rmtree(stale)

    db_path = dst_dir / "results.db"

    try:
        # ── 1. Convert ─────────────────────────────────────────────────
        converted = convert_measurement(
            dst_dir,
            vendor_format=vendor,
            root_dir=dst_dir,
            output_name="unified",
        )
        assert len(converted) > 0, f"No files converted for {vendor}"
        log.info("Converted %d files", len(converted))

        # ── 2. Load dataset ────────────────────────────────────────────
        ds = ImageDataset(dst_dir / "unified")
        assert len(ds) > 0, "Dataset should have rows"
        assert len(ds.intensity_colnames) > 0, "Should have intensity channels"
        log.info("Dataset: %s", ds)

        # Limit to first 1 row and resize 0.1x for practical CPU Cellpose
        ds._metadata = ds._metadata.head(1)
        log.info("Trimmed to %d rows for CPU test", len(ds))

        ds = resize_dataset(ds, scale_factor=0.1)
        log.info("Resized to %s for CPU segmentation", ds.img_shape)

        # ── 3. Segment ─────────────────────────────────────────────────
        ds = segment_dataset(
            ds,
            object_name="cell",
            chan1=ds.intensity_colnames[:1],
        )
        has_masks = len(ds.mask_colnames) > 0
        if has_masks:
            log.info("Masks found: %s", ds.mask_colnames)
        else:
            log.warning("No masks produced by segmentation")

        # ── 4. Image profiling (no thresholds) ─────────────────────────
        profile_images(
            ds,
            channels=ds.intensity_colnames,
            db_path=db_path,
            table_name="image",
        )
        log.info("Image profiling written to %s", db_path)

        # ── 5. Object profiling (all extras) ───────────────────────────
        if has_masks:
            mask_name = ds.mask_colnames[0].replace("mask_", "")
            channels = ds.intensity_colnames
            corr_pairs = None
            if len(channels) >= 2:
                corr_pairs = [(channels[0], channels[1])]

            profile_objects(
                ds,
                mask_name=mask_name,
                intensity_channels=channels,
                radial_channels=channels,
                radial_n_bins=5,
                granularity_channels=channels,
                glcm_channels=channels,
                glcm_distances=[1, 2, 3],
                correlation_pairs=corr_pairs,
                db_path=db_path,
                table_name=mask_name,
            )
            log.info("Object profiling written to %s", db_path)

        # ── 6. Verify DB ───────────────────────────────────────────────
        assert db_path.exists(), "results.db should exist"
        assert db_path.stat().st_size > 0, "results.db should not be empty"

        db = Database(db_path)
        try:
            tables = db.get_tables()
            log.info("DB tables: %s", tables)
            assert "image" in tables, "image table should exist"

            image_df = db.query("SELECT * FROM image")
            expected_prefixes = ["intensity_mean_", "intensity_q", "intensity_sum_"]
            for prefix in expected_prefixes:
                matching = [c for c in image_df.columns if c.startswith(prefix)]
                assert len(matching) > 0, f"No columns with prefix '{prefix}' in image table"
            log.info("Image table columns: %s", list(image_df.columns))

            if has_masks:
                assert mask_name in tables, f"Object table '{mask_name}' should exist"
                obj_df = db.query(f'SELECT * FROM "{mask_name}"')
                log.info(
                    "Object table columns (%d): %s",
                    len(obj_df.columns),
                    list(obj_df.columns),
                )

                shape_cols = [c for c in obj_df.columns if c.startswith("shape_")]
                assert len(shape_cols) > 0, "No shape columns in object table"

                int_cols = [c for c in obj_df.columns if c.startswith("intensity_mean_")]
                assert len(int_cols) > 0, "No intensity columns in object table"

                rad_cols = [c for c in obj_df.columns if c.startswith("radial_")]
                assert len(rad_cols) > 0, "No radial columns in object table"

                gran_cols = [c for c in obj_df.columns if c.startswith("granularity_")]
                assert len(gran_cols) > 0, "No granularity columns in object table"

                glcm_cols = [c for c in obj_df.columns if c.startswith("glcm_")]
                assert len(glcm_cols) > 0, "No GLCM columns in object table"

                corr_cols = [c for c in obj_df.columns if c.startswith("correlation_")]
                if len(channels) >= 2:
                    assert len(corr_cols) > 0, (
                        f"Expected correlation columns for {len(channels)} channels, got none"
                    )
                else:
                    assert len(corr_cols) == 0, (
                        f"Expected no correlation columns for 1 channel, got {corr_cols}"
                    )
        finally:
            db.close()

        log.info("All assertions passed for vendor=%s", vendor)

    finally:
        _clean_output_dir(run_dir)
