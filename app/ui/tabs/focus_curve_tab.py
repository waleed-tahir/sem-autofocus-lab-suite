"""Tab 3: Focus Curve & Coarse-to-Fine Gradient Ascent Workspace.

Features:
- Laboratory Reference Design:
  * Top Metric HUD KPI Cards (Algorithm State, Captures Used, Local Gradient, Best Peak Found)
  * Normalized Variance Curve & Coarse-to-Fine Gradient Trajectory Plot
  * Playback Controls (Auto-Run, Prev, Step +1, Show Full Run, Reset, Speed Selector)
  * Live Interactive Parameter Sliders (Initial Start Z_0, Coarse Step Size ΔZ, Refinement Decay α, Adaptive Step)
  * Step-by-Step Gradient Execution Telemetry Log with color-coded phase badges
  * Synchronized plane inspection on table row click or canvas click
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
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
    """Complete Coarse-to-Fine Gradient Ascent and Focus Curve Analysis Tab."""

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
        self._show_global_cb = QCheckBox("Show Global Sweep Curve")
        self._show_global_cb.setChecked(True)
        self._compute_btn = QPushButton("Compute reference curve")
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

    # ------------------------------------------------------------------ UI Layout

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. Top Controls Bar
        main_layout.addWidget(self._build_top_bar())

        # Splitter between Plot+Controls (Top) and Telemetry Log (Bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        # 2. KPI HUD Metric Cards
        top_layout.addWidget(self._build_kpi_cards())

        # 3. Focus Curve Plot Canvas
        top_layout.addWidget(self._curve_canvas, stretch=1)

        # 4. Playback and Parameter Sliders Bar
        top_layout.addWidget(self._build_playback_and_param_bar())

        splitter.addWidget(top_container)

        # 5. Bottom Telemetry Log Panel
        splitter.addWidget(self._build_telemetry_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, stretch=1)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        lbl_ds = QLabel("Target Image Set:")
        lbl_ds.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569;")
        layout.addWidget(lbl_ds)
        self._dataset_combo.setMinimumWidth(160)
        layout.addWidget(self._dataset_combo)

        lbl_meas = QLabel("Measure:")
        lbl_meas.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569;")
        layout.addWidget(lbl_meas)
        self._measure_combo.setMinimumWidth(180)
        layout.addWidget(self._measure_combo)

        lbl_algo = QLabel("Algorithm:")
        lbl_algo.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569;")
        layout.addWidget(lbl_algo)
        self._algorithm_combo.setMinimumWidth(180)
        layout.addWidget(self._algorithm_combo)

        layout.addSpacing(10)
        layout.addWidget(self._show_global_cb)
        layout.addStretch()
        layout.addWidget(self._compute_btn)
        return bar

    def _build_kpi_cards(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet("background: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 4px;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        def _make_card(title: str):
            card = QFrame()
            card.setStyleSheet("background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 6px 12px;")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(4, 4, 4, 4)
            c_lay.setSpacing(2)
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet("font-size: 14px; font-weight: 700; color: #38bdf8;")
            lbl_sub = QLabel("—")
            lbl_sub.setStyleSheet("font-size: 10px; color: #64748b;")
            c_lay.addWidget(lbl_title)
            c_lay.addWidget(lbl_val)
            c_lay.addWidget(lbl_sub)
            return card, lbl_val, lbl_sub

        # 4 Metric Cards
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
        container.setStyleSheet("background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
        main_lay = QVBoxLayout(container)
        main_lay.setContentsMargins(8, 6, 8, 6)
        main_lay.setSpacing(6)

        # Row 1: Playback Buttons
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._btn_play = QPushButton("Auto-Run Focus")
        self._btn_play.setIcon(get_fluent_icon("play.png"))
        self._btn_play.setStyleSheet(
            "background: #0284c7; color: #ffffff; font-weight: 600; font-size: 11px; "
            "border: none; border-radius: 4px; padding: 6px 14px;"
        )

        self._btn_prev = QPushButton("◀ Prev")
        self._btn_prev.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 11px; border-radius: 4px; padding: 6px 12px;")

        self._btn_step = QPushButton("Step +1 Capture ▶")
        self._btn_step.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 11px; border-radius: 4px; padding: 6px 12px;")

        self._btn_full = QPushButton("Show Full Run ⏭")
        self._btn_full.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 11px; border-radius: 4px; padding: 6px 12px;")

        self._btn_reset = QPushButton("↺ Reset")
        self._btn_reset.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 11px; border-radius: 4px; padding: 6px 12px;")

        self._lbl_step_counter = QLabel("Step: — / —")
        self._lbl_step_counter.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 11px; padding: 0 8px;")

        self._speed_combo = QComboBox()
        self._speed_combo.addItems(["Speed: Fast (150ms)", "Speed: Normal (480ms)", "Speed: Slow (800ms)"])
        self._speed_combo.setCurrentIndex(1)
        self._speed_combo.setStyleSheet("background: #1e293b; color: #f8fafc; font-size: 11px; padding: 4px 8px;")

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

        # Row 2: Interactive Parameter Sliders
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # 1. Z0 Slider
        z0_box = QVBoxLayout()
        self._lbl_z0_title = QLabel("Initial Start Plane (Z_0):  Z = 12")
        self._lbl_z0_title.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 600;")
        self._slider_z0 = QSlider(Qt.Orientation.Horizontal)
        self._slider_z0.setRange(0, 198)
        self._slider_z0.setValue(12)
        z0_box.addWidget(self._lbl_z0_title)
        z0_box.addWidget(self._slider_z0)

        # 2. Coarse Step Slider
        step_box = QVBoxLayout()
        self._lbl_step_title = QLabel("Coarse Step Size (ΔZ_coarse):  14 planes")
        self._lbl_step_title.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 600;")
        self._slider_step = QSlider(Qt.Orientation.Horizontal)
        self._slider_step.setRange(4, 30)
        self._slider_step.setValue(14)
        step_box.addWidget(self._lbl_step_title)
        step_box.addWidget(self._slider_step)

        # 3. Decay Slider
        decay_box = QVBoxLayout()
        self._lbl_decay_title = QLabel("Refinement Decay (α_decay):  0.50×")
        self._lbl_decay_title.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 600;")
        self._slider_decay = QSlider(Qt.Orientation.Horizontal)
        self._slider_decay.setRange(10, 90)
        self._slider_decay.setValue(50)
        decay_box.addWidget(self._lbl_decay_title)
        decay_box.addWidget(self._slider_decay)

        # 4. Adaptive Checkbox
        adapt_box = QVBoxLayout()
        self._cb_adaptive = QCheckBox("Adaptive Gradient Step")
        self._cb_adaptive.setStyleSheet("color: #f8fafc; font-weight: 600; font-size: 11px;")
        lbl_adapt_desc = QLabel("Scales coarse step dynamically by local slope |d(NV)/dZ|")
        lbl_adapt_desc.setStyleSheet("font-size: 9px; color: #64748b;")
        adapt_box.addWidget(self._cb_adaptive)
        adapt_box.addWidget(lbl_adapt_desc)

        row2.addLayout(z0_box, stretch=2)
        row2.addLayout(step_box, stretch=2)
        row2.addLayout(decay_box, stretch=2)
        row2.addLayout(adapt_box, stretch=3)
        main_lay.addLayout(row2)

        return container

    def _build_telemetry_panel(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet("background: #090d16; border: 1px solid #1e293b; border-radius: 8px; padding: 4px;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header bar
        header_bar = QHBoxLayout()
        lbl_title = QLabel("STEP-BY-STEP GRADIENT EXECUTION TELEMETRY LOG")
        lbl_title.setStyleSheet("font-weight: 800; font-size: 11px; color: #f8fafc; letter-spacing: 0.5px;")
        lbl_sub = QLabel("(Click any row to inspect that capture)")
        lbl_sub.setStyleSheet("font-size: 10px; color: #64748b; margin-left: 6px;")
        self._lbl_telemetry_peak = QLabel("Final Peak: —")
        self._lbl_telemetry_peak.setStyleSheet("font-weight: 700; font-size: 11px; color: #10b981;")

        header_bar.addWidget(lbl_title)
        header_bar.addWidget(lbl_sub)
        header_bar.addStretch()
        header_bar.addWidget(self._lbl_telemetry_peak)
        layout.addLayout(header_bar)

        # Telemetry Table
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels([
            "CAPTURE #", "ALGORITHM PHASE", "PLANE Z", "STEP ΔZ",
            "MEAN (M)", "NORM. VAR (NV)", "GRADIENT D(NV)/DZ", "CONTROLLER DECISION"
        ])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #0b0f19;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: 1px solid #1e293b;
                font-family: 'Consolas', 'Segoe UI Mono', monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background: #111827;
                color: #94a3b8;
                font-weight: 700;
                font-size: 10px;
                padding: 4px 6px;
                border: 1px solid #1e293b;
            }
            QTableWidget::item:selected {
                background: #1e293b;
                color: #38bdf8;
            }
        """)

        # Set specific column widths
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
        header.resizeSection(5, 110)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(6, 120)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)
        return container

    # ------------------------------------------------------------------ Signal Wiring

    def _connect_signals(self) -> None:
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_or_param_changed)
        self._measure_combo.currentIndexChanged.connect(self._on_measure_changed)
        self._algorithm_combo.currentIndexChanged.connect(self._on_algo_changed)
        self._show_global_cb.toggled.connect(self._redraw)
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

        # Check if algorithm is gradient: execute live with current slider settings
        if algo_key == "gradient":
            z0 = self._slider_z0.value()
            coarse_step = self._slider_step.value()
            decay = self._slider_decay.value() / 100.0
            adaptive = self._cb_adaptive.isChecked()

            meas = require_measure(str(meas_key))
            ev = Evaluator(dataset, meas)
            algo_spec = require_algo("gradient")
            params = {
                "start_idx": z0,
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
                apply_fit=False,
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
                    apply_fit=False,
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
        if active_rec:
            phase = active_rec.get("phase", "IN PROGRESS")
            if phase == "CONVERGED":
                self._val_state.setText("● CONVERGED (FOCUS LOCKED)")
                self._val_state.setStyleSheet("font-size: 13px; font-weight: 700; color: #10b981;")
                self._sub_state.setText(f"Stage locked onto optimal focal plane Z={result.coarse_idx}")
            elif phase == "OVERSHOOT":
                self._val_state.setText("● OVERSHOOT (REVERSE & REFINE)")
                self._val_state.setStyleSheet("font-size: 13px; font-weight: 700; color: #ef233c;")
                self._sub_state.setText("Score dropped -> Decaying step size")
            else:
                self._val_state.setText(f"● {phase} (IN PROGRESS)")
                self._val_state.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8;")
                self._sub_state.setText("Climbing along ascending gradient")
        else:
            self._val_state.setText("● COMPLETED")
            self._val_state.setStyleSheet("font-size: 13px; font-weight: 700; color: #10b981;")
            self._sub_state.setText(f"Optimal peak Z={result.coarse_idx}")

        # 2. SEM Captures Used Card
        total_global = truth.curve.size if truth else (result.coarse_idx + 100)
        captures_used = active_rec["step"] if active_rec else result.frames_evaluated
        pct_saved = max(0.0, (1.0 - (captures_used / float(total_global))) * 100.0) if total_global > 0 else 0.0
        speedup = (total_global / float(captures_used)) if captures_used > 0 else 1.0
        self._val_scans.setText(f"{captures_used} / {total_global} global")
        self._sub_scans.setText(f"{pct_saved:.1f}% fewer scans ({speedup:.1f}× faster)")

        # 3. Local Gradient Card
        if active_rec and abs(float(active_rec.get("gradient", 0.0))) > 1e-6:
            grad = float(active_rec["gradient"])
            dz = active_rec.get("step_dz", 0)
            color = "#10b981" if grad >= 0 else "#ef233c"
            self._val_grad.setText(f"{grad:+.4f}")
            self._val_grad.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {color};")
            self._sub_grad.setText(f"Step ΔZ = {dz:+d} planes")
        else:
            self._val_grad.setText("0.0000")
            self._val_grad.setStyleSheet("font-size: 14px; font-weight: 700; color: #94a3b8;")
            self._sub_grad.setText("Step ΔZ = 0 planes")

        # 4. Best Peak Found Card
        true_max = truth.peak_idx if truth else result.coarse_idx
        dz_err = abs(result.coarse_idx - true_max)
        self._val_peak.setText(f"Z* = {result.coarse_idx} (True Max: {true_max})")
        self._val_peak.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")
        if dz_err == 0:
            self._sub_peak.setText("Exact Global Peak Locked (ΔZ = 0)")
        else:
            self._sub_peak.setText(f"Focal Error: ΔZ = {dz_err} planes")

    def _populate_telemetry(self, history: List[Dict[str, Any]]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(len(history))

        if not history:
            self._table.blockSignals(False)
            self._lbl_telemetry_peak.setText("Final Peak: —")
            return

        final_peak = history[-1].get("z", history[-1].get("idx", 0))
        unique_captures = len({h.get("z", h.get("idx", 0)) for h in history})
        self._lbl_telemetry_peak.setText(f"Final Peak: Z* = {final_peak} ({unique_captures} unique captures)")

        # Badges styling map
        badge_styles = {
            "INIT": ("background: #1e293b; color: #93c5fd; border: 1px solid #3b82f6; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
            "COARSE_PROBE": ("background: #083344; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
            "COARSE": ("background: #0c4a6e; color: #7dd3fc; border: 1px solid #0369a1; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
            "OVERSHOOT": ("background: #4c0519; color: #fda4af; border: 1px solid #e11d48; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
            "FINE": ("background: #451a03; color: #fcd34d; border: 1px solid #d97706; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
            "CONVERGED": ("background: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 4px; padding: 2px 6px; font-weight: bold;"),
        }

        for row, rec in enumerate(history):
            # 0. Capture #
            it0 = QTableWidgetItem(f"#{rec.get('step', row + 1)}")
            it0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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
            it2.setForeground(QColor("#f8fafc"))
            self._table.setItem(row, 2, it2)

            # 3. Step ΔZ
            dz = rec.get("step_dz", 0)
            dz_str = f"{dz:+d}" if row > 0 else "—"
            it3 = QTableWidgetItem(dz_str)
            it3.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it3.setForeground(QColor("#94a3b8"))
            self._table.setItem(row, 3, it3)

            # 4. Mean (M)
            mean_val = rec.get("mean", 108.85)
            it4 = QTableWidgetItem(f"{mean_val:.2f}")
            it4.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it4.setForeground(QColor("#e2e8f0"))
            self._table.setItem(row, 4, it4)

            # 5. Norm. Var (NV)
            score_val = rec.get("score", 0.0)
            it5 = QTableWidgetItem(f"{score_val:.4f}")
            it5.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it5.setForeground(QColor("#10b981"))
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
                it6.setForeground(QColor("#10b981" if grad >= 0 else "#ef233c"))
            else:
                it6.setForeground(QColor("#94a3b8"))
            self._table.setItem(row, 6, it6)

            # 7. Decision
            it7 = QTableWidgetItem(str(rec.get("decision", "")))
            it7.setForeground(QColor("#e2e8f0"))
            self._table.setItem(row, 7, it7)

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
            self._btn_play.setStyleSheet(
                "background: #e11d48; color: #ffffff; font-weight: 600; font-size: 11px; "
                "border: none; border-radius: 4px; padding: 6px 14px;"
            )
            self._replay_timer.start()
            self._sync_active_step()

    def _stop_animation(self) -> None:
        self._is_playing = False
        self._replay_timer.stop()
        self._btn_play.setText("Auto-Run Focus")
        self._btn_play.setIcon(get_fluent_icon("play.png"))
        self._btn_play.setStyleSheet(
            "background: #0284c7; color: #ffffff; font-weight: 600; font-size: 11px; "
            "border: none; border-radius: 4px; padding: 6px 14px;"
        )

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
