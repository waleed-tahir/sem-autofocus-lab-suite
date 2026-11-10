"""
Modified Gradient Descent / Ascent Autofocus Search with Stochastic Step Decay

Laboratory Stochastic Solution for Escaping Local Maxima:
When discrete autofocus algorithms navigate noisy focal curves (e.g. at fast scan
speeds or on irregular specimens), deterministic gradient ascent can become trapped
in sub-optimal local maxima.

This modified algorithm introduces a stochastic solution:
1. Randomized Decreasing Factor:
   Instead of decaying the step size by a fixed constant factor (alpha_decay = const),
   the decreasing factor is dynamically perturbed on each decay iteration:
       alpha_stochastic = alpha_base * (1 + xi),  where xi ~ Uniform(-jitter, +jitter)
   This breaks deterministic lattice alignment, allowing probes to sample across
   alternative focal sub-intervals and avoid repetitive sampling on noise ridges.

2. Stochastic Local Maximum Escape:
   If the search reaches a local peak candidate, exploratory stochastic probes
   are executed with randomly generated decreasing factors:
       Delta_Z_escape = direction * round(coarse_step * Uniform(alpha_min, alpha_max))
   If a probe discovers a higher focus score, the algorithm breaks out of the local
   basin and resumes coarse ascent towards the global maximum.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Tuple, Any, Optional
import math
import numpy as np


class SearchResult:
    """
    Search result container for Modified Stochastic Gradient Search.
    Compatible with standard 3-tuple unpacking:
        best_idx, evals, history = result
    while also exposing rich named attributes:
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
        self.path = path or [entry.get("idx", entry.get("z", 0)) for entry in history]

    def __iter__(self):
        return iter((self.best_idx, self.evals, self.history))


