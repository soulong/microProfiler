from __future__ import annotations

import logging

import numpy as np
import pytest
import tifffile

from microProfiler.io.dataset import ImageDataset
from microProfiler.preprocessing.tile_splitter import _split_single_image, tile_dataset


class TestSplitSingleImage:
    def test_tile_count_exact(self, temp_dir):
        img = np.ones((64, 64), dtype=np.uint16)
        src = temp_dir / "A1_f1_z1_t1_ch1.tiff"
        tifffile.imwrite(str(src), img)
        n = _split_single_image(src, tile_w=32, tile_h=32, output_dir=temp_dir)
        assert n == 4

    def test_tile_count_partial(self, temp_dir):
        img = np.ones((100, 100), dtype=np.uint16)
        src = temp_dir / "A1_f1_z1_t1_ch1.tiff"
        tifffile.imwrite(str(src), img)
        n = _split_single_image(src, tile_w=64, tile_h=64, output_dir=temp_dir)
        assert n == 1  # only the full 64x64 top-left tile

    def test_tile_naming(self, temp_dir):
        img = np.ones((32, 32), dtype=np.uint16)
        src = temp_dir / "B2_f3_z1_t1_ch2.tiff"
        tifffile.imwrite(str(src), img)
        _split_single_image(src, tile_w=16, tile_h=16, output_dir=temp_dir)
        assert (temp_dir / "B2_f3_z1_t1_ch2_tile0.tiff").exists()
        assert (temp_dir / "B2_f3_z1_t1_ch2_tile1.tiff").exists()
        assert (temp_dir / "B2_f3_z1_t1_ch2_tile2.tiff").exists()
        assert (temp_dir / "B2_f3_z1_t1_ch2_tile3.tiff").exists()

    def test_unmatched_filename_returns_zero(self, temp_dir):
        src = temp_dir / "garbage.txt"
        src.write_text("not an image")
        n = _split_single_image(src, tile_w=16, tile_h=16, output_dir=temp_dir)
        assert n == 0

    def test_multi_channel_warns(self, temp_dir, caplog):
        img = np.ones((16, 16, 3), dtype=np.uint16)
        src = temp_dir / "A1_f1_z1_t1_ch1.tiff"
        tifffile.imwrite(str(src), img)
        with caplog.at_level(logging.WARNING):
            n = _split_single_image(src, tile_w=8, tile_h=8, output_dir=temp_dir)
        assert n == 0
        assert "non-2d" in caplog.text.lower()

    def test_positional_index_with_gaps(self, temp_dir):
        img = np.ones((100, 100), dtype=np.uint16)
        src = temp_dir / "A1_f1_z1_t1_ch1.tiff"
        tifffile.imwrite(str(src), img)
        _split_single_image(src, tile_w=64, tile_h=64, output_dir=temp_dir)
        assert (temp_dir / "A1_f1_z1_t1_ch1_tile0.tiff").exists()
        assert not (temp_dir / "A1_f1_z1_t1_ch1_tile1.tiff").exists()
        assert not (temp_dir / "A1_f1_z1_t1_ch1_tile2.tiff").exists()
        assert not (temp_dir / "A1_f1_z1_t1_ch1_tile3.tiff").exists()


class TestTileDataset:
    def test_small_image_raises(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        with pytest.raises(ValueError, match="smaller than tile size"):
            tile_dataset(ds, tile_w=64, tile_h=64, root_dir=synthetic_unified_dir.parent)

