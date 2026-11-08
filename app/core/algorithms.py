"""Registry of the search algorithms plus the adapters that unify their results.

Each search in ``autofocus.algorithms`` has its own signature and its own result
type.  This module wraps every one of them in the same shape:

    parameter spec  ->  GUI form
    runner          ->  calls the search with those parameters
    adapter         ->  flattens whatever came back into a :class:`RunResult`

Main contents:
    * :class:`ParamSpec` -- one editable parameter, used to build the GUI form.
    * :class:`RunContext` -- everything one run needs (image set, evaluator, ...).
    * :class:`AlgorithmSpec` -- one registry entry.
    * :data:`ALGORITHMS` -- key -> entry, in the order shown in the GUI.
    * :func:`run_algorithm` -- run one entry and return a :class:`RunResult`.

Two details of the read-only package drive the design here:

1. ``coarse_and_fine_search`` defaults its ``coarse_fmo`` to a name that has no
   implementation, so every call passes ``coarse_fmo`` and ``fine_fmo``
   explicitly.
2. The hybrid search evaluates its two stages at different pixel strides and
   stores both in one ``evals`` dictionary.  The adapter therefore never feeds
   that mixed dictionary to the parabola fit; it asks the evaluator for a
   single-resolution snapshot instead.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional

import numpy as np

from app.core.dataset import Dataset
from app.core.evaluator import Evaluator
from app.core.focus_measures import FocusMeasure
from app.core.run_result import RunResult, position_error
from autofocus.algorithms import (
    coarse_and_fine_search,
    coarse_quadratic_search,
    global_scan_search,
    gradient_descent_search,
    quadratic_fit,
)

LOGGER = logging.getLogger(__name__)

#: ``quadratic_fit`` needs five samples, so a half window below 2 makes it fail.
#: With half_window = 1 the window holds 3 frames and ``coarse_quadratic_search``
#: then reads scores it never evaluated, so 2 is enforced as the lower bound.
MIN_HALF_WINDOW = 2

#: Default half window of the fine quadratic fit, as in the read-only package.
DEFAULT_HALF_WINDOW = 12

#: Parameter value that means "let the algorithm choose" for optional indices.
AUTO = -1


@dataclass(frozen=True)
class ParamSpec:
    """One editable algorithm parameter, and how the GUI should show it.

    Attributes:
        name: Keyword the runner reads it under.
        label: Text shown next to the editor.
        kind: ``"int"``, ``"float"``, ``"bool"`` or ``"choice"``.
        default: Value the form starts with and resets to.
        minimum: Lowest accepted value, for numeric kinds.
        maximum: Highest accepted value, for numeric kinds.
        step: Single-step increment of the spin box.
        decimals: Digits shown for the ``"float"`` kind.
        choices: Selectable values for the ``"choice"`` kind.
        tooltip: Explanation shown on hover.
    """

    name: str
    label: str
    kind: str
    default: Any
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    choices: tuple[str, ...] = ()
    tooltip: str = ""


@dataclass(frozen=True)
class GroundTruthRef:
    """The reference an error is measured against.

    Attributes:
        peak_idx: Discrete peak of the exhaustive scan.
        reference_idx: Position the errors use; the sub-frame vertex of the
            reference curve when its fit held, otherwise :attr:`peak_idx`.
        step_um: Stage step between two frames, in micrometres.
    """

    peak_idx: int
    reference_idx: float
    step_um: float


@dataclass(frozen=True)
class RunContext:
    """Everything one algorithm run needs.

    Attributes:
        dataset: Image set to search in.
        evaluator: Fresh evaluator for this run; it owns the score cache.
        measure: Focus measure selected in the GUI.
        wd_mm: Working distance of every frame, in millimetres.  It is handed to
            the searches that accept ``wd`` so their ``fine_wd`` comes out in mm.
        params: Parameter values from the GUI form.
        apply_fit: Whether to add a quadratic fit when the search has no fine
            result of its own.
        fit_half_window: Half window of that added fit.
        ground_truth: Reference for the error fields, or ``None``.
        noise_sigma: Noise that was injected, copied into the result.
        seed: Seed of that noise, copied into the result.
        repeats: How often the run was timed, copied into the result.
    """

    dataset: Dataset
    evaluator: Evaluator
    measure: FocusMeasure
    wd_mm: np.ndarray
    params: Mapping[str, Any]
    apply_fit: bool = True
    fit_half_window: int = DEFAULT_HALF_WINDOW
    ground_truth: Optional[GroundTruthRef] = None
    noise_sigma: float = 0.0
    seed: Optional[int] = None
    repeats: int = 1

    @property
    def max_idx(self) -> int:
        """Highest frame index, which the searches take inclusively."""
        return self.dataset.max_idx

    def param_int(self, name: str) -> int:
        """Read one parameter as an ``int``."""
        return int(self.params[name])

    def param_float(self, name: str) -> float:
        """Read one parameter as a ``float``."""
        return float(self.params[name])

    def param_bool(self, name: str) -> bool:
        """Read one parameter as a ``bool``."""
        return bool(self.params[name])

    def optional_index(self, name: str) -> Optional[int]:
        """Read an index parameter where :data:`AUTO` means "not set"."""
        value = int(self.params[name])
        return None if value < 0 else value

    def optional_positive(self, name: str) -> Optional[int]:
        """Read a step parameter where ``0`` or less means "let it choose"."""
        value = int(self.params[name])
        return None if value <= 0 else value


@dataclass
class SearchOutcome:
    """What a runner hands back to the adapter.

    Attributes:
        result: The search's own result object, whatever its type.
        fine_stride: Pixel stride of the search's finest evaluations.  The
            adapter reuses only scores taken at this stride, so an added
            parabola fit never mixes two resolutions.
    """

    result: Any
    fine_stride: int = 1


# --------------------------------------------------------------------- runners


def _run_global_scan(ctx: RunContext) -> SearchOutcome:
    """Run the exhaustive linear scan over the whole stack."""
    stride = ctx.param_int("stride")
    result = global_scan_search(
        ctx.evaluator,
        max_idx=ctx.max_idx,
        stride=stride,
        fmo_name=ctx.measure.key,
        first_frame=ctx.optional_index("first_frame"),
    )
    return SearchOutcome(result, fine_stride=stride)


def _run_coarse_and_fine(ctx: RunContext) -> SearchOutcome:
    """Run the two-stage hybrid sweep (sparse grid, then a local bracket)."""
    fine_stride = ctx.param_int("fine_stride")
    result = coarse_and_fine_search(
        ctx.evaluator,
        max_idx=ctx.max_idx,
        coarse_step=ctx.optional_positive("coarse_step"),
        # Both names are passed on purpose: the default coarse_fmo of this
        # function names a composite measure that has no implementation.
        coarse_fmo=ctx.measure.key,
        fine_fmo=ctx.measure.key,
        coarse_stride=ctx.param_int("coarse_stride"),
        fine_stride=fine_stride,
        first_frame=ctx.optional_index("first_frame"),
    )
    return SearchOutcome(result, fine_stride=fine_stride)


def _run_gradient(ctx: RunContext) -> SearchOutcome:
    """Run the derivative-based gradient search with noise-floor verification."""
    stride = ctx.param_int("stride")
    result = gradient_descent_search(
        ctx.evaluator,
        max_idx=ctx.max_idx,
        start_idx=ctx.optional_index("start_idx"),
        alpha=ctx.param_float("alpha"),
        delta=ctx.param_int("delta"),
        max_iter=ctx.param_int("max_iter"),
        verify_dist=ctx.param_int("verify_dist"),
        verify_k=ctx.param_float("verify_k"),
        max_restarts=ctx.param_int("max_restarts"),
        verify_peaks=ctx.param_bool("verify_peaks"),
        stride=stride,
        fmo_name=ctx.measure.key,
    )
    return SearchOutcome(result, fine_stride=stride)


def _run_coarse_quadratic(ctx: RunContext, coarse_method: str) -> SearchOutcome:
    """Run a coarse search followed by the built-in fine quadratic fit.

    Args:
        ctx: The run context.
        coarse_method: ``"gradient"`` or ``"grid"``; the two GUI entries differ
            only in this value.
    """
    fine_stride = ctx.param_int("fine_stride")
    result = coarse_quadratic_search(
        ctx.evaluator,
        max_idx=ctx.max_idx,
        coarse_method=coarse_method,
        half_window=max(MIN_HALF_WINDOW, ctx.param_int("half_window")),
        start_idx=ctx.optional_index("start_idx"),
        alpha=ctx.param_float("alpha"),
        delta=ctx.param_int("delta"),
        verify_dist=ctx.param_int("verify_dist"),
        verify_k=ctx.param_float("verify_k"),
        max_restarts=ctx.param_int("max_restarts"),
        coarse_step=ctx.optional_positive("coarse_step"),
        coarse_stride=ctx.param_int("coarse_stride"),
        fine_stride=fine_stride,
        coarse_fmo=ctx.measure.key,
        fine_fmo=ctx.measure.key,
        # Working distances in millimetres, so that fine_wd comes back in mm.
        wd=ctx.wd_mm,
    )
    return SearchOutcome(result, fine_stride=fine_stride)


# -------------------------------------------------------------- shared params


def _stride_param(name: str, label: str, default: int, tooltip: str) -> ParamSpec:
    """Build a pixel-stride parameter."""
    return ParamSpec(name, label, "int", default, minimum=1, maximum=16, step=1,
                     tooltip=tooltip)


_FIRST_FRAME = ParamSpec(
    "first_frame", "First probe frame", "int", AUTO, minimum=AUTO, maximum=100_000, step=1,
    tooltip="Frame probed before the scan starts. -1 probes nothing first.",
)

_START_IDX = ParamSpec(
    "start_idx", "Start frame", "int", AUTO, minimum=AUTO, maximum=100_000, step=1,
    tooltip="Where the gradient climb starts. -1 starts in the middle of the stack.",
)

_ALPHA = ParamSpec(
    "alpha", "Initial step alpha (frames)", "float", 24.0,
    minimum=1.0, maximum=200.0, step=1.0, decimals=1,
    tooltip="First step length of the climb. It is halved on every overshoot.",
)

_DELTA = ParamSpec(
    "delta", "Min. derivative span delta", "int", 3, minimum=1, maximum=50, step=1,
    tooltip="Smallest half span of the centred finite difference, in frames. "
            "A wider span ignores noise ripples but blurs the peak.",
)

_VERIFY_DIST = ParamSpec(
    "verify_dist", "Verify probe distance", "int", 10, minimum=1, maximum=200, step=1,
    tooltip="Distance to the probes that check the peak against the noise floor.",
)

_VERIFY_K = ParamSpec(
    "verify_k", "Verify threshold k", "float", 3.0, minimum=0.0, maximum=20.0,
    step=0.5, decimals=1,
    tooltip="A peak counts as real when it stands k noise sigmas above the probes.",
)

_MAX_RESTARTS = ParamSpec(
    "max_restarts", "Max restarts", "int", 8, minimum=0, maximum=50, step=1,
    tooltip="How often the search may relocate to another basin after a failed check.",
)

_COARSE_STEP = ParamSpec(
    "coarse_step", "Coarse step (frames)", "int", 0, minimum=0, maximum=1000, step=1,
    tooltip="Spacing of the coarse grid. 0 uses max(3, sqrt(frame count)).",
)

_HALF_WINDOW = ParamSpec(
    "half_window", "Fit half window (frames)", "int", DEFAULT_HALF_WINDOW,
    minimum=MIN_HALF_WINDOW, maximum=100, step=1,
    tooltip="Frames taken on each side of the coarse peak for the parabola. "
            "The fit needs at least 5 samples, so the minimum is 2.",
)


@dataclass(frozen=True)
class AlgorithmSpec:
    """One selectable search algorithm.

    Attributes:
        key: Stable identifier used in results, exports and session files.
        display_name: Text shown in the GUI.
        description: One paragraph shown as a tooltip and in the Run tab.
        params: Editable parameters, in form order.
        runner: Calls the underlying search and returns a :class:`SearchOutcome`.
        produces_fine: Whether the search already returns a sub-frame result,
            in which case no extra fit is added.
        is_baseline: Whether this is the exhaustive scan the others are compared to.
    """

    key: str
    display_name: str
    description: str
    params: tuple[ParamSpec, ...]
    runner: Callable[[RunContext], SearchOutcome]
    produces_fine: bool = False
    is_baseline: bool = False

    def defaults(self) -> dict[str, Any]:
        """Default value of every parameter, ready for the GUI form."""
        return {spec.name: spec.default for spec in self.params}


_SPECS: tuple[AlgorithmSpec, ...] = (
    AlgorithmSpec(
        key="global_scan",
        display_name="Global Scan (exhaustive)",
        description=(
            "Scores every frame of the stack. Always finds the true peak, and "
            "reads 100% of the frames, so it is the reference the other "
            "searches are measured against."
        ),
        params=(
            _stride_param("stride", "Pixel stride", 1,
                          "Subsampling of the frame. 1 is full resolution."),
            _FIRST_FRAME,
        ),
        runner=_run_global_scan,
        is_baseline=True,
    ),
    AlgorithmSpec(
        key="coarse_and_fine",
        display_name="Coarse-and-Fine Hybrid",
        description=(
            "Stage 1 sweeps a sparse grid at a large pixel stride to find the "
            "basin of the peak. Stage 2 refines inside that basin at full "
            "resolution and confirms the peak with its two neighbours."
        ),
        params=(
            _COARSE_STEP,
            _stride_param("coarse_stride", "Coarse pixel stride", 4,
                          "Subsampling during the coarse sweep. Larger is faster."),
            _stride_param("fine_stride", "Fine pixel stride", 1,
                          "Subsampling during the fine bracket. 1 is full resolution."),
            _FIRST_FRAME,
        ),
        runner=_run_coarse_and_fine,
    ),
    AlgorithmSpec(
        key="gradient",
        display_name="Gradient Search",
        description=(
            "Climbs the focus curve using centred finite differences, halving "
            "its step on every overshoot. The candidate peak is then checked "
            "against the measured noise floor, and the search relocates to "
            "another basin when that check fails."
        ),
        params=(
            _START_IDX,
            _ALPHA,
            _DELTA,
            ParamSpec("max_iter", "Max iterations", "int", 80, minimum=1, maximum=1000,
                      step=10, tooltip="Upper bound on the steps of one climb."),
            ParamSpec("verify_peaks", "Verify peak against noise", "bool", True,
                      tooltip="Switch the fake-maximum rejection on or off."),
            _VERIFY_DIST,
            _VERIFY_K,
            _MAX_RESTARTS,
            _stride_param("stride", "Pixel stride", 1,
                          "Subsampling of the frame. 1 is full resolution."),
        ),
        runner=_run_gradient,
    ),
    AlgorithmSpec(
        key="coarse_quadratic_gradient",
        display_name="Coarse (gradient) + Quadratic Fit",
        description=(
            "Gradient search for the discrete peak, then a parabola through a "
            "window around it for the sub-frame working distance. This is the "
            "full two-stage answer the assignment asks for."
        ),
        params=(
            _HALF_WINDOW,
            _START_IDX,
            _ALPHA,
            _DELTA,
            _VERIFY_DIST,
            _VERIFY_K,
            _MAX_RESTARTS,
            _stride_param("coarse_stride", "Coarse pixel stride", 1,
                          "Subsampling during the coarse stage. Keep it at 1: the "
                          "fit reuses these scores, so a different stride would "
                          "mix two resolutions in one parabola."),
            _stride_param("fine_stride", "Fine pixel stride", 1,
                          "Subsampling during the fit. 1 is full resolution."),
            _COARSE_STEP,
        ),
        runner=lambda ctx: _run_coarse_quadratic(ctx, "gradient"),
        produces_fine=True,
    ),
    AlgorithmSpec(
        key="coarse_quadratic_grid",
        display_name="Coarse (grid) + Quadratic Fit",
        description=(
            "Sparse grid sweep for the discrete peak, then the same parabola "
            "refinement. The grid has no noise check, so it is the simpler and "
            "more predictable sibling of the gradient variant."
        ),
        params=(
            _HALF_WINDOW,
            _COARSE_STEP,
            _stride_param("coarse_stride", "Coarse pixel stride", 1,
                          "Subsampling during the grid sweep. Keep it at 1: the "
                          "fit reuses these scores."),
            _stride_param("fine_stride", "Fine pixel stride", 1,
                          "Subsampling during the fit. 1 is full resolution."),
            _START_IDX,
            _ALPHA,
            _DELTA,
            _VERIFY_DIST,
            _VERIFY_K,
            _MAX_RESTARTS,
        ),
        runner=lambda ctx: _run_coarse_quadratic(ctx, "grid"),
        produces_fine=True,
    ),
)

#: Read-only mapping of key -> :class:`AlgorithmSpec`, in GUI order.
ALGORITHMS: Mapping[str, AlgorithmSpec] = MappingProxyType(
    {spec.key: spec for spec in _SPECS}
)

#: Key of the exhaustive scan, used as the baseline of every comparison.
BASELINE_KEY = "global_scan"

#: Key the GUI preselects: the complete coarse-plus-fine answer.
DEFAULT_ALGORITHM_KEY = "coarse_quadratic_gradient"


def algorithm_keys() -> list[str]:
    """Keys of every algorithm, in GUI order."""
    return [spec.key for spec in _SPECS]


def require(key: str) -> AlgorithmSpec:
    """Look an algorithm up by key.

    Args:
        key: Registry key.

    Returns:
        The matching entry.

    Raises:
        KeyError: If no entry has that key.
    """
    if key not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm '{key}'. Known: {', '.join(ALGORITHMS)}.")
    return ALGORITHMS[key]


# --------------------------------------------------------------------- adapter


def _history_indices(result: Any) -> tuple[int, ...]:
    """Frame indices in probe order, read from a search's history log.

    Args:
        result: Any search result that carries a ``history`` list.

    Returns:
        The visited indices, in order, duplicates kept.
    """
    history = getattr(result, "history", None) or []
    indices: list[int] = []
    for entry in history:
        if isinstance(entry, Mapping) and "idx" in entry:
            indices.append(int(entry["idx"]))
    return tuple(indices)


def _as_float(value: Any) -> float:
    """Convert a value to ``float``, mapping anything unusable to ``nan``."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number


