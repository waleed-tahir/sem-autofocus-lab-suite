"""
Astigmatism Diagnostic & Stigmator Error Estimation
From Section 3 (Bonus Diagnostic):
Objective lens asymmetry causes directional astigmatism stretching the image
along one axis at under-focus and the orthogonal axis at over-focus.
Logs directional energy asymmetry ratio:
A_xy(z) = (sum Gx^2 - sum Gy^2) / (sum Gx^2 + sum Gy^2)
A_45(z) = (sum G45^2 - sum G135^2) / (sum G45^2 + sum G135^2)
Calculates z_true* = 0.5 * (zx* + zy*) and stigmator error |zx* - zy*|.
"""

from __future__ import annotations
from typing import Dict, Any, List
import cv2
import numpy as np


def compute_directional_gradients(roi: np.ndarray) -> Dict[str, float]:
    """
    Computes directional energy along X, Y, 45-deg, and 135-deg axes.
    """
    gx = cv2.Scharr(roi, cv2.CV_32F, 1, 0)
    gy = cv2.Scharr(roi, cv2.CV_32F, 0, 1)
    
    gx2 = float(np.sum(gx * gx))
    gy2 = float(np.sum(gy * gy))
    
    g45 = 0.70710678 * (gx + gy)
    g135 = 0.70710678 * (gx - gy)
    
    g45_2 = float(np.sum(g45 * g45))
    g135_2 = float(np.sum(g135 * g135))
    
    denom_xy = gx2 + gy2 + 1e-7
    denom_diag = g45_2 + g135_2 + 1e-7
    
    axy = (gx2 - gy2) / denom_xy
    a45 = (g45_2 - g135_2) / denom_diag
    
    return {
        "gx2": gx2,
        "gy2": gy2,
        "g45_2": g45_2,
        "g135_2": g135_2,
        "A_xy": axy,
        "A_45": a45
    }


def analyze_astigmatism_stack(directional_records: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Analyzes an entire focal stack's directional records to locate:
    - zx_peak: frame index of max gx2
    - zy_peak: frame index of max gy2
    - z_true: midpoint 0.5 * (zx_peak + zy_peak)
    - stigmator_error: |zx_peak - zy_peak| (in frames)
    - stigmator_angle_deg: approximate orientation of residual astigmatism
    """
    if not directional_records:
        return {}
        
    gx2_vals = [r["gx2"] for r in directional_records]
    gy2_vals = [r["gy2"] for r in directional_records]
    axy_vals = [r["A_xy"] for r in directional_records]
    a45_vals = [r["A_45"] for r in directional_records]
    
    zx_peak = int(np.argmax(gx2_vals))
    zy_peak = int(np.argmax(gy2_vals))
    
    stigmator_error = abs(zx_peak - zy_peak)
    z_true = 0.5 * (zx_peak + zy_peak)
    
    # Angle of astigmatism in degrees based on asymmetry at mid-plane
    mid_idx = int(round(z_true))
    mid_idx = max(0, min(len(directional_records) - 1, mid_idx))
    axy_mid = axy_vals[mid_idx]
    a45_mid = a45_vals[mid_idx]
    
    theta_rad = 0.5 * np.arctan2(a45_mid, axy_mid)
    theta_deg = float(np.degrees(theta_rad))
    
    return {
        "zx_peak": zx_peak,
        "zy_peak": zy_peak,
        "z_true": z_true,
        "stigmator_error": stigmator_error,
        "stigmator_angle_deg": theta_deg,
        "A_xy_series": axy_vals,
        "A_45_series": a45_vals,
        "has_astigmatism": stigmator_error >= 2
    }
