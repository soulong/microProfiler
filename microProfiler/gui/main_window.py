"""Main window -- top-level application shell with tabs, progress, and log."""
from __future__ import annotations

from pathlib import Path

import yaml
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import (
    QApplication,
    QAbstractSpinBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import logging

from microProfiler.gui.progress_bar import ProgressPanel, QtLogHandler
from microProfiler.gui.session import DictSettings, SessionFile, detect_disk_state
from microProfiler.gui.pipeline_controller import PipelineController
from microProfiler.gui.workers.preview_worker import PreviewWorker
from microProfiler.gui.state import PipelineState
from microProfiler.gui.sidebar import Sidebar
from microProfiler.gui.panels import (
    BaSiCStepPanel, ConvertStepPanel, ProfileStepPanel,
    ResizeStepPanel, SegmentStepPanel, TileStepPanel, ZProjectStepPanel,
)
from microProfiler.io.dataset import ImageDataset
from microProfiler.logging_utils import setup_logging


class _WheelBlocker(QObject):
    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Wheel:
            return False
        pos = event.globalPosition().toPoint()
        w = QApplication.instance().widgetAt(pos)
        for _ in range(4):
            if w is None:
                break
            if isinstance(w, (QAbstractSpinBox, QComboBox)) and not w.hasFocus():
                return True
            w = w.parentWidget()
        return False

_wheel_blocker = _WheelBlocker()




class MainWindow(QMainWindow):
    """Top-level application window with tab-based pipeline navigation."""

    def __init__(self):
        super().__init__()
        self._state = PipelineState()
        self._ctrl = PipelineController(self)
        self._output_manually_set = False

        self.setWindowTitle("microProfiler")
        self.setMinimumSize(1200, 800)
        self._running = False
        self._preview_running = False
        self._preview_worker = PreviewWorker()
        self._preview_worker.preview_ready.connect(self._ctrl.on_preview_ready)
        self._preview_worker.error.connect(self._ctrl.on_preview_error)
        self._preview_pending_step = None
        self._preview_block_index: int | None = None

        # In-app logging
        self._log_handler = QtLogHandler()
        self._log_handler.log_received.connect(self._on_log_message)
        setup_logging(qt_handler=self._log_handler, clear_existing=False)

        self._build_ui()
        self._connect_signals()
        self._restore_session()
        self._apply_compact_widths()

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── Sidebar ────────────────────────────────────────────────────
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # ── Right content area ─────────────────────────────────────────
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # ── Create step panels ─────────────────────────────────────────
        self._convert_panel = ConvertStepPanel(self._state)
        self._resize_panel = ResizeStepPanel(self._state)
        self._basic_panel = BaSiCStepPanel(self._state)
        self._zproject_panel = ZProjectStepPanel(self._state)
        self._tile_panel = TileStepPanel(self._state)
        self._segment_panel = SegmentStepPanel(self._state)
        self._profile_panel = ProfileStepPanel(self._state)

        self._all_step_panels = [
            self._convert_panel, self._resize_panel, self._basic_panel,
            self._zproject_panel, self._tile_panel,
            self._segment_panel, self._profile_panel,
        ]

        self._preprocessing_steps = [
            self._resize_panel, self._basic_panel,
            self._zproject_panel, self._tile_panel,
        ]

        # ── QStackedWidget ─────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ── Page 0: Convert ────────────────────────────────────────────
        convert_page = QWidget()
        convert_layout = QVBoxLayout(convert_page)

        self._convert_splitter = QSplitter()
        self._convert_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Left panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 6, 12)

        input_group = QGroupBox("Input")
        input_form = QFormLayout(input_group)
        self._input_dir = QLineEdit()
        self._input_browse = QPushButton("Browse...")
        self._input_browse.setProperty("class", "secondary")
        input_row = QHBoxLayout()
        input_row.addWidget(self._input_dir)
        input_row.addWidget(self._input_browse)
        self._format_combo = QComboBox()
        self._format_combo.addItems(["operetta", "mica"])
        self._output_dir = QLineEdit()
        self._output_browse = QPushButton("Browse...")
        self._output_browse.setProperty("class", "secondary")
        output_row = QHBoxLayout()
        output_row.addWidget(self._output_dir)
        output_row.addWidget(self._output_browse)
        input_form.addRow("Input directory:", input_row)
        input_form.addRow("Format:", self._format_combo)
        input_form.addRow("Output directory:", output_row)
        left_layout.addWidget(input_group)

        left_layout.addWidget(self._convert_panel)
        left_layout.addStretch()

        # --- Right panel ---
        right_panel = QWidget()
        right_layout_panel = QVBoxLayout(right_panel)
        right_layout_panel.setContentsMargins(6, 12, 12, 12)

        self._convert_info_group = QGroupBox("Dataset Info")
        self._convert_info_layout = QFormLayout(self._convert_info_group)
        self._convert_info_label = QLabel(
            "Run conversion to see dataset information."
        )
        self._convert_info_label.setWordWrap(True)
        self._convert_info_label.setProperty("class", "placeholder")
        self._convert_info_layout.addRow(self._convert_info_label)
        right_layout_panel.addWidget(self._convert_info_group)
        right_layout_panel.addStretch()

        self._convert_splitter.addWidget(left_panel)
        self._convert_splitter.addWidget(right_panel)
        self._convert_splitter.setSizes([700, 300])
        convert_layout.addWidget(self._convert_splitter, 1)
        self._stack.addWidget(convert_page)

        # ── Page 1: Pre-process ────────────────────────────────────────
        pre_page = QWidget()
        pre_layout = QVBoxLayout(pre_page)
        pre_layout.setContentsMargins(12, 12, 12, 12)

        pre_scroll = QScrollArea()
        pre_scroll.setWidgetResizable(True)
        pre_scroll_inner = QWidget()
        pre_scroll_layout = QVBoxLayout(pre_scroll_inner)
        for p in self._preprocessing_steps:
            pre_scroll_layout.addWidget(p)
        self._run_pre_btn = QPushButton("Run Preprocessing")
        self._run_pre_btn.setProperty("class", "primary")
        pre_scroll_layout.addWidget(self._run_pre_btn)
        pre_scroll_layout.addStretch()
        pre_scroll.setWidget(pre_scroll_inner)
        pre_layout.addWidget(pre_scroll, 1)
        self._stack.addWidget(pre_page)

        # ── Page 2: Segmentation ───────────────────────────────────────
        seg_page = QWidget()
        seg_layout = QVBoxLayout(seg_page)
        seg_layout.setContentsMargins(12, 12, 12, 12)

        seg_scroll = QScrollArea()
        seg_scroll.setWidgetResizable(True)
        seg_scroll.setWidget(self._segment_panel)
        seg_layout.addWidget(seg_scroll, 1)

        self._run_seg_btn = QPushButton("Run Segmentation")
        self._run_seg_btn.setProperty("class", "primary")
        seg_layout.addWidget(self._run_seg_btn)
        self._stack.addWidget(seg_page)

        # ── Page 3: Profiling ──────────────────────────────────────────
        prof_page = QWidget()
        prof_layout = QVBoxLayout(prof_page)
        prof_layout.setContentsMargins(12, 12, 12, 12)

        prof_scroll = QScrollArea()
        prof_scroll.setWidgetResizable(True)
        prof_scroll.setWidget(self._profile_panel)
        prof_layout.addWidget(prof_scroll, 1)

        self._run_prof_btn = QPushButton("Run Profiling")
        self._run_prof_btn.setProperty("class", "primary")
        prof_layout.addWidget(self._run_prof_btn)
        self._stack.addWidget(prof_page)

        right_layout.addWidget(self._stack, 1)

        # ── Log view (hidden by default) ───────────────────────────────
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(1000)
        self._log_view.setVisible(False)
        self._log_view.setMaximumHeight(200)
        self._log_view.setProperty("class", "log-panel")
        right_layout.addWidget(self._log_view)

        main_layout.addWidget(right_widget, 1)

        # ── QStatusBar ─────────────────────────────────────────────────
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._run_all_btn = QPushButton("Run All")
        self._run_all_btn.setProperty("class", "primary")
        self._global_progress = ProgressPanel(compact=True)
        self._show_log_btn = QPushButton("Log")
        self._show_log_btn.setCheckable(True)
        self._show_log_btn.setChecked(False)
        self._show_log_btn.setProperty("class", "secondary")
        self._load_config_btn = QPushButton("Load Config")
        self._load_config_btn.setProperty("class", "secondary")
        self._reset_all_btn = QPushButton("Reset All")
        self._reset_all_btn.setProperty("class", "secondary")
        self._log_label = QLabel("")
        self._log_label.setProperty("class", "muted")
        self._log_label.setMaximumWidth(200)

        status_bar.addWidget(self._run_all_btn)
        status_bar.addWidget(self._global_progress, 1)
        status_bar.addPermanentWidget(self._show_log_btn)
        status_bar.addPermanentWidget(self._load_config_btn)
        status_bar.addPermanentWidget(self._reset_all_btn)

        # Block scroll-wheel on unfocused spinboxes/comboboxes globally
        QApplication.instance().installEventFilter(_wheel_blocker)

    # ── Signal connections ────────────────────────────────────────────────

    def _connect_signals(self):
        self._sidebar.navigation_changed.connect(self._on_navigation_changed)
        self._input_browse.clicked.connect(self._browse_input)
        self._output_browse.clicked.connect(self._browse_output)
        self._output_dir.textChanged.connect(self._on_output_changed)
        self._load_config_btn.clicked.connect(self._load_config)
        self._reset_all_btn.clicked.connect(self._reset_all)
        self._run_all_btn.clicked.connect(self._ctrl.run_all)
        self._run_pre_btn.clicked.connect(self._ctrl.run_preprocessing)
        self._run_seg_btn.clicked.connect(self._ctrl.run_segmentation)
        self._run_prof_btn.clicked.connect(self._ctrl.run_profiling)

        self._show_log_btn.toggled.connect(self._log_view.setVisible)

        # Convert panel
        self._convert_panel._apply_btn.clicked.connect(self._ctrl.apply_convert)

        # Global cancel -> current worker
        self._global_progress.cancel_requested.connect(self._ctrl._cancel_current_worker)

        # Step panels
        for step in self._all_step_panels:
            if hasattr(step, "_pick_btn"):
                step._pick_btn.clicked.connect(lambda checked, s=step: self._ctrl.pick_random(s))
            if hasattr(step, "_preview_btn"):
                step._preview_btn.clicked.connect(lambda checked, s=step: self._ctrl.preview_step(s))
            if hasattr(step, "_fit_btn"):
                step._fit_btn.clicked.connect(self._ctrl.fit_basic)
            if hasattr(step, "_apply_btn") and step.step_name != "convert":
                step._apply_btn.clicked.connect(lambda checked, s=step: self._ctrl.apply_step(s))

        # Segment block signals
        self._segment_panel.pick_requested.connect(self._ctrl.on_segment_pick)
        self._segment_panel.preview_requested.connect(self._ctrl.on_segment_preview)

        # Sync segmentation object names to profiling mask dropdowns
        self._segment_panel.parameter_changed.connect(self._ctrl._sync_seg_masks_to_profiling)

    def _on_navigation_changed(self, page_id: str) -> None:
        index_map = {"convert": 0, "preprocess": 1, "segment": 2, "profile": 3}
        if page_id in index_map:
            self._stack.setCurrentIndex(index_map[page_id])

    # ── Logging ────────────────────────────────────────────────────────────

    def _on_log_message(self, message: str) -> None:
        self._log_view.appendPlainText(message)
        # Show last line in the compact label
        self._log_label.setText(message.split("\n")[-1])

    # ── Input / browse ──────────────────────────────────────────────────

    def _browse_input(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if path:
            self._input_dir.setText(path)
            if not self._output_manually_set:
                self._output_dir.blockSignals(True)
                self._output_dir.setText(path)
                self._output_dir.blockSignals(False)
            self._on_input_changed()

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._output_dir.setText(path)
            self._output_manually_set = True

    def _on_output_changed(self) -> None:
        self._output_manually_set = True

    @staticmethod
    def _detect_format(path: Path) -> str:
        """Auto-detect vendor format by scanning directory structure."""
        # Already converted: image/ subdirectory with unified .tiff files
        image_subdir = path / "image"
        if image_subdir.is_dir() and (
            list(image_subdir.glob("*.tiff")) or list(image_subdir.glob("*.tif"))
        ):
            # Peek inside image/ to guess original vendor (well naming differs)
            # Actually both formats look identical after conversion; default operetta
            return "operetta"
        # Operetta: Images/ subdirectory with .tiff files
        if (path / "Images").is_dir() and list((path / "Images").glob("*.tiff")):
            return "operetta"
        # MICA: single-letter row directories (A, B, C, ...)
        for d in path.iterdir():
            if d.is_dir() and len(d.name) == 1 and d.name.isalpha():
                return "mica"
        return "operetta"  # fallback default

    @staticmethod
    def _is_converted(output_path: Path) -> bool:
        """Check whether *output_path* contains converted unified image files."""
        image_subdir = output_path / "image"
        return (
            image_subdir.is_dir()
            and bool(list(image_subdir.glob("*.tiff")) or list(image_subdir.glob("*.tif")))
        )

    def _on_input_changed(self):
        path = Path(self._input_dir.text())
        output_path = self._output_path()

        # Auto-detect vendor format
        detected = self._detect_format(path)
        idx = self._format_combo.findText(detected)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)

        # Reset all step locks and checked states
        for step in self._all_step_panels:
            step.set_locked(False)
            step.setChecked(False)

        if path.exists():
            try:
                # Pass raw vendor pattern so build_metadata scopes file search
                raw_pattern = None
                if not self._is_converted(path):
                    if detected == "operetta":
                        raw_pattern = "Images/"
                    elif detected == "mica":
                        raw_pattern = "[A-P]/"
                ds = ImageDataset(path, image_subdir_pattern=raw_pattern)
                self._state.dataset = ds

                is_converted = self._is_converted(output_path)

                if is_converted:
                    # Converted dataset: enable seg + profile, populate channels
                    self._segment_panel.setChecked(True)
                    self._profile_panel.setChecked(True)
                    self._segment_panel.populate_channels(ds.intensity_colnames)
                    self._profile_panel.populate_channels(ds.intensity_colnames)
                    self._profile_panel.populate_masks(ds.mask_colnames)
                    self._ctrl._sync_seg_masks_to_profiling()
                    self._basic_panel.set_preview_channels(ds.intensity_colnames)
                    self._update_convert_info(ds)

                    # Detect completed steps from session.json or disk state
                    sf = SessionFile(path)
                    data = sf.load()
                    if data:
                        locked = data.get("steps_locked", [])
                        for step in self._all_step_panels:
                            if step.step_name in locked and step.step_name not in ("segment", "profile"):
                                step.set_locked(True)
                        # Restore enabled/checked state for unlocked steps
                        enabled = data.get("steps_enabled", {})
                        for step in self._all_step_panels:
                            if step.step_name not in locked and step.step_name in enabled:
                                step.setChecked(enabled[step.step_name])
                        logging.getLogger("microProfiler").info(
                            f"Session restored — {len(locked)} steps completed"
                        )
                        applied = data.get("steps_applied", [])
                        logging.getLogger("microProfiler").info(
                            f"steps_applied={applied}, steps_locked={locked}"
                        )
                    else:
                        disk = detect_disk_state(output_path)
                        if disk.get("convert"):
                            self._convert_panel.set_locked(True)
                            logging.getLogger("microProfiler").info(
                                "Detected converted dataset on disk"
                            )
                else:
                    # Raw unconverted dataset: only Convert is active
                    self._convert_panel.setChecked(True)
                    self._update_convert_info(ds)

            except Exception as e:
                self._convert_panel.setChecked(True)
                logging.getLogger("microProfiler").info(
                    f"Dataset not loaded: {e} — run Convert to create structured files"
                )
        self._update_tab_status()

    # ── Session restore ─────────────────────────────────────────────────

    def _restore_session(self) -> None:
        # Restore from session.json (project-local settings)
        last_dir = None
        session_root = self._output_dir.text() or self._input_dir.text()
        if session_root:
            sf = SessionFile(Path(session_root))
            data = sf.load()
            if data:
                params = data.get("params", {})
                if params:
                    settings = DictSettings(params)
                    for step in self._all_step_panels:
                        step.load_from_settings(settings)
                enabled = data.get("steps_enabled", {})
                for step in self._all_step_panels:
                    if step.step_name in enabled:
                        step.setChecked(enabled[step.step_name])
                locked = data.get("steps_locked", [])
                for step in self._all_step_panels:
                    if step.step_name in locked and step.step_name not in ("segment", "profile"):
                        step.set_locked(True)
                last_dir = data.get("general", {}).get("input_dir")
                if data.get("running"):
                    QMessageBox.warning(
                        self, "Interrupted Session",
                        "The previous session was interrupted. "
                        "Some steps may need re-running. "
                        "Check the disk state and re-run if needed.",
                    )
                logging.getLogger("microProfiler").info(
                    f"Session restored from {data.get('modified', 'unknown')}"
                )
            else:
                disk = detect_disk_state(Path(session_root))
                if disk.get("convert"):
                    self._convert_panel.set_locked(True)
                    if not disk.get("segment") and not disk.get("profile"):
                        answer = QMessageBox.question(
                            self, "Preprocessing Status",
                            "Was preprocessing (resize, BaSiC, Z-projection, tiling) "
                            "already applied to these images?",
                            QMessageBox.Yes | QMessageBox.No,
                        )
                        if answer == QMessageBox.Yes:
                            for step in self._preprocessing_steps:
                                step.set_locked(True)
                logging.getLogger("microProfiler").info(
                    "New session started - restored parameter values."
                )
        else:
            logging.getLogger("microProfiler").info(
                "New session started - restored parameter values."
            )

        if last_dir and Path(last_dir).is_dir() and not self._input_dir.text():
            self._input_dir.setText(last_dir)
            self._on_input_changed()

        self._update_tab_status()

    # ── Compact widths ──────────────────────────────────────────────────

    @staticmethod
    def _compact_widgets(widget, max_width: int = 200) -> None:
        from PySide6.QtWidgets import QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QAbstractSpinBox
        for child in widget.findChildren(QLineEdit):
            child.setMaximumWidth(max_width)
        for child in widget.findChildren(QSpinBox):
            child.setMaximumWidth(max_width)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in widget.findChildren(QDoubleSpinBox):
            child.setMaximumWidth(max_width)
            child.setButtonSymbols(QAbstractSpinBox.NoButtons)
        for child in widget.findChildren(QComboBox):
            child.setMaximumWidth(max_width)

    def _apply_compact_widths(self) -> None:
        for panel in self._all_step_panels:
            self._compact_widgets(panel)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _output_path(self) -> Path:
        txt = self._output_dir.text() or self._input_dir.text()
        return Path(txt)

    def _update_tab_status(self) -> None:
        ds = self._state.dataset
        has_ds = ds is not None and len(ds) > 0
        self._run_pre_btn.setEnabled(has_ds)
        self._run_seg_btn.setEnabled(has_ds)
        self._run_prof_btn.setEnabled(has_ds)

    # ── Convert info display ──────────────────────────────────────────────

    def _update_convert_info(self, ds) -> None:
        """Populate dataset info panel after conversion."""
        self._convert_info_label.setProperty("class", "")
        self._convert_info_label.style().polish(self._convert_info_label)
        n = len(ds)
        ch = ", ".join(ds.intensity_colnames) if ds.intensity_colnames else "—"
        shape = ds.img_shape
        dtype = ds.img_dtype
        masks = ", ".join(ds.mask_colnames) if ds.mask_colnames else "—"

        lines = [f"Image groups: {n}"]

        # Wells / Fields after Image groups, before Channels
        meta = ds.metadata
        if meta is not None and "well" in meta.columns:
            n_wells = meta["well"].nunique()
            lines.append(f"Wells: {n_wells}")
        if meta is not None and "field" in meta.columns:
            n_fields = meta["field"].nunique()
            lines.append(f"Fields: {n_fields}")

        lines.append(f"Channels: {ch}")
        if shape:
            lines.append(f"Dimensions: {shape[0]}×{shape[1]}")
        if dtype is not None:
            lines.append(f"Data type: {dtype}")
        if ds.mask_colnames:
            lines.append("")  # blank separator before masks
            lines.append(f"Masks: {masks}")

        self._convert_info_label.setText("\n".join(lines))

    def _clear_convert_info(self) -> None:
        """Reset dataset info panel to placeholder."""
        self._convert_info_label.setText("Run conversion to see dataset information.")
        self._convert_info_label.setProperty("class", "placeholder")
        self._convert_info_label.style().polish(self._convert_info_label)

    # ── Config load / reset ─────────────────────────────────────────────

    def _load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Config", "", "Config files (*.yml *.yaml *.json)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                cfg = yaml.safe_load(f)
        except Exception as e:
            QMessageBox.warning(self, "Load Failed", f"Could not load config:\n{e}")
            return
        params = cfg.get("params", {})
        settings = DictSettings(params)
        for step in self._all_step_panels:
            step.load_from_settings(settings)

        # Populate mask dropdowns from segmentation settings + dataset,
        # then re-apply saved mask names (load_from_settings ran before
        # dropdowns had items, so findText would have returned -1).
        self._ctrl._sync_seg_masks_to_profiling()
        profile_params = params.get("profile", {})
        if hasattr(self._profile_panel, "_blocks"):
            for i, block in enumerate(self._profile_panel._blocks):
                name = profile_params.get(f"block_{i}_object_mask_name")
                if name:
                    idx = block._object_mask.findText(str(name))
                    if idx >= 0:
                        block._object_mask.setCurrentIndex(idx)
                    else:
                        block._object_mask.setCurrentText(str(name))
                parent = profile_params.get(f"block_{i}_parent_mask_name")
                if parent:
                    idx = block._parent_mask.findText(str(parent))
                    if idx >= 0:
                        block._parent_mask.setCurrentIndex(idx)
                    else:
                        block._parent_mask.setCurrentText(str(parent))
        logging.getLogger("microProfiler").info(f"Config loaded from {path}")

    def _reset_all(self) -> None:
        for step in self._all_step_panels:
            step.set_locked(False)
            step.setChecked(False)
        self._state.dataset = None
        self._state.random_row_idx = None
        self._input_dir.clear()
        self._output_dir.clear()
        self._output_manually_set = False
        self._clear_convert_info()
        self._update_tab_status()
        logging.getLogger("microProfiler").info("Pipeline reset complete.")

    def _set_running(self, running: bool) -> None:
        self._running = running
        self._input_browse.setEnabled(not running)
        self._output_browse.setEnabled(not running)
        for step in self._all_step_panels:
            step.setEnabled(not running)

    def closeEvent(self, event):
        for w in (getattr(self, "_worker", None), getattr(self, "_preview_worker", None)):
            if w is not None and hasattr(w, "_thread") and w._thread.isRunning():
                w._thread.quit()
                w._thread.wait(3000)
        root = self._output_dir.text() or self._input_dir.text()
        if root:
            sf = SessionFile(Path(root))
            data = sf.load()
            if data:
                sf.set_running(False)
        if self._input_dir.text():
            root = self._output_dir.text() or self._input_dir.text()
            if root:
                SessionFile(Path(root)).save_input_dir(self._input_dir.text())
        super().closeEvent(event)

