"""Tab 5: a zoom on the quadratic fit that produces the sub-frame position.

The coarse search can only name a whole frame.  The position the assignment asks
for comes from the parabola fitted through a window around that frame, and this
tab shows that step on its own: the measured points, the fitted curve, the
vertex, and the reference curve in the same window for comparison.

Main contents:
    * :class:`FineFitTab` -- the plot, the selectors and the numeric summary.
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
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.run_result import RunResult
from app.plots.quadratic_fit_plot import draw_quadratic_fit
from app.ui.app_state import AppState
from app.ui.tabs.common import (
    refresh_algorithm_combo,
    refresh_dataset_combo,
)
from app.ui.widgets.fit_details_card import FitDetailsCard
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

#: Width the details panel needs so its longest line fits without clipping.
SUMMARY_MIN_WIDTH = 420


class FineFitTab(QWidget):
    """Shows the fit window, the parabola and the vertex of one run."""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        """Build the tab.

        Args:
            state: Shared application state.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._state = state

        self._dataset_combo = QComboBox()
        self._algorithm_combo = QComboBox()
        self._canvas = PlotCanvas("fine_fit")
        self._card = FitDetailsCard()
        self._canvas.set_draw_callback(self._draw)

        self._build_layout()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        """Put the selectors on top, the plot beside the summary."""
        self._dataset_combo.setToolTip("Image set whose fit is shown.")
        self._algorithm_combo.setToolTip("Algorithm whose fit is shown.")

        selectors = QHBoxLayout()
        selectors.addWidget(QLabel("Image set:"))
        selectors.addWidget(self._dataset_combo, stretch=1)
        selectors.addSpacing(16)
        selectors.addWidget(QLabel("Algorithm:"))
        selectors.addWidget(self._algorithm_combo, stretch=1)
        selectors.addStretch(2)

        summary_group = QGroupBox("Fit KPI Summary & Details")
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(6, 6, 6, 6)
        summary_layout.addWidget(self._card)
        summary_group.setMinimumWidth(SUMMARY_MIN_WIDTH)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._canvas)
        splitter.addWidget(summary_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([900, SUMMARY_MIN_WIDTH])

        layout = QVBoxLayout(self)
        layout.addLayout(selectors)
        layout.addWidget(splitter, stretch=1)

    def _connect(self) -> None:
        """Wire the selectors and the shared state together."""
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        self._algorithm_combo.currentIndexChanged.connect(self._redraw)

        self._state.datasets_changed.connect(self.refresh)
        self._state.results_changed.connect(self.refresh)
        self._state.ground_truth_changed.connect(self._redraw)
        self._state.active_selection_changed.connect(self._on_active_selection_changed)

    @Slot(str, str)
    def _on_active_selection_changed(self, dataset_key: str, algorithm_key: str) -> None:
        """Pre-select the last run dataset and algorithm."""
        d_idx = self._dataset_combo.findData(dataset_key)
        if d_idx >= 0 and self._dataset_combo.currentIndex() != d_idx:
            self._dataset_combo.blockSignals(True)
            self._dataset_combo.setCurrentIndex(d_idx)
            self._dataset_combo.blockSignals(False)
            self._refresh_algorithm_combo()

        a_idx = self._algorithm_combo.findData(algorithm_key)
        if a_idx >= 0 and self._algorithm_combo.currentIndex() != a_idx:
            self._algorithm_combo.blockSignals(True)
            self._algorithm_combo.setCurrentIndex(a_idx)
            self._algorithm_combo.blockSignals(False)

        self._redraw()

    @Slot()
    def refresh(self) -> None:
        """Rebuild the selectors and redraw."""
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._refresh_algorithm_combo()
        self._redraw()

    def _refresh_algorithm_combo(self) -> None:
        """Offer only the runs of this image set that carry a fit."""
        key = self._dataset_combo.currentData()
        results = self._state.results_for_dataset(str(key)) if key else []
        keys = list(
            dict.fromkeys(
                result.algorithm_key for result in results if result.fit_window is not None
            )
        )
        refresh_algorithm_combo(self._algorithm_combo, keys)

    @Slot()
    def _on_dataset_changed(self) -> None:
        """Rebuild the algorithm list for the new image set and redraw."""
        self._refresh_algorithm_combo()
        self._redraw()

    def _current_result(self) -> Optional[RunResult]:
        """Run the two selectors point at."""
        dataset_key = self._dataset_combo.currentData()
        algorithm_key = self._algorithm_combo.currentData()
        if not dataset_key or not algorithm_key:
            return None
        return self._state.result_for(str(dataset_key), str(algorithm_key))

    @Slot()
    def _redraw(self) -> None:
        """Redraw the plot and refill the summary panel."""
        result = self._current_result()
        self._card.set_result(result)
        self._canvas.redraw()

    def _draw(self, figure: Figure) -> None:
        """Draw the fit of the selected run."""
        result = self._current_result()
        truth = (
            self._state.ground_truth_for(result.dataset_key, result.measure_key)
            if result is not None
            else None
        )
        draw_quadratic_fit(figure, result, truth)

    def canvases(self) -> list[PlotCanvas]:
        """The plots of this tab, for the "export every plot" action."""
        return [self._canvas]
