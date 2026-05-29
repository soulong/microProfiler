"""Pipeline state management for the GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from microProfiler.io.dataset import ImageDataset


@dataclass
class PipelineState:
    """Tracks the current state of the GUI pipeline session."""

    dataset: Optional[ImageDataset] = None
    random_row_idx: int | None = None
    preprocessing_locked: bool = False
    basic_models: Dict[str, object] = field(default_factory=dict)
