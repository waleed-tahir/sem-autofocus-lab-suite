"""Simple, high-performance disk cache for ground truth reference curves and algorithm runs.

Caches computed reference curves (.npz or JSON metadata) and algorithm search runs
to disk under the local app data / cache folder so image sets and repeated searches
do not need to be recomputed across runs and restarts.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Optional

import numpy as np

if TYPE_CHECKING:
    from app.core.dataset import Dataset
    from app.core.experiment import GroundTruth, RunRequest
    from app.core.focus_measures import FocusMeasure
    from app.core.run_result import RunResult

LOGGER = logging.getLogger(__name__)

# Default persistent cache location
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache"))) / "Auto_focus_app" / "disk_cache"


def get_cache_dir() -> Path:
    """Ensure and return the disk cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


# ------------------------------------------------------------- GroundTruth Cache

def _dataset_hash(dataset: Dataset, measure_key: str) -> str:
    """Unique deterministic signature for a dataset and measure configuration."""
    folder_name = dataset.folder.name if hasattr(dataset, "folder") else dataset.label
    content = f"{folder_name}:{dataset.frame_count}:{measure_key}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def load_cached_ground_truth(dataset: Dataset, measure: FocusMeasure) -> Optional[GroundTruth]:
    """Attempt to load a precomputed GroundTruth curve from disk cache."""
    try:
        cache_dir = get_cache_dir()
        sig = _dataset_hash(dataset, measure.key)
        meta_file = cache_dir / f"gt_{sig}.json"
        data_file = cache_dir / f"gt_{sig}.npz"

        if not (meta_file.exists() and data_file.exists()):
            return None

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        data = np.load(data_file)
        wd_mm = data["wd_mm"]
        curve = data["curve"]

        from app.core.curve_stats import CurveStats
        from app.core.experiment import GroundTruth

        truth = GroundTruth(
            dataset_key=dataset.key,
            dataset_label=dataset.label,
            speed=dataset.speed,
            measure_key=meta["measure_key"],
            measure_name=meta["measure_name"],
            curve=curve,
            wd_mm=wd_mm,
            peak_idx=meta["peak_idx"],
            reference_idx=meta["reference_idx"],
            reference_wd_mm=meta["reference_wd_mm"],
            fit_ok=meta.get("fit_ok", True),
            fit_r2=meta.get("fit_r2", 1.0),
            step_um=dataset.measured_step_um() if hasattr(dataset, "measured_step_um") else 0.05,
            elapsed_s=meta.get("elapsed_s", 0.0),
            stats=CurveStats.of(curve),
        )
        LOGGER.info(f"Loaded ground truth from disk cache: {dataset.label} - {measure.display_name}")
        return truth
    except Exception as exc:
        LOGGER.warning(f"Failed to read disk cache for {dataset.label}: {exc}")
        return None