def _coefficients(value: Any) -> Optional[tuple[float, float, float]]:
    """Normalise parabola coefficients into a 3-tuple, or ``None``."""
    if value is None:
        return None
    try:
        a0, a1, a2 = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    return a0, a1, a2


def _window(value: Any) -> Optional[tuple[int, int]]:
    """Normalise a fit window into an ``(lo, hi)`` tuple, or ``None``."""
    if value is None:
        return None
    try:
        lo, hi = (int(item) for item in value)
    except (TypeError, ValueError):
        return None
    return lo, hi


def _refine_with_quadratic_fit(
    ctx: RunContext, coarse_idx: int, fine_stride: int
) -> tuple[Any, dict[int, float]]:
    """Add a quadratic fit to a search that returned no sub-frame result.

    The seed dictionary is a single-resolution snapshot taken from the
    evaluator, never the search's own ``evals``: the hybrid search mixes a
    coarse stride and a fine stride in that dictionary, and a parabola fitted
    through two resolutions would put its vertex in the wrong place.

    Args:
        ctx: The run context.
        coarse_idx: Discrete peak the search settled on.
        fine_stride: Stride the reused scores must have been taken at.

    Returns:
        A ``(fit result, points used)`` pair.
    """
    seed_scores = ctx.evaluator.scores_for(stride=fine_stride, measure_key=ctx.measure.key)
    fit = quadratic_fit(
        ctx.evaluator,
        coarse_idx=coarse_idx,
        max_idx=ctx.max_idx,
        half_window=max(MIN_HALF_WINDOW, ctx.fit_half_window),
        wd=ctx.wd_mm,
        evals=seed_scores,  # quadratic_fit fills this dictionary in place.
        stride=fine_stride,
        fmo_name=ctx.measure.key,
    )
    points = {idx: seed_scores[idx] for idx in range(fit.lo, fit.hi + 1) if idx in seed_scores}
    return fit, points


