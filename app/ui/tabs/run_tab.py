"""Tab 2 (Left): Run selection, options, and execution controls.

Lab Submission Edition:
- Only 2 algorithms: Global Scan (exhaustive) and Gradient Search
- Only 2 focus measures: Normalized Variance and Mean-Normalized Variance
- Clean, open, organized layout without hidden collapsible accordions
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import (
    ALGORITHMS,
    DEFAULT_ALGORITHM_KEY,
    DEFAULT_HALF_WINDOW,
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
from app.ui.widgets.param_form import ParamForm

LOGGER = logging.getLogger(__name__)


def _button_row(left: QPushButton, right: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(left)
    row.addWidget(right)
    return row


class ClickableHeader(QFrame):
    """Header frame emitting clicked on mouse release."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class AccordionSection(QFrame):
    """A collapsible Fluent card with a clickable header and expandable content body."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        content_widget: QWidget,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._is_expanded = False
        self._content_widget = content_widget

        self.setObjectName("accordionSection")
        self.setStyleSheet(
            "QFrame#accordionSection { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; } "
            "QFrame#accordionSection:hover { border-color: #cbd5e1; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Clickable header
        self._header = ClickableHeader()
        self._header.setObjectName("accordionHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(
            "QFrame#accordionHeader { background-color: #f8fafc; border-radius: 5px; } "
            "QFrame#accordionHeader:hover { background-color: #f1f5f9; }"
        )
        h_lay = QHBoxLayout(self._header)
        h_lay.setContentsMargins(10, 8, 10, 8)
        h_lay.setSpacing(8)

        self._icon_lbl = QLabel("▶")
        self._icon_lbl.setStyleSheet("font-size: 9px; color: #64748b; font-weight: bold; min-width: 12px; background: transparent; border: none;")
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #1e293b; background: transparent; border: none;")
        self._title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet("font-size: 10.5px; color: #0284c7; font-weight: 500; background: transparent; border: none;")
        self._summary_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        h_lay.addWidget(self._icon_lbl)
        h_lay.addWidget(self._title_lbl)
        h_lay.addStretch(1)
        h_lay.addWidget(self._summary_lbl)

        # Divider between header and content when expanded
        self._divider = QFrame()
        self._divider.setObjectName("accordionDivider")
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setStyleSheet("QFrame#accordionDivider { background-color: #f1f5f9; max-height: 1px; border: none; }")

        # Content container (scoped with objectName so child widgets like QComboBox never inherit transparent background)
        self._content_container = QFrame()
        self._content_container.setObjectName("accordionContent")
        self._content_container.setStyleSheet("QFrame#accordionContent { background-color: transparent; border: none; }")
        c_lay = QVBoxLayout(self._content_container)
        c_lay.setContentsMargins(10, 8, 10, 10)
        c_lay.setSpacing(6)
        c_lay.addWidget(self._content_widget)

        layout.addWidget(self._header)
        layout.addWidget(self._divider)
        layout.addWidget(self._content_container)

        # Start collapsed by default
        self._divider.setVisible(False)
        self._content_container.setVisible(False)

        self._header.clicked.connect(self.toggle)

    def is_expanded(self) -> bool:
        return self._is_expanded

    def expand(self) -> None:
        if not self._is_expanded:
            self._is_expanded = True
            self._icon_lbl.setText("▼")
            self._header.setStyleSheet(
                "QFrame#accordionHeader { background-color: #f1f5f9; border-top-left-radius: 5px; border-top-right-radius: 5px; "
                "border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; } "
                "QFrame#accordionHeader:hover { background-color: #e2e8f0; }"
            )
            self._divider.setVisible(True)
            self._content_container.setVisible(True)
            self.toggled.emit(True)

    def collapse(self) -> None:
        if self._is_expanded:
            self._is_expanded = False
            self._icon_lbl.setText("▶")
            self._header.setStyleSheet(
                "QFrame#accordionHeader { background-color: #f8fafc; border-radius: 5px; } "
                "QFrame#accordionHeader:hover { background-color: #f1f5f9; }"
            )
            self._divider.setVisible(False)
            self._content_container.setVisible(False)
            self.toggled.emit(False)

    def toggle(self) -> None:
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def set_summary(self, text: str) -> None:
        self._summary_lbl.setText(text)


class RunTab(QWidget):
    """Clean single-column form for selecting and launching autofocus runs."""

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
        self._algorithm_list = make_check_list(65)

        self._build_widgets()
        self._build_layout()
        self._connect()

        self._fill_algorithm_list()
        self._fill_measure_combo()
        self.refresh_datasets()
        self._show_params_for(DEFAULT_ALGORITHM_KEY)
        self._update_all_summaries()

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

        self._apply_fit = QCheckBox("Apply quadratic parabola fit")
        self._apply_fit.setChecked(True)

        self._run_button = QPushButton("Start Search")
        self._run_button.setObjectName("primaryButton")
        self._run_button.setProperty("accent", True)
        self._run_button.setFixedHeight(32)

        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.setFixedHeight(32)
        self._cancel_button.setEnabled(False)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(14)
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setFormat("Idle")

        self._all_algorithms_button = QPushButton("All")
        self._all_algorithms_button.setFixedHeight(24)
        self._no_algorithms_button = QPushButton("None")
        self._no_algorithms_button.setFixedHeight(24)

    def _build_layout(self) -> None:
        """Arranges collapsible accordion cards: collapsed by default, expanding only one at a time."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 1. Target Image Set Content
        w_ds = QWidget()
        box_ds = QVBoxLayout(w_ds)
        box_ds.setContentsMargins(0, 2, 0, 2)
        box_ds.addWidget(self._dataset_combo)

        # 2. Search Algorithms Content
        w_algo = QWidget()
        box_algo = QVBoxLayout(w_algo)
        box_algo.setContentsMargins(0, 2, 0, 2)
        box_algo.setSpacing(4)
        box_algo.addWidget(self._algorithm_list)
        box_algo.addLayout(_button_row(self._all_algorithms_button, self._no_algorithms_button))

        # 3. Focus Measure Content
        w_m = QWidget()
        box_m = QVBoxLayout(w_m)
        box_m.setContentsMargins(0, 2, 0, 2)
        box_m.setSpacing(4)
        box_m.addWidget(self._measure_combo)
        box_m.addWidget(self._measure_hint)

        # 4. Parameters Content
        w_p = QWidget()
        box_p = QVBoxLayout(w_p)
        box_p.setContentsMargins(0, 2, 0, 2)
        box_p.setSpacing(4)
        box_p.addWidget(self._param_target)
        box_p.addWidget(self._algorithm_hint)
        box_p.addWidget(self._param_form)

        # 5. Quadratic Fit Content
        w_opt = QWidget()
        box_opt = QVBoxLayout(w_opt)
        box_opt.setContentsMargins(0, 4, 0, 4)
        box_opt.setSpacing(4)
        box_opt.addWidget(self._apply_fit)

        # Accordion Sections (collapsed by default, mutually exclusive)
        self._sec_ds = AccordionSection("Target Image Set", w_ds)
        self._sec_algo = AccordionSection("Search Algorithms", w_algo)
        self._sec_measure = AccordionSection("Focus Measure", w_m)
        self._sec_params = AccordionSection("Algorithm Parameters", w_p)
        self._sec_opts = AccordionSection("Quadratic Fit", w_opt)

        self._sections = [
            self._sec_ds,
            self._sec_algo,
            self._sec_measure,
            self._sec_params,
            self._sec_opts,
        ]

        for sec in self._sections:
            layout.addWidget(sec)

        layout.addSpacing(4)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.addWidget(self._run_button, 2)
        btn_layout.addWidget(self._cancel_button, 1)
        layout.addLayout(btn_layout)
        layout.addWidget(self._progress)
        layout.addStretch(1)

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

        # Accordion mutual-exclusion: opening one closes all others
        for sec in self._sections:
            sec.toggled.connect(lambda expanded, s=sec: self._on_section_toggled(s, expanded))

        # Live summary updates
        self._dataset_combo.currentIndexChanged.connect(self._update_ds_summary)
        self._measure_combo.currentIndexChanged.connect(self._update_measure_summary)
        self._param_target.currentIndexChanged.connect(self._update_param_summary)
        self._apply_fit.toggled.connect(self._update_opts_summary)
        self._all_algorithms_button.clicked.connect(self._update_algo_summary)
        self._no_algorithms_button.clicked.connect(self._update_algo_summary)

    def _on_section_toggled(self, section: AccordionSection, expanded: bool) -> None:
        if expanded:
            for s in self._sections:
                if s is not section:
                    s.collapse()

    def _update_all_summaries(self) -> None:
        self._update_ds_summary()
        self._update_algo_summary()
        self._update_measure_summary()
        self._update_param_summary()
        self._update_opts_summary()

    def _update_ds_summary(self) -> None:
        text = self._dataset_combo.currentText()
        short = text.split(" ")[0] if text else "—"
        self._sec_ds.set_summary(short)

    def _update_algo_summary(self) -> None:
        active = checked_keys(self._algorithm_list)
        total = len(ALGORITHMS)
        if len(active) == total:
            self._sec_algo.set_summary("All active")
        elif len(active) == 0:
            self._sec_algo.set_summary("None")
        else:
            self._sec_algo.set_summary(f"{len(active)} active")

    def _update_measure_summary(self) -> None:
        key = self._measure_combo.currentData()
        measure = FOCUS_MEASURES.get(str(key))
        if measure:
            self._sec_measure.set_summary(measure.display_name)

    def _update_param_summary(self) -> None:
        text = self._param_target.currentText()
        short = text.split(" ")[0] if text else "Global"
        self._sec_params.set_summary(short)

    def _update_opts_summary(self) -> None:
        fit_str = "Fit: On" if self._apply_fit.isChecked() else "Fit: Off"
        self._sec_opts.set_summary(fit_str)

    def _fill_algorithm_list(self) -> None:
        entries = [(key, ALGORITHMS[key].display_name) for key in algorithm_keys()]
        set_check_items(self._algorithm_list, entries)
        set_all_checked(self._algorithm_list, True)
        self._algorithm_list.model().dataChanged.connect(lambda *_: self._update_algo_summary())

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
            half_window=DEFAULT_HALF_WINDOW,
            noise_sigma=0.0,
            seed=None,
            repeats=1,
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
