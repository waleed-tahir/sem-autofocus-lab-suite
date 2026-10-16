"""
Advanced Electron Microscope Autofocus Engine
Coordinates:
1. Lazy Z-Stack on-demand loader with zero-copy caching
2. Pre-conditioning & Anscombe variance stabilization
3. Dynamic 9-zone variance-gated ROI metering
4. 10 Focus Measure Operators (FMOs)
5. Sub-linear search algorithms (S1 - S4, Global)
6. Sub-frame Gaussian log-quadratic and polynomial peak locks
7. Astigmatism error detection
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import glob
import cv2
import numpy as np

from autofocus_suite.core.preconditioning import (
    anscombe_stabilize, compute_9zone_rois, extract_rois
)
from autofocus_suite.core.fmo_kernels import (
    FMO_REGISTRY, FMO_METADATA
)
from autofocus_suite.core.search_algorithms import (
    SEARCH_REGISTRY, SEARCH_METADATA
)
from autofocus_suite.core.subframe_estimators import (
    gaussian_log_quadratic_fit, savitzky_golay_5point_fit
)
from autofocus_suite.core.astigmatism import (
    compute_directional_gradients, analyze_astigmatism_stack
)
from autofocus_suite.core.metrics import compute_comprehensive_stats


class AutofocusEngine:
    """
    Main Autofocus Engine for SEM/TEM Focal Stacks.
    """
    def __init__(
        self,
        dataset_path: str,
        fmo: str = "m1_scharr",
        search_method: str = "s2_hybrid",
        top_k_rois: int = 3,
        use_anscombe: bool = False,
        preload_images: bool = False,
        preloaded_cache: Optional[Dict[int, np.ndarray]] = None
    ):
        self.dataset_path = dataset_path
        self.fmo_name = fmo
        self.search_method = search_method
        self.top_k_rois = top_k_rois
        self.use_anscombe = use_anscombe

        # Discover image paths
        self.image_paths = sorted(
            glob.glob(os.path.join(dataset_path, "*.png")) or
            glob.glob(os.path.join(dataset_path, "*.jpg")) or
            glob.glob(os.path.join(dataset_path, "*.tif*"))
        )
        if not self.image_paths:
            raise ValueError(f"No image files found in {dataset_path}")

        self.num_frames = len(self.image_paths)
        self.max_idx = self.num_frames - 1

        # Caches
        self.preloaded = preloaded_cache is not None
        self.raw_frame_cache: Dict[int, np.ndarray] = preloaded_cache if preloaded_cache is not None else {}
        self.probed_indices: set[int] = set()
        self.active_rois: Optional[List[Tuple[int, int, int, int]]] = None
        
        if preload_images and not self.raw_frame_cache:
            for i, p in enumerate(self.image_paths):
                self.raw_frame_cache[i] = cv2.imread(p, cv2.IMREAD_GRAYSCALE)

    def load_frame(self, idx: int) -> np.ndarray:
        """Loads frame from memory or lazy loads on-demand."""
        self.probed_indices.add(idx)
        if idx in self.raw_frame_cache:
            return self.raw_frame_cache[idx]
        img = cv2.imread(self.image_paths[idx], cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise IOError(f"Could not read frame at {self.image_paths[idx]}")
        self.raw_frame_cache[idx] = img
        return img
        return img

    def initialize_dynamic_rois(self, sample_idx: Optional[int] = None) -> List[Tuple[int, int, int, int]]:
        """
        Samples the initial frame (default: middle or first sampled frame)
        and computes the Top-K highest-variance MeteringRectangle patches.
        """
        if sample_idx is None:
            sample_idx = self.max_idx // 2
        sample_img = self.load_frame(sample_idx)
        self.active_rois = compute_9zone_rois(sample_img, top_k=self.top_k_rois, stride=2)
        return self.active_rois

    def evaluate_frame(
        self,
        idx: int,
        stride: int = 1,
        fmo_override: Optional[str] = None
    ) -> float:
        """
        Evaluates a frame at index `idx` using current active ROIs and specified FMO.
        """
        idx = max(0, min(self.max_idx, idx))
        if self.active_rois is None:
            self.initialize_dynamic_rois(idx)

        img = self.load_frame(idx)
        patches = extract_rois(
            img,
            self.active_rois,
            stride=stride,
            use_anscombe=self.use_anscombe
        )

        fmo_key = fmo_override or self.fmo_name
        fmo_fn = FMO_REGISTRY.get(fmo_key, FMO_REGISTRY["m1_scharr"])

        scores = [fmo_fn(patch) for patch in patches]
        return float(np.mean(scores)) if scores else 0.0

    def run_autofocus(
        self,
        ground_truth_peak: Optional[int] = None,
        reference_curve: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Executes the configured autofocus search pipeline and calculates all benchmark stats.
        """
        search_fn = SEARCH_REGISTRY.get(self.search_method, SEARCH_REGISTRY["s2_hybrid"])
        
        # Clear evaluation cache for clean timing
        eval_cache: Dict[Tuple[int, int, Optional[str]], float] = {}

        def eval_callback(idx: int, stride: int, fmo_name: Optional[str]) -> float:
            key = (idx, stride, fmo_name)
            if key not in eval_cache:
                eval_cache[key] = self.evaluate_frame(idx, stride, fmo_name)
            return eval_cache[key]

        # Reset active ROIs to guarantee unbiased sampling
        self.active_rois = None

        t0 = time.perf_counter()

        # Run Search Algorithm
        if self.search_method == "s2_hybrid":
            best_idx, evals_dict, history = search_fn(
                eval_callback,
                self.max_idx,
                coarse_fmo="composite_m9_m2",
                fine_fmo=self.fmo_name,
                coarse_stride=4,
                fine_stride=1
            )
        else:
            best_idx, evals_dict, history = search_fn(
                eval_callback,
                self.max_idx,
                fmo_name=self.fmo_name
            )

        t1 = time.perf_counter()
        wall_clock_ms = (t1 - t0) * 1000.0

        # Sub-frame peak fitting
        # Ensure neighbor points are evaluated at stride=1 with primary FMO for accurate fit
        subframe_scores = {}
        for nbr in [best_idx - 2, best_idx - 1, best_idx, best_idx + 1, best_idx + 2]:
            if 0 <= nbr <= self.max_idx:
                subframe_scores[nbr] = eval_callback(nbr, 1, self.fmo_name)

        z_sub_gauss = gaussian_log_quadratic_fit(subframe_scores, best_idx, self.max_idx)
        z_sub_sg5 = savitzky_golay_5point_fit(subframe_scores, best_idx, self.max_idx)

        # Build stats
        frames_read = len(self.probed_indices) if self.probed_indices else len(self.raw_frame_cache)
        
        stats = {}
        if ground_truth_peak is not None and reference_curve is not None:
            stats = compute_comprehensive_stats(
                curve=reference_curve,
                z_gt=ground_truth_peak,
                z_hat=best_idx,
                z_sub=z_sub_gauss,
                wall_clock_ms=wall_clock_ms,
                frames_read=frames_read,
                total_frames=self.num_frames
            )
        else:
            stats = {
                "discrete_peak": best_idx,
                "subframe_peak_gauss": round(z_sub_gauss, 3),
                "subframe_peak_sg5": round(z_sub_sg5, 3),
                "wall_clock_ms": round(wall_clock_ms, 2),
                "frames_read": frames_read,
                "total_frames": self.num_frames,
                "read_percentage": round((frames_read / self.num_frames) * 100.0, 1),
                "io_reduction_pct": round((1.0 - frames_read / self.num_frames) * 100.0, 1)
            }

        return {
            "search_method": self.search_method,
            "fmo": self.fmo_name,
            "discrete_peak": best_idx,
            "subframe_peak_gauss": round(z_sub_gauss, 3),
            "subframe_peak_sg5": round(z_sub_sg5, 3),
            "wall_clock_ms": round(wall_clock_ms, 2),
            "frames_read": frames_read,
            "total_frames": self.num_frames,
            "history": history,
            "stats": stats,
            "active_rois": self.active_rois
        }

    def compute_full_stack_curve(
        self,
        fmo_name: Optional[str] = None,
        stride: int = 1
    ) -> Tuple[List[float], int]:
        """
        Evaluates the entire focal stack to obtain the exact focus profile curve
        and true ground-truth peak index.
        """
        fmo = fmo_name or self.fmo_name
        if self.active_rois is None:
            self.initialize_dynamic_rois(self.max_idx // 2)

        curve = []
        for idx in range(self.num_frames):
            score = self.evaluate_frame(idx, stride=stride, fmo_override=fmo)
            curve.append(score)

        peak_idx = int(np.argmax(curve))
        return curve, peak_idx
