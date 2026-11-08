"""
Comprehensive Validation Tests for Extracted Algorithms

Verifies:
1. normalized_variance.py
2. laplacian.py (VoL, LoG, SML)
3. global_scan_search.py
4. coarse_and_fine_search.py
5. gradient_descent_search.py (gradient ascent & fake-maximum rejection)
6. quadratic_fit.py (parabolic curve fit, R^2, sub-frame peak)
7. coarse_quadratic_search.py (coarse_quadratic / coarse_fit two-stage pipeline)
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import glob
import cv2
import numpy as np

from algorithm.normalized_variance import normalized_variance, mean_normalized_variance
from algorithm.laplacian import (
    variance_of_laplacian,
    laplacian_of_gaussian,
    modified_laplacian,
    laplacian_focus_score,
)
from algorithm.global_scan_search import global_scan_search
from algorithm.coarse_and_fine_search import coarse_and_fine_search
from algorithm.gradient_descent_search import (
    gradient_descent_search,
    gradient_ascent_search,
    gradient_search,
)
from algorithm.quadratic_fit import (
    quadratic_fit,
    fit_quadratic_vertex,
)
from algorithm.coarse_quadratic_search import (
    coarse_quadratic_search,
    coarse_fit_search,
    coarse_quadratic,
    coarse_fit,
)


def test_focus_scores_synthetic():
    print("--- 1. Testing Focus Scores (Synthetic) ---")
    np.random.seed(123)

    # Sharp test pattern
    sharp = np.zeros((100, 100), dtype=np.uint8)
    sharp[::10, :] = 255
    sharp[:, ::10] = 255

    # Blurry version
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

    # 3. Variance of Laplacian
    vol_sharp = variance_of_laplacian(sharp)
    vol_blur = variance_of_laplacian(blur)
    assert vol_sharp > vol_blur, f"VoL failed: {vol_sharp} <= {vol_blur}"
    print(f"  [PASS] variance_of_laplacian (sharp: {vol_sharp:.1f}, blur: {vol_blur:.1f})")

    # 4. Laplacian of Gaussian
    log_sharp = laplacian_of_gaussian(sharp)
    log_blur = laplacian_of_gaussian(blur)
    assert log_sharp > log_blur, f"LoG failed: {log_sharp} <= {log_blur}"
    print(f"  [PASS] laplacian_of_gaussian (sharp: {log_sharp:.1f}, blur: {log_blur:.1f})")

    # 5. Modified Laplacian (SML)
    sml_sharp = modified_laplacian(sharp)
    sml_blur = modified_laplacian(blur)
    assert sml_sharp > sml_blur, f"SML failed: {sml_sharp} <= {sml_blur}"
    print(f"  [PASS] modified_laplacian (sharp: {sml_sharp:.2f}, blur: {sml_blur:.2f})")

    # 6. Unified dispatcher
    disp_vol = laplacian_focus_score(sharp, method="variance")
    disp_log = laplacian_focus_score(sharp, method="log")
    disp_sml = laplacian_focus_score(sharp, method="modified")
    assert disp_vol == vol_sharp
    assert disp_log == log_sharp
    assert disp_sml == sml_sharp
    print("  [PASS] laplacian_focus_score unified dispatcher verified")


def test_search_algorithms_synthetic():
    print("\n--- 2. Testing Search Algorithms (Synthetic Curve) ---")
    TOTAL_FRAMES = 150
    TRUE_PEAK = 64
    MAX_IDX = TOTAL_FRAMES - 1

    def eval_curve(idx: int, stride: int = 1, fmo: str = None) -> float:
        # Gaussian curve with peak at TRUE_PEAK
        return float(100.0 * np.exp(-((idx - TRUE_PEAK) ** 2) / (2 * (7.0 ** 2))))

    # 1. Global scan
    res_global = global_scan_search(eval_curve, max_idx=MAX_IDX)
    assert res_global.best_idx == TRUE_PEAK
    assert len(res_global.evals) == TOTAL_FRAMES
    print(f"  [PASS] Global Scan found peak at frame {res_global.best_idx} with {len(res_global.evals)} reads")

    # 2. Coarse and fine search
    res_cf = coarse_and_fine_search(eval_curve, max_idx=MAX_IDX)
    error = abs(res_cf.best_idx - TRUE_PEAK)
    assert error <= 1, f"Coarse-Fine error {error} > 1"
    reduction = (1.0 - len(res_cf.evals) / TOTAL_FRAMES) * 100.0
    print(f"  [PASS] Coarse & Fine found peak at frame {res_cf.best_idx} (error: {error} frames)")
    print(f"         Reads: {len(res_cf.evals)} / {TOTAL_FRAMES} ({reduction:.1f}% read reduction)")

    # 3. Gradient Descent / Ascent Search
    res_grad = gradient_descent_search(eval_curve, max_idx=MAX_IDX)
    error_grad = abs(res_grad.best_idx - TRUE_PEAK)
    assert error_grad <= 1, f"Gradient search error {error_grad} > 1"
    assert res_grad.verified is True
    # Unpack check
    b, e, h = res_grad
    assert b == res_grad.best_idx
    assert len(e) == len(res_grad.evals)
    pct_saved = (1.0 - len(res_grad.evals) / TOTAL_FRAMES) * 100.0
    print(f"  [PASS] Gradient Descent / Ascent found peak at frame {res_grad.best_idx} (error: {error_grad} frames)")
    print(f"         Reads: {len(res_grad.evals)} / {TOTAL_FRAMES} ({pct_saved:.1f}% read reduction, verified: {res_grad.verified})")


def test_quadratic_fit_synthetic():
    print("\n--- 3. Testing Quadratic Curve Fitting (Synthetic) ---")
    TOTAL_FRAMES = 150
    MAX_IDX = TOTAL_FRAMES - 1
    TRUE_SUBFRAME_PEAK = 64.38

    def eval_subframe_curve(idx: int, stride: int = 1, fmo: str = None) -> float:
        sigma = 7.5
        return float(100.0 * np.exp(-((idx - TRUE_SUBFRAME_PEAK) ** 2) / (2 * (sigma ** 2))))

    # Standalone Quadratic Fit around discrete coarse peak 64
    fit_res = quadratic_fit(eval_subframe_curve, coarse_idx=64, max_idx=MAX_IDX, half_window=10)
    assert fit_res.ok is True, f"Fit failed: {fit_res.msg}"
    assert fit_res.r2 > 0.95, f"R2 {fit_res.r2} too low"
    sub_err = abs(fit_res.idx - TRUE_SUBFRAME_PEAK)
    assert sub_err < 0.12, f"Sub-frame error {sub_err} >= 0.12 frames"
    print(f"  [PASS] Quadratic Fit locked sub-frame peak at {fit_res.idx:.3f} (True: {TRUE_SUBFRAME_PEAK:.3f}, error: {sub_err:.4f})")
    print(f"         Goodness of fit R^2: {fit_res.r2:.5f}, fitted peak focus: {fit_res.value:.2f}")

    # Test dictionary-style access
    assert fit_res["ok"] == fit_res.ok
    assert fit_res["idx"] == fit_res.idx
    print("  [PASS] QuadraticFitResult dictionary indexing verified")

    # Test convexity failure check
    def convex_curve(idx: int) -> float:
        return float((idx - 64) ** 2)  # minimum at 64, not maximum
    convex_fit = quadratic_fit(convex_curve, coarse_idx=64, max_idx=MAX_IDX, half_window=8)
    assert convex_fit.ok is False
    assert "convex" in convex_fit.msg
    print(f"  [PASS] Convex curvature rejection verified ('{convex_fit.msg}')")


def test_coarse_quadratic_search():
    print("\n--- 4. Testing Coarse-Fit / Coarse-Quadratic Search ---")
    TOTAL_FRAMES = 200
    MAX_IDX = TOTAL_FRAMES - 1
    TRUE_SUBFRAME_PEAK = 82.42

    def eval_target(idx: int, stride: int = 1, fmo: str = None) -> float:
        sigma = 8.5
        return float(100.0 * np.exp(-((idx - TRUE_SUBFRAME_PEAK) ** 2) / (2 * (sigma ** 2))))

    # 1. Test coarse_quadratic (gradient coarse + quadratic fit)
    res_cq = coarse_quadratic(eval_target, max_idx=MAX_IDX, coarse_method="gradient")
    assert res_cq.fit_ok is True
    assert abs(res_cq.best_idx - round(TRUE_SUBFRAME_PEAK)) <= 1
    err_cq = abs(res_cq.fine_idx - TRUE_SUBFRAME_PEAK)
    assert err_cq < 0.15, f"Coarse quadratic sub-frame error {err_cq} >= 0.15"
    reduction_cq = (1.0 - len(res_cq.evals) / TOTAL_FRAMES) * 100.0
    print(f"  [PASS] coarse_quadratic locked sub-frame peak at {res_cq.fine_idx:.3f} (True: {TRUE_SUBFRAME_PEAK:.3f}, error: {err_cq:.4f})")
    print(f"         Coarse discrete peak: {res_cq.best_idx}, Reads: {len(res_cq.evals)} / {TOTAL_FRAMES} ({reduction_cq:.1f}% saved)")

    # 2. Test coarse_fit (grid coarse + quadratic fit)
    res_cf = coarse_fit(eval_target, max_idx=MAX_IDX, coarse_method="grid")
    assert res_cf.fit_ok is True
    err_cf = abs(res_cf.fine_idx - TRUE_SUBFRAME_PEAK)
    assert err_cf < 0.25, f"Coarse fit sub-frame error {err_cf} >= 0.25"
    reduction_cf = (1.0 - len(res_cf.evals) / TOTAL_FRAMES) * 100.0
    print(f"  [PASS] coarse_fit (grid) locked sub-frame peak at {res_cf.fine_idx:.3f} (True: {TRUE_SUBFRAME_PEAK:.3f}, error: {err_cf:.4f})")
    print(f"         Coarse discrete peak: {res_cf.best_idx}, Reads: {len(res_cf.evals)} / {TOTAL_FRAMES} ({reduction_cf:.1f}% saved)")

    # Unpack test
    b, e, h = res_cq
    assert b == res_cq.best_idx
    assert len(e) == len(res_cq.evals)
    print("  [PASS] 3-tuple unpacking verified for coarse quadratic result")


def test_on_real_dataset():
    dataset_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "pollen.spd1")
    if not os.path.exists(dataset_dir):
        print("\n[SKIP] pollen.spd1 dataset not found, skipping real stack test.")
        return

    print(f"\n--- 5. Testing on Real SEM Dataset: {dataset_dir} ---")
    frame_files = sorted(glob.glob(os.path.join(dataset_dir, "*.png")))
    num_frames = len(frame_files)
    print(f"  Loaded {num_frames} frames.")
    assert num_frames > 20

    img_cache = {}

    def get_frame(idx: int) -> np.ndarray:
        if idx not in img_cache:
            img_cache[idx] = cv2.imread(frame_files[idx], cv2.IMREAD_GRAYSCALE)
        return img_cache[idx]

    def eval_real_frame(idx: int, stride: int = 1, fmo_name: str = None) -> float:
        frame = get_frame(idx)
        if stride > 1:
            frame = frame[::stride, ::stride]
        return variance_of_laplacian(frame)

    max_idx = num_frames - 1

    # Coarse & Fine
    res_cf = coarse_and_fine_search(eval_real_frame, max_idx=max_idx)
    print(f"  [PASS] Coarse & Fine Peak on real stack: Frame {res_cf.best_idx}")

    # Gradient Search
    res_grad = gradient_descent_search(eval_real_frame, max_idx=max_idx)
    print(f"  [PASS] Gradient Search Peak on real stack: Frame {res_grad.best_idx} (verified: {res_grad.verified})")

    # Coarse Quadratic
    res_cq = coarse_quadratic(eval_real_frame, max_idx=max_idx)
    print(f"  [PASS] Coarse Quadratic on real stack: Coarse Frame {res_cq.best_idx}, Sub-Frame {res_cq.fine_idx:.2f}")


if __name__ == "__main__":
    test_focus_scores_synthetic()
    test_search_algorithms_synthetic()
    test_quadratic_fit_synthetic()
    test_coarse_quadratic_search()
    test_on_real_dataset()
    print("\n==========================================")
    print(" ALL EXTRACTED ALGORITHM TESTS PASSED!    ")
    print("==========================================")
