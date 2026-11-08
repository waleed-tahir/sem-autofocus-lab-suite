"""Tab 9: how far a search drifts when the frames get noisier.

Gaussian noise is added to every frame before it is scored, and the selected
searches are re-run at rising noise levels.  The reference peak stays the one
from the clean scan, so the plot really shows what noise costs in accuracy, not
where the peak of a noisy curve happens to be.

Main contents:
    * :class:`RobustnessTab` -- the sweep controls, the plot and the table.
"""

from __future__ import annotations

import logging
from typing import Optional

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import ALGORITHMS, algorithm_keys
from app.core.experiment import (
    JobOutcome,
    NoiseSweep,
    RobustnessJob,
    RunRequest,
    summarise_robustness,
)
from app.core.focus_measures import FOCUS_MEASURES
from app.core.focus_measures import keys as measure_keys
from app.core.run_result import RunResult
from app.plots.robustness import draw_robustness
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

#: Columns of the aggregated robustness table.
_COLUMNS = (
    "Algorithm", "Noise sigma", "Mean error (um)", "Worst error (um)",
    "Success rate (%)", "Runs",
)

#: Explanations shown when hovering the table headers.
_TOOLTIPS = (
    "Search strategy.",
    "Gaussian noise added to every frame, in grey levels.",
    "Mean distance from the clean reference peak.",
    "Worst distance over the repeats at this noise level.",
    "Share of repeats that landed within one frame of the reference peak.",
    "Repeats behind these numbers.",
)

#: Range of the highest noise level of the sweep, in grey levels.
_MAX_SIGMA_RANGE = (0.5, 80.0)

#: Name :class:`RobustnessJob` reports itself under, so this tab's progress bar
#: only reacts to its own job and not to one another tab started.
_JOB_NAME = RobustnessJob(
    RunRequest(datasets=(), algorithm_keys=(), measure_key=""), NoiseSweep()
).name


