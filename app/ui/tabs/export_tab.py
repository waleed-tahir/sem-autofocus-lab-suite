"""Tab 10: get the results out of the application.

Three kinds of export live here: the result records as CSV and JSON, every plot
of the session as a 300 dpi PNG, and the whole session as one JSON file that can
be loaded again later.  A session file stores only the image-set paths, never the
frames, so it stays small.

Main contents:
    * :class:`ExportTab` -- the export buttons and the session actions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional, Sequence

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.export import (
    EXPORT_DPI,
    ExportError,
    SessionData,
    SessionDataset,
    export_results_csv,
    export_results_json,
    load_session,
    safe_stem,
    save_session,
    suggest_filename,
)
from app.ui.app_state import AppState
from app.ui.tabs.common import InfoPanel
from app.ui.widgets.plot_canvas import PlotCanvas

LOGGER = logging.getLogger(__name__)

#: Signature of the callback that collects every canvas of the window.
CanvasProvider = Callable[[], Sequence[tuple[str, PlotCanvas]]]


class ExportTab(QWidget):
    """Exports results, plots and the whole session.

    Signals:
        session_loaded: A session file was read; the window applies it.
    """

    session_loaded = Signal(object)

    def __init__(
        self,
        state: AppState,
        canvas_provider: CanvasProvider,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Build the tab.

        Args:
            state: Shared application state.
            canvas_provider: Returns ``(name, canvas)`` for every plot of the
                window, so "export every plot" needs no knowledge of the tabs.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._canvas_provider = canvas_provider
        self._session_params: dict[str, dict] = {}
        self._session_algorithms: tuple[str, ...] = ()

        self._summary = InfoPanel()
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(140)
        self._log.setPlaceholderText("Exported files are listed here.")

        self._build_layout()
        self._connect()
        self.refresh()

    def _build_layout(self) -> None:
        """Stack the three export groups above the log."""
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_summary_group())
        layout.addWidget(self._build_results_group())
        layout.addWidget(self._build_plots_group())
        layout.addWidget(self._build_session_group())
        layout.addWidget(self._build_log_group())
        layout.addStretch(1)

    def _build_summary_group(self) -> QGroupBox:
        """What the session currently holds."""
        group = QGroupBox("This session")
        self._summary.setMaximumHeight(90)
        layout = QVBoxLayout(group)
        layout.addWidget(self._summary)
        return group

    def _build_results_group(self) -> QGroupBox:
        """CSV and JSON export of the result records."""
        self._csv_button = QPushButton("Export results as CSV...")
        self._csv_button.setToolTip("One row per run, with every column of the results table.")
        self._json_button = QPushButton("Export results as JSON...")
        self._json_button.setToolTip(
            "The same rows plus the visited frames and the fitted points, so a "
            "plot can be rebuilt outside this application."
        )

        group = QGroupBox("Results")
        row = QHBoxLayout(group)
        row.addWidget(self._csv_button)
        row.addWidget(self._json_button)
        row.addStretch(1)
        return group

    def _build_plots_group(self) -> QGroupBox:
        """PNG export of every plot of the window."""
        self._plots_button = QPushButton("Export every plot as PNG...")
        self._plots_button.setToolTip(
            f"Save every plot of every tab into one folder, at {EXPORT_DPI} dpi."
        )
        hint = QLabel(
            "Each plot is also saveable on its own, with the \"Save PNG...\" "
            "button above it."
        )
        hint.setEnabled(False)

        group = QGroupBox("Plots")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(self._plots_button)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(hint)
        return group

    def _build_session_group(self) -> QGroupBox:
        """Save and load the whole session."""
        self._save_session_button = QPushButton("Save session...")
        self._save_session_button.setToolTip(
            "Store the image-set paths, the settings and the results in one JSON file."
        )
        self._load_session_button = QPushButton("Load session...")
        self._load_session_button.setToolTip(
            "Reload the image sets and settings of a saved session."
        )

        group = QGroupBox("Session")
        row = QHBoxLayout(group)
        row.addWidget(self._save_session_button)
        row.addWidget(self._load_session_button)
        row.addStretch(1)
        return group

    def _build_log_group(self) -> QGroupBox:
        """The list of files written so far."""
        group = QGroupBox("Export log")
        layout = QVBoxLayout(group)
        layout.addWidget(self._log)
        return group

    def _connect(self) -> None:
        """Wire the buttons and the shared state together."""
        self._csv_button.clicked.connect(self.export_csv_dialog)
        self._json_button.clicked.connect(self.export_json_dialog)
        self._plots_button.clicked.connect(self.export_plots_dialog)
        self._save_session_button.clicked.connect(self.save_session_dialog)
        self._load_session_button.clicked.connect(self.load_session_dialog)

        self._state.datasets_changed.connect(self.refresh)
        self._state.results_changed.connect(self.refresh)
        self._state.settings_changed.connect(self.refresh)
        # Without this the reference-curve count on this tab would go stale as
        # soon as another tab computed one.
        self._state.ground_truth_changed.connect(self.refresh)

    # ----------------------------------------------------------------- display

    @Slot()
    def refresh(self) -> None:
        """Describe the session and enable only what is possible."""
        results = self._state.results
        settings = self._state.settings
        self._summary.set_lines(
            [
                f"Image sets:     {self._state.dataset_count}",
                f"Results:        {len(results)}",
                f"Reference runs: {len(self._state.ground_truth)}",
                f"Geometry:       start {settings.start_mm:.4f} mm, "
                f"step {settings.step_um:.3f} um, "
                f"{'increasing' if settings.increasing else 'decreasing'}"
                f"{', measured file preferred' if settings.prefer_file else ''}",
            ]
        )
        for button in (self._csv_button, self._json_button):
            button.setEnabled(bool(results))
        self._save_session_button.setEnabled(self._state.dataset_count > 0)

    def remember_run_selection(
        self, algorithm_keys: Sequence[str], params: dict[str, dict]
    ) -> None:
        """Take over what the Run tab has selected, so a session stores it.

        Args:
            algorithm_keys: Algorithms that are ticked on the Run tab.
            params: Parameter values per algorithm.
        """
        self._session_algorithms = tuple(algorithm_keys)
        self._session_params = {key: dict(values) for key, values in params.items()}

    # ------------------------------------------------------------------ exports

    @Slot()
    def export_csv_dialog(self) -> None:
        """Write every result as a CSV row."""
        path = self._ask_save_path("results", ".csv", "CSV file (*.csv)")
        if path is None:
            return
        self._run_export(
            lambda: export_results_csv(path, self._state.results),
            path,
            "results as CSV",
        )

    @Slot()
    def export_json_dialog(self) -> None:
        """Write every result as a JSON object."""
        path = self._ask_save_path("results", ".json", "JSON file (*.json)")
        if path is None:
            return
        self._run_export(
            lambda: export_results_json(path, self._state.results),
            path,
            "results as JSON",
        )

    @Slot()
    def export_plots_dialog(self) -> None:
        """Write every plot of every tab into one folder."""
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder for the plots")
        if not folder:
            return

        target = Path(folder)
        written: list[Path] = []
        failures: list[str] = []

        for name, canvas in self._canvas_provider():
            path = suggest_filename(safe_stem(name), ".png", target)
            try:
                canvas.save_png(path)
            except ExportError as exc:
                failures.append(str(exc))
                LOGGER.error("%s", exc)
            else:
                written.append(path)
                self._append_log(f"Saved {path}")

        self.refresh()
        if failures:
            QMessageBox.warning(
                self,
                "Some plots could not be saved",
                f"{len(written)} plot(s) saved.\n\nProblems:\n" + "\n".join(failures),
            )
        else:
            QMessageBox.information(
                self,
                "Plots exported",
                f"{len(written)} plot(s) saved into:\n{target}\n\n"
                f"Resolution: {EXPORT_DPI} dpi.",
            )

    @Slot()
    def save_session_dialog(self) -> None:
        """Write the whole session to a JSON file."""
        path = self._ask_save_path("session", ".json", "JSON file (*.json)")
        if path is None:
            return

        session = SessionData(
            datasets=tuple(
                SessionDataset(folder=str(dataset.folder), label=dataset.label)
                for dataset in self._state.datasets
            ),
            settings=self._state.settings,
            measure_key=self._state.measure_key,
            algorithm_keys=self._session_algorithms,
            params=self._session_params,
            results=tuple(result.to_row() for result in self._state.results),
        )
        self._run_export(lambda: save_session(path, session), path, "session")

    @Slot()
    def load_session_dialog(self) -> None:
        """Read a session file and hand it to the window."""
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Load a session", str(Path.home()), "JSON file (*.json)"
        )
        if not chosen:
            return

        try:
            session = load_session(Path(chosen))
        except ExportError as exc:
            LOGGER.error("%s", exc)
            QMessageBox.critical(self, "Could not load this session", str(exc))
            return

        self._append_log(f"Loaded session from {chosen}")
        self.session_loaded.emit(session)

    # ------------------------------------------------------------------ helpers

    def _ask_save_path(self, stem: str, suffix: str, filter_text: str) -> Optional[Path]:
        """Ask the user where to write a file.

        Args:
            stem: Suggested base name.
            suffix: Extension including the dot.
            filter_text: File-type filter of the dialog.

        Returns:
            The chosen path, or ``None`` when the dialog was cancelled.
        """
        suggested = suggest_filename(stem, suffix, Path.home())
        chosen, _ = QFileDialog.getSaveFileName(
            self, f"Save {stem}{suffix}", str(suggested), filter_text
        )
        return Path(chosen) if chosen else None

    def _run_export(
        self, action: Callable[[], object], path: Path, what: str
    ) -> None:
        """Run one export, reporting success or failure to the user.

        Args:
            action: The export call.
            path: File it writes, for the messages.
            what: Short description used in the messages.
        """
        try:
            action()
        except ExportError as exc:
            LOGGER.error("%s", exc)
            self._append_log(f"FAILED to export {what}: {exc}")
            QMessageBox.critical(self, f"Could not export the {what}", str(exc))
            return

        self._append_log(f"Saved {path}")
        QMessageBox.information(self, "Export finished", f"Saved the {what} to:\n{path}")

    def _append_log(self, message: str) -> None:
        """Add one line to the export log."""
        self._log.appendPlainText(message)
