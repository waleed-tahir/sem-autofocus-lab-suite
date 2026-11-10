"""Registry of search algorithms and adapters.

Lab Submission Edition:
- Global Scan (exhaustive linear scan, baseline reference)
- Gradient Search (adaptive centred finite differences with noise floor check)
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
    global_scan_search,
    gradient_descent_search,
    quadratic_fit,
)

LOGGER = logging.getLogger(__name__)

MIN_HALF_WINDOW = 2
DEFAULT_HALF_WINDOW = 12
AUTO = -1


@dataclass(frozen=True)
class ParamSpec:
    """One editable algorithm parameter, and how the GUI should show it."""

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
    """The reference an error is measured against."""

    peak_idx: int
    reference_idx: float
    step_um: float


@dataclass(frozen=True)
class RunContext:
    """Everything one algorithm run needs."""

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
        return self.dataset.max_idx

    def param_int(self, name: str) -> int:
        return int(self.params[name])

    def param_float(self, name: str) -> float:
        return float(self.params[name])

    def param_bool(self, name: str) -> bool:
        return bool(self.params[name])

    def optional_index(self, name: str) -> Optional[int]:
        value = int(self.params[name])
        return None if value < 0 else value

    def optional_positive(self, name: str) -> Optional[int]:
        value = int(self.params[name])
        return None if value <= 0 else value


@dataclass
class SearchOutcome:
    """What a runner hands back to the adapter."""

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


def _run_gradient(ctx: RunContext) -> SearchOutcome:
    """Run the laboratory Coarse-to-Fine Gradient Ascent search."""
    stride = ctx.param_int("stride")
    result = gradient_descent_search(
        ctx.evaluator,
        max_idx=ctx.max_idx,
        start_idx=ctx.optional_index("start_idx") if ctx.params.get("start_idx", 12) >= 0 else 12,
        coarse_step=ctx.param_int("coarse_step"),
        decay=ctx.param_float("decay"),
        adaptive=ctx.param_bool("adaptive"),
        stride=stride,
        fmo_name=ctx.measure.key,
    )
    return SearchOutcome(result, fine_stride=stride)


# -------------------------------------------------------------- shared params


def _stride_param(name: str, label: str, default: int, tooltip: str) -> ParamSpec:
    return ParamSpec(name, label, "int", default, minimum=1, maximum=16, step=1, tooltip=tooltip)


_FIRST_FRAME = ParamSpec(
    "first_frame", "First probe frame", "int", AUTO, minimum=AUTO, maximum=100_000, step=1,
    tooltip="Frame probed before the scan starts. -1 probes nothing first.",
)

_START_IDX = ParamSpec(
    "start_idx", "Initial Start Plane (Z_0)", "int", 12, minimum=0, maximum=100_000, step=1,
    tooltip="Initial focal plane position Z_0.",
)

_COARSE_STEP = ParamSpec(
    "coarse_step", "Coarse Step Size (ΔZ)", "int", 14, minimum=2, maximum=100, step=1,
    tooltip="Coarse ascent step size along ascending gradient.",
)

_DECAY = ParamSpec(
    "decay", "Refinement Decay (α_decay)", "float", 0.50, minimum=0.1, maximum=0.9,
    step=0.05, decimals=2,
    tooltip="Step decay factor for fine refinement.",
)

_ADAPTIVE = ParamSpec(
    "adaptive", "Adaptive Gradient Step", "bool", False,
    tooltip="Scales coarse step dynamically by local slope |d(NV)/dZ|.",
)


@dataclass(frozen=True)
class AlgorithmSpec:
    """One selectable search algorithm."""

    key: str
    display_name: str
    description: str
    params: tuple[ParamSpec, ...]
    runner: Callable[[RunContext], SearchOutcome]
    produces_fine: bool = False
    is_baseline: bool = False

    def defaults(self) -> dict[str, Any]:
        return {spec.name: spec.default for spec in self.params}


_SPECS: tuple[AlgorithmSpec, ...] = (
    AlgorithmSpec(
        key="global_scan",
        display_name="Global Scan (exhaustive)",
        description=(
            "Scores every frame of the stack. Always finds the true peak, and "
            "reads 100% of the frames, serving as the ground-truth baseline."
        ),
        params=(
            _stride_param("stride", "Pixel stride", 1, "Subsampling of the frame. 1 is full resolution."),
            _FIRST_FRAME,
        ),
        runner=_run_global_scan,
        is_baseline=True,
    ),
    AlgorithmSpec(
        key="gradient",
        display_name="Gradient Search",
        description=(
            "Coarse-to-fine gradient ascent: probes initial slope, climbs along "
            "ascending gradient, reverses on overshoot, and refines peak with decayed steps."
        ),
        params=(
            _START_IDX,
            _COARSE_STEP,
            _DECAY,
            _ADAPTIVE,
            _stride_param("stride", "Pixel stride", 1, "Subsampling of the frame. 1 is full resolution."),
        ),
        runner=_run_gradient,
    ),
)

ALGORITHMS: Mapping[str, AlgorithmSpec] = MappingProxyType(
    {spec.key: spec for spec in _SPECS}
)

BASELINE_KEY = "global_scan"
DEFAULT_ALGORITHM_KEY = "global_scan"


def algorithm_keys() -> list[str]:
    return [spec.key for spec in _SPECS]


def require(key: str) -> AlgorithmSpec:
    if key not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm '{key}'. Known: {', '.join(ALGORITHMS)}.")
    return ALGORITHMS[key]


# --------------------------------------------------------------------- adapter


def _history_indices(result: Any) -> tuple[int, ...]:
    history = getattr(result, "history", None) or []
    indices: list[int] = []
    for entry in history:
        if isinstance(entry, Mapping) and "idx" in entry:
            indices.append(int(entry["idx"]))
    return tuple(indices)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _coefficients(value: Any) -> Optional[tuple[float, float, float]]:
    if value is None:
        return None
    try:
        a0, a1, a2 = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    return a0, a1, a2


def _window(value: Any) -> Optional[tuple[int, int]]:
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
    seed_scores = ctx.evaluator.scores_for(stride=fine_stride, measure_key=ctx.measure.key)
    fit = quadratic_fit(
        ctx.evaluator,
        coarse_idx=coarse_idx,
        max_idx=ctx.max_idx,
        half_window=max(MIN_HALF_WINDOW, ctx.fit_half_window),
        wd=ctx.wd_mm,
        evals=seed_scores,
        stride=fine_stride,
        fmo_name=ctx.measure.key,
    )
    points = {idx: seed_scores[idx] for idx in range(fit.lo, fit.hi + 1) if idx in seed_scores}
    return fit, points


def _extra_fit_visits(
    visited: tuple[int, ...], window: Optional[tuple[int, int]]
) -> tuple[int, ...]:
    if window is None:
        return ()
    already = set(visited)
    lo, hi = window
    return tuple(idx for idx in range(lo, hi + 1) if idx not in already)


def _fit_points_from_window(
    ctx: RunContext, window: Optional[tuple[int, int]], fine_stride: int
) -> dict[int, float]:
    if window is None:
        return {}
    scores = ctx.evaluator.scores_for(stride=fine_stride, measure_key=ctx.measure.key)
    lo, hi = window
    return {idx: scores[idx] for idx in range(lo, hi + 1) if idx in scores}


def run_algorithm(spec: AlgorithmSpec, ctx: RunContext) -> RunResult:
    started = time.perf_counter()
    outcome = spec.runner(ctx)
    result = outcome.result

    coarse_idx = int(result.best_idx)
    search_evals: Mapping[int, float] = dict(getattr(result, "evals", {}) or {})
    visited = _history_indices(result)

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
        visited += _extra_fit_visits(visited, fit_window)

    elapsed = time.perf_counter() - started

    coarse_value = _as_float(search_evals.get(coarse_idx, float("nan")))
    if math.isnan(coarse_value):
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
        extra={
            "params": dict(ctx.params),
            "fine_stride": outcome.fine_stride,
            "history": getattr(result, "history", []),
        },
    )


def _compute_errors(
    ctx: RunContext, coarse_idx: int, fine_idx: float, fit_ok: bool
) -> tuple[float, float, float, float]:
    reference = ctx.ground_truth
    if reference is None:
        return float("nan"), float("nan"), float("nan"), float("nan")

    best = fine_idx if fit_ok and not math.isnan(fine_idx) else float(coarse_idx)
    best_error = position_error(best, reference.reference_idx, reference.step_um)
    coarse_error = position_error(float(coarse_idx), reference.reference_idx, reference.step_um)
    return best_error[0], best_error[1], coarse_error[0], coarse_error[1]
