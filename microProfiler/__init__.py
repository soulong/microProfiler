"""microProfiler: microscopy image preprocessing, segmentation, and profiling."""

from importlib.metadata import PackageNotFoundError, version

from microProfiler.io.dataset import ImageDataset
from microProfiler.io.database import Database

try:
    __version__ = version("microProfiler")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "ImageDataset",
    "Database",
]
