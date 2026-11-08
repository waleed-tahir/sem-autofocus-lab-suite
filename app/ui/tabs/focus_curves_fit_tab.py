"""Tab 3: Focus Curves & Fit unified workspace.

Integrates the global focus curve (with search trajectory probes) and the
zoomed fine-fit parabola into a single dual-view workspace with sub-tabs.
Reuses the battle-tested FocusCurveTab and FineFitTab cleanly.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.fine_fit_tab import FineFitTab
from app.ui.tabs.focus_curve_tab import FocusCurveTab
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)


class FocusCurvesAndFitTab(QWidget):
    """Combines global focus curve exploration with fine quadratic fit zoom."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._jobs = jobs

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self._subtabs = QTabWidget()
        self._subtabs.setObjectName("subTabs")

        # Tab A: Focus Curve Trajectories
        self.focus_curve_tab = FocusCurveTab(self._state, self._jobs)
        self._subtabs.addTab(self.focus_curve_tab, "Focus Curve")

        # Tab B: Zoomed Parabola Fit
        self.fine_fit_tab = FineFitTab(self._state)
        self._subtabs.addTab(self.fine_fit_tab, "Fine Fit")

        layout.addWidget(self._subtabs)

    @property
    def canvases(self) -> list[tuple[str, PlotCanvas]]:
        return [
            ("Focus Curve", self.focus_curve_tab._canvas),
            ("Fine Fit", self.fine_fit_tab._canvas),
        ]