def save_cached_ground_truth(truth: GroundTruth) -> None:
    """Save a computed GroundTruth curve to disk cache."""
    try:
        cache_dir = get_cache_dir()
        folder_name = Path(truth.dataset_key).name if truth.dataset_key else truth.dataset_label
        content = f"{folder_name}:{truth.curve.size}:{truth.measure_key}"
        sig = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        meta_file = cache_dir / f"gt_{sig}.json"
        data_file = cache_dir / f"gt_{sig}.npz"

        meta = {
            "dataset_key": truth.dataset_key,
            "dataset_label": truth.dataset_label,
            "measure_key": truth.measure_key,
            "measure_name": truth.measure_name,
            "peak_idx": int(truth.peak_idx),
            "reference_idx": float(truth.reference_idx),
            "reference_wd_mm": float(truth.reference_wd_mm),
            "fit_ok": bool(truth.fit_ok),
            "fit_r2": float(truth.fit_r2),
            "elapsed_s": float(truth.elapsed_s),
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        np.savez_compressed(data_file, wd_mm=truth.wd_mm, curve=truth.curve)
        LOGGER.info(f"Saved ground truth to disk cache: {truth.dataset_label} ({sig})")
    except Exception as exc:
        LOGGER.warning(f"Failed to write disk cache for {truth.dataset_label}: {exc}")


# ------------------------------------------------------------- RunResult Cache

def _run_hash(
    dataset: Dataset,
    algorithm_key: str,
    measure_key: str,
    params: Mapping[str, Any],
    apply_fit: bool,
    fit_half_window: int,
    noise_sigma: float,
    seed: Optional[int],
) -> str:
    """Deterministic signature for an algorithm run configuration."""
    folder_name = dataset.folder.name if hasattr(dataset, "folder") else dataset.label
    params_str = json.dumps(dict(sorted(params.items())), sort_keys=True)
    content = (
        f"{folder_name}:{dataset.frame_count}:{algorithm_key}:{measure_key}:"
        f"{params_str}:{apply_fit}:{fit_half_window}:{noise_sigma}:{seed}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def load_cached_run(
    dataset: Dataset,
    algorithm_key: str,
    measure_key: str,
    params: Mapping[str, Any],
    apply_fit: bool,
    fit_half_window: int,
    noise_sigma: float,
    seed: Optional[int],
) -> Optional[RunResult]:
    """Load a previously executed RunResult from disk cache if parameters match exactly."""
    try:
        cache_dir = get_cache_dir()
        sig = _run_hash(
            dataset, algorithm_key, measure_key, params, apply_fit, fit_half_window, noise_sigma, seed
        )
        run_file = cache_dir / f"run_{sig}.json"
        if not run_file.exists():
            return None

        with open(run_file, "r", encoding="utf-8") as f:
            d = json.load(f)

        from app.core.run_result import RunResult

        result = RunResult(
            algorithm=d["algorithm"],
            algorithm_key=d["algorithm_key"],
            dataset_label=dataset.label,
            dataset_key=dataset.key,
            measure=d["measure"],
            measure_key=d["measure_key"],
            coarse_idx=int(d["coarse_idx"]),
            coarse_value=float(d["coarse_value"]),
            coarse_wd_mm=float(d["coarse_wd_mm"]),
            fine_idx=float(d["fine_idx"]),
            fine_wd_mm=float(d["fine_wd_mm"]),
            fine_value=float(d["fine_value"]),
            fit_ok=bool(d["fit_ok"]),
            fit_r2=float(d["fit_r2"]),
            fit_coeffs=tuple(d["fit_coeffs"]) if d.get("fit_coeffs") else None,
            fit_window=tuple(d["fit_window"]) if d.get("fit_window") else None,
            fit_message=d.get("fit_message", "ok"),
            fit_points={int(k): float(v) for k, v in d.get("fit_points", {}).items()},
            fit_applied_afterwards=bool(d.get("fit_applied_afterwards", False)),
            frames_evaluated=int(d["frames_evaluated"]),
            search_frames=int(d["search_frames"]),
            eval_calls=int(d["eval_calls"]),
            visited=tuple(int(x) for x in d.get("visited", [])),
            evals={int(k): float(v) for k, v in d.get("evals", {}).items()},
            elapsed_s=float(d["elapsed_s"]),
            error_frames=float(d["error_frames"]) if d.get("error_frames") is not None else float("nan"),
            error_um=float(d["error_um"]) if d.get("error_um") is not None else float("nan"),
            coarse_error_frames=float(d["coarse_error_frames"]) if d.get("coarse_error_frames") is not None else float("nan"),
            coarse_error_um=float(d["coarse_error_um"]) if d.get("coarse_error_um") is not None else float("nan"),
            gt_idx=int(d["gt_idx"]) if d.get("gt_idx") is not None else 0,
            gt_reference_idx=float(d["gt_reference_idx"]) if d.get("gt_reference_idx") is not None else 0.0,
            verified=d.get("verified"),
            restarts=int(d.get("restarts", 0)),
            noise_sigma_estimate=float(d["noise_sigma_estimate"]) if d.get("noise_sigma_estimate") is not None else None,
            noise_sigma=float(d["noise_sigma"]),
            seed=d.get("seed"),
            repeats=int(d.get("repeats", 1)),
            extra=d.get("extra", {}),
        )
        LOGGER.info(f"Loaded run from disk cache: {dataset.label} • {algorithm_key} ({sig})")
        return result
    except Exception as exc:
        LOGGER.warning(f"Failed to read run cache for {dataset.label} • {algorithm_key}: {exc}")
        return None


def save_cached_run(
    result: RunResult,
    params: Mapping[str, Any],
    apply_fit: bool,
    fit_half_window: int,
) -> None:
    """Save an executed RunResult to disk cache."""
    try:
        cache_dir = get_cache_dir()
        folder_name = Path(result.dataset_key).name if result.dataset_key else result.dataset_label
        params_str = json.dumps(dict(sorted(params.items())), sort_keys=True)
        content = (
            f"{folder_name}:{len(result.visited)}:{result.algorithm_key}:{result.measure_key}:"
            f"{params_str}:{apply_fit}:{fit_half_window}:{result.noise_sigma}:{result.seed}"
        )
        # Also create sig matching load_cached_run
        sig = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        run_file = cache_dir / f"run_{sig}.json"

        d = {
            "algorithm": result.algorithm,
            "algorithm_key": result.algorithm_key,
            "measure": result.measure,
            "measure_key": result.measure_key,
            "coarse_idx": result.coarse_idx,
            "coarse_value": result.coarse_value,
            "coarse_wd_mm": result.coarse_wd_mm,
            "fine_idx": result.fine_idx,
            "fine_wd_mm": result.fine_wd_mm,
            "fine_value": result.fine_value,
            "fit_ok": result.fit_ok,
            "fit_r2": result.fit_r2,
            "fit_coeffs": list(result.fit_coeffs) if result.fit_coeffs else None,
            "fit_window": list(result.fit_window) if result.fit_window else None,
            "fit_message": result.fit_message,
            "fit_points": {str(k): v for k, v in result.fit_points.items()},
            "fit_applied_afterwards": result.fit_applied_afterwards,
            "frames_evaluated": result.frames_evaluated,
            "search_frames": result.search_frames,
            "eval_calls": result.eval_calls,
            "visited": list(result.visited),
            "evals": {str(k): v for k, v in result.evals.items()},
            "elapsed_s": result.elapsed_s,
            "error_frames": result.error_frames,
            "error_um": result.error_um,
            "coarse_error_frames": result.coarse_error_frames,
            "coarse_error_um": result.coarse_error_um,
            "gt_idx": result.gt_idx,
            "gt_reference_idx": result.gt_reference_idx,
            "verified": result.verified,
            "restarts": result.restarts,
            "noise_sigma_estimate": result.noise_sigma_estimate,
            "noise_sigma": result.noise_sigma,
            "seed": result.seed,
            "repeats": result.repeats,
            "extra": dict(result.extra) if result.extra else {},
        }

        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)

        LOGGER.info(f"Saved run to disk cache: {result.dataset_label} • {result.algorithm} ({sig})")
    except Exception as exc:
        LOGGER.warning(f"Failed to write run cache for {result.dataset_label} • {result.algorithm}: {exc}")


def clear_disk_cache() -> int:
    """Clear all cached entries from disk cache."""
    count = 0
    cache_dir = get_cache_dir()
    for item in cache_dir.glob("*"):
        try:
            item.unlink()
            count += 1
        except Exception:
            pass
    return count
