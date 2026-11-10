"""
Validation Tests for Lab Submission Algorithms

Verifies:
1. normalized_variance.py (Normalized Variance & Mean-Normalized Variance)
2. global_scan_search.py (Exhaustive focal range scan)
3. gradient_descent_search.py (Gradient ascent & noise verification)
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


def test_gradient_search_synthetic():
    print("\n--- 3. Testing Gradient Descent / Ascent Search ---")
    TRUE_PEAK = 45
    TOTAL_FRAMES = 100
    MAX_IDX = TOTAL_FRAMES - 1

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        sigma = 8.0
        return float(100.0 * np.exp(-((idx - TRUE_PEAK) ** 2) / (2 * sigma ** 2)))

    res = gradient_descent_search(synthetic_eval, max_idx=MAX_IDX, start_idx=10, alpha=16.0)
    assert abs(res.best_idx - TRUE_PEAK) <= 1, f"Expected peak near {TRUE_PEAK}, got {res.best_idx}"
    print(f"  [PASS] Gradient Search found peak {res.best_idx} in {len(res.evals)} frame evaluations")


def test_quadratic_fit_synthetic():
    print("\n--- 4. Testing Quadratic Fit Vertex Refinement ---")
    TRUE_SUB_PEAK = 42.35

    def synthetic_eval(idx: int, stride: int = 1, fmo: str | None = None) -> float:
        return float(100.0 - 2.5 * ((idx - TRUE_SUB_PEAK) ** 2))

    fit = quadratic_fit(synthetic_eval, coarse_idx=42, max_idx=100, half_window=5)
    assert fit.ok, f"Fit failed: {fit.msg}"
    assert abs(fit.idx - TRUE_SUB_PEAK) < 0.05, f"Expected {TRUE_SUB_PEAK}, got {fit.idx}"
    print(f"  [PASS] Quadratic Fit vertex: {fit.idx:.3f} (True: {TRUE_SUB_PEAK:.3f}, R2: {fit.r2:.4f})")


if __name__ == "__main__":
    print("Running Lab Submission Algorithm Tests...\n")
    test_focus_scores_synthetic()
    test_global_scan_synthetic()
    test_gradient_search_synthetic()
    test_quadratic_fit_synthetic()
    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")
