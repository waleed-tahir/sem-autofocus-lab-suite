"""Tab 8: Focus measure comparison workspace.

Upgraded per user request:
- Instead of forcing all 5 focus measures to always display together,
  a checkable multi-selection list allows users to select ANY subset of measures to compare.
- "All" and "None" quick selection buttons.
- The plot and the metrics table update dynamically to reflect only the selected measures.
"""

from __future__ import annotations

import logging
from typing import Optional

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.experiment import GroundTruth, MeasureSweepJob
from app.core.focus_measures import FOCUS_MEASURES, keys as measure_keys
from app.plots.measure_comparison import draw_measure_curves, measure_rows
from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.common import (
    checked_keys,
    fill_table,
    integer_cell,
    make_check_list,
    make_table,
    number_cell,
    refresh_dataset_combo,
    set_all_checked,
    set_check_items,
    text_cell,
)
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

_COLUMNS = (
    "Focus measure", "Peak frame", "Peak WD (mm)", "Fine frame", "Fine WD (mm)",
    "Peak value", "FWHM (frames)", "Local maxima", "Peak/noise", "Contrast",
    "Time/frame (ms)", "Total scan (s)",
)

_TOOLTIPS = (
    "Focus measure.",
    "Frame with the highest focus score.",
    "Working distance of that frame, in millimetres.",
    "Sub-frame peak from the quadratic fit.",
    "Working distance of the sub-frame peak, in millimetres.",
    "Raw focus score at the peak.",
    "Full width at half maximum of the peak, in frames.",
    "Number of local maxima across the curve.",
    "Ratio of peak height to the noise floor.",
    "Michelson contrast of the curve.",
    "Time to score one frame, averaged over the stack.",
    "Total time of the exhaustive scan.",
)

CONTROL_PANEL_WIDTH = 340


