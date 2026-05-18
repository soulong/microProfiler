from __future__ import annotations


from microProfiler.io.dataset import ImageDataset
from microProfiler.preprocessing.resizer import resize_dataset


class TestResizeDataset:
    def test_identity_factor_returns_same(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        result = resize_dataset(ds, scale_factor=1.0)
        assert result is ds

    def test_resize_half_new_dir(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        ds.measurement_dir = synthetic_unified_dir
        result = resize_dataset(ds, scale_factor=0.5, root_dir=temp_dir, inplace=False)
        assert len(result) == len(ds)
        assert "resized" in str(result.measurement_dir)

    def test_resized_images_have_correct_shape_new_dir(self, synthetic_unified_dir, temp_dir):
        ds = ImageDataset(synthetic_unified_dir)
        result = resize_dataset(ds, scale_factor=0.5, root_dir=temp_dir, inplace=False)
        img, _ = result.get_imageset(0)
        assert img.shape[0] == 8  # 16 * 0.5
        assert img.shape[1] == 8

    def test_resize_inplace_replaces_originals(self, synthetic_unified_dir):
        ds = ImageDataset(synthetic_unified_dir)
        original_count = len(list(synthetic_unified_dir.glob("*.tiff")))
        result = resize_dataset(ds, scale_factor=0.5, inplace=True)
        assert len(result) == len(ds)
        remaining = list(synthetic_unified_dir.glob("*.tiff"))
        assert len(remaining) == original_count  # same count, same dir
        assert not any(p.name.startswith(".tmp") for p in synthetic_unified_dir.iterdir())

    def test_resize_inplace_no_duplicates(self, synthetic_unified_dir):
        before = set(synthetic_unified_dir.iterdir())
        ds = ImageDataset(synthetic_unified_dir)
        resize_dataset(ds, scale_factor=0.5, inplace=True)
        after = set(synthetic_unified_dir.iterdir())
        assert len(after) == len(before)
