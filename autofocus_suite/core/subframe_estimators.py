"""
Sub-Frame Continuous Peak Estimators
Implements Section 6 from the Lab Specification Guide:
1. 3-Point Gaussian Log-Quadratic Estimator (Gaussian Point Spread Function fit)
2. 5-Point Savitzky-Golay / Polynomial Fit (Shot noise resilient)
3. Standard 3-Point Parabolic Estimator
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import math
import numpy as np


def gaussian_log_quadratic_fit(
    scores: Dict[int, float],
    peak_idx: int,
    max_idx: int,
    eps: float = 1e-7
) -> float:
    """
    3-Point Gaussian Log-Quadratic Estimator:
    Because electron microscope optical PSF is approximately Gaussian near focus,
    the sharpness curve Phi(z) follows a Gaussian bell.
    L_k = ln(max(Phi(k), eps)) around peak index k* yields:
    z_gauss* = k* + 0.5 * (L_{k*-1} - L_{k*+1}) / (L_{k*-1} - 2*L_{k*} + L_{k*+1})
    """
    k = peak_idx
    if k <= 0 or k >= max_idx:
        return float(k)
        
    y_prev = scores.get(k - 1)
    y_curr = scores.get(k)
    y_next = scores.get(k + 1)
    
    if y_prev is None or y_curr is None or y_next is None:
        return float(k)
        
    if y_curr <= y_prev or y_curr <= y_next:
        return float(k)
        
    l_prev = math.log(max(y_prev, eps))
    l_curr = math.log(max(y_curr, eps))
    l_next = math.log(max(y_next, eps))
    
    denom = l_prev - 2.0 * l_curr + l_next
    if abs(denom) < 1e-12 or denom > 0:  # must have negative curvature
        return float(k)
        
    delta = 0.5 * (l_prev - l_next) / denom
    # Clamp sub-frame offset within [-1.0, 1.0] frame
    delta = max(-1.0, min(1.0, delta))
    return float(k + delta)


def savitzky_golay_5point_fit(
    scores: Dict[int, float],
    peak_idx: int,
    max_idx: int
) -> float:
    """
    5-Point Savitzky-Golay / Polynomial Vertex Estimator:
    Fits a degree-2 polynomial to 5 points {k-2, k-1, k, k+1, k+2} around peak
    to filter out high shot noise jitter and estimate continuous vertex.
    """
    k = peak_idx
    if k < 2 or k > max_idx - 2:
        return float(k)
        
    points = [scores.get(k + offset) for offset in [-2, -1, 0, 1, 2]]
    if any(p is None for p in points):
        return float(k)
        
    # Least-squares parabolic fit over x = [-2, -1, 0, 1, 2]
    # y = a*x^2 + b*x + c
    # Normal equations for x in [-2, -1, 0, 1, 2]:
    # sum(x^4) = 34, sum(x^2) = 10, N = 5
    # b = (-2*y[-2] - y[-1] + y[1] + 2*y[2]) / 10
    # a = (2*y[-2] - y[-1] - 2*y[0] - y[1] + 2*y[2]) / 14
    y_m2, y_m1, y_0, y_p1, y_p2 = points
    b = (-2.0 * y_m2 - y_m1 + y_p1 + 2.0 * y_p2) / 10.0
    a = (2.0 * y_m2 - y_m1 - 2.0 * y_0 - y_p1 + 2.0 * y_p2) / 14.0
    
    if a < -1e-12:
        offset = -b / (2.0 * a)
        offset = max(-1.5, min(1.5, offset))
        return float(k + offset)
    return float(k)


def parabolic_3point_fit(
    scores: Dict[int, float],
    peak_idx: int,
    max_idx: int
) -> float:
    """
    Standard 3-point parabolic peak estimator:
    z* = k* + 0.5 * (y_{k-1} - y_{k+1}) / (y_{k-1} - 2*y_k + y_{k+1})
    """
    k = peak_idx
    if k <= 0 or k >= max_idx:
        return float(k)
    y_m1 = scores.get(k - 1)
    y_0 = scores.get(k)
    y_p1 = scores.get(k + 1)
    if y_m1 is None or y_0 is None or y_p1 is None:
        return float(k)
    denom = y_m1 - 2.0 * y_0 + y_p1
    if denom >= 0:
        return float(k)
    delta = 0.5 * (y_m1 - y_p1) / denom
    delta = max(-1.0, min(1.0, delta))
    return float(k + delta)
