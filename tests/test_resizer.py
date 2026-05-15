from __future__ import annotations


from microProfiler.io.dataset import ImageDataset
from microProfiler.preprocessing.resizer import resize_dataset


class TestResizeDataset:
    def test_identity_factor_returns_same(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        result = resize_dataset(ds, scale_factor=1.0)
        assert result is ds

    def test_resize_half(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.measurement_dir = synthetic_unified_dir
        result = resize_dataset(ds, scale_factor=0.5, root_dir=temp_dir)
        assert len(result) == len(ds)
        assert "resized" in str(result.measurement_dir)

    def test_resized_images_have_correct_shape(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        result = resize_dataset(ds, scale_factor=0.5, root_dir=temp_dir)
        img, _ = result.get_imageset(0)
        assert img.shape[0] == 8  # 16 * 0.5
        assert img.shape[1] == 8