class RobustnessTab(QWidget):
    """Runs the selected searches over a range of injected noise levels."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Build the tab.

        Args:
            state: Shared application state.
            jobs: Service that runs the sweep in the worker thread.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._jobs = jobs
        self._results: list[RunResult] = []

        self._dataset_combo = QComboBox()
        self._measure_combo = QComboBox()
        self._algorithm_list = make_check_list(120)
        self._canvas = PlotCanvas("robustness", figure_size=(7.2, 5.6))
        self._table = make_table(_COLUMNS, _TOOLTIPS)
        self._build_controls()
        self._canvas.set_draw_callback(self._draw)

        self._build_layout()
        self._connect()
        self._fill_lists()
        self.refresh()

    def _build_controls(self) -> None:
        """Create the sweep controls and the run buttons."""
        self._max_sigma = QDoubleSpinBox()
        self._max_sigma.setRange(*_MAX_SIGMA_RANGE)
        self._max_sigma.setDecimals(1)
        self._max_sigma.setValue(12.0)
        self._max_sigma.setSingleStep(1.0)
        self._max_sigma.setToolTip("Highest noise level of the sweep, in grey levels.")

        self._steps = QSpinBox()
        self._steps.setRange(1, 20)
        self._steps.setValue(4)
        self._steps.setToolTip(
            "Noise levels above zero. The sweep always starts with a clean run."
        )

        self._repeats = QSpinBox()
        self._repeats.setRange(1, 20)
        self._repeats.setValue(3)
        self._repeats.setToolTip(
            "Runs per noise level, each with a different seed. More repeats make "
            "the success rate meaningful."
        )

        self._seed = QSpinBox()
        self._seed.setRange(0, 1_000_000)
        self._seed.setValue(0)
        self._seed.setToolTip("Seed of the first repeat, so the sweep can be redone.")

        self._run_button = QPushButton("Run robustness sweep")
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setEnabled(False)
        self._clear_button = QPushButton("Clear")

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setFormat("Idle")

        self._cost_hint = QLabel("")
        self._cost_hint.setWordWrap(True)
        self._cost_hint.setEnabled(False)

    def _build_layout(self) -> None:
        """Put the controls on the left, the plot above the table on the right."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_control_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def _build_control_panel(self) -> QWidget:
        """The selection and the sweep settings."""
        self._all_button = QPushButton("All")
        self._none_button = QPushButton("None")
        self._all_button.setMaximumWidth(70)
        self._none_button.setMaximumWidth(70)

        select_row = QHBoxLayout()
        select_row.addStretch(1)
        select_row.addWidget(self._all_button)
        select_row.addWidget(self._none_button)

        group = QGroupBox("Sweep")
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel("Image set:"))
        layout.addWidget(self._dataset_combo)
        layout.addWidget(QLabel("Focus measure:"))
        layout.addWidget(self._measure_combo)
        layout.addWidget(QLabel("Algorithms:"))
        layout.addWidget(self._algorithm_list, stretch=1)
        layout.addLayout(select_row)
        layout.addLayout(_labelled_row("Max noise sigma:", self._max_sigma))
        layout.addLayout(_labelled_row("Noise steps:", self._steps))
        layout.addLayout(_labelled_row("Repeats per level:", self._repeats))
        layout.addLayout(_labelled_row("Random seed:", self._seed))
        layout.addWidget(self._cost_hint)

        buttons = QHBoxLayout()
        buttons.addWidget(self._run_button)
        buttons.addWidget(self._cancel_button)
        buttons.addWidget(self._clear_button)
        layout.addLayout(buttons)
        layout.addWidget(self._progress)

        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)
        panel.setMaximumWidth(340)
        return panel

    def _build_output_panel(self) -> QWidget:
        """The plot above the aggregated table."""
        table_group = QGroupBox("Error and success rate per noise level")
        table_layout = QVBoxLayout(table_group)
        table_layout.addWidget(self._table)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._canvas)
        splitter.addWidget(table_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        return splitter

    def _connect(self) -> None:
        """Wire the controls, the plot and the shared state together."""
        self._run_button.clicked.connect(self._on_run)
        self._cancel_button.clicked.connect(self._jobs.cancel)
        self._clear_button.clicked.connect(self._on_clear)
        self._all_button.clicked.connect(lambda: set_all_checked(self._algorithm_list, True))
        self._none_button.clicked.connect(
            lambda: set_all_checked(self._algorithm_list, False)
        )
        for widget in (self._max_sigma, self._steps, self._repeats):
            widget.valueChanged.connect(self._update_cost_hint)
        self._algorithm_list.itemChanged.connect(self._update_cost_hint)

        self._state.datasets_changed.connect(self.refresh)
        self._jobs.progress.connect(self._on_progress)
        self._jobs.busy_changed.connect(self._on_busy_changed)

    def _fill_lists(self) -> None:
        """Fill the algorithm list and the focus-measure drop-down."""
        entries = [(key, ALGORITHMS[key].display_name) for key in algorithm_keys()]
        # The exhaustive scan would only measure the noise on the reference
        # itself, so the sweep starts with the sub-linear searches ticked.
        preselected = [key for key, _ in entries if key != "global_scan"]
        set_check_items(self._algorithm_list, entries, checked=preselected)

        self._measure_combo.blockSignals(True)
        for key in measure_keys():
            self._measure_combo.addItem(FOCUS_MEASURES[key].display_name, key)
        index = self._measure_combo.findData(self._state.measure_key)
        self._measure_combo.setCurrentIndex(max(0, index))
        self._measure_combo.blockSignals(False)

    @Slot()
    def refresh(self) -> None:
        """Rebuild the image-set drop-down and refresh the cost hint."""
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._update_cost_hint()
        self._run_button.setEnabled(
            self._state.dataset_count > 0 and not self._jobs.is_busy
        )

    @Slot()
    def _update_cost_hint(self) -> None:
        """Say up front how many runs the configured sweep will cost."""
        levels = self._steps.value() + 1
        runs = levels * self._repeats.value() * max(1, len(checked_keys(self._algorithm_list)))
        self._cost_hint.setText(
            f"This sweep performs {runs} search run(s): {levels} noise level(s) x "
            f"{self._repeats.value()} repeat(s) x "
            f"{len(checked_keys(self._algorithm_list))} algorithm(s)."
        )

    @Slot()
    def _on_run(self) -> None:
        """Start the configured sweep."""
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        algorithms = checked_keys(self._algorithm_list)
        if dataset is None or not algorithms:
            LOGGER.warning("Robustness sweep needs an image set and one algorithm.")
            return

        request = RunRequest(
            datasets=(dataset,),
            algorithm_keys=tuple(algorithms),
            measure_key=str(self._measure_combo.currentData()),
            params={key: dict(ALGORITHMS[key].defaults()) for key in algorithms},
            apply_fit=True,
        )
        sweep = NoiseSweep(
            max_sigma=self._max_sigma.value(),
            steps=self._steps.value(),
            repeats=self._repeats.value(),
            seed=self._seed.value(),
        )
        self._jobs.submit(RobustnessJob(request, sweep), self._on_outcome)

    def _on_outcome(self, outcome: JobOutcome) -> None:
        """Keep the sweep results locally and redraw.

        They stay out of the shared results table on purpose: a sweep produces
        dozens of near-identical runs, which would bury the real results.

        Args:
            outcome: What the sweep returned.
        """
        self._results = list(outcome.results)
        self._redraw()

    @Slot()
    def _on_clear(self) -> None:
        """Drop the sweep results of this tab."""
        self._results = []
        self._redraw()

    def _redraw(self) -> None:
        """Redraw the plot and refill the aggregated table."""
        points = summarise_robustness(self._results)
        self._canvas.redraw()
        fill_table(
            self._table,
            [
                (
                    text_cell(point.algorithm),
                    number_cell(point.noise_sigma, 2),
                    number_cell(point.mean_error_um, 2),
                    number_cell(point.max_error_um, 2),
                    number_cell(point.success_rate * 100.0, 1),
                    integer_cell(point.runs),
                )
                for point in points
            ],
        )

    def _draw(self, figure: Figure) -> None:
        """Draw the error and success-rate panels."""
        draw_robustness(figure, summarise_robustness(self._results))

    @Slot(int, int, str)
    def _on_progress(self, done: int, total: int, message: str) -> None:
        """Move this tab's progress bar along while its own job runs."""
        if self._jobs.job_name != _JOB_NAME:
            return
        self._progress.setRange(0, max(1, total))
        self._progress.setValue(done)
        self._progress.setFormat(f"{message}  ({done}/{total})")

    @Slot(bool)
    def _on_busy_changed(self, busy: bool) -> None:
        """Swap the run and cancel buttons while a job runs."""
        self._run_button.setEnabled(not busy and self._state.dataset_count > 0)
        self._cancel_button.setEnabled(busy)
        if not busy:
            self._progress.setRange(0, 1)
            self._progress.setValue(0)
            self._progress.setFormat("Idle")

    def canvases(self) -> list[PlotCanvas]:
        """The plots of this tab, for the "export every plot" action."""
        return [self._canvas]


def _labelled_row(text: str, widget: QWidget) -> QHBoxLayout:
    """Lay a label and its editor out in one row."""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(QLabel(text))
    row.addStretch(1)
    row.addWidget(widget)
    return row
