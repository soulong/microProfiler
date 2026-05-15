from __future__ import annotations

import numpy as np
from skimage.measure import regionprops_table

from microProfiler.profiling.extras import (
    _glcm_all,
    _granularity_all,
    _radial_all,
    make_glcm,
    make_radial_distribution,
    measure_channel_correlation,
)


class TestRadialDistribution:
    def test_radial_all_basic(self):
        img = np.ones((20, 20), dtype=np.float64)
        mask = np.zeros((20, 20), dtype=bool)
        mask[5:15, 5:15] = True
        result = _radial_all(mask, img, nbins=4, channel=0)
        assert len(result) == 4
        assert np.isclose(result.sum(), 1.0, atol=1e-6)

    def test_radial_all_zero_mask(self):
        img = np.ones((10, 10), dtype=np.float64)
        mask = np.zeros((10, 10), dtype=bool)
        result = _radial_all(mask, img, nbins=4, channel=0)
        assert len(result) == 4
        assert np.allclose(result, 0)

    def test_radial_factory_creates_callables(self):
        fns = make_radial_distribution(nbins=3, channel=0)
        assert len(fns) == 3
        mask = np.zeros((10, 10), dtype=bool)
        mask[2:8, 2:8] = True
        intensity = np.ones((10, 10), dtype=np.float64)
        for fn in fns:
            val = fn(mask, intensity)
            assert isinstance(val, float)

    def test_radial_in_regionprops(self):
        mask = np.zeros((20, 20), dtype=np.uint16)
        mask[5:15, 5:15] = 1
        intensity = np.ones((20, 20), dtype=np.float64)
        fns = make_radial_distribution(nbins=4, channel=0)
        props = regionprops_table(mask, intensity, properties=["label"], extra_properties=fns)
        assert "radial_bin0_ch0" in props
        assert "radial_bin3_ch0" in props


class TestGranularity:
    def test_granularity_all_basic(self):
        img = np.random.default_rng(42).uniform(0, 100, size=(32, 32)).astype(np.float64)
        mask = np.ones((32, 32), dtype=bool)
        result = _granularity_all(mask, img, scales=(0, 1, 2), channel=0,
                                  subsample_size=1.0, element_size=10)
        assert len(result) == 3

    def test_granularity_all_zero_mask(self):
        img = np.ones((10, 10), dtype=np.float64)
        mask = np.zeros((10, 10), dtype=bool)
        result = _granularity_all(mask, img, scales=(0, 1), channel=0,
                                  subsample_size=1.0, element_size=10)
        assert len(result) == 2
        assert np.allclose(result, 0)

    def test_granularity_all_uniform(self):
        img = np.full((16, 16), 100.0, dtype=np.float64)
        mask = np.ones((16, 16), dtype=bool)
        result = _granularity_all(mask, img, scales=(0, 1, 2), channel=0,
                                  subsample_size=1.0, element_size=10)
        assert len(result) == 3


class TestGLCM:
    def test_glcm_all_basic(self):
        rng = np.random.default_rng(42)
        img = rng.integers(0, 255, size=(16, 16), dtype=np.uint16).astype(np.float64)
        mask = np.ones((16, 16), dtype=bool)
        result = _glcm_all(mask, img, distances=(1,), angles=(0,), levels=8,
                           channel=0, props=("contrast", "homogeneity"))
        assert len(result) == 2  # 1 distance * 2 props
        assert not np.isnan(result).any()

    def test_glcm_empty_roi(self):
        img = np.ones((10, 10), dtype=np.float64)
        mask = np.zeros((10, 10), dtype=bool)
        result = _glcm_all(mask, img, distances=(1,), angles=(0,), levels=8,
                           channel=0, props=("contrast",))
        assert len(result) == 1
        assert result[0] == 0.0

    def test_glcm_factory(self):
        fns = make_glcm(distances=(1,), angles=(0,), levels=8, channel=0,
                        props=("contrast", "homogeneity"))
        assert len(fns) == 2
        mask = np.ones((16, 16), dtype=bool)
        rng = np.random.default_rng(42)
        img = rng.integers(0, 255, size=(16, 16), dtype=np.uint16).astype(np.float64)
        for fn in fns:
            val = fn(mask, img)
            assert isinstance(val, float)


class TestCorrelation:
    def test_measure_channel_correlation(self):
        rng = np.random.default_rng(42)
        img = rng.uniform(0, 100, size=(16, 16, 2)).astype(np.float64)
        label_img = np.zeros((16, 16), dtype=np.uint16)
        label_img[2:8, 2:8] = 1
        label_img[10:14, 10:14] = 2
        result = measure_channel_correlation(label_img, img, channel_pairs=[(0, 1)])
        assert "label" in result
        assert "correlation_pearson_ch0_ch1" in result
        assert len(result["label"]) == 2
        assert not np.isnan(result["correlation_pearson_ch0_ch1"]).any()

    def test_correlation_identical_channels(self):
        rng = np.random.default_rng(42)
        data = rng.uniform(0, 100, size=(16, 16))
        img = np.stack([data, data], axis=-1)
        label_img = np.zeros((16, 16), dtype=np.uint16)
        label_img[2:8, 2:8] = 1
        result = measure_channel_correlation(label_img, img, channel_pairs=[(0, 1)])
        corr = result["correlation_pearson_ch0_ch1"]
        assert np.allclose(corr, 1.0, atol=1e-6)

    def test_correlation_no_labels(self):
        img = np.random.default_rng(42).uniform(0, 100, size=(16, 16, 2))
        label_img = np.zeros((16, 16), dtype=np.uint16)
        result = measure_channel_correlation(label_img, img)
        assert len(result["label"]) == 0

    def test_correlation_default_pairs(self):
        img = np.random.default_rng(42).uniform(0, 100, size=(16, 16, 3))
        label_img = np.zeros((16, 16), dtype=np.uint16)
        label_img[2:8, 2:8] = 1
        result = measure_channel_correlation(label_img, img)
        assert "correlation_pearson_ch0_ch1" in result
        assert "correlation_pearson_ch1_ch2" in result
