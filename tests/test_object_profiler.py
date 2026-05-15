from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from microProfiler.profiling.object_profiler import (
    _is_boundary,
    _relate_masks,
    measure_objects,
    profile_objects,
)


class TestBoundaryDetection:
    def test_interior_object(self):
        mask = np.zeros((20, 20), dtype=np.uint16)
        mask[5:15, 5:15] = 1
        result = _is_boundary(mask)
        assert result[1] is False

    def test_boundary_touching_edge(self):
        mask = np.zeros((20, 20), dtype=np.uint16)
        mask[0:5, 0:5] = 1  # touches top-left corner
        result = _is_boundary(mask)
        assert result[1] is True

    def test_boundary_bottom_edge(self):
        mask = np.zeros((20, 20), dtype=np.uint16)
        mask[15:20, 5:15] = 1  # touches bottom
        result = _is_boundary(mask)
        assert result[1] is True

    def test_multiple_objects(self):
        mask = np.zeros((20, 20), dtype=np.uint16)
        mask[2:6, 2:6] = 1  # interior
        mask[0:4, 15:20] = 2  # boundary
        result = _is_boundary(mask)
        assert result[1] is False
        assert result[2] is True


class TestRelateMasks:
    def test_basic_relationship(self):
        child = np.zeros((20, 20), dtype=np.uint16)
        parent = np.zeros((20, 20), dtype=np.uint16)
        child[5:15, 5:15] = 1
        parent[3:17, 3:17] = 1
        mapping = _relate_masks(child, parent)
        assert mapping[1] == 1

    def test_child_no_parent_overlap(self):
        child = np.zeros((20, 20), dtype=np.uint16)
        parent = np.zeros((20, 20), dtype=np.uint16)
        child[2:6, 2:6] = 1
        parent[15:19, 15:19] = 2
        mapping = _relate_masks(child, parent)
        assert mapping[1] == 0

    def test_shape_mismatch_raises(self):
        child = np.zeros((10, 10), dtype=np.uint16)
        parent = np.zeros((20, 20), dtype=np.uint16)
        with pytest.raises(ValueError, match="shapes must match"):
            _relate_masks(child, parent)


class TestMeasureObjects:
    def test_basic_measurement(self, simple_mask, multichannel_image):
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # 2 objects
        assert "label" in result.columns
        assert "shape_area" in result.columns
        assert "is_boundary" in result.columns
        assert result["shape_area"].tolist() == [16, 16]

    def test_with_intensity_channels(self, simple_mask, multichannel_image):
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            intensity_channels=["ch1", "ch2"],
        )
        assert "intensity_mean_ch1" in result.columns
        assert "intensity_sum_ch2" in result.columns

    def test_with_parent_mask(self, simple_mask, multichannel_image):
        parent = np.zeros((16, 16), dtype=np.uint16)
        parent[0:16, 0:16] = 1
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            parent_mask=parent,
            parent_mask_name="well",
        )
        assert "parent_well" in result.columns

    def test_with_metadata_row(self, simple_mask, multichannel_image):
        meta = {"well": "A1", "field": 1}
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            metadata_row=meta,
        )
        assert "well" in result.columns
        assert result["well"].iloc[0] == "A1"

    def test_with_radial(self, simple_mask, multichannel_image):
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            radial_channels=["ch1"],
            radial_kwargs={"nbins": 4},
        )
        radial_cols = [c for c in result.columns if c.startswith("radial")]
        assert len(radial_cols) == 4

    def test_with_granularity(self, simple_mask, multichannel_image):
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            granularity_channels=["ch1"],
            granularity_kwargs={"scales": [0, 1], "subsample_size": 0.5, "element_size": 10},
        )
        gran_cols = [c for c in result.columns if c.startswith("granularity")]
        assert len(gran_cols) == 2

    def test_with_glcm(self, simple_mask, multichannel_image):
        result = measure_objects(
            mask=simple_mask,
            img=multichannel_image,
            channel_names=["ch1", "ch2"],
            glcm_channels=["ch1"],
            glcm_kwargs={"distances": [1], "levels": 8},
        )
        glcm_cols = [c for c in result.columns if c.startswith("glcm")]
        assert len(glcm_cols) > 0

    def test_shape_mismatch_raises(self, simple_mask):
        img = np.zeros((10, 10, 2), dtype=np.uint16)
        with pytest.raises(ValueError, match="spatial shapes must match"):
            measure_objects(mask=simple_mask, img=img, channel_names=["ch1", "ch2"])

    def test_unknown_channel_raises(self, simple_mask, multichannel_image):
        with pytest.raises(ValueError, match="unknown channels"):
            measure_objects(
                mask=simple_mask,
                img=multichannel_image,
                channel_names=["ch1", "ch2"],
                intensity_channels=["ch3"],
            )


class TestProfileObjects:
    def test_returns_dataframe(self, operetta_dataset, simple_mask, multichannel_image):
        result = profile_objects(
            ds=operetta_dataset,
            mask_name="cell",
            intensity_channels=["ch1", "ch2"],
            db_path=None,
        )
        assert result is None or isinstance(result, pd.DataFrame)

    def test_no_mask_returns_none(self, operetta_dataset):
        result = profile_objects(
            ds=operetta_dataset,
            mask_name="nonexistent",
            db_path=None,
        )
        assert result is None
