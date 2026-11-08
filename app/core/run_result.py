"""The unified result record of one algorithm run.

Every search in ``autofocus.algorithms`` returns its own result type with its
own extra fields.  The adapters in :mod:`app.core.algorithms` flatten all of
them into the single :class:`RunResult` defined here, which is what the results
table, the plots and the CSV/JSON export read.

Main contents:
    * :class:`RunResult` -- one run of one algorithm on one image set.
    * :data:`RESULT_COLUMNS` -- the table/CSV columns, with their formatting.
    * :func:`position_error` -- error of a position against the ground truth.

Keeping the column list next to the record means the results table and the CSV
export can never drift apart.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from app.core.dataset import MM_PER_UM

#: Shown instead of a number when a field was never filled in.
MISSING_TEXT = "-"


def _is_missing(value: Any) -> bool:
    """Tell whether a value should be printed as :data:`MISSING_TEXT`."""
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


@dataclass(frozen=True)
class RunResult:
    """Outcome of one algorithm run on one image set.

    The coarse fields describe the best *discrete* frame the search settled on.
    The fine fields describe the sub-frame position from the quadratic fit,
    which is the position the assignment asks for.

    Attributes:
        algorithm: Display name of the search.
        algorithm_key: Registry key of the search.
        dataset_label: Display name of the image set.
        dataset_key: Folder path of the image set.
        measure: Display name of the focus measure.
        measure_key: Registry key of the focus measure.
        coarse_idx: Sharpest discrete frame index found.
        coarse_value: Focus score of that frame.
        coarse_wd_mm: Working distance of that frame, in millimetres.
        fine_idx: Sub-frame peak index from the quadratic fit.
        fine_wd_mm: Working distance of the sub-frame peak, in millimetres.
        fine_value: Focus score interpolated at the sub-frame peak.
        fit_ok: Whether the fit found a valid concave maximum inside its window.
        fit_r2: Goodness of fit of the parabola.
        fit_coeffs: ``(A0, A1, A2)`` of ``f(d) = A0 + A1*d + A2*d^2``.
        fit_window: Inclusive frame range ``(lo, hi)`` used by the fit.
        fit_message: Status text the fit returned.
        fit_points: ``{frame index: score}`` the parabola was fitted on.
        fit_applied_afterwards: Whether the adapter added the fit itself,
            because the search returned no sub-frame result of its own.
        frames_evaluated: Distinct frames read by the whole run, fine fit included.
        search_frames: Size of the search's own ``evals`` dictionary.
        eval_calls: How often the search asked for a score, cache hits included.
        visited: Frame indices in the order the search probed them.
        evals: The search's own ``{frame index: score}`` dictionary.
        elapsed_s: Wall-clock time of the search plus its fine refinement.
        error_frames: Distance from the ground-truth peak, in frames.
        error_um: The same error in micrometres.
        coarse_error_frames: Error of the discrete peak, in frames.
        coarse_error_um: Error of the discrete peak, in micrometres.
        gt_idx: Discrete ground-truth peak frame.
        gt_reference_idx: Ground-truth position the errors are measured against.
        verified: Noise-floor verification result, for the gradient search.
        restarts: Basin relocations the gradient search needed.
        noise_sigma_estimate: Noise level the gradient search measured.
        noise_sigma: Gaussian noise that was injected for this run.
        seed: Seed of the injected noise.
        repeats: How many times the run was repeated to average the time.
        extra: Anything else worth keeping, for example the parameters used.
    """

    algorithm: str
    algorithm_key: str
    dataset_label: str
    dataset_key: str
    measure: str
    measure_key: str

    coarse_idx: int
    coarse_value: float
    coarse_wd_mm: float

    fine_idx: float = float("nan")
    fine_wd_mm: float = float("nan")
    fine_value: float = float("nan")
    fit_ok: bool = False
    fit_r2: float = float("nan")
    fit_coeffs: Optional[tuple[float, float, float]] = None
    fit_window: Optional[tuple[int, int]] = None
    fit_message: str = ""
    fit_points: Mapping[int, float] = field(default_factory=dict)
    fit_applied_afterwards: bool = False

    frames_evaluated: int = 0
    search_frames: int = 0
    eval_calls: int = 0
    visited: tuple[int, ...] = ()
    evals: Mapping[int, float] = field(default_factory=dict)
    elapsed_s: float = float("nan")

    error_frames: float = float("nan")
    error_um: float = float("nan")
    coarse_error_frames: float = float("nan")
    coarse_error_um: float = float("nan")
    gt_idx: int = -1
    gt_reference_idx: float = float("nan")

    verified: Optional[bool] = None
    restarts: int = 0
    noise_sigma_estimate: float = float("nan")
    noise_sigma: float = 0.0
    seed: Optional[int] = None
    repeats: int = 1

    extra: Mapping[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------- derived

    @property
    def best_idx(self) -> float:
        """Best position the run produced: the sub-frame one when the fit held."""
        return self.fine_idx if self.fit_ok and not math.isnan(self.fine_idx) else float(
            self.coarse_idx
        )

    @property
    def best_wd_mm(self) -> float:
        """Working distance of :attr:`best_idx`, in millimetres."""
        if self.fit_ok and not math.isnan(self.fine_wd_mm):
            return self.fine_wd_mm
        return self.coarse_wd_mm

    @property
    def elapsed_ms(self) -> float:
        """Wall-clock time of the run, in milliseconds."""
        return self.elapsed_s * 1.0e3

    @property
    def fit_status(self) -> str:
        """Human-readable fit status for the Results and Fine-fit tabs."""
        if self.fit_window is None:
            return "no fit"
        state = "ok" if self.fit_ok else "failed"
        return f"{state} ({self.fit_message})" if self.fit_message else state

    def frames_saved_percent(self, baseline_frames: int) -> float:
        """Share of frames this run avoided compared with a full scan.

        Args:
            baseline_frames: Frames an exhaustive scan would read.

        Returns:
            The saving in percent, or ``nan`` when the baseline is empty.
        """
        if baseline_frames <= 0:
            return float("nan")
        return (1.0 - self.frames_evaluated / baseline_frames) * 100.0

    def to_row(self) -> dict[str, Any]:
        """Flatten the record into scalars for the table and the CSV export."""
        return {column.key: column.value_of(self) for column in RESULT_COLUMNS}


def position_error(position: float, reference: float, step_um: float) -> tuple[float, float]:
    """Error of one position against the ground truth.

    Args:
        position: Position found by a search, in (possibly fractional) frames.
        reference: Ground-truth position, in frames.
        step_um: Stage step between two frames, in micrometres.

    Returns:
        A ``(error_frames, error_um)`` pair.  Both are ``nan`` when either
        position is unknown.
    """
    if math.isnan(position) or math.isnan(reference):
        return float("nan"), float("nan")
    error_frames = abs(float(position) - float(reference))
    return error_frames, error_frames * abs(step_um)


def frames_to_mm(error_frames: float, step_um: float) -> float:
    """Convert a frame distance into millimetres."""
    return error_frames * abs(step_um) * MM_PER_UM


@dataclass(frozen=True)
class ResultColumn:
    """One column of the results table and of the CSV export.

    Attributes:
        key: Column name used in the CSV header and in the JSON export.
        header: Text shown in the table header.
        getter: Pulls the raw value out of a :class:`RunResult`.
        fmt: Formats the raw value for display; ``None`` means ``str``.
        tooltip: Explanation shown when hovering the header.
    """

    key: str
    header: str
    getter: Callable[[RunResult], Any]
    fmt: Optional[Callable[[Any], str]] = None
    tooltip: str = ""

    def value_of(self, result: RunResult) -> Any:
        """Raw value of this column for one run."""
        return self.getter(result)

    def text_of(self, result: RunResult) -> str:
        """Formatted value of this column for one run."""
        value = self.value_of(result)
        if _is_missing(value):
            return MISSING_TEXT
        if self.fmt is not None:
            return self.fmt(value)
        return str(value)


def _fixed(decimals: int) -> Callable[[Any], str]:
    """Build a formatter that prints a float with ``decimals`` digits."""

    def formatter(value: Any) -> str:
        """Print one value with the captured number of decimals."""
        return f"{float(value):.{decimals}f}"

    return formatter


def _boolean(value: Any) -> str:
    """Format a tri-state flag as ``yes`` / ``no`` / ``-``."""
    return "yes" if bool(value) else "no"


def _window(value: Any) -> str:
    """Format an inclusive frame window as ``lo-hi``."""
    lo, hi = value
    return f"{int(lo)}-{int(hi)}"


def _coefficients(value: Any) -> str:
    """Format the three parabola coefficients compactly."""
    return ", ".join(f"{float(coefficient):.4g}" for coefficient in value)


#: Table and CSV columns, in display order.  This is the single definition of
#: what a result "contains" for the user; the Results tab and the export both
#: iterate over it.
RESULT_COLUMNS: tuple[ResultColumn, ...] = (
    ResultColumn("dataset", "Image set", lambda r: r.dataset_label,
                 tooltip="Folder the frames came from."),
    ResultColumn("algorithm", "Algorithm", lambda r: r.algorithm,
                 tooltip="Search strategy used."),
    ResultColumn("measure", "Focus measure", lambda r: r.measure,
                 tooltip="Focus measure used to score the frames."),
    ResultColumn("coarse_idx", "Coarse frame", lambda r: r.coarse_idx,
                 tooltip="Sharpest discrete frame the search found."),
    ResultColumn("coarse_value", "Coarse value", lambda r: r.coarse_value, _fixed(4),
                 tooltip="Focus score of the coarse frame."),
    ResultColumn("coarse_wd_mm", "Coarse WD (mm)", lambda r: r.coarse_wd_mm, _fixed(4),
                 tooltip="Working distance of the coarse frame."),
    ResultColumn("fine_idx", "Fine frame", lambda r: r.fine_idx, _fixed(3),
                 tooltip="Sub-frame peak position from the quadratic fit."),
    ResultColumn("fine_wd_mm", "Fine WD (mm)", lambda r: r.fine_wd_mm, _fixed(5),
                 tooltip="Working distance of the sub-frame peak."),
    ResultColumn("fit_ok", "Fit ok", lambda r: r.fit_ok, _boolean,
                 tooltip="Whether the parabola found a maximum inside its window."),
    ResultColumn("fit_r2", "Fit R2", lambda r: r.fit_r2, _fixed(4),
                 tooltip="Goodness of fit of the parabola."),
    ResultColumn("error_frames", "Error (frames)", lambda r: r.error_frames, _fixed(3),
                 tooltip="Distance from the ground-truth peak, best position used."),
    ResultColumn("error_um", "Error (um)", lambda r: r.error_um, _fixed(2),
                 tooltip="The same error in micrometres."),
    ResultColumn("coarse_error_frames", "Coarse error (frames)",
                 lambda r: r.coarse_error_frames, _fixed(3),
                 tooltip="Error of the discrete peak alone."),
    ResultColumn("frames_evaluated", "Frames read", lambda r: r.frames_evaluated,
                 tooltip="Distinct frames the whole run read, fine fit included."),
    ResultColumn("search_frames", "Search frames", lambda r: r.search_frames,
                 tooltip="Frames the search itself scored, without the added fit."),
    ResultColumn("eval_calls", "Eval calls", lambda r: r.eval_calls,
                 tooltip="Score requests including cache hits."),
    ResultColumn("elapsed_ms", "Time (ms)", lambda r: r.elapsed_ms, _fixed(1),
                 tooltip="Wall-clock time of the search plus its refinement."),
    ResultColumn("verified", "Verified", lambda r: r.verified, _boolean,
                 tooltip="Noise-floor check of the gradient search."),
    ResultColumn("restarts", "Restarts", lambda r: r.restarts,
                 tooltip="Basin relocations the gradient search needed."),
    ResultColumn("noise_sigma", "Noise sigma", lambda r: r.noise_sigma, _fixed(2),
                 tooltip="Gaussian noise added to every frame, in grey levels."),
    ResultColumn("gt_idx", "GT frame", lambda r: r.gt_idx,
                 tooltip="Discrete peak of the exhaustive reference scan."),
    ResultColumn("gt_reference_idx", "GT position", lambda r: r.gt_reference_idx, _fixed(3),
                 tooltip="Reference position the errors are measured against."),
    ResultColumn("fit_window", "Fit window", lambda r: r.fit_window, _window,
                 tooltip="Frame range the parabola was fitted on."),
    ResultColumn("fit_coeffs", "Fit A0, A1, A2", lambda r: r.fit_coeffs, _coefficients,
                 tooltip="Coefficients of f(d) = A0 + A1*d + A2*d^2."),
    ResultColumn("repeats", "Repeats", lambda r: r.repeats,
                 tooltip="Repetitions used to average the run time."),
)


def column_headers() -> list[str]:
    """Headers of :data:`RESULT_COLUMNS`, in display order."""
    return [column.header for column in RESULT_COLUMNS]


def sort_results(results: Sequence[RunResult]) -> list[RunResult]:
    """Order runs for display: by image set, then by algorithm.

    Args:
        results: Runs to order.

    Returns:
        A new, ordered list.
    """
    return sorted(results, key=lambda r: (r.dataset_label.lower(), r.algorithm.lower()))
