"""CSV and JSON export, plus saving and loading a whole session.

The results table, the CSV file and the JSON file all describe the same runs, so
they all iterate over :data:`app.core.run_result.RESULT_COLUMNS`.  Adding a
column there makes it appear in every output at once.

Main contents:
    * :func:`export_results_csv` -- one row per run, the table columns.
    * :func:`export_results_json` -- the same rows plus the visited frames.
    * :class:`SessionData` / :func:`save_session` / :func:`load_session` --
      image-set paths, settings and results in one restorable file.
"""

from __future__ import annotations

import csv
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from app import APP_NAME, APP_VERSION
from app.core.dataset import WorkingDistanceSettings
from app.core.run_result import RESULT_COLUMNS, RunResult

LOGGER = logging.getLogger(__name__)

#: Version of the session-file layout, so a future change can be detected.
SESSION_FORMAT_VERSION = 1

#: Resolution of exported figures; 300 dpi is print quality.
EXPORT_DPI = 300


class ExportError(RuntimeError):
    """Raised when a file cannot be written or a session cannot be read."""


def _json_safe(value: Any) -> Any:
    """Turn a value into something :mod:`json` can serialise.

    ``NaN`` becomes ``None`` because strict JSON has no not-a-number literal,
    and tuples become lists.

    Args:
        value: Any value taken from a result record.

    Returns:
        A JSON-serialisable value.
    """
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def export_results_csv(path: Path, results: Sequence[RunResult]) -> int:
    """Write every run as one CSV row.

    Args:
        path: File to write.
        results: Runs to export.

    Returns:
        How many rows were written.

    Raises:
        ExportError: If the file cannot be written.
    """
    headers = [column.key for column in RESULT_COLUMNS]
    try:
        with Path(path).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            for result in results:
                writer.writerow([column.text_of(result) for column in RESULT_COLUMNS])
    except OSError as exc:
        raise ExportError(f"Cannot write '{path}': {exc}") from exc

    LOGGER.info("Exported %d result row(s) to %s", len(results), path)
    return len(results)


def export_results_json(path: Path, results: Sequence[RunResult]) -> int:
    """Write every run as a JSON object.

    The JSON export carries more than the CSV: the visited frame order and the
    points the parabola was fitted on, which is what a plot would need to be
    rebuilt outside the application.

    Args:
        path: File to write.
        results: Runs to export.

    Returns:
        How many runs were written.

    Raises:
        ExportError: If the file cannot be written.
    """
    payload = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "results": [_result_to_dict(result) for result in results],
    }
    _write_json(path, payload)
    LOGGER.info("Exported %d result(s) to %s", len(results), path)
    return len(results)


