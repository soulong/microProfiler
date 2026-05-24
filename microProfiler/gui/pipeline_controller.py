"""Pipeline controller — orchestrates pipeline execution, preview, and fit operations.

Extracted from MainWindow to keep the window focused on UI management.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QMessageBox

from microProfiler.config import PipelineConfig
from microProfiler.gui.session import DictSettings, SessionFile
from microProfiler.gui.workers.pipeline_worker import PipelineWorker

_STEP_MAPPING = {
    "convert": "convert",
    "resize": "resize",
    "basic": "basic_correction",
    "zproject": "z_projection",
    "tile": "tile",
    "segment": "segmentation",
    "profile": "profiling",
}


class PipelineController(QObject):
    """Handles all pipeline execution orchestration on behalf of MainWindow.

    Parameters
    ----------
    window : MainWindow
        The parent window. The controller accesses ``window`` attributes
        directly for UI updates (progress, locking, channel population).
    """

    def __init__(self, window):
        super().__init__(parent=window)
        self._w = window  # MainWindow reference
        self._pending_executed_steps = []
        self._pending_step = None
        self._preview_block_index: int | None = None
        self._preview_pending_step = None
        # Worker generation counter: incremented in _ensure_worker so that
        # finished-signal handlers from stale workers can be detected.
        self._worker_gen = 0

    # ── Config builders ──────────────────────────────────────────────────

    def _output_path(self) -> Path:
        txt = self._w._output_dir.text() or self._w._input_dir.text()
        return Path(txt)

    def _build_base_config(self) -> PipelineConfig:
        cfg = PipelineConfig(
            input_dir=Path(self._w._input_dir.text()),
            format=self._w._format_combo.currentText(),
        )
        if self._w._output_dir.text():
            cfg.output_dir = Path(self._w._output_dir.text())
        return cfg

    def _build_pipeline_config(self, include_disabled: bool = False) -> PipelineConfig:
        """Build PipelineConfig from all step panels."""
        cfg = self._build_base_config()
        for step in self._w._all_step_panels:
            section = step.build_config_section()
            if section is not None:
                if not include_disabled:
                    if step.step_name == "convert" or not step.is_enabled():
                        continue
                    if not step._controls_widget.isEnabled():
                        continue
                if step.step_name == "segment":
                    cfg.segmentations = section  # List[dict]
                else:
                    attr = _STEP_MAPPING.get(step.step_name, step.step_name)
                    setattr(cfg, attr, section)
        return cfg

    def _build_step_config(self, step) -> PipelineConfig:
        """Build a config that includes only *step* (plus input/output)."""
        cfg = self._build_base_config()
        section = step.build_config_section()
        if section and step.is_enabled():
            if step.step_name == "segment":
                cfg.segmentations = section
            else:
                attr = _STEP_MAPPING.get(step.step_name, step.step_name)
                setattr(cfg, attr, section)
        return cfg

    # ── Worker management ────────────────────────────────────────────────

    def _ensure_worker(self) -> PipelineWorker:
        self._worker_gen += 1
        if hasattr(self._w, "_worker") and self._w._worker is not None:
            try:
                self._w._worker.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._w._worker.cancel()
            if self._w._worker._thread.isRunning():
                self._w._worker._thread.quit()
                self._w._worker._thread.wait(5000)
            self._w._worker.deleteLater()
        worker = PipelineWorker()
        worker.progress.connect(self._w._global_progress.update_progress, Qt.ConnectionType.QueuedConnection)
        worker.error.connect(self.on_pipeline_error, Qt.ConnectionType.QueuedConnection)
        return worker

    def _cancel_current_worker(self) -> None:
        if hasattr(self._w, "_worker") and self._w._worker is not None:
            self._w._worker.cancel()

    # ── Pipeline run handlers ────────────────────────────────────────────

    def _missing_input(self) -> bool:
        if not self._w._input_dir.text():
            QMessageBox.warning(self._w, "Missing Input", "Please select an input directory.")
            return True
        return False

    def apply_convert(self) -> None:
        if self._w._running or self._missing_input():
            return
        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        cfg = self._build_step_config(self._w._convert_panel)
        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._w._worker.finished.connect(self._on_convert_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._worker.run_step(cfg, "convert")

    def _on_convert_finished(self) -> None:
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        self._w._global_progress.finished()
        self._w._set_running(False)
        dataset = getattr(self._w._worker, "_result_ds", None)
        if dataset is not None:
            self._w._convert_panel.set_locked(True)
            self._w._segment_panel.setChecked(True)
            self._w._profile_panel.setChecked(True)
            self._w._state.dataset = dataset
            self._w._state.preprocessing_locked = True
            self._w._update_convert_info(dataset)
            logging.getLogger("microProfiler").info("Conversion complete - dataset reloaded.")
            self._w._segment_panel.populate_channels(dataset.intensity_colnames)
            self._w._profile_panel.populate_channels(dataset.intensity_colnames)
            self._w._profile_panel.populate_masks(dataset.mask_colnames)
            self._sync_seg_masks_to_profiling()
            self._w._basic_panel.set_preview_channels(dataset.intensity_colnames)
            self._w._update_tab_status()
            sf = SessionFile(self._output_path())
            sf.create_initial(self._w._format_combo.currentText())
            sf.add_step("convert")
            sf.set_running(False)

    def run_preprocessing(self) -> None:
        if self._w._running or self._missing_input():
            return
        if self._w._state.dataset is None:
            logging.getLogger("microProfiler").info("No dataset loaded - run Convert first.")
            return

        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)

        cfg = self._build_base_config()
        executed_steps = []
        for step in self._w._preprocessing_steps:
            section = step.build_config_section()
            if section and step.is_enabled():
                attr = _STEP_MAPPING.get(step.step_name, step.step_name)
                setattr(cfg, attr, section)
                executed_steps.append(step)

        if not executed_steps:
            QMessageBox.information(
                self._w, "No Steps To Run",
                "No enabled preprocessing steps to run. "
                "Check the checkbox on each step panel to enable it."
            )
            sf.set_running(False)
            self._w._set_running(False)
            return

        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._pending_executed_steps = executed_steps
        self._w._worker.finished.connect(self._on_preprocessing_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._run_pre_btn.setEnabled(False)
        self._w._worker.run(cfg, ds=self._w._state.dataset)

    def _on_preprocessing_finished(self) -> None:
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        executed_steps = self._pending_executed_steps
        updated_ds = getattr(self._w._worker, "_result_ds", None)
        self._w._global_progress.finished()
        self._w._set_running(False)
        for step in executed_steps:
            step.set_locked(True)
        if updated_ds is not None:
            self._w._state.dataset = updated_ds
            self._w._update_convert_info(updated_ds)
            self._w._segment_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._update_tab_status()
        logging.getLogger("microProfiler").info("Preprocessing complete.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        for step in executed_steps:
            sf.add_step(step.step_name)

    def run_segmentation(self) -> None:
        if self._w._running or self._missing_input():
            return
        if self._w._state.dataset is None:
            logging.getLogger("microProfiler").info("No dataset loaded - run Convert first.")
            return
        name_error = self._w._segment_panel.validate_object_names()
        if name_error:
            QMessageBox.warning(self._w, "Invalid Names", name_error)
            return

        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        cfg = self._build_step_config(self._w._segment_panel)
        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._w._worker.finished.connect(self._on_segmentation_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._worker.run_step(cfg, "segment", ds=self._w._state.dataset)

    def _on_segmentation_finished(self) -> None:
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        self._w._global_progress.finished()
        self._w._set_running(False)
        logging.getLogger("microProfiler").info("Segmentation complete.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        sf.add_step("segment")
        updated_ds = getattr(self._w._worker, "_result_ds", None)
        if updated_ds is not None:
            self._w._state.dataset = updated_ds
            self._w._update_convert_info(updated_ds)
            self._w._segment_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_masks(updated_ds.mask_colnames)
        self._w._update_tab_status()

    def run_profiling(self) -> None:
        if self._w._running or self._missing_input():
            return
        if not self._w._state.dataset:
            logging.getLogger("microProfiler").info("No dataset loaded - run Convert first.")
            return

        self._sync_seg_masks_to_profiling()
        obj_mask = self._w._profile_panel.get_object_mask_name()
        parent_mask = self._w._profile_panel.get_parent_mask_name()
        if parent_mask and parent_mask == obj_mask:
            QMessageBox.warning(
                self._w, "Invalid Mask Selection",
                "Parent mask cannot be the same as the object mask. "
                "Please choose a different parent mask or set it to None."
            )
            return

        # Check if result database exists and ask for overwrite confirmation
        db_path = self._output_path() / "results.db"
        if db_path.exists():
            reply = QMessageBox.question(
                self._w, "Overwrite Results",
                f"Results database already exists at:\n{db_path}\n\n"
                "Do you want to overwrite? This will delete existing results.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            db_path.unlink()
            logging.getLogger("microProfiler").info("Existing results database deleted.")

        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        cfg = self._build_step_config(self._w._profile_panel)
        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._w._worker.finished.connect(self._on_profiling_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._worker.run_step(cfg, "profile", ds=self._w._state.dataset)

    def _on_profiling_finished(self) -> None:
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        self._w._global_progress.finished()
        self._w._set_running(False)
        logging.getLogger("microProfiler").info("Profiling complete.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        sf.add_step("profile")

    def run_all(self) -> None:
        if self._w._running or self._missing_input():
            return
        if self._w._state.dataset is None:
            QMessageBox.warning(
                self._w, "Conversion Required",
                "Please run Convert first before running the full pipeline."
            )
            return
        self._sync_seg_masks_to_profiling()
        cfg = self._build_pipeline_config()
        has_steps = any(
            getattr(cfg, attr)
            for attr in ("resize", "basic_correction", "z_projection", "tile",
                         "segmentations", "profiling")
        )
        if not has_steps:
            QMessageBox.information(
                self._w, "Nothing to Run",
                "No unchecked or incomplete steps to run.",
            )
            return

        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._w._worker.finished.connect(self._on_pipeline_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._run_all_btn.setEnabled(False)
        self._w._worker.run(cfg, ds=self._w._state.dataset)

    def _on_pipeline_finished(self):
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        self._w._global_progress.finished()
        self._w._set_running(False)
        preprocessing_only = [
            self._w._convert_panel, self._w._resize_panel, self._w._basic_panel,
            self._w._zproject_panel, self._w._tile_panel,
        ]
        for step in preprocessing_only:
            step.set_locked(True)
        self._w._state.preprocessing_locked = True
        logging.getLogger("microProfiler").info("Pipeline complete - all steps finished.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        for step in self._w._all_step_panels:
            sf.add_step(step.step_name)
        updated_ds = getattr(self._w._worker, "_result_ds", None)
        if updated_ds is not None:
            self._w._state.dataset = updated_ds
            self._w._segment_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_masks(updated_ds.mask_colnames)
            self._w._update_convert_info(updated_ds)
        self._w._update_tab_status()

    def apply_step(self, step) -> None:
        if self._w._running:
            return
        if self._w._state.dataset is None:
            logging.getLogger("microProfiler").info("No dataset loaded - run Convert first.")
            return
        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        cfg = self._build_step_config(step)

        if step.step_name == "basic" and cfg.basic_correction is not None:
            root = self._output_path()
            model_dir = root / "BaSiC_model"
            if model_dir.exists() and any(model_dir.glob("model_*.pkl")):
                if "fit" in cfg.basic_correction.mode:
                    cfg.basic_correction.mode = "transform"
                    logging.getLogger("microProfiler").info(
                        "Pre-fitted BaSiC models detected — running transform only"
                    )

        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._pending_step = step
        self._w._worker.finished.connect(self._on_step_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._worker.run_step(cfg, step.step_name, ds=self._w._state.dataset)

    def _on_step_finished(self) -> None:
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        step = self._pending_step
        self._w._global_progress.finished()
        if step.step_name != "segment":
            step.set_locked(True)
        self._w._set_running(False)
        step_name = step.step_name
        logging.getLogger("microProfiler").info(f"{step_name} complete.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        sf.add_step(step_name)
        updated_ds = getattr(self._w._worker, "_result_ds", None)
        if updated_ds is not None:
            self._w._state.dataset = updated_ds
            self._w._update_convert_info(updated_ds)
            self._w._segment_panel.populate_channels(updated_ds.intensity_colnames)
            self._w._profile_panel.populate_channels(updated_ds.intensity_colnames)
            if hasattr(updated_ds, "mask_colnames"):
                self._w._profile_panel.populate_masks(updated_ds.mask_colnames)
        self._w._update_tab_status()

    # ── BaSiC fit ────────────────────────────────────────────────────────

    def fit_basic(self) -> None:
        if self._w._running:
            return
        if self._w._state.dataset is None:
            logging.getLogger("microProfiler").info("No dataset loaded - run Convert first.")
            return
        self._w._set_running(True)
        sf = SessionFile(self._output_path())
        sf.set_running(True)
        cfg = self._build_base_config()
        section = self._w._basic_panel.build_config_section()
        section["mode"] = "fit"
        cfg.basic_correction = section
        self._w._worker = self._ensure_worker()
        self._current_run_gen = self._worker_gen
        self._w._worker.finished.connect(self._on_fit_finished, Qt.ConnectionType.QueuedConnection)
        self._w._global_progress.reset()
        self._w._worker.run_step(cfg, "basic", ds=self._w._state.dataset)

    def _on_fit_finished(self):
        if getattr(self, "_current_run_gen", -1) != self._worker_gen:
            return
        self._w._global_progress.finished()
        self._w._set_running(False)
        logging.getLogger("microProfiler").info("BaSiC model fit complete.")
        sf = SessionFile(self._output_path())
        sf.set_running(False)

    # ── Preview ──────────────────────────────────────────────────────────

    def _ensure_random_row(self) -> bool:
        if self._w._state.random_row_idx is None:
            logging.getLogger("microProfiler").info("Click 'Pick Random' first to select an image.")
            return False
        return True

    def pick_random(self, step=None) -> None:
        ds = self._w._state.dataset
        if ds is not None and len(ds) > 0:
            import random as _random
            self._w._state.random_row_idx = _random.randint(0, len(ds) - 1)
            idx = self._w._state.random_row_idx
            logging.getLogger("microProfiler").info(
                f"Picked random row {idx}"
            )
            # For BaSiC, immediately load and show the raw image
            if step and step.step_name == "basic" and hasattr(step, "_channel_tiles"):
                from microProfiler.io.loaders import read_image
                row = ds.metadata.iloc[idx]
                row_dir = Path(row["directory"])
                for ch in ds.intensity_colnames:
                    img = read_image(row_dir / row[ch])
                    step._channel_tiles[ch][0].set_image(img)

    def on_segment_pick(self, block_index: int) -> None:
        ds = self._w._state.dataset
        if ds is None or len(ds) == 0:
            return
        import random as _random
        self._w._state.random_row_idx = _random.randint(0, len(ds) - 1)
        idx = self._w._state.random_row_idx
        logging.getLogger("microProfiler").info(
            f"Segment block {block_index}: picked random row {idx}"
        )
        blocks = self._w._segment_panel._blocks
        if block_index >= len(blocks):
            return
        block = blocks[block_index]
        chan1 = block.get_chan1() or ds.intensity_colnames[:1]
        chan2 = block.get_chan2() or None

        from microProfiler.io.loaders import read_image
        row = ds.metadata.iloc[idx]
        row_dir = Path(row["directory"])

        if chan1:
            ch = chan1[0]
            c1_img = read_image(row_dir / row[ch])
            self._w._segment_panel.set_preview_c1(block_index, c1_img)
        if chan2:
            ch = chan2[0]
            try:
                c2_img = read_image(row_dir / row[ch])
                self._w._segment_panel.set_preview_c2(block_index, c2_img)
            except Exception:
                pass

    def on_segment_preview(self, block_index: int) -> None:
        if self._w._preview_running:
            return
        ds = self._w._state.dataset
        if not self._ensure_random_row() or ds is None:
            return
        blocks = self._w._segment_panel._blocks
        if block_index >= len(blocks):
            return
        block = blocks[block_index]
        idx = self._w._state.random_row_idx
        seg_params = block.build_config_section()
        seg_params.pop("object_name", None)
        self._preview_block_index = block_index
        self._preview_pending_step = self._w._segment_panel
        self._w._preview_running = True
        logging.getLogger("microProfiler").info(
            f"Segment preview block {block_index} row {idx}"
        )
        self._w._preview_worker.preview_segment(ds, idx, seg_params)

    def preview_step(self, step) -> None:
        if self._w._preview_running:
            return
        ds = self._w._state.dataset
        if not self._ensure_random_row() or ds is None:
            return
        idx = self._w._state.random_row_idx
        logging.getLogger("microProfiler").info(
            f"Preview start: {step.step_name} row {idx}"
        )
        self._preview_pending_step = step
        self._preview_block_index = None
        self._w._preview_running = True
        if step.step_name == "basic":
            chans = ds.intensity_colnames
            self._w._preview_worker.preview_basic(ds, idx, chans)

    def on_preview_ready(self, result) -> None:
        self._w._preview_running = False
        step = self._preview_pending_step
        if step is None:
            return
        extra = result.get("extra", {})
        after = result.get("after", [])
        before = result.get("before", [])

        if step.step_name == "basic":
            step.update_preview_raw(dict(before))
            step.update_preview_corrected(dict(after))
            flatfield = extra.get("flatfield", {})
            if flatfield:
                step.update_preview_flatfield(flatfield)
        elif step.step_name == "segment":
            block_idx = self._preview_block_index
            if block_idx is None:
                return
            c1 = extra.get("c1_img")
            c2 = extra.get("c2_img")
            mask = extra.get("mask")
            if c1 is not None:
                self._w._segment_panel.set_preview_c1(block_idx, c1)
            if c2 is not None:
                self._w._segment_panel.set_preview_c2(block_idx, c2)
            if mask is not None:
                self._w._segment_panel.set_preview_mask(block_idx, mask)
        logging.getLogger("microProfiler").info(f"Preview complete for {step.step_name}")
        self._preview_pending_step = None
        self._preview_block_index = None

    def on_preview_error(self, message: str) -> None:
        self._w._preview_running = False
        step_name = (
            self._preview_pending_step.step_name
            if self._preview_pending_step else "unknown"
        )
        logging.getLogger("microProfiler").error(
            f"Preview error ({step_name}): {message}"
        )
        self._preview_pending_step = None
        self._preview_block_index = None

    # ── Helpers ──────────────────────────────────────────────────────────

    def _sync_seg_masks_to_profiling(self) -> None:
        seg_names = self._w._segment_panel.get_object_names()
        if seg_names:
            self._w._profile_panel.populate_masks(["mask_" + n for n in seg_names])

    def on_pipeline_error(self, message: str) -> None:
        self._w._global_progress.show_error(message)
        self._w._set_running(False)
        sf = SessionFile(self._output_path())
        sf.set_running(False)
        QMessageBox.critical(self._w, "Pipeline Error", message)
