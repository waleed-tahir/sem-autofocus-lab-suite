"""Tab 3: the outputs the assignment asks for.

For a chosen image set and algorithm this tab states, plainly and in one place:

* the coarse sharpest image, shown large, with its frame index, focus value and
  working distance;
* the fine sharpest position from the quadratic fit, as a fractional frame index
  and as a working distance, with the fit quality;
* a sortable table of every run of the session.

Main contents:
    * :class:`ResultsTab` -- the selectors, the large image, the summary and the
      results table.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.dataset import DatasetError
from app.core.export import export_results_csv, export_results_json
from app.core.run_result import RESULT_COLUMNS, RunResult, sort_results
from app.ui.app_state import AppState
from app.ui.tabs.common import (
    KEY_ROLE,
    InfoPanel,
    NumericItem,
    fill_table,
    make_table,
    refresh_algorithm_combo,
    refresh_dataset_combo,
)
from app.ui.widgets.image_viewer import ImageViewer

LOGGER = logging.getLogger(__name__)

#: Text shown while nothing has been run yet.
_NO_RUN_TEXT = "No run selected. Run an algorithm on the Run tab first."

#: Width the two summary panels need so their longest line fits without clipping.
SUMMARY_MIN_WIDTH = 320


class ResultsTab(QWidget):
    """Shows the required outputs of one run and the table of every run."""

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
        self._viewer = ImageViewer()
        self._caption = QLabel(_NO_RUN_TEXT)
        self._coarse_panel = InfoPanel()
        self._fine_panel = InfoPanel()
        self._table = make_table(
            [column.header for column in RESULT_COLUMNS],
            [column.tooltip for column in RESULT_COLUMNS],
        )
        self._clear_button = QPushButton("Clear all results")

        self._build_layout()
        self._connect()
        self.refresh()

    # ------------------------------------------------------------------ layout

    def _build_layout(self) -> None:
        """Put the single-run view above the table of every run."""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._build_single_run_panel())
        splitter.addWidget(self._build_table_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([480, 260])

        layout = QVBoxLayout(self)
        layout.addLayout(self._build_selector_row())
        layout.addWidget(splitter, stretch=1)

    def _build_selector_row(self) -> QHBoxLayout:
        """The image-set and algorithm drop-downs."""
        self._dataset_combo.setToolTip("Image set whose result is shown.")
        self._algorithm_combo.setToolTip("Algorithm whose result is shown.")

        row = QHBoxLayout()
        row.addWidget(QLabel("Image set:"))
        row.addWidget(self._dataset_combo, stretch=1)
        row.addSpacing(16)
        row.addWidget(QLabel("Algorithm:"))
        row.addWidget(self._algorithm_combo, stretch=1)
        row.addStretch(2)
        return row

    def _build_single_run_panel(self) -> QWidget:
        """The coarse image on the left, the two summaries on the right."""
        image_group = QGroupBox("Coarse sharpest image")
        self._caption.setWordWrap(True)
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout = QVBoxLayout(image_group)
        image_layout.addWidget(self._viewer, stretch=1)
        image_layout.addWidget(self._caption)

        coarse_group = QGroupBox("Coarse result (sharpest frame)")
        coarse_group.setMinimumHeight(210)
        coarse_layout = QVBoxLayout(coarse_group)
        coarse_layout.setContentsMargins(10, 14, 10, 10)
        coarse_layout.addWidget(self._coarse_panel)

        fine_group = QGroupBox("Fine result (quadratic fit)")
        fine_group.setMinimumHeight(210)
        fine_layout = QVBoxLayout(fine_group)
        fine_layout.setContentsMargins(10, 14, 10, 10)
        fine_layout.addWidget(self._fine_panel)

        summaries = QWidget()
        summary_layout = QVBoxLayout(summaries)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(coarse_group, stretch=1)
        summary_layout.addWidget(fine_group, stretch=1)
        summaries.setMinimumWidth(380)

        panel = QSplitter(Qt.Orientation.Horizontal)
        panel.addWidget(image_group)
        panel.addWidget(summaries)
        panel.setStretchFactor(0, 3)
        panel.setStretchFactor(1, 2)
        panel.setSizes([760, SUMMARY_MIN_WIDTH])
        return panel

    def _build_table_panel(self) -> QWidget:
        """The sortable table of every run of the session with export actions."""
        group = QGroupBox("All runs of this session (click a header to sort)")
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 4)

        export_csv_btn = QPushButton("Export CSV...")
        export_csv_btn.setFixedHeight(24)
        export_csv_btn.clicked.connect(self._export_csv)

        export_json_btn = QPushButton("Export JSON...")
        export_json_btn.setFixedHeight(24)
        export_json_btn.clicked.connect(self._export_json)

        buttons.addWidget(export_csv_btn)
        buttons.addWidget(export_json_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._clear_button)

        layout = QVBoxLayout(group)
        layout.addLayout(buttons)
        layout.addWidget(self._table, stretch=1)
        return group

    def _export_csv(self) -> None:
        if not self._state.results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results as CSV", "autofocus_results.csv", "CSV Files (*.csv)")
        if path:
            try:
                export_results_csv(path, self._state.results)
                QMessageBox.information(self, "Export Successful", f"Saved {len(self._state.results)} results to:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not write CSV:\n{e}")

    def _export_json(self) -> None:
        if not self._state.results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results as JSON", "autofocus_results.json", "JSON Files (*.json)")
        if path:
            try:
                export_results_json(path, self._state.results)
                QMessageBox.information(self, "Export Successful", f"Saved {len(self._state.results)} results to:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not write JSON:\n{e}")

    def _connect(self) -> None:
        """Wire the selectors, the table and the shared state together."""
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        self._algorithm_combo.currentIndexChanged.connect(self._update_single_run)
        self._table.itemSelectionChanged.connect(self._on_table_selection)
        self._clear_button.clicked.connect(self._state.clear_results)

        self._state.datasets_changed.connect(self.refresh)
        self._state.results_changed.connect(self.refresh)
        self._state.settings_changed.connect(self.refresh)
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
        self._update_single_run()

    # ----------------------------------------------------------------- refresh

    @Slot()
    def refresh(self) -> None:
        """Rebuild the selectors, the table and the single-run view."""
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._refresh_algorithm_combo()
        self._refresh_table()
        self._update_single_run()
        self._clear_button.setEnabled(bool(self._state.results))

    def _refresh_algorithm_combo(self) -> None:
        """Offer only the algorithms that have a result for this image set."""
        key = self._dataset_combo.currentData()
        results = self._state.results_for_dataset(str(key)) if key else []
        # Keys are de-duplicated while keeping the order the runs happened in.
        keys = list(dict.fromkeys(result.algorithm_key for result in results))
        refresh_algorithm_combo(self._algorithm_combo, keys)

    def _refresh_table(self) -> None:
        """Refill the table with every run of the session."""
        results = sort_results(self._state.results)
        rows = [
            tuple(
                (column.text_of(result), column.value_of(result))
                for column in RESULT_COLUMNS
            )
            for result in results
        ]
        keys = [f"{result.dataset_key}|{result.algorithm_key}" for result in results]
        fill_table(self._table, rows, keys)

    @Slot()
    def _on_dataset_changed(self) -> None:
        """Rebuild the algorithm list, then redraw the single-run view."""
        self._refresh_algorithm_combo()
        self._update_single_run()

    @Slot()
    def _on_table_selection(self) -> None:
        """Point the selectors at the run the user clicked in the table."""
        items = self._table.selectedItems()
        if not items:
            return
        first = self._table.item(items[0].row(), 0)
        if not isinstance(first, NumericItem):
            return

        stored = first.data(KEY_ROLE)
        if not stored or "|" not in str(stored):
            return

        dataset_key, algorithm_key = str(stored).split("|", 1)
        dataset_index = self._dataset_combo.findData(dataset_key)
        if dataset_index >= 0:
            self._dataset_combo.setCurrentIndex(dataset_index)
        algorithm_index = self._algorithm_combo.findData(algorithm_key)
        if algorithm_index >= 0:
            self._algorithm_combo.setCurrentIndex(algorithm_index)

    # ------------------------------------------------------------- single run

    def current_result(self) -> Optional[RunResult]:
        """Run the two selectors currently point at."""
        dataset_key = self._dataset_combo.currentData()
        algorithm_key = self._algorithm_combo.currentData()
        if not dataset_key or not algorithm_key:
            return None
        return self._state.result_for(str(dataset_key), str(algorithm_key))

    @Slot()
    def _update_single_run(self) -> None:
        """Redraw the image, the caption and the two summary panels."""
        result = self.current_result()
        if result is None:
            self._viewer.clear_frame()
            self._caption.setText(_NO_RUN_TEXT)
            self._coarse_panel.set_lines([_NO_RUN_TEXT])
            self._fine_panel.set_lines([])
            return

        self._show_coarse_frame(result)
        self._coarse_panel.set_lines(self._coarse_lines(result))
        self._fine_panel.set_lines(self._fine_lines(result))

    def _show_coarse_frame(self, result: RunResult) -> None:
        """Load and show the sharpest frame of a run."""
        dataset = self._state.dataset(result.dataset_key)
        if dataset is None:
            self._viewer.clear_frame()
            self._caption.setText(
                f"The image set '{result.dataset_label}' is no longer loaded."
            )
            return

        try:
            frame = dataset.frame(result.coarse_idx)
        except DatasetError as exc:
            LOGGER.error("Cannot show the coarse frame: %s", exc)
            self._viewer.clear_frame()
            self._caption.setText(f"Cannot read frame {result.coarse_idx}: {exc}")
            return

        self._viewer.set_frame(frame)
        self._caption.setText(
            f"<b>Frame {result.coarse_idx}</b> of {dataset.label} &nbsp;|&nbsp; "
            f"focus value <b>{result.coarse_value:.6f}</b> &nbsp;|&nbsp; "
            f"working distance <b>{result.coarse_wd_mm:.5f} mm</b>"
        )

    def _coarse_lines(self, result: RunResult) -> list[str]:
        """Build the coarse-result summary."""
        return [
            f"Algorithm:        {result.algorithm}",
            f"Focus measure:    {result.measure}",
            "",
            f"Sharpest frame:   {result.coarse_idx}",
            f"Focus value:      {result.coarse_value:.6f}",
            f"Working distance: {result.coarse_wd_mm:.5f} mm",
            "",
            f"Frames read:      {result.frames_evaluated}"
            f"   (search alone: {result.search_frames})",
            f"Score requests:   {result.eval_calls}",
            f"Run time:         {result.elapsed_ms:.1f} ms"
            + (f"   (mean of {result.repeats})" if result.repeats > 1 else ""),
            "",
            f"Reference frame:  {result.gt_idx}"
            f"   (position {_number(result.gt_reference_idx, 3)})",
            f"Coarse error:     {_number(result.coarse_error_frames, 3)} frames"
            f"   ({_number(result.coarse_error_um, 2)} um)",
            _verification_line(result),
        ]

    def _fine_lines(self, result: RunResult) -> list[str]:
        """Build the fine-result summary."""
        if result.fit_window is None:
            return [
                "No quadratic fit was applied to this run.",
                "",
                "Switch \"Apply the quadratic fit to every algorithm\" on,",
                "on the Run tab, and run the algorithm again.",
            ]

        lo, hi = result.fit_window
        source = "added by this application" if result.fit_applied_afterwards else (
            "returned by the algorithm"
        )
        lines = [
            f"Fine frame:       {_number(result.fine_idx, 3)}   (fractional index)",
            f"Fine WD:          {_number(result.fine_wd_mm, 5)} mm",
            f"Fitted value:     {_number(result.fine_value, 6)}",
            "",
            f"Fit status:       {result.fit_status}",
            f"Fit R2:           {_number(result.fit_r2, 5)}",
            f"Fit window:       frames {lo} to {hi}   ({hi - lo + 1} points)",
            f"Fit source:       {source}",
        ]
        if result.fit_coeffs is not None:
            a0, a1, a2 = result.fit_coeffs
            lines += [
                "",
                "f(d) = A0 + A1*d + A2*d^2",
                f"A0 = {a0:.6g}",
                f"A1 = {a1:.6g}",
                f"A2 = {a2:.6g}",
            ]
        lines += [
            "",
            f"Error vs reference: {_number(result.error_frames, 3)} frames"
            f"   ({_number(result.error_um, 2)} um)",
        ]
        return lines


def _number(value: float, decimals: int) -> str:
    """Format a number, printing a dash when it is unknown."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{value:.{decimals}f}"


def _verification_line(result: RunResult) -> str:
    """Describe the noise-floor check, which only the gradient search runs."""
    if result.verified is None:
        return "Peak check:       not applicable to this algorithm"
    state = "passed" if result.verified else "failed"
    return (
        f"Peak check:       {state}"
        f"   (restarts: {result.restarts}, "
        f"noise sigma: {_number(result.noise_sigma_estimate, 4)})"
    )
