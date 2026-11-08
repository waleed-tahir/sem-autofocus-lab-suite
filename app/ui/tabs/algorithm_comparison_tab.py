"""Tab 6: Algorithmic Trade-offs powered by modern interactive PyQtGraph charts.

Displays anti-aliased GPU-accelerated bar graphs, KPI summary tiles,
and the beam-time savings matrix with responsive styling.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.run_result import RunResult
from app.plots.algorithm_bars import frames_saved_table
from app.ui.app_state import AppState
from app.ui.tabs.common import (
    fill_table,
    integer_cell,
    make_table,
    number_cell,
    refresh_dataset_combo,
    text_cell,
)
from app.ui.widgets.modern_plot_widget import ModernAlgorithmBarChart

LOGGER = logging.getLogger(__name__)

_COLUMNS = (
    "Algorithm", "Frames read", "Baseline frames", "Frames saved (%)",
    "Time (ms)", "Speed-up", "Error (um)",
)

_TOOLTIPS = (
    "Search strategy.",
    "Distinct frames this run read, fine fit included.",
    "Frames an exhaustive scan reads.",
    "Share of frames this search never had to acquire.",
    "Wall-clock time of the search plus its refinement.",
    "Baseline time divided by this run's time.",
    "Distance from the reference peak, in micrometres.",
)


class AlgorithmComparisonTab(QWidget):
    """Modern PyQtGraph algorithmic trade-offs visualization."""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._state = state

        self._dataset_combo = QComboBox()
        self._chart = ModernAlgorithmBarChart()
        self._table = make_table(_COLUMNS, _TOOLTIPS)
        self._table.setMinimumHeight(110)

        self._build_layout()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top Control Row
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Target Image Set:"))
        self._dataset_combo.setMinimumWidth(240)
        top_bar.addWidget(self._dataset_combo)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 4 KPI Tiles inspired by generated UI
        self._kpi_strip = self._build_kpi_strip()
        layout.addWidget(self._kpi_strip)

        # Splitter: Modern PyQtGraph Bars on Top, Savings Matrix Below
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._chart)

        table_group = QGroupBox("Beam Time && Exposure Savings Matrix")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(4, 8, 4, 4)
        table_layout.addWidget(self._table)
        splitter.addWidget(table_group)

        splitter.setSizes([260, 160])
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
        self._chart.set_results(results)
        self._fill_table(results)
        self._update_kpis(results)

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

        best_saved = max(candidates, key=lambda r: r.frames_saved_percent(base_frames))
        fastest = min(results, key=lambda r: r.elapsed_ms)
        min_err = min(results, key=lambda r: r.coarse_error_um if r.coarse_error_um is not None else 999.0)

        saved_pct = f"{best_saved.frames_saved_percent(base_frames):.1f}%"
        self._kpi_best_algo_val.setText(best_saved.algorithm)
        self._kpi_max_savings_val.setText(saved_pct)
        self._kpi_fastest_time_val.setText(f"{fastest.elapsed_ms:.0f} ms ({fastest.algorithm})")
        err_val = f"{min_err.coarse_error_um:.2f} µm" if min_err.coarse_error_um is not None else "-"
        self._kpi_min_error_val.setText(f"{err_val} ({min_err.algorithm})")

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
