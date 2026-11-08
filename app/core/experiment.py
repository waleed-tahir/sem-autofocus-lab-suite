"""Ground truth and the runnable jobs of the application.

Everything the user can start from the GUI is expressed here as a *job*: a plain
object with an :meth:`execute` method that reports progress through callbacks and
checks for cancellation between steps.  The Qt worker in
:mod:`app.workers.run_worker` only has to run a job, which keeps all Qt code out
of this module.

Main contents:
    * :class:`GroundTruth` -- the exhaustive reference curve of one image set
      and one focus measure.
    * :class:`JobContext` -- progress, logging and cancellation callbacks.
    * :class:`JobOutcome` -- what every job returns.
    * :class:`AlgorithmRunJob` -- N algorithms x M image sets (the Run tab).
    * :class:`GroundTruthJob` -- reference curves for the speed comparison.
    * :class:`MeasureSweepJob` -- all focus measures on one image set.
    * :class:`RobustnessJob` -- the same runs over a range of noise levels.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from app.core.algorithms import (
    AlgorithmSpec,
    GroundTruthRef,
    RunContext,
    run_algorithm,
)
from app.core.algorithms import (
    require as require_algorithm,
)
from app.core.curve_stats import CurveStats
from app.core.dataset import Dataset
from app.core.disk_cache import (
    load_cached_ground_truth,
    load_cached_run,
    save_cached_ground_truth,
    save_cached_run,
)
from app.core.evaluator import make_eval_func
from app.core.focus_measures import FocusMeasure
from app.core.focus_measures import require as require_measure
from app.core.run_result import RunResult
from autofocus.algorithms import global_scan_search, quadratic_fit

LOGGER = logging.getLogger(__name__)

#: Half window used when the reference curve is refined to a sub-frame vertex.
GROUND_TRUTH_HALF_WINDOW = 12

#: A run counts as successful in the robustness test when it lands this close.
SUCCESS_TOLERANCE_FRAMES = 1.0


class JobCancelledError(Exception):
    """Raised inside a job when the user pressed Cancel."""


def _ignore_progress(done: int, total: int, message: str) -> None:
    """Default progress sink, used when a job runs without a GUI."""
    del done, total, message


def _ignore_message(message: str) -> None:
    """Default log sink, used when a job runs without a GUI."""
    del message


def _never_cancelled() -> bool:
    """Default cancellation check: a job without a GUI runs to the end."""
    return False


@dataclass(frozen=True)
class GroundTruth:
    """Exhaustive reference scan of one image set with one focus measure.

    The curve is produced by ``global_scan_search`` at full resolution, so it
    holds a score for every frame.  Its peak is what every other search is
    compared against.

    Attributes:
        dataset_key: Folder path of the image set.
        dataset_label: Display name of the image set.
        speed: SEM scanning speed of the image set, or ``None``.
        measure_key: Registry key of the focus measure.
        measure_name: Display name of the focus measure.
        curve: Focus score of every frame, index aligned.
        wd_mm: Working distance of every frame, in millimetres.
        peak_idx: Index of the highest score.
        reference_idx: Sub-frame vertex of the curve when its fit held,
            otherwise :attr:`peak_idx`.  Errors are measured against this.
        reference_wd_mm: Working distance of :attr:`reference_idx`.
        fit_ok: Whether the sub-frame refinement of the curve succeeded.
        fit_r2: Goodness of fit of that refinement.
        step_um: Average stage step of the image set, in micrometres.
        elapsed_s: Time the scan took.
        stats: Width, noise and local-maximum descriptors of the curve.
    """

    dataset_key: str
    dataset_label: str
    speed: Optional[int]
    measure_key: str
    measure_name: str
    curve: np.ndarray
    wd_mm: np.ndarray
    peak_idx: int
    reference_idx: float
    reference_wd_mm: float
    fit_ok: bool
    fit_r2: float
    step_um: float
    elapsed_s: float
    stats: CurveStats

    @property
    def cache_key(self) -> tuple[str, str]:
        """Key the reference is cached under: image set plus focus measure."""
        return self.dataset_key, self.measure_key

    @property
    def peak_value(self) -> float:
        """Focus score at :attr:`peak_idx`."""
        return float(self.curve[self.peak_idx])

    @property
    def peak_wd_mm(self) -> float:
        """Working distance of :attr:`peak_idx`, in millimetres."""
        return float(self.wd_mm[self.peak_idx])

    @property
    def frame_count(self) -> int:
        """Number of frames the reference scan covered."""
        return int(self.curve.size)

    def as_reference(self) -> GroundTruthRef:
        """Shrink this record to what the error computation needs."""
        return GroundTruthRef(
            peak_idx=self.peak_idx,
            reference_idx=self.reference_idx,
            step_um=self.step_um,
        )


def compute_ground_truth(
    dataset: Dataset,
    measure: FocusMeasure,
    progress: Optional[Callable[[int, int], None]] = None,
) -> GroundTruth:
    """Scan one image set exhaustively to build its reference curve.

    Args:
        dataset: Image set to scan.
        measure: Focus measure to score the frames with.
        progress: Optional ``(done, total) -> None`` callback; raise
            :class:`JobCancelledError` from it to stop the scan.

    Returns:
        The filled :class:`GroundTruth`.

    Raises:
        DatasetError: If a frame cannot be read.
        JobCancelledError: If ``progress`` raises it.
    """
    wd_mm = dataset.working_distances()
    evaluator = make_eval_func(dataset, measure)
    total = dataset.frame_count

    def reporting_eval(idx: int, stride: int = 1, fmo_name: Optional[str] = None) -> float:
        """Score one frame and report how far the scan got."""
        value = evaluator(idx, stride, fmo_name)
        if progress is not None:
            progress(evaluator.unique_frames, total)
        return value

    started = time.perf_counter()
    scan = global_scan_search(
        reporting_eval, max_idx=dataset.max_idx, stride=1, fmo_name=measure.key
    )
    elapsed = time.perf_counter() - started

    curve = np.array([scan.evals[idx] for idx in range(dataset.frame_count)], dtype=np.float64)

    # Refine the reference peak itself, so a sub-frame result is compared with a
    # sub-frame reference instead of with a rounded frame index.  The fit reads
    # the curve that is already in memory and costs no extra frame.
    def read_curve(idx: int, stride: int = 1, fmo_name: Optional[str] = None) -> float:
        """Serve an already-computed score out of the curve.

        ``stride`` and ``fmo_name`` are unused but must stay in the signature:
        the search package inspects the parameter count to decide how to call an
        evaluation function, and a two-argument function would be called wrongly.
        """
        del stride, fmo_name  # The whole curve was scanned at full resolution.
        return float(curve[int(idx)])

    fit = quadratic_fit(
        read_curve,
        coarse_idx=int(scan.best_idx),
        max_idx=dataset.max_idx,
        half_window=GROUND_TRUTH_HALF_WINDOW,
        wd=wd_mm,
        evals={idx: float(value) for idx, value in enumerate(curve)},
        stride=1,
        fmo_name=measure.key,
    )
    reference_idx = float(fit.idx) if fit.ok else float(scan.best_idx)
    reference_wd = float(fit.wd) if fit.ok else float(wd_mm[scan.best_idx])

    return GroundTruth(
        dataset_key=dataset.key,
        dataset_label=dataset.label,
        speed=dataset.speed,
        measure_key=measure.key,
        measure_name=measure.display_name,
        curve=curve,
        wd_mm=wd_mm,
        peak_idx=int(scan.best_idx),
        reference_idx=reference_idx,
        reference_wd_mm=reference_wd,
        fit_ok=bool(fit.ok),
        fit_r2=float(fit.r2),
        step_um=dataset.measured_step_um(),
        elapsed_s=elapsed,
        stats=CurveStats.of(curve),
    )


@dataclass
class JobContext:
    """Callbacks a job uses to talk to the GUI.

    Attributes:
        report: ``(done, total, message) -> None``, drives the progress bar.
        log: ``(message) -> None``, appends one line to the log panel.
        cancelled: ``() -> bool``, ``True`` once the user pressed Cancel.
        known_ground_truth: Reference curves computed earlier.  Jobs read from
            this snapshot and return whatever they had to compute, so the worker
            thread never mutates state the GUI thread owns.
    """

    report: Callable[[int, int, str], None] = _ignore_progress
    log: Callable[[str], None] = _ignore_message
    cancelled: Callable[[], bool] = _never_cancelled
    known_ground_truth: Mapping[tuple[str, str], GroundTruth] = field(default_factory=dict)

    def check_cancelled(self) -> None:
        """Stop the job when the user asked for it.

        Raises:
            JobCancelledError: If :attr:`cancelled` returns ``True``.
        """
        if self.cancelled():
            raise JobCancelledError("Stopped by the user.")


@dataclass
class JobOutcome:
    """What a finished job hands back to the GUI.

    Attributes:
        results: Runs the job produced.
        ground_truths: Reference curves the job had to compute; the GUI merges
            them into its cache on the main thread.
        message: One-line summary for the status bar.
    """

    results: list[RunResult] = field(default_factory=list)
    ground_truths: list[GroundTruth] = field(default_factory=list)
    message: str = ""


class _GroundTruthProvider:
    """Serves reference curves to a job, computing the missing ones once."""

    def __init__(self, ctx: JobContext) -> None:
        """Start from the snapshot the GUI handed over."""
        self._ctx = ctx
        self._known: dict[tuple[str, str], GroundTruth] = dict(ctx.known_ground_truth)
        self._computed: list[GroundTruth] = []

    @property
    def computed(self) -> list[GroundTruth]:
        """Reference curves this job had to compute itself."""
        return list(self._computed)

    def get(self, dataset: Dataset, measure: FocusMeasure) -> GroundTruth:
        """Return the reference curve of one image set and measure.

        Args:
            dataset: Image set.
            measure: Focus measure.

        Returns:
            The cached curve, or a freshly computed one.

        Raises:
            JobCancelledError: If the user cancels during the scan.
        """
        key = (dataset.key, measure.key)
        cached = self._known.get(key)
        if cached is not None:
            return cached

        # Check persistent disk cache before running full exhaustive scan
        disk_cached = load_cached_ground_truth(dataset, measure)
        if disk_cached is not None:
            self._known[key] = disk_cached
            self._computed.append(disk_cached)
            self._ctx.log(
                f"Loaded ground truth from disk cache: {dataset.label} with {measure.display_name} "
                f"(peak frame {disk_cached.peak_idx})."
            )
            return disk_cached

        self._ctx.log(
            f"Reference scan: {dataset.label} with {measure.display_name} "
            f"({dataset.frame_count} frames)."
        )

        def progress(done: int, total: int) -> None:
            """Forward the scan progress and honour a cancel request."""
            self._ctx.check_cancelled()
            self._ctx.report(done, total, f"Reference scan {dataset.label}: {done}/{total}")

        truth = compute_ground_truth(dataset, measure, progress=progress)
        self._known[key] = truth
        self._computed.append(truth)
        save_cached_ground_truth(truth)
        self._ctx.log(
            f"  peak at frame {truth.peak_idx} (WD {truth.peak_wd_mm:.4f} mm), "
            f"sub-frame {truth.reference_idx:.3f} in {truth.elapsed_s:.1f} s."
        )
        return truth


@dataclass(frozen=True)
class RunRequest:
    """Everything the Run tab collected from the user.

    Attributes:
        datasets: Image sets to search in.
        algorithm_keys: Registry keys of the searches to run.
        measure_key: Registry key of the focus measure.
        params: ``{algorithm key: {parameter: value}}`` from the GUI forms.
        apply_fit: Add a quadratic fit to searches that have no fine result.
        half_window: Half window of that added fit.
        noise_sigma: Gaussian noise to inject, in grey levels.
        seed: Seed of that noise.
        repeats: How often to repeat each run; the reported time is the mean.
    """

    datasets: tuple[Dataset, ...]
    algorithm_keys: tuple[str, ...]
    measure_key: str
    params: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    apply_fit: bool = True
    half_window: int = GROUND_TRUTH_HALF_WINDOW
    noise_sigma: float = 0.0
    seed: Optional[int] = None
    repeats: int = 1

    @property
    def total_runs(self) -> int:
        """Number of algorithm-on-image-set combinations."""
        return len(self.datasets) * len(self.algorithm_keys)

    def params_for(self, spec: AlgorithmSpec) -> dict[str, Any]:
        """Parameter values for one algorithm, filled up with its defaults."""
        values = spec.defaults()
        values.update(self.params.get(spec.key, {}))
        return values


def _run_once(
    spec: AlgorithmSpec,
    dataset: Dataset,
    measure: FocusMeasure,
    params: Mapping[str, Any],
    request: RunRequest,
    truth: GroundTruth,
    seed: Optional[int],
) -> RunResult:
    """Run one algorithm once, with a brand-new evaluator.

    A fresh evaluator per run is what keeps two runs from sharing focus values,
    so the reported frame counts and times belong to this run alone.

    Args:
        spec: Algorithm to run.
        dataset: Image set to search in.
        measure: Focus measure to use.
        params: Parameter values for this algorithm.
        request: The surrounding request, for the fit and noise options.
        truth: Reference curve of this image set and measure.
        seed: Seed for the injected noise.

    Returns:
        The result of this single run.
    """
    evaluator = make_eval_func(dataset, measure, noise_sigma=request.noise_sigma, seed=seed)
    ctx = RunContext(
        dataset=dataset,
        evaluator=evaluator,
        measure=measure,
        wd_mm=truth.wd_mm,
        params=params,
        apply_fit=request.apply_fit,
        fit_half_window=request.half_window,
        ground_truth=truth.as_reference(),
        noise_sigma=request.noise_sigma,
        seed=seed,
        repeats=request.repeats,
    )
    return run_algorithm(spec, ctx)


def _average_time(results: Sequence[RunResult]) -> RunResult:
    """Keep the first run but replace its time by the mean over all repeats.

    Args:
        results: Repeats of one and the same run.

    Returns:
        The first result, with :attr:`RunResult.elapsed_s` averaged.
    """
    mean_elapsed = float(np.mean([r.elapsed_s for r in results]))
    return replace(results[0], elapsed_s=mean_elapsed, repeats=len(results))


class AlgorithmRunJob:
    """Runs every selected algorithm on every selected image set.

    This is what the Run tab starts.  The reference curve of each image set is
    computed once and reused for every algorithm on that set.
    """

    def __init__(self, request: RunRequest) -> None:
        """Store the request to execute."""
        self.request = request
        self.name = "Algorithm run"

    def execute(self, ctx: JobContext) -> JobOutcome:
        """Run the request.

        Args:
            ctx: Progress, logging and cancellation callbacks.

        Returns:
            Every produced run plus the reference curves that had to be computed.

        Raises:
            JobCancelledError: If the user pressed Cancel.
        """
        request = self.request
        measure = require_measure(request.measure_key)
        truths = _GroundTruthProvider(ctx)
        results: list[RunResult] = []

        total = max(1, request.total_runs)
        done = 0
        for dataset in request.datasets:
            ctx.check_cancelled()
            truth = truths.get(dataset, measure)

            for key in request.algorithm_keys:
                ctx.check_cancelled()
                spec = require_algorithm(key)
                params = request.params_for(spec)
                ctx.report(done, total, f"{dataset.label}: {spec.display_name}")

                # Check if this exact run is already cached on disk
                cached_run = load_cached_run(
                    dataset=dataset,
                    algorithm_key=key,
                    measure_key=measure.key,
                    params=params,
                    apply_fit=request.apply_fit,
                    fit_half_window=request.half_window,
                    noise_sigma=request.noise_sigma,
                    seed=request.seed,
                )
                if cached_run is not None:
                    results.append(cached_run)
                    done += 1
                    ctx.report(done, total, f"{dataset.label}: {spec.display_name} (cached)")
                    ctx.log(f"  [Disk Cache] {cached_run.algorithm} on {dataset.label}: coarse {cached_run.coarse_idx}, {cached_run.frames_evaluated} frames.")
                    continue

                repeats: list[RunResult] = []
                for repeat in range(max(1, request.repeats)):
                    ctx.check_cancelled()
                    seed = None if request.seed is None else request.seed + repeat
                    repeats.append(
                        _run_once(spec, dataset, measure, params, request, truth, seed)
                    )

                result = _average_time(repeats)
                save_cached_run(
                    result=result,
                    params=params,
                    apply_fit=request.apply_fit,
                    fit_half_window=request.half_window,
                )
                results.append(result)
                done += 1
                ctx.report(done, total, f"{dataset.label}: {spec.display_name}")
                ctx.log(_describe(result))

        return JobOutcome(
            results=results,
            ground_truths=truths.computed,
            message=f"{len(results)} run(s) finished.",
        )


def _describe(result: RunResult) -> str:
    """One log line summarising a finished run."""
    fine = "-" if math.isnan(result.fine_idx) else f"{result.fine_idx:.3f}"
    error = "-" if math.isnan(result.error_um) else f"{result.error_um:.1f} um"
    return (
        f"  {result.algorithm}: coarse frame {result.coarse_idx} "
        f"(WD {result.coarse_wd_mm:.4f} mm), fine {fine} "
        f"(WD {result.fine_wd_mm:.5f} mm), error {error}, "
        f"{result.frames_evaluated} frames, {result.elapsed_ms:.0f} ms."
    )


class GroundTruthJob:
    """Computes the reference curves of several image sets with one measure.

    The Speed-comparison tab needs the full curve of every scanning speed, which
    is exactly a reference scan per image set.
    """

    def __init__(self, datasets: Sequence[Dataset], measure_key: str) -> None:
        """Store the image sets and the focus measure to scan with."""
        self.datasets = tuple(datasets)
        self.measure_key = measure_key
        self.name = "Reference curves"

    def execute(self, ctx: JobContext) -> JobOutcome:
        """Scan every image set.

        Args:
            ctx: Progress, logging and cancellation callbacks.

        Returns:
            The reference curves, in ``ground_truths``.

        Raises:
            JobCancelledError: If the user pressed Cancel.
        """
        measure = require_measure(self.measure_key)
        truths = _GroundTruthProvider(ctx)
        collected: list[GroundTruth] = []

        for position, dataset in enumerate(self.datasets, start=1):
            ctx.check_cancelled()
            ctx.report(position - 1, len(self.datasets), f"Scanning {dataset.label}")
            collected.append(truths.get(dataset, measure))
            ctx.report(position, len(self.datasets), f"Scanned {dataset.label}")

        return JobOutcome(
            ground_truths=truths.computed,
            message=f"{len(collected)} reference curve(s) ready.",
        )


class MeasureSweepJob:
    """Computes the reference curve of one image set with every focus measure.

    This is what the Focus-measure-comparison tab needs: five curves over the
    same frames, so their shape, width and cost can be compared directly.
    """

    def __init__(self, dataset: Dataset, measure_keys: Sequence[str]) -> None:
        """Store the image set and the focus measures to compare."""
        self.dataset = dataset
        self.measure_keys = tuple(measure_keys)
        self.name = "Focus measure sweep"

    def execute(self, ctx: JobContext) -> JobOutcome:
        """Scan the image set once per focus measure.

        Args:
            ctx: Progress, logging and cancellation callbacks.

        Returns:
            One reference curve per measure, in ``ground_truths``.

        Raises:
            JobCancelledError: If the user pressed Cancel.
        """
        truths = _GroundTruthProvider(ctx)
        collected: list[GroundTruth] = []

        for position, key in enumerate(self.measure_keys, start=1):
            ctx.check_cancelled()
            measure = require_measure(key)
            ctx.report(position - 1, len(self.measure_keys), f"Scanning {measure.display_name}")
            collected.append(truths.get(self.dataset, measure))
            ctx.report(position, len(self.measure_keys), f"Scanned {measure.display_name}")

        return JobOutcome(
            ground_truths=truths.computed,
            message=f"{len(collected)} focus-measure curve(s) ready.",
        )


@dataclass(frozen=True)
class NoiseSweep:
    """The noise levels a robustness test walks through.

    Attributes:
        max_sigma: Highest noise standard deviation, in grey levels.
        steps: How many levels to use above zero.
        repeats: Runs per level, each with a different seed.
        seed: Seed of the first run; later runs add to it.
    """

    max_sigma: float = 10.0
    steps: int = 5
    repeats: int = 3
    seed: int = 0

    def sigmas(self) -> list[float]:
        """The noise levels, starting at a clean run with sigma 0."""
        if self.steps <= 0 or self.max_sigma <= 0.0:
            return [0.0]
        span = self.max_sigma / self.steps
        return [round(index * span, 6) for index in range(self.steps + 1)]


class RobustnessJob:
    """Runs the selected algorithms over a range of injected noise levels.

    The reference curve stays the clean one: the question is how far a search
    drifts from the true peak as the frames get noisier, not where the peak of a
    noisy curve would be.
    """

    def __init__(self, request: RunRequest, sweep: NoiseSweep) -> None:
        """Store the base request and the noise levels to walk through."""
        self.request = request
        self.sweep = sweep
        self.name = "Robustness sweep"

    def execute(self, ctx: JobContext) -> JobOutcome:
        """Run every algorithm at every noise level.

        Args:
            ctx: Progress, logging and cancellation callbacks.

        Returns:
            One run per algorithm, noise level and repeat.

        Raises:
            JobCancelledError: If the user pressed Cancel.
        """
        request = self.request
        measure = require_measure(request.measure_key)
        truths = _GroundTruthProvider(ctx)
        sigmas = self.sweep.sigmas()
        results: list[RunResult] = []

        total = max(1, len(request.datasets) * len(request.algorithm_keys) * len(sigmas))
        done = 0
        for dataset in request.datasets:
            ctx.check_cancelled()
            truth = truths.get(dataset, measure)

            for key in request.algorithm_keys:
                spec = require_algorithm(key)
                params = request.params_for(spec)

                for sigma in sigmas:
                    ctx.check_cancelled()
                    label = f"{dataset.label}: {spec.display_name}, sigma {sigma:g}"
                    ctx.report(done, total, label)
                    noisy_request = replace(request, noise_sigma=sigma)

                    for repeat in range(max(1, self.sweep.repeats)):
                        ctx.check_cancelled()
                        seed = self.sweep.seed + repeat
                        results.append(
                            _run_once(
                                spec, dataset, measure, params, noisy_request, truth, seed
                            )
                        )

                    done += 1
                    ctx.report(done, total, label)

                ctx.log(f"  {spec.display_name} on {dataset.label}: {len(sigmas)} noise level(s).")

        return JobOutcome(
            results=results,
            ground_truths=truths.computed,
            message=f"{len(results)} robustness run(s) finished.",
        )


@dataclass(frozen=True)
class RobustnessPoint:
    """Aggregated robustness figures for one algorithm at one noise level.

    Attributes:
        algorithm_key: Registry key of the algorithm.
        algorithm: Display name of the algorithm.
        noise_sigma: Noise level, in grey levels.
        mean_error_um: Mean position error over the repeats, in micrometres.
        max_error_um: Worst position error over the repeats, in micrometres.
        success_rate: Share of repeats that landed within one frame.
        runs: How many repeats went into these numbers.
    """

    algorithm_key: str
    algorithm: str
    noise_sigma: float
    mean_error_um: float
    max_error_um: float
    success_rate: float
    runs: int


def summarise_robustness(results: Iterable[RunResult]) -> list[RobustnessPoint]:
    """Group robustness runs by algorithm and noise level.

    Args:
        results: Runs produced by a :class:`RobustnessJob`.

    Returns:
        One :class:`RobustnessPoint` per algorithm and noise level, ordered by
        algorithm and then by rising noise.
    """
    grouped: dict[tuple[str, float], list[RunResult]] = {}
    for result in results:
        grouped.setdefault((result.algorithm_key, result.noise_sigma), []).append(result)

    points: list[RobustnessPoint] = []
    for (key, sigma), runs in grouped.items():
        errors = np.array([run.error_um for run in runs], dtype=np.float64)
        frame_errors = np.array([run.error_frames for run in runs], dtype=np.float64)
        successes = np.count_nonzero(frame_errors <= SUCCESS_TOLERANCE_FRAMES)
        points.append(
            RobustnessPoint(
                algorithm_key=key,
                algorithm=runs[0].algorithm,
                noise_sigma=sigma,
                mean_error_um=float(np.nanmean(errors)),
                max_error_um=float(np.nanmax(errors)),
                success_rate=successes / len(runs),
                runs=len(runs),
            )
        )
    return sorted(points, key=lambda point: (point.algorithm, point.noise_sigma))
