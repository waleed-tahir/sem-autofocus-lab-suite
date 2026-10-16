"""
Pre-Conditioning & Dynamic Variance-Gated ROI Metering
Implements:
1. Anscombe Variance-Stabilizing Transform (Poisson shot noise -> unit-variance Gaussian)
2. Dynamic 9-Zone Variance Gating (Upgraded CONTROL_AF_REGIONS, Top-K highest variance patches)
3. Adaptive Pixel Striding (zero-copy numpy slicing)
"""

from __future__ import annotations
from typing import List, Tuple
import cv2
import numpy as np


def anscombe_stabilize(img: np.ndarray) -> np.ndarray:
    """
    Anscombe Variance-Stabilizing Transform:
    I_stab(x, y) = 2.0 * sqrt(I(x, y) + 3/8)
    Converts intensity-dependent Poisson electron shot noise into uniform additive
    Gaussian noise (sigma^2 approx 1), preventing bright specimen charging artifacts
    from dominating gradient sums.
    """
    return 2.0 * np.sqrt(img.astype(np.float32) + 0.375)


def compute_9zone_rois(
    img: np.ndarray,
    top_k: int = 3,
    stride: int = 2
) -> List[Tuple[int, int, int, int]]:
    """
    Dynamic 9-Zone Variance Gating:
    Partitions the central ~60-70% field of view into a 3x3 grid of MeteringRectangle patches.
    Computes local contrast variance for all 9 candidate zones on the sampled frame.
    Returns the Top-K highest-variance bounding boxes: [(y0, y1, x0, x1), ...].
    
    Rejects empty vacuum background and low-contrast edge artifacts.
    """
    h, w = img.shape[:2]
    bh, bw = h // 5, w // 5
    candidates = []

    for r in range(1, 4):
        for c in range(1, 4):
            y0, y1 = r * bh, (r + 1) * bh
            x0, x1 = c * bw, (c + 1) * bw
            patch = img[y0:y1:stride, x0:x1:stride]
            patch_var = float(np.var(patch))
            candidates.append((patch_var, (y0, y1, x0, x1)))

    candidates.sort(key=lambda item: item[0], reverse=True)
    k = max(1, min(top_k, len(candidates)))
    return [box for _, box in candidates[:k]]


def extract_rois(
    img: np.ndarray,
    rois: List[Tuple[int, int, int, int]],
    stride: int = 1,
    use_anscombe: bool = False
) -> List[np.ndarray]:
    """
    Extracts the designated ROI patches from an image, applying optional
    Anscombe stabilization and adaptive zero-copy striding.
    """
    processed = anscombe_stabilize(img) if use_anscombe else img
    patches = []
    for (y0, y1, x0, x1) in rois:
        if stride > 1:
            patch = processed[y0:y1:stride, x0:x1:stride]
        else:
            patch = processed[y0:y1, x0:x1]
        patches.append(patch)
    return patches
