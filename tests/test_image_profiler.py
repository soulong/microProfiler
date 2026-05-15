from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from microProfiler.profiling.image_profiler import measure_single_image, profile_images


class TestMeasureSingleImage:
    def test_uniform_image(self):
        img = np.full((10, 10, 2), 100, dtype=np.uint16)
        result = measure_single_image(img, ["ch1", "ch2"])
        assert result["intensity_mean_ch1"] == 100.0
        assert result["intensity_mean_ch2"] == 100.0
        assert result["intensity_sum_ch1"] == 10000.0
        assert result["intensity_q99_ch1"] == 100.0

    def test_all_zero_image(self):
        img = np.zeros((10, 10, 1), dtype=np.uint16)
        result = measure_single_image(img, ["ch1"])
        assert result["intensity_mean_ch1"] == 0.0
        assert result["intensity_sum_ch1"] == 0.0
        assert result["intensity_q25_ch1"] == 0.0

    def test_subset_channels(self):
        img = np.zeros((10, 10, 3), dtype=np.uint16)
        img[..., 0] = 50
        img[..., 1] = 100
        img[..., 2] = 200
        result = measure_single_image(img, ["ch1", "ch2", "ch3"], intensity_channels=["ch2"])
        assert "intensity_mean_ch2" in result
        assert "intensity_mean_ch1" not in result

    def test_channel_name_mismatch_raises(self):
        img = np.zeros((10, 10, 2), dtype=np.uint16)
        with pytest.raises(ValueError, match="names for 2 channels"):
            measure_single_image(img, ["ch1"])  # only 1 name for 2 channels

    def test_wrong_ndim_raises(self):
        img = np.zeros((10, 10), dtype=np.uint16)
        with pytest.raises(ValueError, match="must be"):
            measure_single_image(img, ["ch1"])

    def test_threshold_detects_objects(self):
        img = np.zeros((20, 20, 1), dtype=np.uint16)
        img[2:8, 2:8, 0] = 500
        result = measure_single_image(img, ["ch1"], thresholds={"ch1": 300.0})
        assert result["shape_n_object_ch1"] >= 1
        assert result["shape_area_ch1"] > 0

    def test_threshold_no_objects(self):
        img = np.zeros((20, 20, 1), dtype=np.uint16)
        result = measure_single_image(img, ["ch1"], thresholds={"ch1": 300.0})
        assert result["shape_n_object_ch1"] == 0
        assert result["shape_area_ch1"] == 0


class TestProfileImages:
    def test_profile_returns_dataframe(self, operetta_dataset):
        result = profile_images(operetta_dataset, db_path=None)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(operetta_dataset)

    def test_profile_writes_to_db(self, operetta_dataset, db_path):
        result = profile_images(operetta_dataset, db_path=db_path)
        assert result is None
        assert db_path.exists()
