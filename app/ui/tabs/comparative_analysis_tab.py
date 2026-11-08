"""Tab 4: Comparative Analysis workspace.

Consolidates deep scientific comparison dimensions:
- Algorithm Cost vs. Error
- SEM Scan Speeds
- Focus Measure Functions
All accessible via compact nested sub-tabs with zero tab-bar crowding.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.algorithm_comparison_tab import AlgorithmComparisonTab
from app.ui.tabs.measure_comparison_tab import MeasureComparisonTab
from app.ui.tabs.speed_comparison_tab import SpeedComparisonTab
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)


class ComparativeAnalysisTab(QWidget):
    """Consolidated comparison suite with modern pill-style sub-tabs."""

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

        # 1. Algorithms Cost vs Error
        self.algo_tab = AlgorithmComparisonTab(self._state)
        self._subtabs.addTab(self.algo_tab, "Algorithms")

        # 2. Scanning Speeds
        self.speed_tab = SpeedComparisonTab(self._state, self._jobs)
        self._subtabs.addTab(self.speed_tab, "Scanning Speeds")

        # 3. Focus Measures
        self.measure_tab = MeasureComparisonTab(self._state, self._jobs)
        self._subtabs.addTab(self.measure_tab, "Focus Measures")

        layout.addWidget(self._subtabs)

    @property
    def canvases(self) -> list[tuple[str, PlotCanvas]]:
        all_c: list[tuple[str, PlotCanvas]] = []
        for tab in (self.algo_tab, self.speed_tab, self.measure_tab):
            if hasattr(tab, "canvases"):
                all_c.extend(tab.canvases)
            elif hasattr(tab, "_canvas"):
                all_c.append((tab.__class__.__name__, tab._canvas))
        return all_c