def _extra_fit_visits(
    visited: tuple[int, ...], window: Optional[tuple[int, int]]
) -> tuple[int, ...]:
    """Frames the added fit read that the search had not probed before.

    Args:
        visited: Frames the search itself probed, in order.
        window: Inclusive frame range the fit covered.

    Returns:
        The new frames in ascending order, ready to append to ``visited``.
    """
    if window is None:
        return ()
    already = set(visited)
    lo, hi = window
    return tuple(idx for idx in range(lo, hi + 1) if idx not in already)


def _fit_points_from_window(
    ctx: RunContext, window: Optional[tuple[int, int]], fine_stride: int
) -> dict[int, float]:
    """Collect the scores inside a fit window, at one single resolution."""
    if window is None:
        return {}
    scores = ctx.evaluator.scores_for(stride=fine_stride, measure_key=ctx.measure.key)
    lo, hi = window
    return {idx: scores[idx] for idx in range(lo, hi + 1) if idx in scores}


def run_algorithm(spec: AlgorithmSpec, ctx: RunContext) -> RunResult:
    """Run one algorithm and flatten its outcome into a :class:`RunResult`.

    The measured time covers the search and, when one is added, the fine
    quadratic fit, because together they are what produces the position the
    assignment asks for.

    Args:
        spec: Registry entry to run.
        ctx: Image set, evaluator, parameters and ground-truth reference.

    Returns:
        The unified record of this run.

    Raises:
        Exception: Anything the underlying search or the image loader raises is
            passed through; the caller turns it into a log entry and a dialog.
    """
    started = time.perf_counter()
    outcome = spec.runner(ctx)
    result = outcome.result

    coarse_idx = int(result.best_idx)
    search_evals: Mapping[int, float] = dict(getattr(result, "evals", {}) or {})
    visited = _history_indices(result)

    # Some searches already refine to a sub-frame position; the others get the
    # parabola applied here, which the Run tab can switch off.
    fine_idx = _as_float(getattr(result, "fine_idx", float("nan")))
    fit_ok = bool(getattr(result, "fit_ok", False))
    fit_r2 = _as_float(getattr(result, "fit_r2", float("nan")))
    fit_coeffs = _coefficients(getattr(result, "fit_coeffs", None))
    fit_window = _window(getattr(result, "fit_window", None))
    fit_message = str(getattr(result, "fit_message", ""))
    fine_wd_mm = _as_float(getattr(result, "fine_wd", float("nan")))
    fine_value = _as_float(getattr(result, "fine_value", float("nan")))
    fit_points = _fit_points_from_window(ctx, fit_window, outcome.fine_stride)
    fit_added = False

    if math.isnan(fine_idx) and ctx.apply_fit:
        fit, fit_points = _refine_with_quadratic_fit(ctx, coarse_idx, outcome.fine_stride)
        fit_added = True
        fine_idx = _as_float(fit.idx)
        fine_wd_mm = _as_float(fit.wd)
        fine_value = _as_float(fit.value)
        fit_ok = bool(fit.ok)
        fit_r2 = _as_float(fit.r2)
        fit_coeffs = _coefficients(fit.coeffs)
        fit_window = (int(fit.lo), int(fit.hi))
        fit_message = str(fit.msg)
        # The fit reads frames of its own, which the search's history never saw.
        # They belong in the visited list, otherwise the focus-curve plot would
        # show fewer markers than the reported frame count.
        visited += _extra_fit_visits(visited, fit_window)

    elapsed = time.perf_counter() - started

    coarse_value = _as_float(search_evals.get(coarse_idx, float("nan")))
    if math.isnan(coarse_value):
        # The hybrid search can pick a frame whose stored score came from the
        # coarse stride; ask the evaluator for the full-resolution score.
        coarse_value = ctx.evaluator(coarse_idx, 1, ctx.measure.key)
    coarse_wd_mm = float(ctx.wd_mm[coarse_idx])

    errors = _compute_errors(ctx, coarse_idx, fine_idx, fit_ok)

    return RunResult(
        algorithm=spec.display_name,
        algorithm_key=spec.key,
        dataset_label=ctx.dataset.label,
        dataset_key=ctx.dataset.key,
        measure=ctx.measure.display_name,
        measure_key=ctx.measure.key,
        coarse_idx=coarse_idx,
        coarse_value=coarse_value,
        coarse_wd_mm=coarse_wd_mm,
        fine_idx=fine_idx,
        fine_wd_mm=fine_wd_mm,
        fine_value=fine_value,
        fit_ok=fit_ok,
        fit_r2=fit_r2,
        fit_coeffs=fit_coeffs,
        fit_window=fit_window,
        fit_message=fit_message,
        fit_points=fit_points,
        fit_applied_afterwards=fit_added,
        frames_evaluated=ctx.evaluator.unique_frames,
        search_frames=len(search_evals),
        eval_calls=ctx.evaluator.eval_calls,
        visited=visited,
        evals=search_evals,
        elapsed_s=elapsed,
        error_frames=errors[0],
        error_um=errors[1],
        coarse_error_frames=errors[2],
        coarse_error_um=errors[3],
        gt_idx=ctx.ground_truth.peak_idx if ctx.ground_truth else -1,
        gt_reference_idx=(
            ctx.ground_truth.reference_idx if ctx.ground_truth else float("nan")
        ),
        verified=getattr(result, "verified", None),
        restarts=int(getattr(result, "restarts", 0) or 0),
        noise_sigma_estimate=_as_float(getattr(result, "noise_sigma", float("nan"))),
        noise_sigma=ctx.noise_sigma,
        seed=ctx.seed,
        repeats=ctx.repeats,
        extra={"params": dict(ctx.params), "fine_stride": outcome.fine_stride},
    )


def _compute_errors(
    ctx: RunContext, coarse_idx: int, fine_idx: float, fit_ok: bool
) -> tuple[float, float, float, float]:
    """Errors of the coarse and the best position against the ground truth.

    Args:
        ctx: The run context, which carries the reference.
        coarse_idx: Discrete peak the search found.
        fine_idx: Sub-frame peak, possibly ``nan``.
        fit_ok: Whether the sub-frame peak is trustworthy.

    Returns:
        ``(error_frames, error_um, coarse_error_frames, coarse_error_um)``, all
        ``nan`` when no reference is available.
    """
    reference = ctx.ground_truth
    if reference is None:
        return float("nan"), float("nan"), float("nan"), float("nan")

    best = fine_idx if fit_ok and not math.isnan(fine_idx) else float(coarse_idx)
    best_error = position_error(best, reference.reference_idx, reference.step_um)
    coarse_error = position_error(float(coarse_idx), reference.reference_idx, reference.step_um)
    return best_error[0], best_error[1], coarse_error[0], coarse_error[1]
