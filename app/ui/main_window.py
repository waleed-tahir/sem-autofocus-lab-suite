"""Native Main Window for Static Autofocusing Lab (Lab Submission Edition).

Features a streamlined 4-tab workflow:
1. Datasets: image stack loading & inspection
2. Run & Results: search controls, sharpest image, and runs table
3. Focus Curve: full focal curve with probe replay
4. Algorithm Comparison: Global Scan vs Gradient Search trade-offs
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTabWidget,
    QWidget,
)

from app import APP_NAME, APP_VERSION
from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.algorithm_comparison_tab import AlgorithmComparisonTab
from app.ui.tabs.datasets_tab import DatasetsTab
from app.ui.tabs.export_tab import ExportTab
from app.ui.tabs.focus_curve_tab import FocusCurveTab
from app.ui.tabs.run_results_tab import RunAndResultsTab
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

DEFAULT_WINDOW_SIZE = (1240, 740)


class MainWindow(QMainWindow):
    """Native Main Window for Autofocus Lab Suite."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(*DEFAULT_WINDOW_SIZE)

        self._state = AppState(self)
        self._jobs = JobService(self._state, self)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("mainTabs")

        self._build_tabs()
        self._build_status_bar()
        self._setup_shortcuts()
        self._connect()

        self.setMenuBar(None)
        self.setCentralWidget(self._tabs)
        self._update_status()
        self._maybe_load_default_datasets()

    def _maybe_load_default_datasets(self) -> None:
        """Auto-load sample datasets if a 'datasets' folder exists adjacent to the app or project root."""
        import sys
        from pathlib import Path
        from app.core.dataset import discover_image_folders

        candidates = [
            Path(sys.executable).parent / "datasets",
            Path(__file__).resolve().parents[2] / "datasets",
            Path("datasets"),
        ]
        for candidate in candidates:
            if candidate.is_dir():
                folders = discover_image_folders(candidate)
                if folders:
                    loaded, _ = self._state.add_datasets(folders)
                    for ds in loaded:
                        self.datasets_tab._maybe_preload(ds)
                    if loaded:
                        self.datasets_tab._select_dataset(loaded[0].key)
                    break

    def _build_tabs(self) -> None:
        """Create the streamlined 4-tab workflows."""
        # Tab 1: Datasets (stack loading, geometry, frame inspection)
        self.datasets_tab = DatasetsTab(self._state)

        # Tab 2: Run & Results (unified execution + output)
        self.run_results_tab = RunAndResultsTab(self._state, self._jobs)

        # Tab 3: Focus Curve (complete focal curve + step replay)
        self.focus_curve_tab = FocusCurveTab(self._state, self._jobs)

        # Tab 4: Algorithm Comparison (Global scan vs Gradient search trade-offs)
        self.algo_comparison_tab = AlgorithmComparisonTab(self._state)

        # Export Tab instance to handle session & CSV export dialogs cleanly
        self.export_tab = ExportTab(self._state, self.all_canvases)

        # Add 4 main tabs with clean titles and descriptive tooltips
        for widget, title, tooltip in (
            (self.datasets_tab, "Datasets", "Load image sets, calibrate geometry, and inspect frames."),
            (self.run_results_tab, "Run && Results", "Unified command center: choose algorithms, execute, and view sharpest image & table."),
            (self.focus_curve_tab, "Focus Curve", "Focal curve trajectory and step-by-step search replay."),
            (self.algo_comparison_tab, "Algorithm Comparison", "Performance, frame savings, and error comparison between Global Scan and Gradient Search."),
        ):
            idx = self._tabs.addTab(widget, title)
            self._tabs.setTabToolTip(idx, tooltip)

    def _build_status_bar(self) -> None:
        self._status_label = QLabel("Ready")
        self._status_progress = QProgressBar()
        self._status_progress.setMaximumWidth(220)
        self._status_progress.setFixedHeight(12)
        self._status_progress.setRange(0, 1)
        self._status_progress.setVisible(False)

        bar = self.statusBar()
        bar.addPermanentWidget(self._status_progress)
        bar.addPermanentWidget(self._status_label)

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts directly on the window."""
        self.addAction(self._action("Add Folder", self.datasets_tab.add_folder_dialog, "Ctrl+O"))
        self.addAction(self._action("Run Selected", self.run_results_tab.start_run, "F5"))
        self.addAction(self._action("Cancel", self._jobs.cancel, "Esc"))
        self.addAction(self._action("Go to Datasets", lambda: self._tabs.setCurrentIndex(0), "Ctrl+1"))
        self.addAction(self._action("Go to Run & Results", lambda: self._tabs.setCurrentIndex(1), "Ctrl+2"))
        self.addAction(self._action("Go to Focus Curve", lambda: self._tabs.setCurrentIndex(2), "Ctrl+3"))
        self.addAction(self._action("Go to Algorithm Comparison", lambda: self._tabs.setCurrentIndex(3), "Ctrl+4"))
        self.addAction(self._action("Quit", self.close, "Ctrl+Q"))

    def _action(self, text: str, slot, shortcut: str = "") -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(shortcut)
        return action

    def _connect(self) -> None:
        self._state.datasets_changed.connect(self._update_status)
        self._state.results_changed.connect(self._update_status)
        self._jobs.busy_changed.connect(self._on_busy_changed)
        self._jobs.progress.connect(self._on_job_progress)
        self._jobs.message.connect(self._on_job_message)
        self.export_tab.session_loaded.connect(self._on_session_loaded)

    def _update_status(self) -> None:
        nd = self._state.dataset_count
        nr = len(self._state.results)
        self._status_label.setText(f"{nd} dataset{'s' if nd != 1 else ''} loaded  |  {nr} run result{'s' if nr != 1 else ''}")

    @Slot(bool)
    def _on_busy_changed(self, busy: bool) -> None:
        self._status_progress.setVisible(busy)
        if not busy:
            self._update_status()

    @Slot(str)
    def _on_job_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 3000)

    @Slot(int, int, str)
    def _on_job_progress(self, current: int, total: int, message: str) -> None:
        self._status_progress.setRange(0, max(1, total))
        self._status_progress.setValue(current)
        self.statusBar().showMessage(message, 3000)

    @Slot(object)
    def _on_session_loaded(self, session) -> None:
        self._state.clear_results()
        self._state.clear_datasets()
        self._update_status()

    def all_canvases(self) -> list[tuple[str, PlotCanvas]]:
        return [("Focus Curve", self.focus_curve_tab._curve_canvas)]

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<b>{APP_NAME} {APP_VERSION}</b><br>"
            f"<i>Lab Submission Edition</i><br><br>"
            f"Optimized for scanning electron microscopy autofocusing evaluation.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._jobs.is_busy:
            self._jobs.cancel()
        event.accept()