class MeasureComparisonTab(QWidget):
    """Compares selectable focus measures on one image set."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._jobs = jobs

        self._dataset_combo = QComboBox()
        self._measure_list = make_check_list(120)
        self._measure_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._canvas = PlotCanvas("measure_comparison")
        self._table = make_table(_COLUMNS, _TOOLTIPS)
        self._table.setMinimumHeight(180)
        self._compute_button = QPushButton("Compute missing curves")
        self._compute_button.setObjectName("primaryButton")
        self._compute_button.setProperty("accent", True)
        self._status = QLabel("")
        self._canvas.set_draw_callback(self._draw)

        self._build_layout()
        self._fill_measure_list()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        self._dataset_combo.setToolTip("Image set to scan with selected focus measures.")
        self._compute_button.setToolTip("Compute missing reference curves for selected measures.")
        self._status.setWordWrap(True)
        self._status.setEnabled(False)

        # Left control panel
        ctrl_group = QGroupBox("Measure Selection")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(8)

        ctrl_layout.addWidget(QLabel("Image set:"))
        ctrl_layout.addWidget(self._dataset_combo)

        ctrl_layout.addSpacing(4)
        ctrl_layout.addWidget(QLabel("Focus measures to compare:"))
        ctrl_layout.addWidget(self._measure_list, stretch=1)

        btn_row = QHBoxLayout()
        self._all_btn = QPushButton("Select All")
        self._none_btn = QPushButton("Clear All")
        self._all_btn.setFixedHeight(24)
        self._none_btn.setFixedHeight(24)
        self._all_btn.clicked.connect(lambda: set_all_checked(self._measure_list, True))
        self._none_btn.clicked.connect(lambda: set_all_checked(self._measure_list, False))
        btn_row.addWidget(self._all_btn, stretch=1)
        btn_row.addWidget(self._none_btn, stretch=1)
        ctrl_layout.addLayout(btn_row)

        ctrl_layout.addSpacing(6)
        ctrl_layout.addWidget(self._compute_button)
        ctrl_layout.addWidget(self._status)

        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.addWidget(ctrl_group)
        left_panel.setMaximumWidth(CONTROL_PANEL_WIDTH)

        # Right side: plot on top, metrics table below
        table_group = QGroupBox("Peak, Sharpness and Cost Metrics")
        table_group.setMinimumHeight(220)
        table_layout = QVBoxLayout(table_group)
        self._table.setMinimumHeight(200)
        table_layout.addWidget(self._table)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self._canvas)
        right_splitter.addWidget(table_group)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)
        right_splitter.setSizes([380, 260])

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 4)

        layout = QVBoxLayout(self)
        layout.addWidget(main_splitter)

    def _fill_measure_list(self) -> None:
        items = [(key, FOCUS_MEASURES[key].display_name) for key in measure_keys()]
        set_check_items(self._measure_list, items)
        set_all_checked(self._measure_list, True)

    def _connect(self) -> None:
        self._dataset_combo.currentIndexChanged.connect(self.refresh)
        self._measure_list.itemChanged.connect(self._on_measure_selection_changed)
        self._compute_button.clicked.connect(self._on_compute)
        self._state.datasets_changed.connect(self._on_datasets_changed)
        self._state.ground_truth_changed.connect(self.refresh)
        self._state.active_selection_changed.connect(self._on_active_selection_changed)
        self._jobs.busy_changed.connect(lambda busy: self._update_button(busy))

    @Slot(str, str)
    def _on_active_selection_changed(self, dataset_key: str, algorithm_key: str) -> None:
        d_idx = self._dataset_combo.findData(dataset_key)
        if d_idx >= 0 and self._dataset_combo.currentIndex() != d_idx:
            self._dataset_combo.blockSignals(True)
            self._dataset_combo.setCurrentIndex(d_idx)
            self._dataset_combo.blockSignals(False)
            self.refresh()

    @Slot()
    def _on_datasets_changed(self) -> None:
        refresh_dataset_combo(self._dataset_combo, self._state)
        self.refresh()

    @Slot()
    def _on_measure_selection_changed(self) -> None:
        self._canvas.redraw()
        self._fill_table(self._selected_truths())

    def _all_truths_for_dataset(self) -> list[GroundTruth]:
        key = self._dataset_combo.currentData()
        return self._state.ground_truths_for_dataset(str(key)) if key else []

    def _selected_truths(self) -> list[GroundTruth]:
        selected_keys = set(checked_keys(self._measure_list))
        return [
            truth for truth in self._all_truths_for_dataset()
            if truth.measure_key in selected_keys
        ]

    @Slot()
    def refresh(self) -> None:
        if self._dataset_combo.count() != self._state.dataset_count:
            refresh_dataset_combo(self._dataset_combo, self._state)

        all_truths = self._all_truths_for_dataset()
        selected_truths = self._selected_truths()

        self._canvas.redraw()
        self._fill_table(selected_truths)

        total = len(measure_keys())
        if not self._dataset_combo.currentData():
            self._status.setText("Load an image set first, on the Datasets tab.")
        else:
            self._status.setText(
                f"{len(all_truths)} of {total} focus measures available for this image set."
            )
        self._update_button(self._jobs.is_busy)

    def _update_button(self, busy: bool) -> None:
        has_dataset = bool(self._dataset_combo.currentData())
        selected_keys = checked_keys(self._measure_list)
        available = {t.measure_key for t in self._all_truths_for_dataset()}
        missing_selected = [k for k in selected_keys if k not in available]
        if missing_selected:
            self._compute_button.setText(f"Compute missing curves ({len(missing_selected)})")
        else:
            self._compute_button.setText("Recompute selected curves")
        self._compute_button.setEnabled(has_dataset and len(selected_keys) > 0 and not busy)

    def _fill_table(self, truths: list[GroundTruth]) -> None:
        fill_table(
            self._table,
            [
                (
                    text_cell(row.measure),
                    integer_cell(row.peak_idx),
                    number_cell(row.peak_wd_mm, 5),
                    number_cell(row.fine_idx, 3),
                    number_cell(row.fine_wd_mm, 5),
                    number_cell(row.peak_value, 4),
                    number_cell(row.fwhm, 2),
                    integer_cell(row.local_maxima),
                    number_cell(row.snr, 1),
                    number_cell(row.contrast, 3),
                    number_cell(row.compute_ms, 2),
                    number_cell(row.total_s, 2),
                )
                for row in measure_rows(truths)
            ],
        )

    def _draw(self, figure: Figure) -> None:
        draw_measure_curves(figure, self._selected_truths())

    @Slot()
    def _on_compute(self) -> None:
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        if dataset is None:
            return

        selected_keys = checked_keys(self._measure_list)
        pending = [
            m_key for m_key in selected_keys
            if self._state.ground_truth_for(dataset.key, m_key) is None
        ]
        if not pending:
            pending = list(selected_keys)
        if not pending:
            return
        self._jobs.submit(
            MeasureSweepJob(dataset, pending), lambda _: self.refresh()
        )

    def canvases(self) -> list[PlotCanvas]:
        return [self._canvas]
