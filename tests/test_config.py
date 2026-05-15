from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from microProfiler.config import (
    PipelineConfig,
    ProfilingConfig,
    SegmentationConfig,
    VendorFormat,
    load_config,
)


class TestPipelineConfig:
    def test_minimal_config(self):
        cfg = PipelineConfig(input_dir=Path("/data"), format="operetta")
        assert cfg.input_dir == Path("/data")
        assert cfg.format == VendorFormat.operetta
        assert cfg.convert is None

    def test_mica_format(self):
        cfg = PipelineConfig(input_dir=Path("/data"), format="mica")
        assert cfg.format == VendorFormat.mica

    def test_missing_input_dir_raises(self):
        with pytest.raises(ValidationError):
            PipelineConfig()

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            PipelineConfig(input_dir=Path("/data"), format="invalid")

    def test_segmentation_config(self):
        cfg = PipelineConfig(
            input_dir=Path("/data"),
            segmentation={"object_name": "nuclei", "chan1": ["ch1"]},
        )
        assert cfg.segmentation is not None
        assert cfg.segmentation.object_name == "nuclei"
        assert cfg.segmentation.chan1 == ["ch1"]

    def test_profiling_config(self):
        cfg = PipelineConfig(
            input_dir=Path("/data"),
            profiling={"image_channels": ["ch1"], "object_mask_name": "cell"},
        )
        assert cfg.profiling is not None
        assert cfg.profiling.image_channels == ["ch1"]
        assert cfg.profiling.object_mask_name == "cell"
        assert cfg.profiling.object_radial_bins == 5  # default


class TestProfilingConfig:
    def test_defaults(self):
        cfg = ProfilingConfig()
        assert cfg.image_channels is None
        assert cfg.object_mask_name is None
        assert cfg.object_radial_bins == 5

    def test_radial_bins_validation(self):
        with pytest.raises(ValidationError):
            ProfilingConfig(object_radial_bins=0)


class TestSegmentationConfig:
    def test_defaults(self):
        cfg = SegmentationConfig()
        assert cfg.object_name == "cell"
        assert cfg.chan1 == []
        assert cfg.flow_threshold == 0.4

    def test_invalid_merge_raises(self):
        with pytest.raises(ValidationError):
            SegmentationConfig(merge1="invalid")


class TestLoadConfig:
    def test_load_valid_yaml(self, temp_dir):
        data = {
            "input_dir": "/data",
            "format": "operetta",
            "z_projection": {"method": "mean"},
        }
        path = temp_dir / "config.yaml"
        with open(path, "w") as f:
            yaml.dump(data, f)
        cfg = load_config(path)
        assert cfg.input_dir == Path("/data")
        assert cfg.z_projection is not None
        assert cfg.z_projection.method == "mean"

    def test_empty_path_raises(self):
        with pytest.raises(ValidationError):
            load_config()

    def test_nonexistent_path_with_overrides(self):
        overrides = {"input_dir": "/data", "format": "operetta"}
        cfg = load_config(Path("/nonexistent/file.yaml"), overrides=overrides)
        assert cfg is not None
        assert cfg.input_dir == Path("/data")

    def test_deep_merge(self):
        overrides = {
            "input_dir": "/data",
            "format": "operetta",
            "z_projection": {"method": "min"},
            "profiling": {"image_channels": ["ch1"]},
        }
        cfg = load_config(path=None, overrides=overrides)
        assert cfg.z_projection is not None
        assert cfg.z_projection.method == "min"
        assert cfg.profiling is not None

    def test_cli_overrides_merge(self):
        base = {"input_dir": "/data", "format": "operetta"}
        overrides = {"z_projection": {"method": "max"}}
        cfg_dict = base.copy()
        if overrides:
            from microProfiler.config import _deep_merge
            _deep_merge(cfg_dict, overrides)
        cfg = PipelineConfig(**cfg_dict)
        assert cfg.z_projection is not None
        assert cfg.z_projection.method == "max"
