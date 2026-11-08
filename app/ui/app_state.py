"""The shared state of the window, in one explicit object.

Ten tabs have to agree on which image sets are loaded, which working-distance
settings apply, which runs exist and which reference curves are already
computed.  Rather than scattering that across the tabs or into module-level
globals, it lives in one :class:`AppState` that the main window creates and
hands to every tab.  Tabs react to its signals instead of calling each other.

Main contents:
    * :class:`AppState` -- image sets, settings, results and reference curves.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from PySide6.QtCore import QObject, Signal

from app.core.dataset import (
    Dataset,
    DatasetError,
    WorkingDistanceSettings,
    unique_label,
)
from app.core.experiment import GroundTruth
from app.core.focus_measures import DEFAULT_MEASURE_KEY
from app.core.run_result import RunResult

LOGGER = logging.getLogger(__name__)


class AppState(QObject):
    """Everything the tabs share, with a signal per kind of change.

    Signals:
        datasets_changed: An image set was added, removed or relabelled.
        settings_changed: The working-distance settings changed, which
            invalidates every working distance on screen.
        results_changed: Runs were added or cleared.
        ground_truth_changed: A reference curve became available.
        measure_changed: The selected focus measure changed.
    """

    datasets_changed = Signal()
    settings_changed = Signal()
    results_changed = Signal()
    ground_truth_changed = Signal()
    measure_changed = Signal(str)
    active_selection_changed = Signal(str, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Create empty state with the assignment's default settings."""
        super().__init__(parent)
        self._datasets: dict[str, Dataset] = {}
        self._results: list[RunResult] = []
        self._ground_truth: dict[tuple[str, str], GroundTruth] = {}
        self._settings = WorkingDistanceSettings()
        self._measure_key = DEFAULT_MEASURE_KEY
        self._preload = False
        self._last_dataset_key: Optional[str] = None
        self._last_algorithm_key: Optional[str] = None

    @property
    def last_dataset_key(self) -> Optional[str]:
        return self._last_dataset_key

    @property
    def last_algorithm_key(self) -> Optional[str]:
        return self._last_algorithm_key

    def set_active_selection(self, dataset_key: Optional[str], algorithm_key: Optional[str]) -> None:
        """Set and broadcast the last run or active dataset and algorithm."""
        changed = False
        if dataset_key and dataset_key != self._last_dataset_key:
            self._last_dataset_key = dataset_key
            changed = True
        if algorithm_key and algorithm_key != self._last_algorithm_key:
            self._last_algorithm_key = algorithm_key
            changed = True
        if changed and self._last_dataset_key:
            self.active_selection_changed.emit(self._last_dataset_key, self._last_algorithm_key or "")

    # ------------------------------------------------------------- image sets

    @property
    def datasets(self) -> list[Dataset]:
        """Loaded image sets, in the order they were added."""
        return list(self._datasets.values())

    @property
    def dataset_count(self) -> int:
        """How many image sets are loaded."""
        return len(self._datasets)

    def dataset(self, key: str) -> Optional[Dataset]:
        """Look one image set up by its folder path."""
        return self._datasets.get(key)

    def dataset_by_label(self, label: str) -> Optional[Dataset]:
        """Look one image set up by the name shown in the GUI."""
        return next((item for item in self._datasets.values() if item.label == label), None)

    def add_dataset(self, folder: Path, label: Optional[str] = None) -> Dataset:
        """Load one image set and make it known to every tab.

        Args:
            folder: Folder that directly holds the frames.
            label: Name for the GUI; the folder name is used when ``None``.

        Returns:
            The loaded image set, or the existing one when the folder was
            already loaded.

        Raises:
            DatasetError: If the folder cannot be scanned or holds too few images.
        """
        resolved = Path(folder).resolve()
        existing = self._datasets.get(str(resolved))
        if existing is not None:
            LOGGER.info("Image set '%s' is already loaded.", existing.label)
            return existing

        taken = [item.label for item in self._datasets.values()]
        dataset = Dataset(
            resolved,
            label=unique_label(label or resolved.name, taken),
            settings=self._settings,
        )
        self._datasets[dataset.key] = dataset
        LOGGER.info("Loaded %r", dataset)
        self.datasets_changed.emit()
        return dataset

    def add_datasets(self, folders: Iterable[Path]) -> tuple[list[Dataset], list[str]]:
        """Load several image sets, collecting the failures instead of stopping.

        Args:
            folders: Folders to load.

        Returns:
            A ``(loaded image sets, error messages)`` pair.  The errors are
            shown to the user in one dialog rather than one dialog per folder.
        """
        loaded: list[Dataset] = []
        errors: list[str] = []
        for folder in folders:
            try:
                loaded.append(self.add_dataset(Path(folder)))
            except DatasetError as exc:
                errors.append(str(exc))
                LOGGER.warning("Skipped '%s': %s", folder, exc)
        return loaded, errors

    def remove_dataset(self, key: str) -> None:
        """Forget one image set, together with its results and reference curves."""
        dataset = self._datasets.pop(key, None)
        if dataset is None:
            return
        dataset.release()
        self._results = [result for result in self._results if result.dataset_key != key]
        self._ground_truth = {
            cache_key: truth
            for cache_key, truth in self._ground_truth.items()
            if cache_key[0] != key
        }
        LOGGER.info("Removed image set '%s'.", dataset.label)
        self.datasets_changed.emit()
        self.results_changed.emit()
        self.ground_truth_changed.emit()

    def clear_datasets(self) -> None:
        """Forget every image set, result and reference curve."""
        for dataset in self._datasets.values():
            dataset.release()
        self._datasets.clear()
        self._results.clear()
        self._ground_truth.clear()
        LOGGER.info("Cleared every image set.")
        self.datasets_changed.emit()
        self.results_changed.emit()
        self.ground_truth_changed.emit()

    def rename_dataset(self, key: str, label: str) -> None:
        """Change the name one image set is shown under."""
        dataset = self._datasets.get(key)
        if dataset is None or not label.strip():
            return
        taken = [item.label for item in self._datasets.values() if item.key != key]
        dataset.label = unique_label(label.strip(), taken)
        self.datasets_changed.emit()

    # ---------------------------------------------------------------- settings

    @property
    def settings(self) -> WorkingDistanceSettings:
        """Working-distance settings that apply to every image set."""
        return self._settings

    def set_settings(self, settings: WorkingDistanceSettings) -> None:
        """Apply new working-distance settings to every loaded image set.

        Every working distance on screen depends on these, so the reference
        curves keep their scores but their stored positions go stale; they are
        dropped so the next run recomputes them against the new geometry.

        Args:
            settings: The new settings.
        """
        if settings == self._settings:
            return
        self._settings = settings
        for dataset in self._datasets.values():
            dataset.settings = settings
        self._ground_truth.clear()
        LOGGER.info(
            "Working distances: start %.4f mm, step %.3f um, %s, file %s.",
            settings.start_mm, settings.step_um,
            "increasing" if settings.increasing else "decreasing",
            "preferred" if settings.prefer_file else "ignored",
        )
        self.settings_changed.emit()
        self.ground_truth_changed.emit()

    @property
    def preload_enabled(self) -> bool:
        """Whether newly used image sets are decoded into memory up front."""
        return self._preload

    def set_preload_enabled(self, enabled: bool) -> None:
        """Switch preloading on or off for future loads."""
        self._preload = bool(enabled)

    @property
    def measure_key(self) -> str:
        """Registry key of the selected focus measure."""
        return self._measure_key

    def set_measure_key(self, key: str) -> None:
        """Select a focus measure and tell the tabs about it."""
        if key == self._measure_key:
            return
        self._measure_key = key
        self.measure_changed.emit(key)

    # ----------------------------------------------------------------- results

    @property
    def results(self) -> list[RunResult]:
        """Every run of this session, oldest first."""
        return list(self._results)

    def add_results(self, results: Sequence[RunResult]) -> None:
        """Append runs to the session.

        A new run of the same algorithm on the same image set with the same
        focus measure and noise level replaces the older one, so repeating a
        run with different parameters updates the table instead of filling it
        with near-duplicates.

        Args:
            results: Runs to add.
        """
        if not results:
            return
        for result in results:
            signature = (
                result.dataset_key, result.algorithm_key,
                result.measure_key, result.noise_sigma,
            )
            self._results = [
                existing
                for existing in self._results
                if (
                    existing.dataset_key, existing.algorithm_key,
                    existing.measure_key, existing.noise_sigma,
                ) != signature
            ]
            self._results.append(result)
        if results:
            latest = results[-1]
            self.set_active_selection(latest.dataset_key, latest.algorithm_key)
        self.results_changed.emit()

    def clear_results(self) -> None:
        """Drop every run of this session."""
        if not self._results:
            return
        self._results.clear()
        self.results_changed.emit()

    def results_for_dataset(self, dataset_key: str) -> list[RunResult]:
        """Runs on one image set."""
        return [result for result in self._results if result.dataset_key == dataset_key]

    def result_for(self, dataset_key: str, algorithm_key: str) -> Optional[RunResult]:
        """Most recent run of one algorithm on one image set."""
        matches = [
            result
            for result in self._results
            if result.dataset_key == dataset_key and result.algorithm_key == algorithm_key
        ]
        return matches[-1] if matches else None

    # ------------------------------------------------------------ ground truth

    @property
    def ground_truth(self) -> Mapping[tuple[str, str], GroundTruth]:
        """Read-only view of the reference curves computed so far."""
        return dict(self._ground_truth)

    def add_ground_truths(self, truths: Sequence[GroundTruth]) -> None:
        """Merge reference curves a job computed into the cache.

        Called on the GUI thread from a job's ``finished`` handler, which is
        what keeps the cache single-writer even though jobs run in a thread.

        Args:
            truths: Reference curves to store.
        """
        if not truths:
            return
        for truth in truths:
            self._ground_truth[truth.cache_key] = truth
        self.ground_truth_changed.emit()

    def ground_truth_for(self, dataset_key: str, measure_key: str) -> Optional[GroundTruth]:
        """Reference curve of one image set and focus measure, if computed."""
        return self._ground_truth.get((dataset_key, measure_key))

    def ground_truths_for_measure(self, measure_key: str) -> list[GroundTruth]:
        """Reference curves of every image set for one focus measure."""
        return [
            truth
            for (_, key), truth in self._ground_truth.items()
            if key == measure_key
        ]

    def ground_truths_for_dataset(self, dataset_key: str) -> list[GroundTruth]:
        """Reference curves of one image set for every focus measure."""
        return [
            truth
            for (key, _), truth in self._ground_truth.items()
            if key == dataset_key
        ]
