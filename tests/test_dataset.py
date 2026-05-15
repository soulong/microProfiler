from __future__ import annotations

import numpy as np
import pytest

from microProfiler.io.dataset import ImageDataset, _detect_intensity_suffix


class TestDetectIntensitySuffix:
    def test_detect_tiff(self, synthetic_unified_dir):
        ext = _detect_intensity_suffix(synthetic_unified_dir)
        assert ext == ".tiff"

    def test_no_images_raises(self, temp_dir):
        with pytest.raises(FileNotFoundError):
            _detect_intensity_suffix(temp_dir)


class TestBuildMetadata:
    def test_build_from_unified_dir(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        assert len(ds) == 3  # 3 unique (well, field, stack, timepoint) combos
        assert ds.intensity_colnames == ["ch1", "ch2"]
        assert ds.mask_colnames == []

    def test_intensity_columns(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        assert "ch1" in ds.intensity_colnames
        assert "ch2" in ds.intensity_colnames

    def test_metadata_columns(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        cols = ds.metadata.columns.tolist()
        assert "well" in cols
        assert "field" in cols
        assert "stack" in cols
        assert "timepoint" in cols
        assert "directory" in cols
        assert "ch1" in cols
        assert "ch2" in cols

    def test_empty_directory_raises(self, temp_dir):
        with pytest.raises(FileNotFoundError):
            ImageDataset(temp_dir)


class TestFilterMetadata:
    def test_filter_by_well(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.filter_metadata("well", "A1")
        assert len(ds) == 2
        assert all(ds.metadata["well"] == "A1")

    def test_chained_filters(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.filter_metadata("well", "A1").filter_metadata("stack", r"1")
        assert len(ds) == 1

    def test_filter_no_match(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.filter_metadata("well", r"Z99")
        assert len(ds) == 0


class TestGetImageset:
    def test_load_all_channels(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        img, masks = ds.get_imageset(0)
        assert img.shape == (16, 16, 2)
        assert img.dtype == np.uint16
        assert masks == {}

    def test_load_subset_channels(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        img, _ = ds.get_imageset(0, channels=["ch1"])
        assert img.shape == (16, 16, 1)

    def test_channel_order(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        img, _ = ds.get_imageset(0, channels=["ch2", "ch1"])
        assert img.shape == (16, 16, 2)


class TestExportMetadata:
    def test_export_to_db(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        db_path = temp_dir / "meta.db"
        ds.export_metadata(write_db=str(db_path))
        assert db_path.exists()

    def test_export_default_db(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.export_metadata(write_db=True)
        assert (synthetic_unified_dir / "results.db").exists()
        (synthetic_unified_dir / "results.db").unlink()

    def test_export_none_skips(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.export_metadata(write_db=None)  # should not raise


class TestRepr:
    def test_repr(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        r = repr(ds)
        assert "ImageDataset" in r
        assert "ch1" in r
        assert "ch2" in r
