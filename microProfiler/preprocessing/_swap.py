"""Temp→swap atomicity context manager for in-place preprocessing."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)


class TempSwap:
    """Context manager that provides temp→swap atomicity for file writes.

    Writes go to a hidden ``.tmp_{step_name}/`` subdirectory under
    *target_dir*.  On success the temp files are moved to *target_dir*
    and the original source files are deleted.  On failure the temp
    directory is cleaned up and *target_dir* is left untouched.

    Parameters
    ----------
    target_dir : Path
        The directory to eventually write into.
    step_name : str
        Short identifier for the temp subdirectory (e.g. ``"basic"``).

    Example
    -------
    >>> with TempSwap(target_dir, "basic") as swap:
    ...     for src in source_paths:
    ...         corrected = process(src)
    ...         write_image(swap.temp_dir / src.name, corrected)
    ...         swap.mark_original(src)
    """

    def __init__(self, target_dir: Path, step_name: str) -> None:
        self.target_dir = Path(target_dir)
        self.temp_dir = self.target_dir / f".tmp_{step_name}"
        self._originals: List[Path] = []
        self._finalized = False

    @property
    def originals(self) -> List[Path]:
        """List of original source files marked for deletion on success."""
        return list(self._originals)

    def mark_original(self, path: Path) -> None:
        """Record a source file to delete after a successful swap."""
        self._originals.append(Path(path))

    def mark_originals(self, paths: List[Path]) -> None:
        """Record multiple source files to delete after a successful swap."""
        self._originals.extend(Path(p) for p in paths)

    def __enter__(self) -> TempSwap:
        """Create the temp directory and return ``self``."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        log.debug("TempSwap: created temp dir %s", self.temp_dir)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> bool:
        """Clean up temp directory on error or perform the swap on success."""
        if exc_type is not None:
            self._cleanup_temp()
            return False

        if self._finalized:
            return False

        try:
            self._swap()
        except Exception:
            log.exception("TempSwap: swap failed after processing — target may be inconsistent")
            raise

        return False

    def _swap(self) -> None:
        """Move temp files to target, then delete originals.

        Originals that share a filename with a moved temp file are
        *not* deleted — the move already overwrote them.
        """
        # Collect names of moved files to avoid re-deleting them
        moved_names: set[str] = set()

        for item in self.temp_dir.iterdir():
            dest = self.target_dir / item.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(item), str(dest))
            moved_names.add(item.name)

        # Delete originals, skipping any already overwritten by the move
        for src in self._originals:
            if src.exists() and src.name not in moved_names:
                src.unlink()

        # Clean up temp dir
        self._cleanup_temp()
        self._finalized = True

    def _cleanup_temp(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
