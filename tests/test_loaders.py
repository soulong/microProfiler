from __future__ import annotations

import numpy as np
import pytest

from microProfiler.io.loaders import IntensityNormalizer, read_image, write_image


class TestReadWrite:
    def test_read_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            read_image("nonexistent.tiff")

    def test_write_and_read_back(self, temp_dir, sample_image):
        path = temp_dir / "test.tiff"
        write_image(path, sample_image)
        assert path.exists()
        result = read_image(path)
        assert np.array_equal(result, sample_image)

    def test_read_png(self, temp_dir, sample_image):
        from PIL import Image
        path = temp_dir / "test.png"
        Image.fromarray(sample_image).save(str(path))
        result = read_image(path)
        assert np.array_equal(result, sample_image)


class TestIntensityNormalizer:
    def test_none_method_returns_same_dtype(self):
        img = np.array([[100, 200], [300, 400]], dtype=np.uint16)
        norm = IntensityNormalizer(method=None)
        result = norm(img)
        assert result.dtype == np.uint16
        assert np.array_equal(result, img)

    def test_percentile_basic(self):
        img = np.array([[0, 1000], [50000, 65535]], dtype=np.uint16)
        norm = IntensityNormalizer(method="percentile", pmin=0, pmax=100)
        result = norm(img)
        assert result.dtype == np.uint16
        assert result.min() >= 0
        assert result.max() <= 65535

    def test_percentile_uniform_image(self):
        img = np.full((4, 4), 1000, dtype=np.uint16)
        norm = IntensityNormalizer(method="percentile", pmin=1, pmax=99.8)
        result = norm(img)
        assert result.dtype == np.uint16
        assert result.min() == result.max()

    def test_percentile_with_zeros(self):
        img = np.array([[0, 0], [0, 0]], dtype=np.uint16)
        norm = IntensityNormalizer(method="percentile")
        result = norm(img)
        assert result.dtype == np.uint16

    def test_minmax_normalization(self):
        img = np.array([[0, 1000], [50000, 65535]], dtype=np.uint16)
        norm = IntensityNormalizer(method="minmax")
        result = norm(img)
        assert result.dtype == np.uint16
        assert result.min() == 0
        assert result.max() == 65535

    def test_minmax_uniform(self):
        img = np.full((4, 4), 1000, dtype=np.uint16)
        norm = IntensityNormalizer(method="minmax")
        result = norm(img)
        assert result.dtype == np.uint16

    def test_zscore_basic(self):
        rng = np.random.default_rng(42)
        img = rng.integers(0, 1000, size=(16, 16), dtype=np.uint16)
        norm = IntensityNormalizer(method="zscore")
        result = norm(img)
        # zscore returns uint16 (clipped), but the scaling is different
        assert result.dtype == np.uint16

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown normalization method"):
            IntensityNormalizer(method="invalid")
