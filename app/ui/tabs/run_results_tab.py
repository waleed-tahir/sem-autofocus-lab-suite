"""Tab 2: Run & Results unified workspace.

Combines the full RunTab execution engine (supporting all algorithms, parameters,
focus measures, options, and live worker logs) with the ResultsTab viewer
(sharpest image, numeric coarse/fine summaries, and sortable runs table)
in an efficient, compact 2-pane layout.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.results_tab import ResultsTab
from app.ui.tabs.run_tab import RunTab

LOGGER = logging.getLogger(__name__)


class RunAndResultsTab(QWidget):
    """Unified command and inspection center hosting Run controls and Results output."""

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
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)

        # 1. Left: Unified single-column RunTab controls in a scroll area with sticky action footer
        self.run_tab = RunTab(self._state, self._jobs)
        
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        run_scroll = QScrollArea()
        run_scroll.setWidget(self.run_tab)
        run_scroll.setWidgetResizable(True)
        run_scroll.setFrameShape(QFrame.Shape.NoFrame)

        left_container.setMinimumWidth(320)
        left_container.setMaximumWidth(420)
        left_layout.addWidget(run_scroll, stretch=1)

        # 2. Right: Complete ResultsTab
        self.results_tab = ResultsTab(self._state)

        self._splitter.addWidget(left_container)
        self._splitter.addWidget(self.results_tab)
        self._splitter.setSizes([340, 900])

        layout.addWidget(self._splitter)

    def _connect_signals(self) -> None:
        # When a run completes, automatically refresh the results view
        self.run_tab.results_ready.connect(self._on_results_ready)

    @Slot()
    def _on_results_ready(self) -> None:
        self.results_tab.refresh()

    @Slot()
    def start_run(self) -> None:
        """Triggered from menu or F5 accelerator."""
        self.run_tab.start_run()
