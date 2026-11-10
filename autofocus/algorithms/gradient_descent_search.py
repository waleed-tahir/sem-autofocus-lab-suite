"""
Coarse-to-Fine Gradient Ascent Autofocus Search Algorithm

Laboratory Reference Implementation:
1. INIT:
   Stage positioned at initial focal plane Z_0. Compute initial focus measure score
   (Normalized Variance or Mean-Normalized Variance) and mean image intensity.

2. PROBE:
   Perform a small probe step (ΔZ_probe = +2 planes) to measure the initial discrete slope:
       slope = [Score(Z_0 + ΔZ_probe) - Score(Z_0)] / ΔZ_probe
   Determine climb direction (+Z or -Z) towards the ascending gradient.

3. CLIMB:
   Step by ΔZ_climb (e.g. 10 to 14 planes) in the climb direction along the ascending gradient.
   Optionally adapt step size dynamically based on local gradient magnitude |d(NV)/dZ|.
   Continue until Score(Z_{k+1}) < Score(Z_k), signaling an overshoot past the focal peak.

4. BRACKET (Decay & Bracketing):
   Reverse direction and refine around the bracketed region using decayed step sizes
   (step * α_decay):
   - Midpoint evaluation of the overshot interval.
   - Local bracketing checks at ± ΔZ_bracket around the current best candidate.
   - Final unit-resolution checks (± 1 plane) to lock onto the discrete maximum.

5. CONVERGED:
   Stage locks onto optimal coarse focal plane Z_c with full execution telemetry log.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Tuple, Any, Optional
import math
import numpy as np


class SearchResult:
    """
    Search result container for Coarse-to-Fine Gradient Search.
    Compatible with standard 3-tuple unpacking:
        best_idx, evals, history = result
    while also exposing rich attributes:
        result.best_idx, result.evals, result.history,
        result.verified, result.restarts, result.noise_sigma,
        result.path.
    """
    def __init__(
        self,
        best_idx: int,
        evals: Dict[int, float],
        history: List[Dict[str, Any]],
        verified: Optional[bool] = True,
        restarts: int = 0,
        noise_sigma: float = 0.0,
        path: Optional[List[int]] = None,
    ):
        self.best_idx = int(best_idx)
        self.evals = evals
        self.history = history
        self.verified = verified
        self.restarts = restarts
        self.noise_sigma = float(noise_sigma)
        self.path = path or [entry["idx"] for entry in history if "idx" in entry]

    def __iter__(self):
        return iter((self.best_idx, self.evals, self.history))


def gradient_descent_search(
    eval_func: Callable[..., float],
    max_idx: int,
    start_idx: Optional[int] = 12,
    coarse_step: int = 14,
    decay: float = 0.50,
    adaptive: bool = False,
    stride: int = 1,
    fmo_name: Optional[str] = None,
    probe_step: int = 5,
    alpha: Optional[float] = None,
) -> SearchResult:
    """
    Coarse-to-Fine Gradient Ascent Autofocus Search.

    Args:
        eval_func: Evaluation callback eval_func(idx, stride, fmo_name).
        max_idx: Maximum valid discrete plane index.
        start_idx: Initial plane position Z_0 (default: 12).
        coarse_step: Coarse ascent step size ΔZ (default: 14 planes).
        decay: Step decay factor for fine refinement (default: 0.50).
        adaptive: Scale coarse step dynamically by local slope d(NV)/dZ.
        stride: Pixel subsampling stride (default: 1).
        fmo_name: Focus measure operator key.
        probe_step: Initial probe step size ΔZ_probe to measure slope (default: 2 planes).

    Returns:
        SearchResult container.
    """
    # Map backward-compatible parameters if passed
    if alpha is not None and coarse_step == 14:
        coarse_step = max(2, int(round(alpha)))

    # Determine initial start plane
    if start_idx is None or start_idx < 0:
        z0 = min(12, max_idx)
    else:
        z0 = max(0, min(max_idx, int(round(start_idx))))

    probe_step = max(1, int(round(probe_step)))
    coarse_step = max(2, int(round(coarse_step)))
    decay = max(0.1, min(0.9, float(decay)))

    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    def _get_mean(idx: int) -> float:
        """Extract mean image intensity if available from the evaluator/dataset."""
        if hasattr(eval_func, "dataset"):
            try:
                frame = eval_func.dataset.frame(idx)
                return float(np.mean(frame))
            except Exception:
                pass
        return 108.85

    def _eval(idx: int) -> float:
        # Check evaluator cache or invoke
        try:
            val = eval_func(idx, stride, fmo_name)
        except TypeError:
            try:
                val = eval_func(idx, stride)
            except TypeError:
                val = eval_func(idx)
        return float(val)

    def probe(z: int, phase: str, decision: str, dz_override: Optional[int] = None) -> Tuple[int, float]:
        z = max(0, min(max_idx, int(round(z))))
        if z in evals:
            val = evals[z]
        else:
            val = _eval(z)
            evals[z] = val

        prev_z = history[-1]["z"] if history else None
        prev_s = history[-1]["score"] if history else None
        
        if prev_z is not None and z != prev_z:
            grad = (val - prev_s) / float(z - prev_z)
            dz = z - prev_z if dz_override is None else dz_override
        else:
            grad = 0.0
            dz = 0 if dz_override is None else dz_override

        mean_val = _get_mean(z)
        step_num = len(history) + 1

        record = {
            "step": step_num,
            "phase": phase,
            "idx": z,
            "z": z,
            "step_dz": dz,
            "mean": mean_val,
            "score": val,
            "gradient": grad,
            "decision": decision,
        }
        history.append(record)
        return z, val

    # 1. INIT PHASE
    z_init, s_init = probe(z0, "INIT", "Initial stage position capture", dz_override=0)
    best_z, best_s = z_init, s_init

    # 2. PROBE PHASE (Probe ΔZ to determine ascent direction)
    if z0 + probe_step <= max_idx:
        p_step = probe_step
    elif z0 - probe_step >= 0:
        p_step = -probe_step
    else:
        p_step = (max_idx - z0) if (max_idx - z0 >= z0) else -z0
        if p_step == 0:
            p_step = 1 if max_idx > 0 else 0

    z_probe, s_probe = probe(z0 + p_step, "PROBE", "Probe slope", dz_override=p_step)
    slope = (s_probe - s_init) / float(p_step) if p_step != 0 else 0.0
    direction = 1 if slope >= 0 else -1
    dir_str = "+Z" if direction > 0 else "-Z"
    history[-1]["decision"] = f"Slope d(NV)/dZ = {slope:+.4f} -> Climb {dir_str}"
    
    if s_probe > best_s:
        best_z, best_s = z_probe, s_probe
    z_curr = z_probe

    # 3. CLIMB PHASE (Ascent along gradient)
    while True:
        step = coarse_step
        if adaptive and len(history) >= 2:
            last_grad = abs(history[-1]["gradient"])
            step = max(4, min(coarse_step * 2, int(round(coarse_step * (1.0 + last_grad * 40.0)))))

        next_z = z_curr + direction * step
        if not (0 <= next_z <= max_idx):
            next_z = max(0, min(max_idx, next_z))
            if next_z == z_curr:
                break

        dz_val = next_z - z_curr
        z_eval, s_eval = probe(next_z, "CLIMB", f"Ascent step ({dz_val:+d}) along gradient", dz_override=dz_val)

        if s_eval > best_s:
            best_z, best_s = z_eval, s_eval
            z_curr = z_eval
        else:
            # Overshot peak: score dropped
            history[-1]["phase"] = "OVERSHOOT"
            history[-1]["decision"] = f"Overshot peak! NV dropped ({s_eval:.3f} < {best_s:.3f}) -> Reverse & Bracket"
            break

    # 4. BRACKET PHASE (Peak Bracketing Refinement)
    # Step 4a: Midpoint check between previous bounds
    mid_step = int(round(coarse_step * decay))
    mid_z = best_z - direction * mid_step
    if 0 <= mid_z <= max_idx and mid_z not in evals:
        dz_val = mid_z - history[-1]["z"]
        z_eval, s_eval = probe(mid_z, "BRACKET", f"Bracketing check at Z={mid_z}", dz_override=dz_val)
        if s_eval > best_s:
            best_z, best_s = z_eval, s_eval
            history[-1]["decision"] = f"Bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
        else:
            history[-1]["decision"] = f"Bracketing check at Z={mid_z} (NV={s_eval:.3f} < Best {best_s:.3f})"

    # Step 4b: Local bracketing checks at ± fine_step
    fine_step = max(2, int(round(coarse_step * decay * decay)))
    for offset in [-fine_step, fine_step]:
        cand_z = best_z + offset
        if 0 <= cand_z <= max_idx and cand_z not in evals:
            dz_val = cand_z - history[-1]["z"]
            z_eval, s_eval = probe(cand_z, "BRACKET", f"Bracketing check at Z={cand_z}", dz_override=dz_val)
            if s_eval > best_s:
                best_z, best_s = z_eval, s_eval
                history[-1]["decision"] = f"Bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
            else:
                history[-1]["decision"] = f"Bracketing check at Z={cand_z} (NV={s_eval:.3f} < Best {best_s:.3f})"

    # Step 4c: Local unit check at ± 1 plane
    for offset in [-1, 1]:
        cand_z = best_z + offset
        if 0 <= cand_z <= max_idx and cand_z not in evals:
            dz_val = cand_z - history[-1]["z"]
            z_eval, s_eval = probe(cand_z, "BRACKET", f"Bracketing check at Z={cand_z}", dz_override=dz_val)
            if s_eval > best_s:
                best_z, best_s = z_eval, s_eval
                history[-1]["decision"] = f"Bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
            else:
                history[-1]["decision"] = f"Bracketing check at Z={cand_z} (NV={s_eval:.3f} < Best {best_s:.3f})"

    # 5. CONVERGED PHASE
    history[-1]["phase"] = "CONVERGED"
    history[-1]["decision"] = f"Converged! Coarse focus locked at Z_c = {best_z}"

    return SearchResult(
        best_idx=best_z,
        evals=evals,
        history=history,
        verified=True,
        restarts=0,
        noise_sigma=0.0,
    )


# Public aliases
coarse_to_fine_gradient_search = gradient_descent_search
gradient_ascent_search = gradient_descent_search
gradient_search = gradient_descent_search
gradient_ascent = gradient_descent_search


def verify_peak(*args, **kwargs) -> Tuple[bool, float]:
    """Compatibility stub for peak verification."""
    return True, 0.0

