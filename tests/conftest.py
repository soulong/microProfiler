from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.loaders import write_image


@pytest.fixture
def temp_dir() -> Path:
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(str(path), ignore_errors=True)


@pytest.fixture
def db_path(temp_dir: Path) -> Path:
    return temp_dir / "test.db"


@pytest.fixture
def sample_image() -> np.ndarray:
    return np.array([[100, 200], [300, 400]], dtype=np.uint16)


@pytest.fixture
def synthetic_unified_dir(temp_dir: Path) -> Path:
    d = temp_dir / "unified"
    d.mkdir(parents=True, exist_ok=True)
    for well, field, stack, tp, ch in [
        ("A1", 1, 1, 1, 1),
        ("A1", 1, 1, 1, 2),
        ("A1", 1, 2, 1, 1),
        ("A1", 1, 2, 1, 2),
        ("B2", 1, 1, 1, 1),
        ("B2", 1, 1, 1, 2),
    ]:
        data = np.full((16, 16), ch * 100, dtype=np.uint16)
        name = f"{well}_f{field}_z{stack}_t{tp}_ch{ch}.tiff"
        write_image(d / name, data)
    return d


@pytest.fixture
def operetta_test_dir() -> Path:
    return Path("tests/test_dataset/operetta/2026-05-01_plate_Measurement 1")


@pytest.fixture
def mica_test_dir() -> Path:
    return Path("tests/test_dataset/mica/Sequence 002")


@pytest.fixture
def operetta_dataset(synthetic_unified_dir: Path) -> ImageDataset:
    return ImageDataset(synthetic_unified_dir)


@pytest.fixture
def simple_mask() -> np.ndarray:
    mask = np.zeros((16, 16), dtype=np.uint16)
    mask[2:6, 2:6] = 1
    mask[8:12, 8:12] = 2
    return mask


@pytest.fixture
def multichannel_image() -> np.ndarray:
    img = np.zeros((16, 16, 2), dtype=np.uint16)
    img[..., 0] = 100
    img[2:6, 2:6, 0] = 200
    img[8:12, 8:12, 0] = 50
    img[..., 1] = 50
    img[2:6, 2:6, 1] = 100
    img[8:12, 8:12, 1] = 200
    return img
