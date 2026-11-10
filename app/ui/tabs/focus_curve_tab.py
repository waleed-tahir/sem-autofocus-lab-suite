"""Tab 3: Focus Curve & Coarse-to-Fine Gradient Ascent Workspace.

Fluent Desktop Edition:
- 100% Native Windows Fluent Design (Light Theme)
- Top Metric KPI Cards (Algorithm State, Captures Used, Local Gradient, Best Peak Found)
- Clean, uncluttered Focus Curve and Coarse-to-Fine Gradient Trajectory Plot
- Smooth reference curve always drawn underneath
- Fluent Playback Controls (Auto-Run, Prev, Step +1, Show Full Run, Reset, Speed Selector)
- Interactive Live Parameter Sliders (Initial Start Z_0, Initial Probe Step ΔZ_probe, Coarse Step Size ΔZ, Refinement Decay α, Adaptive Step)
- Step-by-Step Gradient Execution Telemetry Log with soft pastel phase badges
- Synchronized inspection on table row click or canvas click
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import (
    ALGORITHMS,
    DEFAULT_ALGORITHM_KEY,
    RunContext,
    algorithm_keys,
    require as require_algo,
    run_algorithm,
)
from app.core.evaluator import Evaluator
from app.core.experiment import GroundTruth, GroundTruthJob
from app.core.focus_measures import FOCUS_MEASURES, require as require_measure
from app.core.run_result import RunResult
from app.plots.focus_curve import draw_focus_curve
from app.ui.app_state import AppState
from app.ui.icons import get_fluent_icon
from app.ui.job_service import JobService
from app.ui.tabs.common import (
    refresh_algorithm_combo,
    refresh_dataset_combo,
)
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)


class FocusCurveTab(QWidget):
    """Complete Coarse-to-Fine Gradient Ascent and Focus Curve Analysis Tab in Fluent UI."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._jobs = jobs

        # Top Bar Selectors
        self._dataset_combo = QComboBox()
        self._measure_combo = QComboBox()
        self._algorithm_combo = QComboBox()
        self._show_global_cb = QCheckBox("Show Reference Curve")
        self._show_global_cb.setChecked(True)
        self._show_fit_cb = QCheckBox("Show Quadratic Fit")
        self._show_fit_cb.setChecked(True)
        self._compute_btn = QPushButton("Compute Reference Curve")
        self._compute_btn.setObjectName("primaryButton")
        self._compute_btn.setProperty("accent", True)

        # Plot Canvas
        self._curve_canvas = PlotCanvas("focus_curve")
        self._curve_canvas.set_draw_callback(self._draw_curve)

        # Replay Animation State
        self._replay_timer = QTimer(self)
        self._replay_timer.setInterval(480)  # Default: Normal 480ms
        self._replay_timer.timeout.connect(self._on_replay_tick)
        self._replay_step: Optional[int] = None
        self._is_playing: bool = False
        self._cached_run_result: Optional[RunResult] = None

        self._build_ui()
        self._connect_signals()
        self.refresh()

    # ------------------------------------------------------------------ UI Layout (Fluent)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Top Controls Bar
        main_layout.addWidget(self._build_top_bar())

        # Splitter between Plot+Controls (Top) and Telemetry Log (Bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # 2. KPI HUD Metric Cards (Fluent Light Mode)
        top_layout.addWidget(self._build_kpi_cards())

        # 3. Focus Curve Plot Canvas
        top_layout.addWidget(self._curve_canvas, stretch=1)

        # 4. Playback and Parameter Sliders Bar
        top_layout.addWidget(self._build_playback_and_param_bar())

        splitter.addWidget(top_container)

        # 5. Bottom Telemetry Log Panel
        splitter.addWidget(self._build_telemetry_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, stretch=1)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setStyleSheet(
            "QFrame#topBar { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; } "
            "QFrame#topBar QLabel { border: none; background: transparent; }"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        lbl_ds = QLabel("Target Image Set:")
        lbl_ds.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 11.5px; color: #424242;")
        layout.addWidget(lbl_ds)
        self._dataset_combo.setMinimumWidth(180)
        layout.addWidget(self._dataset_combo)

        lbl_meas = QLabel("Focus Measure:")
        lbl_meas.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 11.5px; color: #424242;")
        layout.addWidget(lbl_meas)
        self._measure_combo.setMinimumWidth(190)
        layout.addWidget(self._measure_combo)

        lbl_algo = QLabel("Search Algorithm:")
        lbl_algo.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 11.5px; color: #424242;")
        layout.addWidget(lbl_algo)
        self._algorithm_combo.setMinimumWidth(190)
        layout.addWidget(self._algorithm_combo)

        layout.addSpacing(10)
        layout.addWidget(self._show_global_cb)
        layout.addSpacing(10)
        layout.addWidget(self._show_fit_cb)
        layout.addStretch()
        layout.addWidget(self._compute_btn)
        return bar

    def _build_kpi_cards(self) -> QWidget:
        container = QFrame()
        container.setObjectName("kpiContainer")
        container.setStyleSheet(
            "QFrame#kpiContainer { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; } "
            "QFrame#kpiContainer QLabel { border: none; background: transparent; }"
        )
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        def _make_card(title: str):
            card = QFrame()
            card.setObjectName("kpiCard")
            card.setStyleSheet(
                "QFrame#kpiCard { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; } "
                "QFrame#kpiCard QLabel { border: none; background: transparent; outline: none; }"
            )
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(10, 6, 10, 6)
            c_lay.setSpacing(2)
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet("border: none; background: transparent; font-size: 10px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet("border: none; background: transparent; font-size: 15px; font-weight: 700; color: #0f172a;")
            lbl_sub = QLabel("—")
            lbl_sub.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            c_lay.addWidget(lbl_title)
            c_lay.addWidget(lbl_val)
            c_lay.addWidget(lbl_sub)
            return card, lbl_val, lbl_sub

        self._card_state, self._val_state, self._sub_state = _make_card("ALGORITHM STATE")
        self._card_scans, self._val_scans, self._sub_scans = _make_card("SEM CAPTURES USED")
        self._card_grad, self._val_grad, self._sub_grad = _make_card("LOCAL GRADIENT D(NV)/DZ")
        self._card_peak, self._val_peak, self._sub_peak = _make_card("BEST PEAK FOUND (Z*)")

        layout.addWidget(self._card_state, stretch=1)
        layout.addWidget(self._card_scans, stretch=1)
        layout.addWidget(self._card_grad, stretch=1)
        layout.addWidget(self._card_peak, stretch=1)
        return container

    def _build_playback_and_param_bar(self) -> QWidget:
        container = QFrame()
        container.setObjectName("playbackBar")
        container.setStyleSheet(
            "QFrame#playbackBar { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; } "
            "QFrame#playbackBar QLabel { border: none; background: transparent; }"
        )
        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(10, 8, 10, 8)
        main_lay.setSpacing(8)

        # Row 1: Playback Buttons
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._btn_play = QPushButton("Auto-Run Focus")
        self._btn_play.setIcon(get_fluent_icon("play.png"))
        self._btn_play.setObjectName("primaryButton")
        self._btn_play.setProperty("accent", True)
        self._btn_play.setFixedHeight(28)

        self._btn_prev = QPushButton("◀ Prev")
        self._btn_prev.setFixedHeight(28)

        self._btn_step = QPushButton("Step +1 Capture ▶")
        self._btn_step.setFixedHeight(28)

        self._btn_full = QPushButton("Show Full Run ⏭")
        self._btn_full.setFixedHeight(28)

        self._btn_reset = QPushButton("↺ Reset")
        self._btn_reset.setFixedHeight(28)

        self._lbl_step_counter = QLabel("Step: — / —")
        self._lbl_step_counter.setStyleSheet("color: #0067c0; font-weight: 700; font-size: 11.5px; padding: 0 8px;")

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["Speed: Fast (150ms)", "Speed: Normal (480ms)", "Speed: Slow (800ms)"])
        self._speed_combo.setCurrentIndex(1)
        self._speed_combo.setFixedHeight(28)

        row1.addWidget(self._btn_play)
        row1.addWidget(self._btn_prev)
        row1.addWidget(self._btn_step)
        row1.addWidget(self._btn_full)
        row1.addWidget(self._btn_reset)
        row1.addSpacing(10)
        row1.addWidget(self._lbl_step_counter)
        row1.addStretch()
        row1.addWidget(self._speed_combo)
        main_lay.addLayout(row1)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #f0f0f0; background: #f0f0f0; max-height: 1px;")
        main_lay.addWidget(line)

        # Row 2: Live Parameter Sliders (Fluent Style)
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        # 1. Z0 Slider
        z0_box = QVBoxLayout()
        z0_box.setSpacing(2)
        self._lbl_z0_title = QLabel("Initial Start Plane (Z_0):  Z = 12")
        self._lbl_z0_title.setStyleSheet("font-size: 10.5px; color: #475569; font-weight: 600;")
        self._slider_z0 = QSlider(Qt.Orientation.Horizontal)
        self._slider_z0.setRange(0, 198)
        self._slider_z0.setValue(12)
        z0_box.addWidget(self._lbl_z0_title)
        z0_box.addWidget(self._slider_z0)

        # 2. Probe Step Slider
        probe_box = QVBoxLayout()
        probe_box.setSpacing(2)
        self._lbl_probe_title = QLabel("Initial Probe Step (ΔZ_probe):  2 planes")
        self._lbl_probe_title.setStyleSheet("font-size: 10.5px; color: #475569; font-weight: 600;")
        self._slider_probe = QSlider(Qt.Orientation.Horizontal)
        self._slider_probe.setRange(1, 20)
        self._slider_probe.setValue(2)
        probe_box.addWidget(self._lbl_probe_title)
        probe_box.addWidget(self._slider_probe)

        # 3. Coarse Step Slider
        step_box = QVBoxLayout()
        step_box.setSpacing(2)
        self._lbl_step_title = QLabel("Coarse Step Size (ΔZ_coarse):  14 planes")
        self._lbl_step_title.setStyleSheet("font-size: 10.5px; color: #475569; font-weight: 600;")
        self._slider_step = QSlider(Qt.Orientation.Horizontal)
        self._slider_step.setRange(4, 30)
        self._slider_step.setValue(14)
        step_box.addWidget(self._lbl_step_title)
        step_box.addWidget(self._slider_step)

        # 4. Decay Slider
        decay_box = QVBoxLayout()
        decay_box.setSpacing(2)
        self._lbl_decay_title = QLabel("Refinement Decay (α_decay):  0.50×")
        self._lbl_decay_title.setStyleSheet("font-size: 10.5px; color: #475569; font-weight: 600;")
        self._slider_decay = QSlider(Qt.Orientation.Horizontal)
        self._slider_decay.setRange(10, 90)
        self._slider_decay.setValue(50)
        decay_box.addWidget(self._lbl_decay_title)
        decay_box.addWidget(self._slider_decay)

        # 5. Adaptive Checkbox
        adapt_box = QVBoxLayout()
        adapt_box.setSpacing(2)
        self._cb_adaptive = QCheckBox("Adaptive Gradient Step")
        self._cb_adaptive.setStyleSheet("font-weight: 600; font-size: 11px; color: #1e293b;")
        lbl_adapt_desc = QLabel("Scales coarse step dynamically by local slope |d(NV)/dZ|")
        lbl_adapt_desc.setStyleSheet("font-size: 9.5px; color: #64748b;")
        adapt_box.addWidget(self._cb_adaptive)
        adapt_box.addWidget(lbl_adapt_desc)

        row2.addLayout(z0_box, stretch=2)
        row2.addLayout(probe_box, stretch=2)
        row2.addLayout(step_box, stretch=2)
        row2.addLayout(decay_box, stretch=2)
        row2.addLayout(adapt_box, stretch=3)
        main_lay.addLayout(row2)

        return container

    def _build_telemetry_panel(self) -> QWidget:
        container = QFrame()
        container.setObjectName("telemetryContainer")
        container.setStyleSheet(
            "QFrame#telemetryContainer { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; } "
            "QFrame#telemetryContainer QLabel { border: none; background: transparent; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header bar
        header_bar = QHBoxLayout()
        lbl_title = QLabel("STEP-BY-STEP GRADIENT EXECUTION TELEMETRY LOG")
        lbl_title.setStyleSheet("font-weight: 700; font-size: 11.5px; color: #1e293b; letter-spacing: 0.3px;")
        lbl_sub = QLabel("(Click any row to inspect that capture)")
        lbl_sub.setStyleSheet("font-size: 10.5px; color: #64748b; margin-left: 6px;")
        self._lbl_telemetry_peak = QLabel("Final Peak: —")
        self._lbl_telemetry_peak.setStyleSheet("font-weight: 700; font-size: 11.5px; color: #047857;")

        header_bar.addWidget(lbl_title)
        header_bar.addWidget(lbl_sub)
        header_bar.addStretch()
        header_bar.addWidget(self._lbl_telemetry_peak)
        layout.addLayout(header_bar)

        # Telemetry Table with native Fluent styling
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "CAPTURE #", "ALGORITHM PHASE", "PLANE Z", "STEP ΔZ",
            "MEAN (M)", "NORM. VAR (NV)", "GRADIENT D(NV)/DZ", "CONTROLLER DECISION"
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)

        # Clean column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 85)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 130)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(2, 85)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(3, 85)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(4, 90)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 115)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 125)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)
        return container

    # ------------------------------------------------------------------ Signal Wiring

    def _connect_signals(self) -> None:
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_or_param_changed)
        self._measure_combo.currentIndexChanged.connect(self._on_measure_changed)
        self._algorithm_combo.currentIndexChanged.connect(self._on_algo_changed)
        self._show_global_cb.toggled.connect(self._redraw)
        self._show_fit_cb.toggled.connect(self._on_show_fit_toggled)
        self._compute_btn.clicked.connect(self._on_compute_reference)

        # Playback controls
        self._btn_play.clicked.connect(self._toggle_play)
        self._btn_prev.clicked.connect(self._step_prev)
        self._btn_step.clicked.connect(self._step_next)
        self._btn_full.clicked.connect(self._show_full_run)
        self._btn_reset.clicked.connect(self._reset_run)
        self._speed_combo.currentIndexChanged.connect(self._on_speed_changed)

        # Live sliders
        self._slider_z0.valueChanged.connect(self._on_slider_z0_changed)
        self._slider_probe.valueChanged.connect(self._on_slider_probe_changed)
        self._slider_step.valueChanged.connect(self._on_slider_step_changed)
        self._slider_decay.valueChanged.connect(self._on_slider_decay_changed)
        self._cb_adaptive.toggled.connect(self._on_adaptive_toggled)

        # Table click synchronization
        self._table.cellClicked.connect(self._on_table_row_clicked)

        # State notifications
        self._state.datasets_changed.connect(self.refresh)
        self._state.ground_truth_changed.connect(lambda *_: self._redraw())
        self._state.results_changed.connect(self._on_external_runs_changed)

    # ------------------------------------------------------------------ Data & Refresh

    def refresh(self) -> None:
        """Refresh dataset and algorithm combos."""
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._refresh_measure_combo()
        refresh_algorithm_combo(self._algorithm_combo, algorithm_keys())
        
        # Default algorithm to Gradient Search in Focus Curve tab for immediate inspection
        grad_idx = self._algorithm_combo.findData("gradient")
        if grad_idx >= 0 and self._algorithm_combo.currentIndex() != grad_idx:
            self._algorithm_combo.blockSignals(True)
            self._algorithm_combo.setCurrentIndex(grad_idx)
            self._algorithm_combo.blockSignals(False)

        self._recalculate_current_run()

    def _refresh_measure_combo(self) -> None:
        curr = self._measure_combo.currentData()
        self._measure_combo.blockSignals(True)
        self._measure_combo.clear()
        for spec in FOCUS_MEASURES.values():
            self._measure_combo.addItem(spec.display_name, spec.key)
        if curr:
            idx = self._measure_combo.findData(curr)
            if idx >= 0:
                self._measure_combo.setCurrentIndex(idx)
        self._measure_combo.blockSignals(False)

    @Slot()
    def _on_dataset_or_param_changed(self) -> None:
        key = self._dataset_combo.currentData()
        ds = self._state.dataset(str(key)) if key else None
        if ds:
            self._slider_z0.setRange(0, ds.max_idx)
            if self._slider_z0.value() > ds.max_idx:
                self._slider_z0.setValue(min(12, ds.max_idx))
            max_probe = max(1, min(20, ds.max_idx // 2))
            self._slider_probe.setMaximum(max_probe)
            if self._slider_probe.value() > max_probe:
                self._slider_probe.setValue(min(2, max_probe))
        self._recalculate_current_run()

    @Slot()
    def _on_measure_changed(self) -> None:
        self._recalculate_current_run()

    @Slot()
    def _on_algo_changed(self) -> None:
        self._recalculate_current_run()

    @Slot(int)
    def _on_slider_z0_changed(self, val: int) -> None:
        self._lbl_z0_title.setText(f"Initial Start Plane (Z_0):  Z = {val}")
        self._recalculate_current_run()

    @Slot(int)
    def _on_slider_probe_changed(self, val: int) -> None:
        unit = "plane" if val == 1 else "planes"
        self._lbl_probe_title.setText(f"Initial Probe Step (ΔZ_probe):  {val} {unit}")
        self._recalculate_current_run()

    @Slot(int)
    def _on_slider_step_changed(self, val: int) -> None:
        self._lbl_step_title.setText(f"Coarse Step Size (ΔZ_coarse):  {val} planes")
        self._recalculate_current_run()

    @Slot(int)
    def _on_slider_decay_changed(self, val: int) -> None:
        factor = val / 100.0
        self._lbl_decay_title.setText(f"Refinement Decay (α_decay):  {factor:.2f}×")
        self._recalculate_current_run()

    @Slot(bool)
    def _on_adaptive_toggled(self, checked: bool) -> None:
        self._recalculate_current_run()

    @Slot(int)
    def _on_speed_changed(self, idx: int) -> None:
        intervals = [150, 480, 800]
        self._replay_timer.setInterval(intervals[min(idx, len(intervals) - 1)])

    @Slot()
    def _on_external_runs_changed(self) -> None:
        self._recalculate_current_run()

    # ------------------------------------------------------------------ Execution & Recalculation

    def _recalculate_current_run(self) -> None:
        """Run or fetch algorithm execution in real time and populate UI."""
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        algo_key = self._algorithm_combo.currentData() or "gradient"
        meas_key = self._measure_combo.currentData() or "normalized_variance"

        if dataset is None:
            self._cached_run_result = None
            self._populate_telemetry([])
            self._update_kpi_cards(None)
            self._curve_canvas.redraw()
            return

        # Ensure ground truth is present so the underlying focus curve is ALWAYS smooth and visible
        truth = self._state.ground_truth_for(str(key), str(meas_key))
        if truth is None and not self._jobs.is_busy:
            # Generate quick reference ground truth
            self._jobs.submit(
                GroundTruthJob([dataset], str(meas_key)),
                lambda _: self._redraw(),
            )

        # Check if algorithm is gradient: execute live with current slider settings
        if algo_key in ("gradient", "gradient_modified"):
            z0 = self._slider_z0.value()
            probe_step = self._slider_probe.value()
            coarse_step = self._slider_step.value()
            decay = self._slider_decay.value() / 100.0
            adaptive = self._cb_adaptive.isChecked()

            meas = require_measure(str(meas_key))
            ev = Evaluator(dataset, meas)
            algo_spec = require_algo(str(algo_key))
            params = {
                "start_idx": z0,
                "probe_step": probe_step,
                "coarse_step": coarse_step,
                "decay": decay,
                "adaptive": adaptive,
                "stride": 1,
            }
            ctx = RunContext(
                dataset=dataset,
                evaluator=ev,
                measure=meas,
                wd_mm=dataset.working_distances(),
                params=params,
                apply_fit=True,
            )
            self._cached_run_result = run_algorithm(algo_spec, ctx)
        else:
            # Global scan
            runs = self._state.results_for_dataset(str(key))
            matched = [r for r in runs if r.algorithm_key == algo_key and r.measure_key == meas_key]
            if matched:
                self._cached_run_result = matched[-1]
            else:
                meas = require_measure(str(meas_key))
                ev = Evaluator(dataset, meas)
                algo_spec = require_algo(str(algo_key))
                ctx = RunContext(
                    dataset=dataset,
                    evaluator=ev,
                    measure=meas,
                    wd_mm=dataset.working_distances(),
                    params=algo_spec.defaults(),
                    apply_fit=True,
                )
                self._cached_run_result = run_algorithm(algo_spec, ctx)

        history = self._cached_run_result.extra.get("history", [])
        total_steps = len(history) if history else len(self._cached_run_result.visited)
        
        # Default replay step is full completion unless actively playing
        if not self._is_playing:
            self._replay_step = total_steps
        
        self._populate_telemetry(history)
        self._update_kpi_cards(self._cached_run_result)
        self._update_step_label(total_steps)
        self._curve_canvas.redraw()

    # ------------------------------------------------------------------ Telemetry & KPI Cards

    def _update_kpi_cards(self, result: Optional[RunResult]) -> None:
        truth = self._current_truth()
        if not result:
            self._val_state.setText("NO DATA")
            self._sub_state.setText("Select dataset to begin")
            self._val_scans.setText("—")
            self._sub_scans.setText("—")
            self._val_grad.setText("—")
            self._sub_grad.setText("—")
            self._val_peak.setText("—")
            self._sub_peak.setText("—")
            return

        history = result.extra.get("history", [])
        step_idx = (self._replay_step or len(history)) - 1
        active_rec = history[step_idx] if (history and 0 <= step_idx < len(history)) else None

        # 1. Algorithm State Card
        show_fit = self._show_fit_cb.isChecked()
        if active_rec:
            phase = active_rec.get("phase", "IN PROGRESS")
            if phase == "CONVERGED":
                if show_fit and result.fit_ok and not math.isnan(result.fine_idx):
                    self._val_state.setText("● Converged + Fine Refined")
                    self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #047857;")
                    self._sub_state.setText(f"Stage locked: Coarse Z_c={result.coarse_idx} | Fine Z*={result.fine_idx:.2f}")
                    self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
                else:
                    self._val_state.setText("● Converged (Focus Locked)")
                    self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #047857;")
                    self._sub_state.setText(f"Stage locked onto optimal focal plane Z={result.coarse_idx}")
                    self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            elif phase == "OVERSHOOT":
                self._val_state.setText("● Overshoot (Reverse & Bracket)")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #dc2626;")
                self._sub_state.setText("Score dropped -> Decaying step size")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            elif phase in ("BRACKET", "FINE"):
                self._val_state.setText("● Peak Bracketing")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #d97706;")
                self._sub_state.setText("Bracketing discrete coarse peak")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            elif phase in ("CLIMB", "COARSE"):
                self._val_state.setText("● Gradient Climb")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #0067c0;")
                self._sub_state.setText("Climbing along ascending gradient")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            elif phase in ("PROBE", "COARSE_PROBE"):
                self._val_state.setText("● Slope Probe")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #0284c7;")
                self._sub_state.setText("Probing initial slope direction")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            elif phase == "ESCAPE_PROBE":
                self._val_state.setText("● Escape Probe")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #9333ea;")
                self._sub_state.setText("Stochastic exploration past local trap")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            else:
                self._val_state.setText(f"● {phase.replace('_', ' ').title()}")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #0067c0;")
                self._sub_state.setText("Climbing along ascending gradient")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
        else:
            if show_fit and result.fit_ok and not math.isnan(result.fine_idx):
                self._val_state.setText("● Fine Refined (Quadratic Fit)")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #047857;")
                self._sub_state.setText(f"Sub-frame optimal vertex Z*={result.fine_idx:.2f}")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
            else:
                self._val_state.setText("● Complete")
                self._val_state.setStyleSheet("border: none; background: transparent; font-size: 14px; font-weight: 700; color: #047857;")
                self._sub_state.setText(f"Optimal peak Z={result.coarse_idx}")
                self._sub_state.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")

        # 2. SEM Captures Used Card
        total_global = truth.curve.size if truth else 199
        captures_used = active_rec.get("step", result.frames_evaluated) if active_rec else result.frames_evaluated
        pct_saved = max(0.0, (1.0 - (captures_used / float(total_global))) * 100.0) if total_global > 0 else 0.0
        speedup = (total_global / float(captures_used)) if captures_used > 0 else 1.0
        self._val_scans.setText(f"{captures_used} / {total_global} frames")
        self._val_scans.setStyleSheet("border: none; background: transparent; font-size: 15px; font-weight: 700; color: #0f172a;")
        self._sub_scans.setText(f"{pct_saved:.1f}% frames saved ({speedup:.1f}× faster)")
        self._sub_scans.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #047857; font-weight: 600;")

        # 3. Local Gradient Card
        if active_rec and abs(float(active_rec.get("gradient", 0.0))) > 1e-6:
            grad = float(active_rec["gradient"])
            dz = active_rec.get("step_dz", 0)
            color = "#047857" if grad >= 0 else "#dc2626"
            self._val_grad.setText(f"{grad:+.4f}")
            self._val_grad.setStyleSheet(f"border: none; background: transparent; font-size: 15px; font-weight: 700; color: {color};")
            self._sub_grad.setText(f"Step ΔZ = {dz:+d} planes")
            self._sub_grad.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")
        else:
            self._val_grad.setText("0.0000")
            self._val_grad.setStyleSheet("border: none; background: transparent; font-size: 15px; font-weight: 700; color: #64748b;")
            self._sub_grad.setText("Step ΔZ = 0 planes")
            self._sub_grad.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #64748b;")

        # 4. Best Peak Found Card
        true_max = truth.peak_idx if truth else result.coarse_idx
        dz_err = abs(result.coarse_idx - true_max)
        if show_fit and result.fit_ok and not math.isnan(result.fine_idx):
            self._val_peak.setText(f"Z_c={result.coarse_idx} | Z*={result.fine_idx:.2f}")
            self._val_peak.setStyleSheet("border: none; background: transparent; font-size: 13.5px; font-weight: 700; color: #0067c0;")
            self._sub_peak.setText(f"Fine WD = {result.fine_wd_mm:.4f} mm (R²={result.fit_r2:.3f})")
            self._sub_peak.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #047857; font-weight: 600;")
        else:
            self._val_peak.setText(f"Z_c = {result.coarse_idx} (True Max: {true_max})")
            self._val_peak.setStyleSheet("border: none; background: transparent; font-size: 15px; font-weight: 700; color: #0067c0;")
            if dz_err == 0:
                self._sub_peak.setText("Exact Global Peak Locked (ΔZ = 0)")
                self._sub_peak.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #047857; font-weight: 600;")
            else:
                self._sub_peak.setText(f"Focal Error: ΔZ = {dz_err} planes")
                self._sub_peak.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #dc2626; font-weight: 600;")

    def _populate_telemetry(self, history: List[Dict[str, Any]]) -> None:
        result = self._cached_run_result
        show_fit = self._show_fit_cb.isChecked()
        has_fit = result is not None and result.fit_ok and result.fit_coeffs is not None and show_fit
        extra_rows = 1 if has_fit else 0
        total_rows = len(history) + extra_rows

        self._table.blockSignals(True)
        self._table.setRowCount(total_rows)

        if not history:
            self._table.blockSignals(False)
            self._lbl_telemetry_peak.setText("Final Peak: —")
            return

        final_peak = history[-1].get("z", history[-1].get("idx", 0))
        unique_captures = len({h.get("z", h.get("idx", 0)) for h in history})
        peak_str = f"Final Peak: Z_c = {final_peak}"
        if has_fit:
            peak_str += f" | Fine Z* = {result.fine_idx:.2f}"
        self._lbl_telemetry_peak.setText(f"{peak_str} ({unique_captures} unique captures)")

        # Soft, clean Fluent pastel badges
        badge_styles = {
            "INIT": ("background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "PROBE": ("background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "COARSE_PROBE": ("background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "CLIMB": ("background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "COARSE": ("background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "OVERSHOOT": ("background: #fff1f2; color: #e11d48; border: 1px solid #fecdd3; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "BRACKET": ("background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "FINE": ("background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "ESCAPE_PROBE": ("background: #fdf4ff; color: #9333ea; border: 1px solid #f0abfc; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "CONVERGED": ("background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 10.5px;"),
            "QUADRATIC_FIT": ("background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 4px; padding: 2px 6px; font-weight: 700; font-size: 10.5px;"),
        }

        for row, rec in enumerate(history):
            # 0. Capture #
            it0 = QTableWidgetItem(f"#{rec.get('step', row + 1)}")
            it0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it0.setForeground(QColor("#475569"))
            self._table.setItem(row, 0, it0)

            # 1. Phase badge
            phase = rec.get("phase", "COARSE")
            lbl_badge = QLabel(f" {phase} ")
            lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_badge.setStyleSheet(badge_styles.get(phase, badge_styles["COARSE"]))
            badge_container = QWidget()
            b_lay = QHBoxLayout(badge_container)
            b_lay.setContentsMargins(4, 2, 4, 2)
            b_lay.addWidget(lbl_badge)
            self._table.setCellWidget(row, 1, badge_container)

            # 2. Plane Z
            plane_z = rec.get("z", rec.get("idx", 0))
            it2 = QTableWidgetItem(f"Z = {plane_z}")
            it2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it2.setForeground(QColor("#0f172a"))
            font2 = it2.font()
            font2.setBold(True)
            it2.setFont(font2)
            self._table.setItem(row, 2, it2)

            # 3. Step ΔZ
            dz = rec.get("step_dz", 0)
            dz_str = f"{dz:+d}" if row > 0 else "—"
            it3 = QTableWidgetItem(dz_str)
            it3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it3.setForeground(QColor("#64748b"))
            self._table.setItem(row, 3, it3)

            # 4. Mean (M)
            mean_val = rec.get("mean", 108.85)
            it4 = QTableWidgetItem(f"{mean_val:.2f}")
            it4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it4.setForeground(QColor("#334155"))
            self._table.setItem(row, 4, it4)

            # 5. Norm. Var (NV)
            score_val = rec.get("score", 0.0)
            it5 = QTableWidgetItem(f"{score_val:.4f}")
            it5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it5.setForeground(QColor("#047857"))
            font5 = it5.font()
            font5.setBold(True)
            it5.setFont(font5)
            self._table.setItem(row, 5, it5)

            # 6. Gradient d(NV)/dZ
            grad = rec.get("gradient", 0.0)
            grad_str = f"{grad:+.4f}" if row > 0 else "—"
            it6 = QTableWidgetItem(grad_str)
            it6.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if row > 0:
                it6.setForeground(QColor("#047857" if grad >= 0 else "#dc2626"))
            else:
                it6.setForeground(QColor("#94a3b8"))
            self._table.setItem(row, 6, it6)

            # 7. Decision
            it7 = QTableWidgetItem(str(rec.get("decision", "")))
            it7.setForeground(QColor("#1e293b"))
            self._table.setItem(row, 7, it7)

        # Optional Concluding Quadratic Fit Row
        if has_fit and result is not None:
            fit_row = len(history)
            it0 = QTableWidgetItem("FIT")
            it0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it0.setForeground(QColor("#047857"))
            font0 = it0.font()
            font0.setBold(True)
            it0.setFont(font0)
            self._table.setItem(fit_row, 0, it0)

            lbl_badge = QLabel(" QUADRATIC_FIT ")
            lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_badge.setStyleSheet(badge_styles["QUADRATIC_FIT"])
            bc = QWidget()
            bl = QHBoxLayout(bc)
            bl.setContentsMargins(4, 2, 4, 2)
            bl.addWidget(lbl_badge)
            self._table.setCellWidget(fit_row, 1, bc)

            it2 = QTableWidgetItem(f"Z* = {result.fine_idx:.3f}")
            it2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it2.setForeground(QColor("#059669"))
            font2 = it2.font()
            font2.setBold(True)
            it2.setFont(font2)
            self._table.setItem(fit_row, 2, it2)

            it3 = QTableWidgetItem("Sub-frame")
            it3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it3.setForeground(QColor("#64748b"))
            self._table.setItem(fit_row, 3, it3)

            it4 = QTableWidgetItem("—")
            it4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it4.setForeground(QColor("#94a3b8"))
            self._table.setItem(fit_row, 4, it4)

            it5 = QTableWidgetItem(f"{result.fine_value:.4f}")
            it5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it5.setForeground(QColor("#047857"))
            font5 = it5.font()
            font5.setBold(True)
            it5.setFont(font5)
            self._table.setItem(fit_row, 5, it5)

            it6 = QTableWidgetItem("0.0000 (Vertex)")
            it6.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it6.setForeground(QColor("#059669"))
            self._table.setItem(fit_row, 6, it6)

            it7 = QTableWidgetItem(f"Parabolic vertex Z*={result.fine_idx:.3f} (WD={result.fine_wd_mm:.5f} mm, R²={result.fit_r2:.4f})")
            it7.setForeground(QColor("#065f46"))
            font7 = it7.font()
            font7.setBold(True)
            it7.setFont(font7)
            self._table.setItem(fit_row, 7, it7)

        self._table.blockSignals(False)

    # ------------------------------------------------------------------ Playback Controls

    @Slot()
    def _toggle_play(self) -> None:
        if not self._cached_run_result:
            return
        history = self._cached_run_result.extra.get("history", [])
        total = len(history) or len(self._cached_run_result.visited)
        if total <= 0:
            return

        if self._is_playing:
            self._stop_animation()
        else:
            if self._replay_step is None or self._replay_step >= total:
                self._replay_step = 1

            self._is_playing = True
            self._btn_play.setText("Pause")
            self._btn_play.setIcon(get_fluent_icon("pause.png"))
            self._btn_play.setStyleSheet("background-color: #dc2626; color: #ffffff; border: 1px solid #b91c1c;")
            self._replay_timer.start()
            self._sync_active_step()

    def _stop_animation(self) -> None:
        self._is_playing = False
        self._replay_timer.stop()
        self._btn_play.setText("Auto-Run Focus")
        self._btn_play.setIcon(get_fluent_icon("play.png"))
        self._btn_play.setStyleSheet("")  # Reset to standard primaryButton QSS

    @Slot()
    def _on_replay_tick(self) -> None:
        if not self._cached_run_result:
            self._stop_animation()
            return
        history = self._cached_run_result.extra.get("history", [])
        total = len(history) or len(self._cached_run_result.visited)
        curr = (self._replay_step or 1) + 1
        if curr > total:
            self._stop_animation()
            self._replay_step = total
        else:
            self._replay_step = curr
        self._sync_active_step()

    @Slot()
    def _step_prev(self) -> None:
        self._stop_animation()
        if not self._cached_run_result:
            return
        curr = (self._replay_step or 1) - 1
        self._replay_step = max(1, curr)
        self._sync_active_step()

    @Slot()
    def _step_next(self) -> None:
        self._stop_animation()
        if not self._cached_run_result:
            return
        history = self._cached_run_result.extra.get("history", [])
        total = len(history) or len(self._cached_run_result.visited)
        curr = (self._replay_step or 0) + 1
        self._replay_step = min(total, curr)
        self._sync_active_step()

    @Slot()
    def _show_full_run(self) -> None:
        self._stop_animation()
        if not self._cached_run_result:
            return
        history = self._cached_run_result.extra.get("history", [])
        total = len(history) or len(self._cached_run_result.visited)
        self._replay_step = total
        self._sync_active_step()

    @Slot()
    def _reset_run(self) -> None:
        self._stop_animation()
        self._replay_step = 1
        self._sync_active_step()

    def _sync_active_step(self) -> None:
        if not self._cached_run_result:
            return
        history = self._cached_run_result.extra.get("history", [])
        total = len(history) or len(self._cached_run_result.visited)
        step = self._replay_step or total
        self._update_step_label(total)
        self._update_kpi_cards(self._cached_run_result)

        # Highlight corresponding row in table
        if 0 < step <= self._table.rowCount():
            self._table.blockSignals(True)
            self._table.selectRow(step - 1)
            self._table.scrollToItem(self._table.item(step - 1, 0))
            self._table.blockSignals(False)

        self._curve_canvas.redraw()

    def _update_step_label(self, total: int) -> None:
        step = self._replay_step if self._replay_step is not None else total
        self._lbl_step_counter.setText(f"Step {step} / {total}")

    @Slot(int, int)
    def _on_table_row_clicked(self, row: int, col: int) -> None:
        self._stop_animation()
        self._replay_step = row + 1
        self._sync_active_step()

    # ------------------------------------------------------------------ Drawing & Reference

    def _current_truth(self) -> Optional[GroundTruth]:
        key = self._dataset_combo.currentData()
        if not key:
            return None
        meas_key = self._measure_combo.currentData() or "normalized_variance"
        return self._state.ground_truth_for(str(key), str(meas_key))

    @Slot(bool)
    def _on_show_fit_toggled(self, checked: bool) -> None:
        if self._cached_run_result:
            history = self._cached_run_result.extra.get("history", [])
            self._populate_telemetry(history)
            self._update_kpi_cards(self._cached_run_result)
        self._redraw()

    @Slot()
    def _redraw(self) -> None:
        self._compute_btn.setEnabled(
            self._current_truth() is None and bool(self._dataset_combo.currentData())
            and not self._jobs.is_busy
        )
        self._curve_canvas.redraw()

    def _draw_curve(self, figure: Figure) -> None:
        truth = self._current_truth()
        results = [self._cached_run_result] if self._cached_run_result else []
        draw_focus_curve(
            figure=figure,
            truth=truth,
            results=results,
            replay_step=self._replay_step,
            show_global=self._show_global_cb.isChecked(),
            show_fit=self._show_fit_cb.isChecked(),
        )

    @Slot()
    def _on_compute_reference(self) -> None:
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        if dataset is None:
            return
        meas_key = self._measure_combo.currentData() or "normalized_variance"
        self._jobs.submit(
            GroundTruthJob([dataset], str(meas_key)),
            lambda _: self._recalculate_current_run(),
        )

    def canvases(self) -> list[PlotCanvas]:
        return [self._curve_canvas]
