from __future__ import annotations

import numpy as np
import pytest

from microProfiler.preprocessing.z_projection import _project_group


class TestProjectGroup:
    @pytest.fixture
    def z_stack(self):
        """Create a stack of 3 images with known values."""
        stack = np.zeros((3, 10, 10), dtype=np.uint16)
        stack[0, :, :] = 10
        stack[1, :, :] = 50
        stack[2, :, :] = 100
        return stack

    def _make_paths(self, stack, temp_dir):
        import tifffile
        paths = []
        for i in range(len(stack)):
            p = temp_dir / f"z{i}.tiff"
            tifffile.imwrite(str(p), stack[i])
            paths.append(p)
        return paths

    def test_max_projection(self, z_stack, temp_dir):
        paths = self._make_paths(z_stack, temp_dir)
        result = _project_group(paths, method="max")
        assert np.allclose(result, 100)

    def test_min_projection(self, z_stack, temp_dir):
        paths = self._make_paths(z_stack, temp_dir)
        result = _project_group(paths, method="min")
        assert np.allclose(result, 10)

    def test_mean_projection(self, z_stack, temp_dir):
        paths = self._make_paths(z_stack, temp_dir)
        result = _project_group(paths, method="mean")
        expected = np.mean(z_stack, axis=0)
        assert np.allclose(result, expected)

    def test_unknown_method(self, z_stack, temp_dir):
        paths = self._make_paths(z_stack, temp_dir)
        with pytest.raises(ValueError, match="Unknown projection method"):
            _project_group(paths, method="invalid")

    def test_single_image(self, temp_dir):
        import tifffile
        p = temp_dir / "single.tiff"
        tifffile.imwrite(str(p), np.ones((5, 5), dtype=np.uint16))
        result = _project_group([p], method="max")
        assert result.shape == (5, 5)
        assert np.allclose(result, 1)