def _result_to_dict(result: RunResult) -> dict[str, Any]:
    """Flatten one run into a JSON-ready dictionary."""
    row = {column.key: _json_safe(column.value_of(result)) for column in RESULT_COLUMNS}
    row.update(
        {
            "algorithm_key": result.algorithm_key,
            "dataset_key": result.dataset_key,
            "measure_key": result.measure_key,
            "fine_value": _json_safe(result.fine_value),
            "fit_message": result.fit_message,
            "fit_applied_afterwards": result.fit_applied_afterwards,
            "visited": list(result.visited),
            "fit_points": {str(idx): value for idx, value in sorted(result.fit_points.items())},
            "seed": result.seed,
            "noise_sigma_estimate": _json_safe(result.noise_sigma_estimate),
            "params": _json_safe(dict(result.extra.get("params", {}))),
        }
    )
    return row


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a JSON file with readable indentation.

    Raises:
        ExportError: If the file cannot be written.
    """
    try:
        Path(path).write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        raise ExportError(f"Cannot write '{path}': {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise ExportError(f"Cannot encode the data for '{path}': {exc}") from exc


@dataclass(frozen=True)
class SessionDataset:
    """One image set as it is stored in a session file.

    Attributes:
        folder: Folder the frames were read from.
        label: Name the image set had in the GUI.
    """

    folder: str
    label: str


@dataclass(frozen=True)
class SessionData:
    """A whole session: which image sets were loaded, how, and what came out.

    Attributes:
        datasets: Image sets to restore.
        settings: Working-distance settings that were active.
        measure_key: Focus measure that was selected.
        algorithm_keys: Algorithms that were selected.
        params: Parameter values per algorithm.
        results: Runs to restore into the table.
    """

    datasets: tuple[SessionDataset, ...] = ()
    settings: WorkingDistanceSettings = field(default_factory=WorkingDistanceSettings)
    measure_key: str = ""
    algorithm_keys: tuple[str, ...] = ()
    params: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    results: tuple[Mapping[str, Any], ...] = ()


def save_session(path: Path, session: SessionData) -> None:
    """Write a session file.

    Only the image-set *paths* are stored, never the frames, so the file stays
    small and can be reopened as long as the folders are still there.

    Args:
        path: File to write.
        session: Session to store.

    Raises:
        ExportError: If the file cannot be written.
    """
    payload = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "format": SESSION_FORMAT_VERSION,
        "datasets": [
            {"folder": item.folder, "label": item.label} for item in session.datasets
        ],
        "settings": {
            "start_mm": session.settings.start_mm,
            "step_um": session.settings.step_um,
            "increasing": session.settings.increasing,
            "prefer_file": session.settings.prefer_file,
        },
        "measure_key": session.measure_key,
        "algorithm_keys": list(session.algorithm_keys),
        "params": _json_safe(dict(session.params)),
        "results": [_json_safe(dict(row)) for row in session.results],
    }
    _write_json(path, payload)
    LOGGER.info("Saved session with %d image set(s) to %s", len(session.datasets), path)


def load_session(path: Path) -> SessionData:
    """Read a session file written by :func:`save_session`.

    Args:
        path: File to read.

    Returns:
        The stored session.

    Raises:
        ExportError: If the file is missing, not valid JSON, or not a session.
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExportError(f"Cannot read '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError(f"'{path}' is not a valid JSON file: {exc}") from exc

    if not isinstance(raw, dict) or "datasets" not in raw:
        raise ExportError(f"'{path}' does not look like a session file.")

    stored_format = int(raw.get("format", SESSION_FORMAT_VERSION))
    if stored_format > SESSION_FORMAT_VERSION:
        raise ExportError(
            f"'{path}' uses session format {stored_format}, but this version of "
            f"the application only understands {SESSION_FORMAT_VERSION}."
        )

    settings_raw = raw.get("settings") or {}
    defaults = WorkingDistanceSettings()
    settings = WorkingDistanceSettings(
        start_mm=float(settings_raw.get("start_mm", defaults.start_mm)),
        step_um=float(settings_raw.get("step_um", defaults.step_um)),
        increasing=bool(settings_raw.get("increasing", defaults.increasing)),
        prefer_file=bool(settings_raw.get("prefer_file", defaults.prefer_file)),
    )

    datasets = tuple(
        SessionDataset(folder=str(item.get("folder", "")), label=str(item.get("label", "")))
        for item in raw.get("datasets", [])
        if isinstance(item, dict) and item.get("folder")
    )

    return SessionData(
        datasets=datasets,
        settings=settings,
        measure_key=str(raw.get("measure_key", "")),
        algorithm_keys=tuple(str(key) for key in raw.get("algorithm_keys", [])),
        params={
            str(key): dict(value)
            for key, value in (raw.get("params") or {}).items()
            if isinstance(value, dict)
        },
        results=tuple(row for row in raw.get("results", []) if isinstance(row, dict)),
    )


def suggest_filename(stem: str, suffix: str, folder: Optional[Path] = None) -> Path:
    """Build a file name that does not overwrite an existing file.

    Args:
        stem: Base name without extension.
        suffix: Extension including the dot, for example ``".png"``.
        folder: Target folder; the current directory when ``None``.

    Returns:
        ``folder/stem+suffix``, or the same with ``_2``, ``_3``, ... appended.
    """
    base = Path(folder or Path.cwd())
    candidate = base / f"{stem}{suffix}"
    counter = 2
    while candidate.exists():
        candidate = base / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def safe_stem(text: str) -> str:
    """Turn arbitrary text into a file-name-safe stem.

    Args:
        text: Label such as an image-set or algorithm name.

    Returns:
        The text with every character outside ``[A-Za-z0-9._-]`` replaced by an
        underscore.
    """
    cleaned = "".join(
        character if character.isalnum() or character in "._-" else "_" for character in text
    )
    return cleaned.strip("_") or "export"
