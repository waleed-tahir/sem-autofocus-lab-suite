"""
Validation Tests for Lab Submission Algorithms

Verifies:
1. normalized_variance.py (Normalized Variance & Mean-Normalized Variance)
2. global_scan_search.py (Exhaustive focal range scan)
3. gradient_descent_search.py (Coarse-to-fine gradient ascent & rich telemetry)
4. quadratic_fit.py (Parabolic vertex interpolation)
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import cv2
import numpy as np

from autofocus.algorithms.normalized_variance import normalized_variance, mean_normalized_variance
from autofocus.algorithms.global_scan_search import global_scan_search
from autofocus.algorithms.gradient_descent_search import (
    gradient_descent_search,
    gradient_ascent_search,
    gradient_search,
    coarse_to_fine_gradient_search,
)
from autofocus.algorithms.gradient_descent_search_modified import (
    gradient_descent_search_modified,
    stochastic_gradient_search,
)
from autofocus.algorithms.quadratic_fit import (
    quadratic_fit,
    fit_quadratic_vertex,
)


def test_focus_scores_synthetic():
    print("--- 1. Testing Focus Scores (Synthetic) ---")
    np.random.seed(123)

    sharp = np.zeros((100, 100), dtype=np.uint8)
    sharp[::10, :] = 255
    sharp[:, ::10] = 255

    blur = cv2.GaussianBlur(sharp, (15, 15), 5.0)

    # 1. Normalized Variance
    nv_sharp = normalized_variance(sharp)
    nv_blur = normalized_variance(blur)
    assert nv_sharp > nv_blur, f"Normalized variance failed: {nv_sharp} <= {nv_blur}"
    print(f"  [PASS] normalized_variance (sharp: {nv_sharp:.2f}, blur: {nv_blur:.2f})")

    # 2. Mean-Normalized Variance
    mnv_sharp = mean_normalized_variance(sharp)
    mnv_blur = mean_normalized_variance(blur)
    assert mnv_sharp > mnv_blur, f"Mean-normalized variance failed: {mnv_sharp} <= {mnv_blur}"
    print(f"  [PASS] mean_normalized_variance (sharp: {mnv_sharp:.4f}, blur: {mnv_blur:.4f})")


def test_global_scan_synthetic():
    print("\n--- 2. Testing Global Scan Search ---")
    TRUE_PEAK = 37
    TOTAL_FRAMES = 80
    MAX_IDX = TOTAL_FRAMES - 1

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        sigma = 5.0
        return float(100.0 * np.exp(-((idx - TRUE_PEAK) ** 2) / (2 * sigma ** 2)))

    res = global_scan_search(synthetic_eval, max_idx=MAX_IDX)
    assert res.best_idx == TRUE_PEAK, f"Expected {TRUE_PEAK}, got {res.best_idx}"
    assert len(res.evals) == TOTAL_FRAMES
    print(f"  [PASS] Global Scan found peak {res.best_idx} reading {len(res.evals)} frames")


def test_coarse_to_fine_gradient_search():
    print("\n--- 3. Testing Coarse-to-Fine Gradient Ascent Search ---")
    TRUE_PEAK = 97
    TOTAL_FRAMES = 200
    MAX_IDX = TOTAL_FRAMES - 1

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        # Realistic SEM focus curve shape
        sigma = 16.0
        peak_nv = 16.85
        noise = 0.05 * np.sin(idx * 0.5)
        return float(8.0 + (peak_nv - 8.0) * np.exp(-((idx - TRUE_PEAK) ** 2) / (2 * sigma ** 2)) + noise)

    res = gradient_descent_search(
        synthetic_eval,
        max_idx=MAX_IDX,
        start_idx=12,
        coarse_step=14,
        decay=0.50,
        adaptive=False,
    )

    # Unpackable as 3-tuple
    best_idx, evals, history = res
    assert abs(best_idx - TRUE_PEAK) <= 1, f"Expected peak near {TRUE_PEAK}, got {best_idx}"
    assert len(evals) < 25, f"Expected < 25 evaluations, got {len(evals)}"

    phases = [h["phase"] for h in history]
    assert "INIT" in phases, "Missing INIT phase in telemetry"
    assert ("PROBE" in phases or "COARSE_PROBE" in phases), "Missing PROBE phase in telemetry"
    assert ("CLIMB" in phases or "COARSE" in phases), "Missing CLIMB phase in telemetry"
    assert "OVERSHOOT" in phases, "Missing OVERSHOOT phase in telemetry"
    assert ("BRACKET" in phases or "FINE" in phases), "Missing BRACKET phase in telemetry"
    assert "CONVERGED" in phases, "Missing CONVERGED phase in telemetry"

    # Verify telemetry columns
    for h in history:
        for key in ("step", "phase", "z", "step_dz", "mean", "score", "gradient", "decision"):
            assert key in h, f"Missing telemetry field '{key}' in record {h}"

    savings_pct = (1.0 - len(evals) / float(TOTAL_FRAMES)) * 100.0
    print(f"  [PASS] Coarse-to-Fine Gradient Search locked onto peak {best_idx} in {len(evals)} captures ({savings_pct:.1f}% fewer scans)")
    print(f"  [PASS] Telemetry history contains all 6 phases: {set(phases)}")


def test_stochastic_gradient_search():
    print("\n--- 4. Testing Stochastic Gradient Search (gradient_descent_search_modified.py) ---")
    TRUE_PEAK = 99
    TOTAL_FRAMES = 200
    MAX_IDX = TOTAL_FRAMES - 1

    # Realistic noisy focus curve where local noise ripples trap deterministic search
    def noisy_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        base = 10.0 + 15.0 * np.exp(-((idx - TRUE_PEAK) ** 2) / (2 * 25.0 ** 2))
        # High frequency noise ripples creating local maxima
        ripple = 0.5 * np.sin(idx * 0.9) + 0.3 * np.cos(idx * 1.4)
        return float(base + ripple)

    # 1. Verify deterministic search gets trapped at local maximum Z=9
    det_res = gradient_descent_search(
        noisy_eval,
        max_idx=MAX_IDX,
        start_idx=0,
        coarse_step=20,
        decay=0.43,
    )
    assert det_res.best_idx < 30, f"Deterministic search unexpectedly escaped local trap: {det_res.best_idx}"
    print(f"  [PASS] Deterministic search trapped at local maximum Z={det_res.best_idx} ({len(det_res.evals)} evals)")

    # 2. Verify stochastic search with randomly modified decreasing factor escapes to global peak
    for seed in [42, 101, 777]:
        res = gradient_descent_search_modified(
            noisy_eval,
            max_idx=MAX_IDX,
            start_idx=0,
            coarse_step=20,
            decay=0.43,
            stochastic_jitter=0.25,
            seed=seed,
        )
        best_idx, evals, history = res
        assert abs(best_idx - TRUE_PEAK) <= 6, f"Expected global peak near {TRUE_PEAK}, got {best_idx}"
        assert len(evals) < 30, f"Expected < 30 evaluations, got {len(evals)}"
        print(f"  [PASS] Stochastic Seed {seed}: escaped local trap and locked onto peak {best_idx} in {len(evals)} captures")


def test_quadratic_fit_synthetic():
    print("\n--- 4. Testing Quadratic Fit Vertex Refinement ---")
    TRUE_SUB_PEAK = 42.35

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        return float(100.0 - 2.5 * ((idx - TRUE_SUB_PEAK) ** 2))

    fit = quadratic_fit(synthetic_eval, coarse_idx=42, max_idx=100, half_window=5)
    assert fit.ok, f"Fit failed: {fit.msg}"
    assert abs(fit.idx - TRUE_SUB_PEAK) < 0.05, f"Expected {TRUE_SUB_PEAK}, got {fit.idx}"
    print(f"  [PASS] Quadratic Fit vertex: {fit.idx:.3f} (True: {TRUE_SUB_PEAK:.3f}, R2: {fit.r2:.4f})")


def test_probe_step_variation():
    print("\n--- 5. Testing Initial Probe Step Size Variation ---")
    TRUE_PEAK = 50
    MAX_IDX = 100

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        return float(100.0 - 0.5 * ((idx - TRUE_PEAK) ** 2))

    for p_step in [1, 3, 5, 8]:
        z0 = 10
        res = gradient_descent_search(
            synthetic_eval,
            max_idx=MAX_IDX,
            start_idx=z0,
            coarse_step=10,
            probe_step=p_step,
        )
        best_idx, evals, history = res
        assert len(history) >= 2
        probe_rec = history[1]
        assert probe_rec["phase"] == "PROBE"
        assert probe_rec["z"] == z0 + p_step
        assert probe_rec["step_dz"] == p_step
        expected_grad = (synthetic_eval(z0 + p_step) - synthetic_eval(z0)) / float(p_step)
        assert abs(probe_rec["gradient"] - expected_grad) < 1e-5
        assert abs(best_idx - TRUE_PEAK) <= 2
        print(f"  [PASS] probe_step={p_step}: probe Z={probe_rec['z']}, step_dz={probe_rec['step_dz']:+d}, grad={probe_rec['gradient']:+.4f}")


if __name__ == "__main__":
    print("Running Lab Submission Algorithm Tests...\n")
    test_focus_scores_synthetic()
    test_global_scan_synthetic()
    test_coarse_to_fine_gradient_search()
    test_stochastic_gradient_search()
    test_quadratic_fit_synthetic()
    test_probe_step_variation()
    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")
