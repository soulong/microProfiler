"""Configuration management for the microProfiler pipeline."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VendorFormat(str, Enum):
    operetta = "operetta"
    mica = "mica"


class ProjectionMethod(str, Enum):
    max = "max"
    mean = "mean"
    min = "min"


class ConvertConfig(BaseModel):
    """Converter configuration."""

    output_name: str = Field("image", description="Output directory name under root")
    resize_factor: float = Field(
        1.0, ge=0.1, le=4.0, description="Resize scale factor during conversion",
    )
    delete_original: bool = Field(
        False, description="Delete original vendor files after conversion",
    )


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration."""

    model_config = ConfigDict(validate_assignment=True)

    input_dir: Path = Field(..., description="Path to raw measurement directory")
    output_dir: Optional[Path] = Field(None, description="Output directory for processed files")
    format: VendorFormat = Field(VendorFormat.operetta, description="Vendor format of input data")

    convert: Optional[ConvertConfig] = Field(None, description="Converter configuration")
    resize: Optional[ResizeConfig] = Field(None, description="Resize step configuration")
    basic_correction: Optional[BasicConfig] = Field(
        None, description="BaSiC shading correction configuration",
    )
    z_projection: Optional[ZProjectionConfig] = Field(
        None, description="Z-projection configuration",
    )
    tile: Optional[TileConfig] = Field(None, description="Tile splitting configuration")

    segmentations: List[SegmentationConfig] = Field(
        default_factory=list, description="Segmentation configurations (multi-seg supported)",
    )

    @field_validator("segmentations", mode="before")
    @classmethod
    def _migrate_single_seg(cls, v: Any) -> Any:
        """Accept a single dict (old format) and wrap in a list."""
        if isinstance(v, dict):
            return [v]
        return v

    profiling: Optional[ProfilingConfig] = Field(None, description="Profiling configuration")


class ResizeConfig(BaseModel):
    scale_factor: float = Field(1.0, ge=0.1, le=4.0, description="Resize scale factor")


class BasicConfig(BaseModel):
    mode: str = Field("fit-transform", pattern=r"^(fit|transform|fit-transform)$")
    n_image: int = Field(50, ge=1, description="Number of images for fitting")
    working_size: int = Field(64, ge=16, description="Working size for BaSiC model")
    enable_darkfield: bool = Field(False, description="Enable darkfield estimation")


class ZProjectionConfig(BaseModel):
    method: ProjectionMethod = Field(ProjectionMethod.max, description="Projection method")


class TileConfig(BaseModel):
    tile_width: int = Field(1024, ge=64, description="Tile width in pixels")
    tile_height: int = Field(1024, ge=64, description="Tile height in pixels")


class SegmentationConfig(BaseModel):
    object_name: str = Field("cell", description="Object name for masks")
    chan1: List[str] = Field(default_factory=list, description="First channel group")
    chan2: Optional[List[str]] = Field(None, description="Second channel group")
    merge1: str = Field("mean", pattern=r"^(mean|max|min)$")
    merge2: str = Field("mean", pattern=r"^(mean|max|min)$")
    model_name: str = Field("cpsam", description="Cellpose model name")
    diameter: Optional[float] = Field(None, description="Object diameter in pixels")
    flow_threshold: float = Field(0.4, ge=0.0)
    cellprob_threshold: float = Field(0.0, ge=0.0)


class ProfilingConfig(BaseModel):
    image_channels: Optional[List[str]] = Field(
        None, description="Channels for image profiling",
    )
    image_thresholds: Optional[Dict[str, float]] = Field(
        None, description="Per-channel thresholds for image-level object detection",
    )
    object_mask_name: Optional[str] = Field(
        None, description="Mask for object profiling",
    )
    parent_mask_name: Optional[str] = Field(
        None, description="Parent mask for hierarchical object assignment",
    )
    object_intensity_channels: Optional[List[str]] = Field(
        None, description="Channels for object intensity",
    )
    object_radial_channels: Optional[List[str]] = Field(
        None, description="Channels for radial distribution",
    )
    object_radial_bins: int = Field(5, ge=1)
    object_granularity_channels: Optional[List[str]] = Field(None)
    object_granularity_scales: Optional[str] = Field(
        None, description="Comma-separated scale indices for granularity (e.g. '0,1,2,3,4')",
    )
    object_granularity_subsample: Optional[float] = Field(
        None, ge=0.01, le=1.0, description="Granularity subsample fraction",
    )
    object_granularity_element_size: Optional[int] = Field(
        None, ge=1, le=100, description="Granularity element size",
    )
    object_glcm_channels: Optional[List[str]] = Field(None)
    object_glcm_distances: Optional[List[int]] = Field(None)
    object_glcm_levels: Optional[int] = Field(
        None, ge=2, le=256, description="GLCM quantization levels",
    )
    object_glcm_angles: Optional[str] = Field(
        None, description="Comma-separated GLCM angles in radians (e.g. '0,0.785,1.571,2.356')",
    )
    correlation_pairs: Optional[List[List[str]]] = Field(
        None, description="Channel pairs for correlation",
    )


def load_config(
    path: Optional[Union[str, Path]] = None,
    overrides: Optional[Dict] = None,
) -> PipelineConfig:
    """Load pipeline configuration from YAML file with optional CLI overrides.

    Parameters
    ----------
    path : str or Path, optional
        Path to a YAML configuration file.
    overrides : dict, optional
        Dictionary of overrides merged on top of the file config.

    Returns
    -------
    PipelineConfig
        Validated pipeline configuration.
    """
    config_dict: Dict = {}

    if path is not None:
        path = Path(path)
        if path.exists():
            with open(path) as f:
                config_dict = yaml.safe_load(f) or {}

    if overrides:
        _deep_merge(config_dict, overrides)

    return PipelineConfig(**config_dict)


def _deep_merge(base: Dict, overrides: Dict) -> None:
    """Recursively merge overrides into base dict.

    Parameters
    ----------
    base : dict
        Base dictionary (modified in-place).
    overrides : dict
        Override values to merge.
    """
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
