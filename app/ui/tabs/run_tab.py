"""Tab 2: Run selection, options, and execution controls.

Organized into clean, full-width collapsible accordion cards:
- Starts with all sections collapsed.
- Exclusive accordion behavior: opening one automatically closes any other open section.
- Fixed border styling across the entire column width.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import (
    ALGORITHMS,
    DEFAULT_ALGORITHM_KEY,
    MIN_HALF_WINDOW,
    algorithm_keys,
)
from app.core.experiment import AlgorithmRunJob, JobOutcome, RunRequest
from app.core.focus_measures import FOCUS_MEASURES
from app.core.focus_measures import keys as measure_keys
from app.ui.app_state import AppState
from app.ui.job_service import JobService
from app.ui.tabs.common import (
    checked_keys,
    make_check_list,
    set_all_checked,
    set_check_items,
)
from app.ui.widgets.collapsible_section import CollapsibleSection
from app.ui.widgets.param_form import ParamForm

LOGGER = logging.getLogger(__name__)

_NOISE_RANGE = (0.0, 50.0)
_REPEAT_RANGE = (1, 20)


def _labelled_row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setStyleSheet("color: #5e5e5e; font-size: 11px;")
    row.addWidget(lbl)
    row.addWidget(widget)
    return row


def _button_row(left: QPushButton, right: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(left)
    row.addWidget(right)
    return row


class RunTab(QWidget):
    """Clean single-column form with exclusive single-open accordion sections."""

    results_ready = Signal()

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._jobs = jobs
        self._params: dict[str, dict[str, Any]] = {
            key: spec.defaults() for key, spec in ALGORITHMS.items()
        }

        self._dataset_combo = QComboBox()
        self._algorithm_list = make_check_list(110)
        self._sections: list[CollapsibleSection] = []

        self._build_widgets()
        self._build_layout()
        self._connect()

        self._fill_algorithm_list()
        self._fill_measure_combo()
        self.refresh_datasets()
        self._show_params_for(DEFAULT_ALGORITHM_KEY)

    def _build_widgets(self) -> None:
        self._measure_combo = QComboBox()
        self._measure_hint = QLabel("")
        self._measure_hint.setWordWrap(True)
        self._measure_hint.setStyleSheet("color: #5e5e5e; font-size: 10.5px;")

        self._param_target = QComboBox()
        self._param_form = ParamForm()
        self._algorithm_hint = QLabel("")
        self._algorithm_hint.setWordWrap(True)
        self._algorithm_hint.setStyleSheet("color: #5e5e5e; font-size: 10.5px;")

        self._apply_fit = QCheckBox("Apply quadratic parabola fit to all")
        self._apply_fit.setChecked(True)

        self._half_window = QSpinBox()
        self._half_window.setRange(MIN_HALF_WINDOW, 100)
        self._half_window.setValue(12)
        self._half_window.setSuffix(" frames")

        self._noise_sigma = QDoubleSpinBox()
        self._noise_sigma.setRange(*_NOISE_RANGE)
        self._noise_sigma.setDecimals(2)
        self._noise_sigma.setSingleStep(0.5)

        self._seed = QSpinBox()
        self._seed.setRange(0, 1_000_000)
        self._seed.setValue(0)

        self._repeats = QSpinBox()
        self._repeats.setRange(*_REPEAT_RANGE)
        self._repeats.setValue(1)

        self._run_button = QPushButton("Start Search")
        self._run_button.setObjectName("primaryButton")
        self._run_button.setProperty("accent", True)
        self._run_button.setFixedHeight(30)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setFixedHeight(30)
        self._cancel_button.setEnabled(False)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(12)
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setFormat("Idle")

        self._all_algorithms_button = QPushButton("All")
        self._no_algorithms_button = QPushButton("None")

    def _build_layout(self) -> None:
        """Arranges sections into a full-width exclusive accordion."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Target Image Set (Single selection)
        ds_content = QWidget()
        ds_box = QVBoxLayout(ds_content)
        ds_box.setContentsMargins(0, 0, 0, 0)
        ds_box.setSpacing(4)
        self._dataset_combo.setToolTip("Target image set to autofocus.")
        ds_box.addWidget(self._dataset_combo)
        self.sec_datasets = CollapsibleSection("Target Image Set", ds_content, initially_expanded=False)

        # 2. Search Algorithms
        algo_content = QWidget()
        algo_box = QVBoxLayout(algo_content)
        algo_box.setContentsMargins(0, 0, 0, 0)
        algo_box.setSpacing(4)
        algo_box.addWidget(self._algorithm_list)
        algo_box.addLayout(_button_row(self._all_algorithms_button, self._no_algorithms_button))
        self.sec_algos = CollapsibleSection("Search Algorithms", algo_content, initially_expanded=False)

        # 3. Focus Measure
        m_content = QWidget()
        m_box = QVBoxLayout(m_content)
        m_box.setContentsMargins(0, 0, 0, 0)
        m_box.setSpacing(4)
        m_box.addWidget(self._measure_combo)
        m_box.addWidget(self._measure_hint)
        self.sec_measure = CollapsibleSection("Focus Measure", m_content, initially_expanded=False)

        # 4. Parameters
        p_content = QWidget()
        p_box = QVBoxLayout(p_content)
        p_box.setContentsMargins(0, 0, 0, 0)
        p_box.setSpacing(4)
        p_box.addWidget(self._param_target)
        p_box.addWidget(self._algorithm_hint)
        p_box.addWidget(self._param_form)
        self.sec_params = CollapsibleSection("Algorithm Parameters", p_content, initially_expanded=False)

        # 5. Options
        opt_content = QWidget()
        opt_box = QVBoxLayout(opt_content)
        opt_box.setContentsMargins(0, 0, 0, 0)
        opt_box.setSpacing(4)
        opt_box.addWidget(self._apply_fit)
        opt_box.addLayout(_labelled_row("Fit half window:", self._half_window))
        opt_box.addLayout(_labelled_row("Noise sigma (σ):", self._noise_sigma))
        opt_box.addLayout(_labelled_row("Random seed:", self._seed))
        opt_box.addLayout(_labelled_row("Repeats (mean):", self._repeats))
        self.sec_options = CollapsibleSection("Execution Options", opt_content, initially_expanded=False)

        self._sections = [
            self.sec_datasets,
            self.sec_algos,
            self.sec_measure,
            self.sec_params,
            self.sec_options,
        ]

        # Register mutual exclusion (only one expanded at a time)
        for sec in self._sections:
            layout.addWidget(sec)
            sec.toggled.connect(self._make_exclusive_handler(sec))

        # Bottom Action Bar (always visible)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._run_button, 2)
        btn_layout.addWidget(self._cancel_button, 1)
        layout.addLayout(btn_layout)
        layout.addWidget(self._progress)
        layout.addStretch(1)

    def _make_exclusive_handler(self, active_sec: CollapsibleSection):
        def handler(expanded: bool) -> None:
            if expanded:
                for other in self._sections:
                    if other is not active_sec and other.is_expanded:
                        other.set_expanded(False)
        return handler

    def _connect(self) -> None:
        self._run_button.clicked.connect(self.start_run)
        self._cancel_button.clicked.connect(self._jobs.cancel)
        self._all_algorithms_button.clicked.connect(lambda: set_all_checked(self._algorithm_list, True))
        self._no_algorithms_button.clicked.connect(lambda: set_all_checked(self._algorithm_list, False))

        self._measure_combo.currentIndexChanged.connect(self._on_measure_changed)
        self._param_target.currentIndexChanged.connect(self._on_param_target_changed)
        self._param_form.values_changed.connect(self._on_params_changed)

        self._state.datasets_changed.connect(self.refresh_datasets)
        self._jobs.progress.connect(self._on_progress)
        self._jobs.busy_changed.connect(self._on_busy_changed)

    def _fill_algorithm_list(self) -> None:
        entries = [(key, ALGORITHMS[key].display_name) for key in algorithm_keys()]
        set_check_items(self._algorithm_list, entries)
        set_all_checked(self._algorithm_list, True)

        self._param_target.blockSignals(True)
        self._param_target.clear()
        for key, name in entries:
            self._param_target.addItem(name, key)
        self._param_target.blockSignals(False)

    def _fill_measure_combo(self) -> None:
        self._measure_combo.blockSignals(True)
        self._measure_combo.clear()
        for key in measure_keys():
            self._measure_combo.addItem(FOCUS_MEASURES[key].display_name, key)
        idx = self._measure_combo.findData(self._state.measure_key)
        self._measure_combo.setCurrentIndex(max(0, idx))
        self._measure_combo.blockSignals(False)
        self._update_measure_hint()

    @Slot()
    def refresh_datasets(self) -> None:
        self._dataset_combo.blockSignals(True)
        current = self._dataset_combo.currentData() or self._state.last_dataset_key
        self._dataset_combo.clear()
        for dataset in self._state.datasets:
            label = (
                f"{dataset.label} ({dataset.frame_count} fr"
                + (f", spd {dataset.speed}" if dataset.speed is not None else "") + ")"
            )
            self._dataset_combo.addItem(label, dataset.key)
        index = self._dataset_combo.findData(current) if current else 0
        if index >= 0:
            self._dataset_combo.setCurrentIndex(index)
        self._dataset_combo.blockSignals(False)
        self._run_button.setEnabled(self._dataset_combo.count() > 0 and not self._jobs.is_busy)

    @Slot()
    def _on_measure_changed(self) -> None:
        key = self._measure_combo.currentData()
        if key:
            self._state.set_measure_key(str(key))
        self._update_measure_hint()

    def _update_measure_hint(self) -> None:
        key = self._measure_combo.currentData()
        measure = FOCUS_MEASURES.get(str(key)) if key else None
        if measure is None:
            self._measure_hint.setText("")
            return
        self._measure_hint.setText(f"{measure.formula} — {measure.description}")

    @Slot()
    def _on_param_target_changed(self) -> None:
        key = self._param_target.currentData()
        if key:
            self._show_params_for(str(key))

    def _show_params_for(self, key: str) -> None:
        spec = ALGORITHMS.get(key)
        if spec is None:
            return
        self._algorithm_hint.setText(spec.description)
        self._param_form.set_specs(spec.params)
        self._param_form.set_values(self._params.get(key, spec.defaults()))

    @Slot(dict)
    def _on_params_changed(self, values: dict) -> None:
        key = self._param_target.currentData()
        if key:
            self._params[str(key)] = dict(values)

    @Slot()
    def start_run(self) -> None:
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        if dataset is None:
            return
        datasets = [dataset]
        algorithms = checked_keys(self._algorithm_list)
        if not algorithms:
            return

        request = self.build_request(datasets, algorithms)
        self._jobs.submit(AlgorithmRunJob(request), self._on_outcome)

    def build_request(self, datasets, algorithms) -> RunRequest:
        return RunRequest(
            datasets=tuple(datasets),
            algorithm_keys=tuple(algorithms),
            measure_key=str(self._measure_combo.currentData()),
            params={key: dict(self._params.get(key, {})) for key in algorithms},
            apply_fit=self._apply_fit.isChecked(),
            half_window=self._half_window.value(),
            noise_sigma=self._noise_sigma.value(),
            seed=self._seed.value(),
            repeats=self._repeats.value(),
        )

    def selected_algorithm_keys(self) -> list[str]:
        return checked_keys(self._algorithm_list)

    def parameters(self) -> dict[str, dict[str, Any]]:
        return {key: dict(values) for key, values in self._params.items()}

    def _on_outcome(self, outcome: JobOutcome) -> None:
        self._state.add_results(outcome.results)
        if outcome.results:
            self.results_ready.emit()

    @Slot(int, int, str)
    def _on_progress(self, done: int, total: int, message: str) -> None:
        self._progress.setRange(0, max(1, total))
        self._progress.setValue(done)
        self._progress.setFormat(f"{message} ({done}/{total})")

    @Slot(bool)
    def _on_busy_changed(self, busy: bool) -> None:
        self._run_button.setEnabled(not busy and self._state.dataset_count > 0)
        self._cancel_button.setEnabled(busy)
        if not busy:
            self._progress.setFormat("Idle")
