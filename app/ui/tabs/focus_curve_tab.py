"""Tab 4: the focus curve.

Updated per user request:
- Review ONE algorithm at a time (via single-selection combo) to eliminate clutter and confusion.
- Step-by-step interactive replay controls (Play, Pause, Step Forward, Reset, Slider)
  to visualize how the search algorithm probes the focus curve step-by-step.
"""

from __future__ import annotations

import logging
from typing import Optional

from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.experiment import GroundTruthJob
from app.core.focus_measures import FOCUS_MEASURES, keys as measure_keys
from app.core.run_result import RunResult
from app.plots.focus_curve import draw_focus_curve
from app.ui.app_state import AppState
from app.ui.icons import get_fluent_icon
from app.ui.job_service import JobService
from app.ui.tabs.common import (
    refresh_algorithm_combo,
    refresh_dataset_combo,
)
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

CONTROL_PANEL_WIDTH = 340


class FocusCurveTab(QWidget):
    """Shows the focus curve with a single selected algorithm and animated step replay."""

    def __init__(
        self,
        state: AppState,
        jobs: JobService,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._state = state
        self._jobs = jobs

        self._dataset_combo = QComboBox()
        self._measure_combo = QComboBox()
        self._algorithm_combo = QComboBox()
        self._curve_canvas = PlotCanvas("focus_curve")
        self._status = QLabel("")
        self._compute_button = QPushButton("Compute reference curve")
        self._compute_button.setObjectName("primaryButton")
        self._compute_button.setProperty("accent", True)

        # Replay Animation State
        self._replay_timer = QTimer(self)
        self._replay_timer.setInterval(120)  # ms per probe step
        self._replay_timer.timeout.connect(self._on_replay_tick)
        self._replay_step: Optional[int] = None
        self._is_playing: bool = False

        self._curve_canvas.set_draw_callback(self._draw_curve)

        self._build_layout()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_controls())
        splitter.addWidget(self._curve_canvas)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def _build_controls(self) -> QWidget:
        self._dataset_combo.setToolTip("Image set whose focus curve is drawn.")
        self._measure_combo.setToolTip("Focus measure (variance / Laplacian operator) used to evaluate frames.")
        self._algorithm_combo.setToolTip("Select ONE algorithm at a time for clean, focused inspection.")
        self._status.setWordWrap(True)
        self._status.setEnabled(False)

        group = QGroupBox("Curve & Algorithm Selection")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)

        lbl_dataset = QLabel("Image Set")
        lbl_dataset.setStyleSheet("font-weight: 600; font-size: 11px; color: #424242;")
        layout.addWidget(lbl_dataset)
        layout.addWidget(self._dataset_combo)

        layout.addSpacing(2)
        lbl_measure = QLabel("Focus Measure")
        lbl_measure.setStyleSheet("font-weight: 600; font-size: 11px; color: #424242;")
        layout.addWidget(lbl_measure)
        layout.addWidget(self._measure_combo)

        layout.addSpacing(2)
        lbl_algo = QLabel("Search Algorithm")
        lbl_algo.setStyleSheet("font-weight: 600; font-size: 11px; color: #424242;")
        layout.addWidget(lbl_algo)
        layout.addWidget(self._algorithm_combo)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e5e5e5; background: #e5e5e5; max-height: 1px;")
        layout.addSpacing(4)
        layout.addWidget(line)
        layout.addSpacing(4)

        # Replay Controls Box
        replay_group = QGroupBox("Search Step Replay")
        replay_layout = QVBoxLayout(replay_group)
        replay_layout.setContentsMargins(10, 14, 10, 10)
        replay_layout.setSpacing(8)

        self._replay_label = QLabel("Probes: - / -")
        self._replay_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #0067c0; background: #ebf3fc; border-radius: 3px; padding: 2px 6px;"
        )
        replay_layout.addWidget(self._replay_label)

        self._replay_slider = QSlider(Qt.Orientation.Horizontal)
        self._replay_slider.setRange(0, 0)
        self._replay_slider.setValue(0)
        self._replay_slider.valueChanged.connect(self._on_slider_moved)
        replay_layout.addWidget(self._replay_slider)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._play_btn = QPushButton("Play")
        self._play_btn.setIcon(get_fluent_icon("play.png"))
        self._step_btn = QPushButton("Step")
        self._step_btn.setIcon(get_fluent_icon("step_forward.png"))
        self._reset_btn = QPushButton("Reset View")
        self._reset_btn.setIcon(get_fluent_icon("reset_view.png"))

        for btn in (self._play_btn, self._step_btn, self._reset_btn):
            btn.setFixedHeight(26)
            btn_row.addWidget(btn)

        self._play_btn.clicked.connect(self._toggle_play)
        self._step_btn.clicked.connect(self._step_forward)
        self._reset_btn.clicked.connect(self._reset_to_all)
        replay_layout.addLayout(btn_row)

        layout.addWidget(replay_group)

        layout.addSpacing(6)
        self._compute_button.setFixedHeight(28)
        layout.addWidget(self._compute_button)
        layout.addWidget(self._status)
        layout.addStretch(1)

        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)
        panel.setMaximumWidth(CONTROL_PANEL_WIDTH)
        return panel

    def _connect(self) -> None:
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_changed)
        self._measure_combo.currentIndexChanged.connect(self._on_measure_changed)
        self._algorithm_combo.currentIndexChanged.connect(self._on_algorithm_changed)
        self._compute_button.clicked.connect(self._on_compute)

        self._state.datasets_changed.connect(self.refresh)
        self._state.results_changed.connect(self.refresh)
        self._state.ground_truth_changed.connect(self._redraw)
        self._state.measure_changed.connect(self._sync_measure_combo)
        self._state.active_selection_changed.connect(self._on_active_selection_changed)
        self._jobs.busy_changed.connect(
            lambda busy: self._compute_button.setEnabled(not busy)
        )

    def _fill_measure_combo(self) -> None:
        self._measure_combo.blockSignals(True)
        self._measure_combo.clear()
        for key in measure_keys():
            self._measure_combo.addItem(FOCUS_MEASURES[key].display_name, key)
        index = self._measure_combo.findData(self._state.measure_key)
        self._measure_combo.setCurrentIndex(max(0, index))
        self._measure_combo.blockSignals(False)

    def _sync_measure_combo(self, key: str) -> None:
        index = self._measure_combo.findData(key)
        if index >= 0 and self._measure_combo.currentIndex() != index:
            self._measure_combo.blockSignals(True)
            self._measure_combo.setCurrentIndex(index)
            self._measure_combo.blockSignals(False)
        self._redraw()

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

        self._reset_replay_limits()
        self._redraw()

    @property
    def _selected_measure_key(self) -> str:
        data = self._measure_combo.currentData()
        return str(data) if data else self._state.measure_key

    @Slot()
    def _on_measure_changed(self) -> None:
        key = self._selected_measure_key
        self._state.set_measure(key)
        self._reset_replay_limits()
        self._redraw()

    @Slot()
    def refresh(self) -> None:
        self._fill_measure_combo()
        refresh_dataset_combo(self._dataset_combo, self._state)
        self._refresh_algorithm_combo()
        self._reset_replay_limits()
        self._redraw()

    def _refresh_algorithm_combo(self) -> None:
        key = self._dataset_combo.currentData()
        results = self._state.results_for_dataset(str(key)) if key else []
        keys = list(dict.fromkeys(result.algorithm_key for result in results))
        refresh_algorithm_combo(self._algorithm_combo, keys)

    @Slot()
    def _on_dataset_changed(self) -> None:
        self._refresh_algorithm_combo()
        self._reset_replay_limits()
        self._redraw()

    @Slot()
    def _on_algorithm_changed(self) -> None:
        self._reset_replay_limits()
        self._redraw()

    def _current_result(self) -> Optional[RunResult]:
        dataset_key = self._dataset_combo.currentData()
        algorithm_key = self._algorithm_combo.currentData()
        if not dataset_key or not algorithm_key:
            return None
        return self._state.result_for(str(dataset_key), str(algorithm_key))

    def _current_truth(self):
        key = self._dataset_combo.currentData()
        if not key:
            return None
        return self._state.ground_truth_for(str(key), self._selected_measure_key)

    def _reset_replay_limits(self) -> None:
        self._stop_animation()
        result = self._current_result()
        if result and result.visited:
            total = len(result.visited)
            self._replay_slider.setEnabled(True)
            self._replay_slider.blockSignals(True)
            self._replay_slider.setRange(1, total)
            self._replay_slider.setValue(total)
            self._replay_slider.blockSignals(False)
            self._replay_step = None  # None means full result
            self._replay_label.setText(f"Probes: {total} / {total} (Complete)")
            self._play_btn.setEnabled(True)
            self._step_btn.setEnabled(True)
            self._reset_btn.setEnabled(True)
        else:
            self._replay_slider.setEnabled(False)
            self._replay_slider.setRange(0, 0)
            self._replay_step = None
            self._replay_label.setText("Probes: - / -")
            self._play_btn.setEnabled(False)
            self._step_btn.setEnabled(False)
            self._reset_btn.setEnabled(False)

    def _stop_animation(self) -> None:
        self._is_playing = False
        self._replay_timer.stop()
        self._play_btn.setText("Play")
        self._play_btn.setIcon(get_fluent_icon("play.png"))

    @Slot()
    def _toggle_play(self) -> None:
        result = self._current_result()
        if not result or not result.visited:
            return

        total = len(result.visited)
        if self._is_playing:
            self._stop_animation()
        else:
            if self._replay_step is None or self._replay_step >= total:
                self._replay_step = 1
                self._replay_slider.blockSignals(True)
                self._replay_slider.setValue(1)
                self._replay_slider.blockSignals(False)

            self._is_playing = True
            self._play_btn.setText("Pause")
            self._play_btn.setIcon(get_fluent_icon("pause.png"))
            self._replay_timer.start()
            self._redraw()

    @Slot()
    def _on_replay_tick(self) -> None:
        result = self._current_result()
        if not result or not result.visited:
            self._stop_animation()
            return

        total = len(result.visited)
        curr = (self._replay_step or 1) + 1
        if curr > total:
            self._stop_animation()
            self._replay_step = None
            self._replay_slider.blockSignals(True)
            self._replay_slider.setValue(total)
            self._replay_slider.blockSignals(False)
            self._replay_label.setText(f"Probes: {total} / {total} (Complete)")
        else:
            self._replay_step = curr
            self._replay_slider.blockSignals(True)
            self._replay_slider.setValue(curr)
            self._replay_slider.blockSignals(False)
            self._replay_label.setText(f"Replay Probe: {curr} / {total}")
        self._curve_canvas.redraw()

    @Slot()
    def _step_forward(self) -> None:
        self._stop_animation()
        result = self._current_result()
        if not result or not result.visited:
            return
        total = len(result.visited)
        curr = (self._replay_step or 0) + 1
        if curr > total:
            curr = total
            self._replay_step = None
        else:
            self._replay_step = curr
        self._replay_slider.blockSignals(True)
        self._replay_slider.setValue(curr)
        self._replay_slider.blockSignals(False)
        self._replay_label.setText(f"Replay Probe: {curr} / {total}")
        self._curve_canvas.redraw()

    @Slot()
    def _reset_to_all(self) -> None:
        self._stop_animation()
        result = self._current_result()
        if result and result.visited:
            total = len(result.visited)
            self._replay_step = None
            self._replay_slider.blockSignals(True)
            self._replay_slider.setValue(total)
            self._replay_slider.blockSignals(False)
            self._replay_label.setText(f"Probes: {total} / {total} (Complete)")
        self._curve_canvas.redraw()

    @Slot(int)
    def _on_slider_moved(self, value: int) -> None:
        self._stop_animation()
        result = self._current_result()
        if not result or not result.visited:
            return
        total = len(result.visited)
        if value >= total:
            self._replay_step = None
            self._replay_label.setText(f"Probes: {total} / {total} (Complete)")
        else:
            self._replay_step = value
            self._replay_label.setText(f"Replay Probe: {value} / {total}")
        self._curve_canvas.redraw()

    @Slot()
    def _redraw(self) -> None:
        truth = self._current_truth()
        self._compute_button.setEnabled(
            truth is None and bool(self._dataset_combo.currentData())
            and not self._jobs.is_busy
        )
        if truth is None:
            self._status.setText(
                "No reference curve for this image set yet. "
                "Click 'Compute reference curve' or run a search."
            )
        else:
            self._status.setText(
                f"Reference peak: frame {truth.peak_idx}, "
                f"WD {truth.reference_wd_mm:.4f} mm."
            )
        self._curve_canvas.redraw()

    def _draw_curve(self, figure: Figure) -> None:
        result = self._current_result()
        results = [result] if result is not None else []
        draw_focus_curve(
            figure,
            self._current_truth(),
            results,
            replay_step=self._replay_step,
        )

    @Slot()
    def _on_compute(self) -> None:
        key = self._dataset_combo.currentData()
        dataset = self._state.dataset(str(key)) if key else None
        if dataset is None:
            return
        self._jobs.submit(
            GroundTruthJob([dataset], self._selected_measure_key),
            lambda _: self._redraw(),
        )

    def canvases(self) -> list[PlotCanvas]:
        return [self._curve_canvas]
