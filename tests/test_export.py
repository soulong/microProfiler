from __future__ import annotations

import pandas as pd
import pytest

from microProfiler.io.export import write_dataloader


class TestWriteDataloader:
    @pytest.fixture
    def sample_metadata(self):
        return pd.DataFrame({
            "well": ["A1", "A1"],
            "field": [1, 2],
            "directory": ["/imgs", "/imgs"],
            "ch1": ["img1_ch1.tiff", "img2_ch1.tiff"],
            "ch2": ["img1_ch2.tiff", "img2_ch2.tiff"],
        })

    def test_returns_dataframe_without_path(self, sample_metadata):
        result = write_dataloader(
            sample_metadata,
            image_colnames=["ch1", "ch2"],
            mask_colnames=None,
            out_path=None,
        )
        assert isinstance(result, pd.DataFrame)
        assert "Image_FileName_ch1" in result.columns
        assert "Image_PathName_ch1" in result.columns
        assert "Metadata_well" in result.columns
        assert "ch1" not in result.columns  # renamed

    def test_with_masks(self, sample_metadata):
        meta = sample_metadata.copy()
        meta["mask_cell"] = ["img1_mask.png", "img2_mask.png"]
        result = write_dataloader(
            meta,
            image_colnames=["ch1", "ch2"],
            mask_colnames=["mask_cell"],
            out_path=None,
        )
        assert "Image_ObjectsFileName_mask_cell" in result.columns
        assert "Image_ObjectsPathName_mask_cell" in result.columns

    def test_writes_csv(self, sample_metadata, temp_dir):
        path = temp_dir / "dataloader.csv"
        result = write_dataloader(
            sample_metadata,
            image_colnames=["ch1", "ch2"],
            mask_colnames=None,
            out_path=str(path),
        )
        assert path.exists()
        # Also returns the df
        assert isinstance(result, pd.DataFrame)
