"""Session persistence — session.json for pipeline parameters and step status."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def session_save_path(directory: Path) -> Path:
    """Return the path to the .microprofiler/session.json file for *directory*."""
    return directory / ".microprofiler" / "session.json"


def detect_disk_state(directory: Path) -> Dict[str, bool]:
    """Detect which pipeline steps have been applied by inspecting disk state.

    Returns a dict with keys: *convert*, *segment*, *profile*.
    Preprocessing steps (resize, basic, zproject, tile) cannot be detected
    from disk alone because they modify images in-place.
    """
    state: Dict[str, bool] = {
        "convert": False,
        "segment": False,
        "profile": False,
    }

    if not directory.exists():
        return state

    images_dir = directory / "Images"
    if images_dir.is_dir() and list(images_dir.glob("*.tiff")):
        state["convert"] = True

    images_dir = directory / "Images"
    mask_files = list(images_dir.glob("mask_*.tiff")) if images_dir.is_dir() else []
    if mask_files:
        state["segment"] = True

    if (directory / "results.db").exists():
        state["profile"] = True

    return state


class DictSettings:
    """In-memory dict-based settings, matching the QSettingsPersistence interface
    for backward compatibility with ``save_to_settings`` / ``load_from_settings``.

    Wraps a nested dict: ``{step_name: {key: value, ...}, ...}``
    where values are stored as native Python types (not strings).
    """

    def __init__(self, data: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self._data: Dict[str, Dict[str, Any]] = data or {}

    def save_params(self, step_name: str, params: Dict[str, Any]) -> None:
        self._data[step_name] = params

    def load_params(self, step_name: str) -> Dict[str, Any]:
        return self._data.get(step_name, {})

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return self._data

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> "DictSettings":
        return cls(data)


class SessionFile:
    """Read/write ``.microprofiler/session.json`` atomically."""

    VERSION = 1

    class _Data:
        version: int

    def __init__(self, data_dir: Path):
        self._path = session_save_path(data_dir)

    def exists(self) -> bool:
        return self._path.exists()

    def load(self) -> Optional[Dict[str, Any]]:
        if not self._path.exists():
            return None
        try:
            with open(self._path) as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, data: Dict[str, Any]) -> None:
        data.setdefault("version", self.VERSION)
        data["modified"] = datetime.now().isoformat()
        self._path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self._path)

    def create_initial(self, format: str) -> None:
        self.save({
            "version": self.VERSION,
            "format": format,
            "created": datetime.now().isoformat(),
            "running": False,
            "steps_applied": [],
            "steps_locked": [],
        })

    def add_step(self, step_name: str) -> None:
        data = self.load() or {}
        applied: List[str] = data.get("steps_applied", [])
        locked: List[str] = data.get("steps_locked", [])
        if step_name not in applied:
            applied.append(step_name)
        if step_name not in locked:
            locked.append(step_name)
        data["steps_applied"] = applied
        data["steps_locked"] = locked
        self.save(data)

    def set_running(self, running: bool) -> None:
        data = self.load()
        if data is None:
            return
        data["running"] = running
        self.save(data)

    def save_all_params(self, params: Dict[str, Dict[str, Any]]) -> None:
        """Save full pipeline parameters into session.json."""
        data = self.load() or {}
        data["params"] = params
        self.save(data)

    def load_all_params(self) -> Dict[str, Dict[str, Any]]:
        """Load pipeline parameters from session.json as native types."""
        data = self.load()
        if not data or "params" not in data:
            return {}
        return data["params"]

    def save_input_dir(self, path: str) -> None:
        data = self.load() or {}
        data["general"] = dict(data.get("general", {}))
        data["general"]["input_dir"] = path
        self.save(data)

    def load_input_dir(self) -> str | None:
        data = self.load()
        if data and "general" in data:
            return data["general"].get("input_dir")
        return None