def gradient_descent_search_modified(
    eval_func: Callable[..., float],
    max_idx: int,
    start_idx: Optional[int] = 12,
    coarse_step: int = 20,
    decay: float = 0.43,
    adaptive: bool = False,
    stride: int = 1,
    fmo_name: Optional[str] = None,
    probe_step: int = 2,
    stochastic_jitter: float = 0.25,
    max_escape_attempts: int = 2,
    seed: Optional[int] = None,
    alpha: Optional[float] = None
) -> SearchResult:
    """
    Stochastic Coarse-to-Fine Gradient Ascent Autofocus Search.

    Args:
        eval_func: Evaluation callback eval_func(idx, stride, fmo_name).
        max_idx: Maximum valid discrete plane index.
        start_idx: Initial plane position Z_0 (default: 12).
        coarse_step: Coarse ascent step size Delta_Z (default: 20 planes).
        decay: Base step decreasing factor for fine refinement (default: 0.43).
        adaptive: Scale coarse step dynamically by local slope |d(NV)/dZ|.
        stride: Pixel subsampling stride (default: 1).
        fmo_name: Focus measure operator key.
        probe_step: Initial probe step size Delta_Z_probe to measure slope (default: 2 planes).
        stochastic_jitter: Maximum percentage perturbation applied to the decreasing factor.
        max_escape_attempts: Number of stochastic exploration attempts to escape local maxima.
        seed: Random number generator seed for deterministic reproducibility.

    Returns:
        SearchResult container.
    """
    # Map backward-compatible parameters if passed
    if alpha is not None and coarse_step == 20:
        coarse_step = max(2, int(round(alpha)))

    # PRNG for stochastic decreasing factor modifications
    rng = np.random.default_rng(seed)

    # Determine initial start plane
    if start_idx is None or start_idx < 0:
        z0 = min(12, max_idx)
    else:
        z0 = max(0, min(max_idx, int(round(start_idx))))

    probe_step = max(1, int(round(probe_step)))
    coarse_step = max(2, int(round(coarse_step)))
    decay = max(0.1, min(0.9, float(decay)))
    stochastic_jitter = max(0.05, min(0.60, float(stochastic_jitter)))

    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}



    def _eval(idx: int) -> float:
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

        step_num = len(history) + 1

        record = {
            "step": step_num,
            "phase": phase,
            "idx": z,
            "z": z,
            "step_dz": dz,
            "score": val,
            "gradient": grad,
            "decision": decision,
        }
        history.append(record)
        return z, val

    # 1. INIT PHASE
    z_init, s_init = probe(z0, "INIT", "Initial stage position capture", dz_override=0)
    best_z, best_s = z_init, s_init

    # 2. PROBE PHASE
    if z0 <= probe_step:
        p_step = probe_step if z0 + probe_step <= max_idx else max(0, max_idx - z0)
        z_probe, s_probe = probe(z0 + p_step, "PROBE", "Probe slope", dz_override=p_step)
        direction = 1
        slope = (s_probe - s_init) / float(p_step) if p_step != 0 else 0.0
        history[-1]["decision"] = f"Stage at lower boundary Z={z0} -> Climb +Z"
    elif z0 >= max_idx - probe_step:
        p_step = -probe_step if z0 - probe_step >= 0 else -z0
        z_probe, s_probe = probe(z0 + p_step, "PROBE", "Probe slope", dz_override=p_step)
        direction = -1
        slope = (s_probe - s_init) / float(p_step) if p_step != 0 else 0.0
        history[-1]["decision"] = f"Stage at upper boundary Z={z0} -> Climb -Z"
    else:
        p_step = probe_step
        z_probe, s_probe = probe(z0 + p_step, "PROBE", "Probe slope", dz_override=p_step)
        slope = (s_probe - s_init) / float(p_step)
        direction = 1 if slope >= 0 else -1
        dir_str = "+Z" if direction > 0 else "-Z"
        history[-1]["decision"] = f"Slope d(NV)/dZ = {slope:+.4f} -> Climb {dir_str}"

    if s_probe > best_s:
        best_z, best_s = z_probe, s_probe
    z_curr = z_probe

    # 3. CLIMB PHASE (Ascent along gradient)
    coarse_steps_taken = 0
    reversed_initial = False

    while True:
        step = coarse_step
        if adaptive and len(history) >= 2:
            last_grad = abs(history[-1]["gradient"])
            step = max(4, min(coarse_step * 2, int(round(coarse_step * (1.0 + last_grad * 40.0)))))

        next_z = z_curr + direction * step
        if not (0 <= next_z <= max_idx):
            next_z = max(0, min(max_idx, next_z))
            if next_z == z_curr:
                if coarse_steps_taken == 0 and not reversed_initial:
                    direction = -direction
                    reversed_initial = True
                    z_curr = z_init
                    continue
                else:
                    break

        dz_val = next_z - z_curr
        z_eval, s_eval = probe(next_z, "CLIMB", f"Ascent step ({dz_val:+d}) along gradient", dz_override=dz_val)

        if s_eval > best_s:
            best_z, best_s = z_eval, s_eval
            z_curr = z_eval
            coarse_steps_taken += 1
        else:
            # Score did not improve: check if initial noise dip misled probe
            if coarse_steps_taken == 0 and not reversed_initial:
                direction = -direction
                reversed_initial = True
                z_curr = z_init
                history[-1]["phase"] = "PROBE"
                history[-1]["decision"] = f"Initial slope was noise dip (NV {s_eval:.3f} <= {best_s:.3f}) -> Reverse direction to {'+Z' if direction > 0 else '-Z'}"
                continue

            # Overshot peak after climbing
            history[-1]["phase"] = "OVERSHOOT"
            history[-1]["decision"] = f"Overshot peak! NV dropped ({s_eval:.3f} < {best_s:.3f}) -> Reverse & Bracket"
            break

    # 4. BRACKET PHASE (Stochastic Peak Bracketing)
    # Stochastically modify decreasing factor: alpha_rand in [decay*(1-jitter), decay*(1+jitter)]
    jitter_val = rng.uniform(-stochastic_jitter, stochastic_jitter)
    stochastic_decay = max(0.15, min(0.85, decay * (1.0 + jitter_val)))
    mid_step = int(round(coarse_step * stochastic_decay))
    mid_z = best_z - direction * mid_step

    if 0 <= mid_z <= max_idx and mid_z not in evals:
        dz_val = mid_z - history[-1]["z"]
        z_eval, s_eval = probe(
            mid_z,
            "BRACKET",
            f"Stochastic midpoint (decay α={stochastic_decay:.3f}) at Z={mid_z}",
            dz_override=dz_val
        )
        if s_eval > best_s:
            best_z, best_s = z_eval, s_eval
            history[-1]["decision"] = f"Stochastic bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
        else:
            history[-1]["decision"] = f"Bracketing check (α={stochastic_decay:.3f}) at Z={mid_z} (NV={s_eval:.3f} < Best {best_s:.3f})"

    # Perturbed fine bracket steps
    jitter_fine = rng.uniform(-stochastic_jitter, stochastic_jitter)
    stochastic_fine_decay = max(0.15, min(0.85, (decay * decay) * (1.0 + jitter_fine)))
    fine_step = max(2, int(round(coarse_step * stochastic_fine_decay)))

    for offset in [-fine_step, fine_step]:
        cand_z = best_z + offset
        if 0 <= cand_z <= max_idx and cand_z not in evals:
            dz_val = cand_z - history[-1]["z"]
            z_eval, s_eval = probe(
                cand_z,
                "BRACKET",
                f"Stochastic bracket (ΔZ={fine_step}) at Z={cand_z}",
                dz_override=dz_val
            )
            if s_eval > best_s:
                best_z, best_s = z_eval, s_eval
                history[-1]["decision"] = f"Bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
            else:
                history[-1]["decision"] = f"Bracketing check at Z={cand_z} (NV={s_eval:.3f} < Best {best_s:.3f})"

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

    # 5. STOCHASTIC ESCAPE FROM LOCAL MAXIMA
    # If trapped in a local noise peak, test exploratory stochastic jumps with randomized factor
    for attempt in range(max_escape_attempts + 1):
        rand_factor = rng.uniform(0.75, 2.25)
        escape_step = int(round(coarse_step * rand_factor))
        escaped = False
        for escape_dir in [direction, -direction]:
            esc_z = best_z + escape_dir * escape_step
            if 0 <= esc_z <= max_idx and esc_z not in evals:
                dz_val = esc_z - history[-1]["z"]
                z_eval, s_eval = probe(
                    esc_z,
                    "ESCAPE_PROBE",
                    f"Stochastic escape probe (attempt {attempt+1}, factor={rand_factor:.2f}) at Z={esc_z}",
                    dz_override=dz_val
                )
                if s_eval > best_s:
                    best_z, best_s = z_eval, s_eval
                    history[-1]["decision"] = f"Stochastic jump escaped local maximum! New Best Z_c = {best_z} (NV = {best_s:.3f}). Resuming climb."
                    # Resume coarse climb in this direction from the escaped focal position
                    z_curr = best_z
                    direction = escape_dir
                    while True:
                        next_z = max(0, min(max_idx, z_curr + direction * coarse_step))
                        if next_z == z_curr:
                            break
                        dz_c = next_z - z_curr
                        ze_c, se_c = probe(next_z, "CLIMB", f"Ascent step ({dz_c:+d}) along gradient", dz_override=dz_c)
                        if se_c > best_s:
                            best_z, best_s = ze_c, se_c
                            z_curr = ze_c
                        else:
                            history[-1]["phase"] = "OVERSHOOT"
                            history[-1]["decision"] = f"Overshot peak! NV dropped ({se_c:.3f} < {best_s:.3f}) -> Reverse & Bracket"
                            break
                    escaped = True
                    break
        if escaped:
            # After resuming climb and overshooting the global peak, run final unit refinement
            for offset in [-1, 1]:
                cand_z = best_z + offset
                if 0 <= cand_z <= max_idx and cand_z not in evals:
                    dz_val = cand_z - history[-1]["z"]
                    z_eval, s_eval = probe(cand_z, "BRACKET", f"Bracketing check at Z={cand_z}", dz_override=dz_val)
                    if s_eval > best_s:
                        best_z, best_s = z_eval, s_eval
                        history[-1]["decision"] = f"Bracketing improved peak! New Best Z_c = {best_z} (NV = {best_s:.3f})"
            break

    # 6. CONVERGED PHASE
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
stochastic_gradient_search = gradient_descent_search_modified
coarse_to_fine_gradient_search_modified = gradient_descent_search_modified
gradient_ascent_search_modified = gradient_descent_search_modified
gradient_descent_search = gradient_descent_search_modified
gradient_search = gradient_descent_search_modified
