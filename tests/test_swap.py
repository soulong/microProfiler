from __future__ import annotations

from pathlib import Path

import pytest

from microProfiler.preprocessing._swap import TempSwap
from microProfiler.io.loaders import write_image


def _create_file(path: Path, content: str = "data") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestTempSwap:
    def test_normal_flow(self, temp_dir: Path):
        target = temp_dir / "target"
        target.mkdir()
        src = _create_file(target / "original.txt")

        with TempSwap(target, "test") as swap:
            (swap.temp_dir / "output.txt").write_text("new")
            swap.mark_original(src)

        assert (target / "output.txt").exists()
        assert not (target / "original.txt").exists()
        assert not (temp_dir / ".tmp_test").exists()

    def test_crash_during_write_leaves_target_untouched(self, temp_dir: Path):
        target = temp_dir / "target"
        target.mkdir()
        src = _create_file(target / "original.txt")

        class TestCrash(Exception):
            pass

        with pytest.raises(TestCrash):
            with TempSwap(target, "test") as swap:
                (swap.temp_dir / "partial.txt").write_text("partial")
                swap.mark_original(src)
                raise TestCrash("crash")

        assert (target / "original.txt").exists()
        assert not (target / "partial.txt").exists()
        assert not (temp_dir / ".tmp_test").exists()

    def test_crash_during_swap_leaves_safe_duplicates(self, temp_dir: Path, monkeypatch):
        target = temp_dir / "target"
        target.mkdir()
        src = _create_file(target / "original.txt")

        def crashing_swap(self_swap):
            (self_swap.temp_dir / "output.txt").write_text("new")
            raise RuntimeError("simulated crash during swap")

        monkeypatch.setattr(TempSwap, "_swap", crashing_swap)

        with pytest.raises(RuntimeError):
            with TempSwap(target, "test") as swap:
                (swap.temp_dir / "output.txt").write_text("new")
                swap.mark_original(src)

        assert (target / "original.txt").exists()
        assert not (temp_dir / ".tmp_test").exists()

    def test_cleanup_on_failure_removes_temp_dir(self, temp_dir: Path):
        target = temp_dir / "target"
        target.mkdir()

        with pytest.raises(ValueError):
            with TempSwap(target, "test") as swap:
                (swap.temp_dir / "f.txt").write_text("f")
                raise ValueError("fail")

        assert not (temp_dir / ".tmp_test").exists()
        assert not (target / "f.txt").exists()

    def test_mark_originals_multiple(self, temp_dir: Path):
        target = temp_dir / "target"
        target.mkdir()
        f1 = _create_file(target / "a.txt")
        f2 = _create_file(target / "b.txt")

        with TempSwap(target, "test") as swap:
            (swap.temp_dir / "out.txt").write_text("new")
            swap.mark_originals([f1, f2])

        assert (target / "out.txt").exists()
        assert not (target / "a.txt").exists()
        assert not (target / "b.txt").exists()

    def test_no_originals_marked(self, temp_dir: Path):
        target = temp_dir / "target"
        target.mkdir()

        with TempSwap(target, "test") as swap:
            (swap.temp_dir / "out.txt").write_text("new")

        assert (target / "out.txt").exists()
        assert not (temp_dir / ".tmp_test").exists()

    def test_write_image_integration(self, temp_dir: Path):
        import numpy as np
        target = temp_dir / "target"
        target.mkdir()
        orig = target / "orig.tiff"
        write_image(orig, np.ones((4, 4), dtype=np.uint16))

        with TempSwap(target, "test") as swap:
            write_image(swap.temp_dir / "replaced.tiff", np.full((4, 4), 99, dtype=np.uint16))
            swap.mark_original(orig)

        assert (target / "replaced.tiff").exists()
        assert not (target / "orig.tiff").exists()
