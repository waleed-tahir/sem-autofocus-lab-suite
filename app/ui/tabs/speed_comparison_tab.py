"""Tab 7: what the SEM scanning speed does to the focus curve.

A faster scan collects fewer electrons per pixel, so the frames are noisier, the
focus curve is rougher and a search has more false peaks to get trapped in.  This
tab puts the complete curve of every loaded image set on one pair of axes,
rescaled so they can be compared, and lists the hard numbers underneath.

Main contents:
    * :class:`SpeedComparisonTab` -- the curves, the quality bars and the table.
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

from app.core.experiment import GroundTruth, GroundTruthJob
from app.core.focus_measures import FOCUS_MEASURES
from app.core.focus_measures import keys as measure_keys
from app.plots.speed_comparison import draw_speed_curves, draw_speed_metrics, speed_rows
from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.common import (
    fill_table,
    integer_cell,
    make_table,
    number_cell,
    text_cell,
)
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

#: Columns of the per-speed table.
_COLUMNS = (
    "Image set", "Speed", "Frames", "Peak frame", "Coarse WD (mm)",
    "Fine frame", "Fine WD (mm)", "Peak value", "FWHM (frames)",
    "Noise sigma", "Peak/noise", "Local maxima", "Contrast", "Scan time (s)",
)

#: Explanations shown when hovering the table headers.
_TOOLTIPS = (
    "Folder the frames came from.",
    "SEM scanning speed read from the folder name.",
    "Frames in the focal stack.",
    "Peak frame of the exhaustive reference scan.",
    "Working distance of that frame.",
    "Sub-frame peak of the reference curve.",
    "Working distance of that sub-frame peak.",
    "Raw focus score at the peak.",
    "Peak width at half height. A narrow peak localises better.",
    "Noise on the curve, estimated from its second differences.",
    "Peak height above the floor divided by that noise.",
    "False peaks a search could get trapped in.",
    "Peak value divided by the lowest value of the curve.",
    "Time the exhaustive reference scan took.",
)


class SpeedComparisonTab(QWidget):
    """Compares the focus curves of every loaded scanning speed."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Build the tab.

        Args:
            state: Shared application state.
            jobs: Service used to compute the reference curves.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._jobs = jobs

        self._measure_combo = QComboBox()
        self._curve_canvas = PlotCanvas("speed_curves")
        self._metrics_canvas = PlotCanvas("speed_metrics", figure_size=(7.2, 6.2))
        self._table = make_table(_COLUMNS, _TOOLTIPS)
        self._table.setMinimumHeight(180)
        self._compute_button = QPushButton("Compute reference curves")
        self._compute_button.setObjectName("primaryButton")
        self._compute_button.setProperty("accent", True)
        self._status = QLabel("")

        self._curve_canvas.set_draw_callback(self._draw_curves)
        self._metrics_canvas.set_draw_callback(self._draw_metrics)

        self._build_layout()
        self._connect()
        self._fill_measure_combo()
        self.refresh()

    def _build_layout(self) -> None:
        """Put the controls on top, the two plots beside each other, table below."""
        self._measure_combo.setToolTip("Focus measure the curves are computed with.")
        self._compute_button.setToolTip(
            "Scan every loaded image set from end to end with this focus measure."
        )
        self._status.setWordWrap(True)
        self._status.setEnabled(False)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Focus measure:"))
        controls.addWidget(self._measure_combo)
        controls.addSpacing(16)
        controls.addWidget(self._compute_button)
        controls.addSpacing(16)
        controls.addWidget(self._status, stretch=1)

        plots = QSplitter(Qt.Orientation.Horizontal)
        plots.addWidget(self._curve_canvas)
        plots.addWidget(self._metrics_canvas)
        plots.setStretchFactor(0, 1)
        plots.setStretchFactor(1, 1)
        plots.setSizes([500, 500])

        table_group = QGroupBox("Peak position and curve quality per speed")
        table_group.setMinimumHeight(220)
        table_layout = QVBoxLayout(table_group)
        self._table.setMinimumHeight(200)
        table_layout.addWidget(self._table)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(plots)
        splitter.addWidget(table_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([380, 260])

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(splitter, stretch=1)

    def _connect(self) -> None:
        """Wire the controls, the plots and the shared state together."""
        self._measure_combo.currentIndexChanged.connect(self.refresh)
        self._compute_button.clicked.connect(self._on_compute)
        self._state.datasets_changed.connect(self.refresh)
        self._state.ground_truth_changed.connect(self.refresh)
        self._jobs.busy_changed.connect(self._on_busy_changed)

    def _fill_measure_combo(self) -> None:
        """Fill the focus-measure drop-down, starting at the required default."""
        self._measure_combo.blockSignals(True)
        for key in measure_keys():
            self._measure_combo.addItem(FOCUS_MEASURES[key].display_name, key)
        index = self._measure_combo.findData(self._state.measure_key)
        self._measure_combo.setCurrentIndex(max(0, index))
        self._measure_combo.blockSignals(False)

    @property
    def _measure_key(self) -> str:
        """Focus measure currently chosen in this tab."""
        return str(self._measure_combo.currentData() or self._state.measure_key)

    def _truths(self) -> list[GroundTruth]:
        """Reference curves available for the chosen focus measure."""
        return self._state.ground_truths_for_measure(self._measure_key)

    @Slot()
    def refresh(self) -> None:
        """Redraw both plots, refill the table and update the status line."""
        truths = self._truths()
        self._curve_canvas.redraw()
        self._metrics_canvas.redraw()
        self._fill_table(truths)

        missing = self._state.dataset_count - len(truths)
        if missing > 0:
            self._compute_button.setText(f"Compute reference curves ({missing} missing)")
        else:
            self._compute_button.setText("Recompute reference curves")
        self._compute_button.setEnabled(self._state.dataset_count > 0 and not self._jobs.is_busy)
        if self._state.dataset_count == 0:
            self._status.setText("Load some image sets first, on the Datasets tab.")
        elif missing > 0:
            self._status.setText(
                f"{len(truths)} of {self._state.dataset_count} image set(s) scanned. "
                f"Press the button to scan the remaining {missing}."
            )
        else:
            self._status.setText(
                f"All {len(truths)} image set(s) scanned with "
                f"{FOCUS_MEASURES[self._measure_key].display_name}."
            )

    def _fill_table(self, truths: list[GroundTruth]) -> None:
        """Refill the per-speed table."""
        fill_table(
            self._table,
            [
                (
                    text_cell(row.label),
                    integer_cell(row.speed) if row.speed is not None else ("-", None),
                    integer_cell(row.frames),
                    integer_cell(row.coarse_idx),
                    number_cell(row.coarse_wd_mm, 5),
                    number_cell(row.fine_idx, 3),
                    number_cell(row.fine_wd_mm, 5),
                    number_cell(row.peak_value, 4),
                    number_cell(row.fwhm, 2),
                    number_cell(row.noise_sigma, 5),
                    number_cell(row.snr, 1),
                    integer_cell(row.local_maxima),
                    number_cell(row.contrast, 3),
                    number_cell(row.elapsed_s, 2),
                )
                for row in speed_rows(truths)
            ],
        )

    def _draw_curves(self, figure: Figure) -> None:
        """Draw one normalised focus curve per scanning speed."""
        draw_speed_curves(figure, self._truths())

    def _draw_metrics(self, figure: Figure) -> None:
        """Draw the curve-quality bars per scanning speed."""
        draw_speed_metrics(figure, self._truths())

    @Slot()
    def _on_compute(self) -> None:
        """Scan every loaded image set with this measure; if all already scanned, recompute."""
        measure_key = self._measure_key
        pending = [
            dataset
            for dataset in self._state.datasets
            if self._state.ground_truth_for(dataset.key, measure_key) is None
        ]
        if not pending:
            pending = list(self._state.datasets)
        if not pending:
            return
        self._jobs.submit(GroundTruthJob(pending, measure_key), lambda _: self.refresh())

    @Slot(bool)
    def _on_busy_changed(self, busy: bool) -> None:
        """Disable the compute button while a job runs."""
        self._compute_button.setEnabled(
            not busy and self._state.dataset_count > 0
        )

    def canvases(self) -> list[PlotCanvas]:
        """The plots of this tab, for the "export every plot" action."""
        return [self._curve_canvas, self._metrics_canvas]
