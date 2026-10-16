"""
Evaluation Metrics & Diagnostic Selection Suite
Implements Section 7 from the Lab Specification Guide:
1. Discrete Localization Error (Delta z_err = |z_hat* - z_gt|)
2. Continuous Sub-Frame Error (|z_sub* - z_gt|)
3. Peak Sharpness Ratio (PSR = (Phi_max - mu_tail) / sigma_tail)
4. Unimodal Monotonicity Score (M_uni in [0, 1])
5. Wall-Clock Execution Latency (T_ms)
6. Disk I/O Frame Read Reduction (% saved)
"""

from __future__ import annotations
from typing import Dict, List, Any
import numpy as np


def compute_peak_sharpness_ratio(curve: List[float], peak_idx: int, guard_band: int = 15) -> float:
    """
    Peak Sharpness Ratio (PSR):
    Measures signal-to-noise prominence of focus peak above defocused background frames.
    PSR = (Phi_max - mu_tail) / (sigma_tail + eps)
    Tail is defined as frames outside [peak_idx - guard_band, peak_idx + guard_band].
    """
    n = len(curve)
    if n == 0:
        return 0.0
        
    phi_max = curve[peak_idx]
    
    # Collect tail points outside guard band
    tail_indices = [i for i in range(n) if abs(i - peak_idx) > guard_band]
    if not tail_indices:
        tail_indices = [0, n - 1]
        
    tail_vals = [curve[i] for i in tail_indices]
    mu_tail = float(np.mean(tail_vals))
    sigma_tail = float(np.std(tail_vals))
    
    psr = (phi_max - mu_tail) / (sigma_tail + 1e-7)
    return float(max(0.0, psr))


def compute_monotonicity_score(curve: List[float], peak_idx: int) -> float:
    """
    Unimodal Monotonicity Score (M_uni in [0, 1]):
    Fraction of adjacent steps moving monotonically toward the peak:
    - Step i < peak: Phi[i+1] >= Phi[i]
    - Step i >= peak: Phi[i+1] <= Phi[i]
    Higher score indicates smooth climb without local bumps.
    Score < 0.85 requires hybrid coarse-fine search.
    """
    n = len(curve)
    if n <= 1:
        return 1.0
        
    monotonic_steps = 0
    total_steps = n - 1
    
    # Left side of peak: ascending
    for i in range(peak_idx):
        if curve[i + 1] >= curve[i]:
            monotonic_steps += 1
            
    # Right side of peak: descending
    for i in range(peak_idx, total_steps):
        if curve[i + 1] <= curve[i]:
            monotonic_steps += 1
            
    return float(monotonic_steps / total_steps)


def compute_comprehensive_stats(
    curve: List[float],
    z_gt: int,
    z_hat: int,
    z_sub: float,
    wall_clock_ms: float,
    frames_read: int,
    total_frames: int
) -> Dict[str, Any]:
    """
    Aggregates all 5 primary benchmark metrics.
    """
    discrete_err = abs(z_hat - z_gt)
    subframe_err = abs(z_sub - float(z_gt))
    psr = compute_peak_sharpness_ratio(curve, z_gt)
    m_uni = compute_monotonicity_score(curve, z_gt)
    read_pct = (frames_read / max(1, total_frames)) * 100.0
    io_reduction_pct = 100.0 - read_pct
    
    return {
        "discrete_error_frames": discrete_err,
        "subframe_error": round(subframe_err, 4),
        "peak_sharpness_ratio_psr": round(psr, 2),
        "monotonicty_m_uni": round(m_uni, 4),
        "wall_clock_ms": round(wall_clock_ms, 2),
        "frames_read": frames_read,
        "total_frames": total_frames,
        "read_percentage": round(read_pct, 1),
        "io_reduction_pct": round(io_reduction_pct, 1),
        "is_accurate": discrete_err <= 1
    }
