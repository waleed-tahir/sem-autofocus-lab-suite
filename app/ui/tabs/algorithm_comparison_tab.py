"""Tab 4: Algorithmic Trade-offs between Global Scan and Gradient Search.

Displays side-by-side metric comparison bar charts, KPI summary tiles,
and the beam-time savings matrix.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.run_result import RunResult
from app.plots.algorithm_bars import draw_algorithm_bars, frames_saved_table
from app.ui.app_state import AppState
from app.ui.tabs.common import (
    fill_table,
    integer_cell,
    make_table,
    number_cell,
    refresh_dataset_combo,
    text_cell,
)
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

_COLUMNS = (
    "Algorithm",
    "Frames read",
    "Baseline frames",
    "Frames saved (%)",
    "Time (ms)",
    "Speed-up",
    "Error (µm)",
)

_TOOLTIPS = (
    "Search strategy.",
    "Distinct frames evaluated during the search.",
    "Frames read by the exhaustive baseline scan.",
    "Percentage of frames avoided vs. exhaustive baseline.",
    "Total wall-clock search time in milliseconds.",
    "Baseline time divided by algorithm time.",
    "Distance from reference ground truth peak in micrometres.",
)


class AlgorithmComparisonTab(QWidget):
    """Algorithmic trade-offs and speedup visualization."""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._state = state

        self._dataset_combo = QComboBox()
        self._canvas = PlotCanvas("algorithm_comparison")
        self._table = make_table(_COLUMNS, _TOOLTIPS)
        self._table.setMinimumHeight(110)

        # Distribute columns evenly across the table width
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._canvas.set_draw_callback(self._draw_chart)

        self._build_layout()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top Control Row
        top_bar = QHBoxLayout()
        lbl_target = QLabel("Target Image Set:")
        lbl_target.setStyleSheet("font-weight: 600; font-size: 11px; color: #424242;")
        top_bar.addWidget(lbl_target)
        self._dataset_combo.setMinimumWidth(240)
        top_bar.addWidget(self._dataset_combo)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # KPI Summary Tiles
        self._kpi_strip = self._build_kpi_strip()
        layout.addWidget(self._kpi_strip)

        # Splitter: Side-by-side Bar Charts on Top, Savings Matrix Below
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._canvas)

        table_group = QGroupBox("Beam Time && Exposure Savings Matrix")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(6, 10, 6, 6)
        table_layout.addWidget(self._table)
        splitter.addWidget(table_group)

        splitter.setSizes([320, 160])
        layout.addWidget(splitter, stretch=1)

    def _build_kpi_strip(self) -> QWidget:
        container = QFrame()
        container.setObjectName("kpiStrip")
        container.setStyleSheet(
            "QFrame#kpiStrip { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; }"
        )
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        def make_tile(title: str, text_color: str = "#0067c0") -> tuple[QWidget, QLabel]:
            tile = QWidget()
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(4, 2, 4, 2)
            tl.setSpacing(1)
            caption = QLabel(title.upper())
            caption.setStyleSheet("font-size: 9.5px; font-weight: 600; color: #5e5e5e; letter-spacing: 0.3px;")
            value = QLabel("-")
            value.setWordWrap(True)
            value.setStyleSheet(f"font-size: 12.5px; font-weight: 600; color: {text_color};")
            tl.addWidget(caption)
            tl.addWidget(value)
            return tile, value

        t1, self._kpi_best_algo_val = make_tile("Optimal Algorithm", "#0067c0")
        t2, self._kpi_max_savings_val = make_tile("Max Frames Saved", "#107c41")
        t3, self._kpi_fastest_time_val = make_tile("Fastest Convergence", "#1c1c1c")
        t4, self._kpi_min_error_val = make_tile("Min Error vs Baseline", "#1c1c1c")

        layout.addWidget(t1, stretch=1)
        layout.addWidget(t2, stretch=1)
        layout.addWidget(t3, stretch=1)
        layout.addWidget(t4, stretch=1)

        return container

    def _connect(self) -> None:
        self._dataset_combo.currentIndexChanged.connect(self._redraw)
        self._state.datasets_changed.connect(self.refresh)
        self._state.results_changed.connect(self.refresh)
        self._state.active_selection_changed.connect(self._on_active_selection_changed)

    @Slot(str, str)
    def _on_active_selection_changed(self, dataset_key: str, algorithm_key: str) -> None:
        d_idx = self._dataset_combo.findData(dataset_key)
        if d_idx >= 0 and self._dataset_combo.currentIndex() != d_idx:
            self._dataset_combo.blockSignals(True)
            self._dataset_combo.setCurrentIndex(d_idx)
            self._dataset_combo.blockSignals(False)
            self._redraw()

    @Slot()
    def refresh(self) -> None:
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._redraw()

    def _current_results(self) -> list[RunResult]:
        key = self._dataset_combo.currentData()
        if not key:
            return []
        latest: dict[str, RunResult] = {}
        for result in self._state.results_for_dataset(str(key)):
            latest[result.algorithm_key] = result
        return list(latest.values())

    @Slot()
    def _redraw(self) -> None:
        results = self._current_results()
        self._canvas.redraw()
        self._fill_table(results)
        self._update_kpis(results)

    def _draw_chart(self, figure: Figure) -> None:
        results = self._current_results()
        draw_algorithm_bars(figure, results)

    @staticmethod
    def _is_converged(r: RunResult, max_error_frames: float = 10.0, max_error_um: float = 60.0) -> bool:
        """Tell whether a run successfully converged to focus within tolerance."""
        err_frames = (
            r.coarse_error_frames
            if (r.coarse_error_frames is not None and not math.isnan(r.coarse_error_frames))
            else None
        )
        err_um = (
            r.coarse_error_um
            if (r.coarse_error_um is not None and not math.isnan(r.coarse_error_um))
            else None
        )
        if err_frames is not None:
            return err_frames <= max_error_frames
        if err_um is not None:
            return err_um <= max_error_um
        return True

    def _update_kpis(self, results: list[RunResult]) -> None:
        if not results:
            self._kpi_best_algo_val.setText("-")
            self._kpi_max_savings_val.setText("-")
            self._kpi_fastest_time_val.setText("-")
            self._kpi_min_error_val.setText("-")
            return

        baseline = next((r for r in results if r.algorithm_key == "global_scan"), None)
        base_frames = baseline.frames_evaluated if baseline else max(r.frames_evaluated for r in results)

        sublinear = [r for r in results if r.algorithm_key != "global_scan"]
        candidates = sublinear if sublinear else results

        # 1. Optimal Algorithm:
        # Must satisfy focal convergence (within depth-of-field / coarse frame tolerance).
        # Among converged candidates, pick the one with the highest frame savings (or fastest/lowest error).
        # If no algorithm converged, fall back to the one closest to focus.
        converged = [r for r in candidates if self._is_converged(r)]

        if converged:
            optimal = max(
                converged,
                key=lambda r: (
                    r.frames_saved_percent(base_frames),
                    -(r.coarse_error_um if (r.coarse_error_um is not None and not math.isnan(r.coarse_error_um)) else 999.0),
                    -r.elapsed_ms,
                ),
            )
        else:
            optimal = min(
                candidates,
                key=lambda r: (
                    r.coarse_error_um if (r.coarse_error_um is not None and not math.isnan(r.coarse_error_um)) else 9999.0
                ),
            )

        # 2. Max Frames Saved:
        # Savings of the optimal converged algorithm relative to the baseline
        saved_pct_val = optimal.frames_saved_percent(base_frames)
        saved_pct_str = f"{saved_pct_val:.1f}%" if not math.isnan(saved_pct_val) else "0.0%"

        # 3. Fastest Convergence:
        # Minimum runtime among converged algorithms (or all candidates if none converged)
        fast_pool = converged if converged else candidates
        fastest = min(fast_pool, key=lambda r: r.elapsed_ms)

        # 4. Min Error vs Baseline:
        # Best accuracy among candidate search algorithms compared against the baseline
        err_pool = sublinear if sublinear else results
        min_err = min(
            err_pool,
            key=lambda r: (
                r.coarse_error_um if (r.coarse_error_um is not None and not math.isnan(r.coarse_error_um)) else 9999.0
            ),
        )
        err_val = (
            f"{min_err.coarse_error_um:.2f} µm"
            if (min_err.coarse_error_um is not None and not math.isnan(min_err.coarse_error_um))
            else "-"
        )

        self._kpi_best_algo_val.setText(optimal.algorithm)
        self._kpi_best_algo_val.setToolTip(
            f"{optimal.algorithm}\nCoarse Error: {optimal.coarse_error_um:.2f} µm\nFrames Saved: {saved_pct_str}"
        )

        self._kpi_max_savings_val.setText(saved_pct_str)
        self._kpi_max_savings_val.setToolTip(f"Achieved by {optimal.algorithm} relative to {base_frames} baseline frames")

        self._kpi_fastest_time_val.setText(f"{fastest.elapsed_ms:.0f} ms ({fastest.algorithm})")
        self._kpi_fastest_time_val.setToolTip(f"{fastest.algorithm}: {fastest.elapsed_ms:.1f} ms")

        self._kpi_min_error_val.setText(f"{err_val} ({min_err.algorithm})")
        self._kpi_min_error_val.setToolTip(f"{min_err.algorithm}: {err_val} error vs baseline")

    def _fill_table(self, results: list[RunResult]) -> None:
        rows = frames_saved_table(results)
        cells = [
            (
                text_cell(row.algorithm),
                integer_cell(row.frames_evaluated),
                integer_cell(row.baseline_frames),
                number_cell(row.saved_percent, 1),
                number_cell(row.elapsed_ms, 1),
                number_cell(row.speedup, 2),
                number_cell(row.error_um, 2),
            )
            for row in rows
        ]
        fill_table(self._table, cells)

    @property
    def canvases(self) -> list[tuple[str, PlotCanvas]]:
        return [("Algorithm Comparison", self._canvas)]
