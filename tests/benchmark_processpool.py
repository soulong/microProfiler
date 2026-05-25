"""Benchmark ProcessPoolExecutor for object profiling on mica dataset."""
import time, copy, gc
import numpy as np
import pandas as pd
from pathlib import Path
from microProfiler.io.dataset import ImageDataset
from microProfiler.profiling.object_profiler import profile_objects


def replicate(ds, factor):
    df = ds.metadata.copy()
    dfs = []
    for i in range(factor):
        d = df.copy()
        d['well'] = [f'{w}_r{i}' for w in d['well']]
        dfs.append(d)
    new_meta = pd.concat(dfs, ignore_index=True)
    new_ds = copy.copy(ds)
    new_ds._metadata = new_meta
    return new_ds


def limit_mask_objects(mask, max_label=50):
    """Zero out all labels > max_label to limit objects per image."""
    result = mask.copy()
    result[result > max_label] = 0
    return result


class LimitedMaskDataset:
    """Wrapper that limits mask objects on the fly."""
    def __init__(self, ds, mask_name, max_objects=50):
        self._ds = ds
        self._mask_name = mask_name
        self._max_objects = max_objects

    def __getattr__(self, name):
        return getattr(self._ds, name)

    def __len__(self):
        return len(self._ds)

    def get_imageset(self, idx, channels=None, masks=None):
        image_data, mask_data = self._ds.get_imageset(idx, channels, masks)
        if self._mask_name in mask_data:
            mask_data[self._mask_name] = limit_mask_objects(
                mask_data[self._mask_name], self._max_objects
            )
        return image_data, mask_data


def main():
    ds_dir = Path(r'C:\Users\haohe\Desktop\test_result\mica\Sequence 002\image')
    base_ds = ImageDataset(ds_dir)
    mask_name = base_ds.mask_colnames[0].removeprefix('mask_')

    # Count objects per image to verify
    total = 0
    for i in range(len(base_ds)):
        _, masks = base_ds.get_imageset(i)
        mask = masks[mask_name]
        total += len(set(mask.flatten())) - 1
    print(f'Base: {len(base_ds)} images, ~{total} objects ({total//len(base_ds)}/img), mask={mask_name}')

    # Quick verify: first image with first 50 objects
    _, masks = base_ds.get_imageset(0)
    full_obj = len(set(masks[mask_name].flatten())) - 1
    limited = limit_mask_objects(masks[mask_name], 50)
    n_limited = len(set(limited.flatten())) - 1
    print(f'  Image 0: {full_obj} objects full, {n_limited} limited to 50')

    max_obj = 50

    def benchmark(ds, mask, n_workers, label):
        gc.collect()
        t0 = time.perf_counter()
        result = profile_objects(
            ds, mask_name=mask,
            intensity_channels=ds.intensity_colnames,
            n_workers=n_workers,
        )
        t1 = time.perf_counter()
        n_rows = len(result) if result is not None else 0
        rate = n_rows / (t1 - t0) if t1 > t0 else 0
        print(f'  {label}: {t1-t0:.2f}s, {n_rows} objs ({rate:.0f} obj/s)')
        return t1 - t0

    for factor in [1, 3, 6]:
        ds = replicate(base_ds, factor)
        wds = LimitedMaskDataset(ds, mask_name, max_obj)
        n = len(wds)
        est_obj = n * max_obj
        print(f'\n=== {n} images, ~{est_obj} objects (factor {factor}x, max {max_obj} obj/img) ===')

        t_seq = benchmark(wds, mask_name, 1, 'n_workers=1 ')
        t_4 = benchmark(wds, mask_name, 4, 'n_workers=4 ')
        t_8 = benchmark(wds, mask_name, 8, 'n_workers=8 ')
        if t_seq > 0:
            print(f'  Speedup: 4w={t_seq/t_4:.1f}x, 8w={t_seq/t_8:.1f}x')


if __name__ == '__main__':
    main()
