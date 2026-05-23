"""PipelineWorker — runs the full pipeline or a single step in a QThread with progress signals."""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from microProfiler.config import PipelineConfig
from microProfiler.pipeline import run_pipeline, run_step


class PipelineWorker(QObject):
    """Worker object that runs the pipeline or a single step in a background thread."""

    progress = Signal(str, int, int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False
        self._step_name: str | None = None
        self._thread: QThread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._execute)

    def run(self, cfg: PipelineConfig, ds=None) -> None:
        """Run the full pipeline. Pass pre-loaded dataset to skip disk loading."""
        self._cancelled = False
        self._cfg = cfg
        self._step_name = None
        self._ds = ds
        self._thread.start()

    def run_step(self, cfg: PipelineConfig, step_name: str, ds=None) -> None:
        """Run a single pipeline step. Pass pre-loaded dataset to skip disk loading."""
        self._cancelled = False
        self._cfg = cfg
        self._step_name = step_name
        self._ds = ds
        self._thread.start()

    def cancel(self) -> None:
        self._cancelled = True

    def _execute(self) -> None:
        try:
            def progress_cb(step, cur, tot, msg):
                if self._cancelled:
                    raise InterruptedError("Cancelled by user")
                self.progress.emit(step, cur, tot, msg)

            if self._step_name:
                self._result_ds = run_step(
                    self._cfg, self._step_name, progress_cb=progress_cb, ds=self._ds
                )
            else:
                self._result_ds = run_pipeline(self._cfg, progress_cb=progress_cb, ds=self._ds)
            self.finished.emit()
        except InterruptedError:
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._thread.quit()
