"""Pipeline state management for the GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from microProfiler.config import PipelineConfig
from microProfiler.io.dataset import ImageDataset


@dataclass
class PipelineState:
    """Tracks the current state of the GUI pipeline session."""

    input_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    format: str = "operetta"

    dataset: Optional[ImageDataset] = None
    random_row_idx: int | None = None

    preprocessing_locked: bool = False
    steps_applied: set = field(default_factory=set)
    steps_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "convert": True,
        "resize": False,
        "basic": False,
        "zproject": False,
        "tile": False,
        "segment": False,
        "profile": False,
    })

    basic_models: Dict[str, object] = field(default_factory=dict)

    config: Optional[PipelineConfig] = None

    def build_config(self) -> PipelineConfig:
        """Build a PipelineConfig from current state (overridden by step panels at runtime)."""
        return PipelineConfig(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            format=self.format,
        )
