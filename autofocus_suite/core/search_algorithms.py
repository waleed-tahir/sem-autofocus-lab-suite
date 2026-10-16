"""
Sub-Linear Z-Stack Search Algorithms for Electron Microscopy
Implements Section 5 from the Lab Specification Guide:
- S1: Fibonacci Search (Theoretical minimum frame reads O(log_phi N))
- S2: Hybrid Two-Stage Coarse-to-Fine Sweep (Most robust, wide-basin coarse -> razor-sharp fine)
- S3: Multi-Resolution Pyramid Bracket (3-tier resolution decimation)
- S4: Speculative Parallel ThreadPool Sweep (Two-batch asynchronous disk I/O)
- Baseline: Global Exhaustive Linear Scan (Ground truth reference)
- Legacy: Golden Section Search & Hill Climbing
"""

from __future__ import annotations
from typing import Callable, Dict, List, Tuple, Any, Optional
import math
from concurrent.futures import ThreadPoolExecutor


def search_fibonacci(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    stride: int = 2,
    fine_stride: int = 1,
    fmo_name: Optional[str] = None
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    S1 — Fibonacci Lattice Search:
    Places interior probe points at Fibonacci ratios F_{k-2}/F_k and F_{k-1}/F_k.
    Reuses one interior evaluation on every iteration, locating the exact discrete
    maximum in ~11-13 frame reads for a 200-frame stack.
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    def probe(idx: int, current_stride: int, stage: str) -> float:
        idx = max(0, min(max_idx, int(round(idx))))
        if idx in evals:
            return evals[idx]
        val = eval_func(idx, current_stride, fmo_name)
        evals[idx] = val
        history.append({
            "step": len(history) + 1,
            "idx": idx,
            "score": val,
            "stride": current_stride,
            "stage": stage
        })
        return val

    # Generate Fibonacci sequence up to >= max_idx + 1
    target = max_idx + 1
    fib = [1, 1]
    while fib[-1] < target:
        fib.append(fib[-1] + fib[-2])
    n_fib = len(fib) - 1

    a = 0
    b = fib[n_fib]  # virtual upper bound
    x1 = a + fib[n_fib - 2]
    x2 = a + fib[n_fib - 1]

    # Initial evaluations clamped to valid stack range
    f1 = probe(min(x1, max_idx), stride, "coarse_fib")
    f2 = probe(min(x2, max_idx), stride, "coarse_fib")

    for k in range(n_fib - 1, 2, -1):
        if f1 > f2:
            b = x2
            x2 = x1
            f2 = f1
            x1 = a + fib[k - 2]
            f1 = probe(min(x1, max_idx), stride, "coarse_fib")
        else:
            a = x1
            x1 = x2
            f1 = f2
            x2 = a + fib[k - 1]
            f2 = probe(min(x2, max_idx), stride, "coarse_fib")

    # Find the best candidate among all evaluated
    best_candidate = max(evals.keys(), key=lambda idx: evals[idx])

    # Fine bracket check on neighbors with fine_stride
    for neighbor in [best_candidate - 1, best_candidate, best_candidate + 1]:
        if 0 <= neighbor <= max_idx:
            probe(neighbor, fine_stride, "fine_bracket")

    final_best = max(evals.keys(), key=lambda idx: evals[idx])
    return final_best, evals, history


def search_hybrid_coarse_fine(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    coarse_fmo: str = "composite_m9_m2",
    fine_fmo: Optional[str] = None,
    coarse_stride: int = 4,
    fine_stride: int = 1
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    S2 — Hybrid Two-Stage Coarse-to-Fine Sweep (Most Robust):
    Stage 1: Evaluates every s = max(3, round(sqrt(N))) frame at pixel_stride=4
             using wide-basin composite operator (M9 + M2).
    Stage 2: Runs fine sweep around [kc - s, kc + s] at pixel_stride=1 using
             the primary high-precision FMO.
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    def probe(idx: int, current_stride: int, current_fmo: Optional[str], stage: str) -> float:
        idx = max(0, min(max_idx, int(round(idx))))
        val = eval_func(idx, current_stride, current_fmo)
        evals[idx] = val
        history.append({
            "step": len(history) + 1,
            "idx": idx,
            "score": val,
            "stride": current_stride,
            "fmo": current_fmo or "default",
            "stage": stage
        })
        return val

    # Stage 1: Coarse Grid Sweep
    num_frames = max_idx + 1
    step_s = max(3, int(round(math.sqrt(num_frames))))
    coarse_indices = list(range(0, num_frames, step_s))
    if coarse_indices[-1] != max_idx:
        coarse_indices.append(max_idx)

    coarse_scores = {}
    for idx in coarse_indices:
        coarse_scores[idx] = probe(idx, coarse_stride, coarse_fmo, "coarse_grid")

    # Coarse peak
    kc = max(coarse_scores.keys(), key=lambda k: coarse_scores[k])

    # Stage 2: Fine Bracket Search
    # Refine window [kc - step_s, kc + step_s]
    w_start = max(0, kc - step_s)
    w_end = min(max_idx, kc + step_s)

    # Sub-sample inside window with step = 2 first, then peak neighbors
    mid_step = max(1, step_s // 4)
    fine_probes = list(range(w_start, w_end + 1, mid_step))
    if w_end not in fine_probes:
        fine_probes.append(w_end)

    fine_scores = {}
    for idx in fine_probes:
        fine_scores[idx] = probe(idx, fine_stride, fine_fmo, "fine_window")

    best_fine = max(fine_scores.keys(), key=lambda k: fine_scores[k])

    # Exact 3-point peak confirmation
    for nbr in [best_fine - 1, best_fine, best_fine + 1]:
        if 0 <= nbr <= max_idx and nbr not in evals:
            val = probe(nbr, fine_stride, fine_fmo, "fine_bracket")
            fine_scores[nbr] = val

    overall_best = max(fine_scores.keys(), key=lambda k: fine_scores[k])
    return overall_best, evals, history


def search_pyramid_bracket(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    fmo_name: Optional[str] = None
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    S3 — Multi-Resolution Pyramid Bracket:
    Downsamples frames by 4x across 9-point global grid, refines at 2x across 5
    mid-tier points, evaluates full resolution only on final 5-frame neighborhood.
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    def probe(idx: int, stride: int, stage: str) -> float:
        idx = max(0, min(max_idx, int(round(idx))))
        val = eval_func(idx, stride, fmo_name)
        evals[idx] = val
        history.append({
            "step": len(history) + 1,
            "idx": idx,
            "score": val,
            "stride": stride,
            "stage": stage
        })
        return val

    # Tier 1: 9-point global coarse grid (stride 4)
    t1_indices = [int(round(i * max_idx / 8.0)) for i in range(9)]
    t1_scores = {}
    for idx in t1_indices:
        t1_scores[idx] = probe(idx, 4, "tier1_global_4x")

    k_t1 = max(t1_scores.keys(), key=lambda k: t1_scores[k])
    span1 = max(4, int(max_idx / 8.0))

    # Tier 2: 5 mid-tier points (stride 2) around k_t1
    t2_start = max(0, k_t1 - span1)
    t2_end = min(max_idx, k_t1 + span1)
    t2_indices = [int(round(t2_start + i * (t2_end - t2_start) / 4.0)) for i in range(5)]
    t2_scores = {}
    for idx in t2_indices:
        t2_scores[idx] = probe(idx, 2, "tier2_mid_2x")

    k_t2 = max(t2_scores.keys(), key=lambda k: t2_scores[k])

    # Tier 3: 5 full-resolution points (stride 1) around k_t2
    t3_start = max(0, k_t2 - 2)
    t3_end = min(max_idx, k_t2 + 2)
    t3_scores = {}
    for idx in range(t3_start, t3_end + 1):
        t3_scores[idx] = probe(idx, 1, "tier3_full_1x")

    best_idx = max(t3_scores.keys(), key=lambda k: t3_scores[k])
    return best_idx, evals, history


def search_speculative_parallel(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    fmo_name: Optional[str] = None,
    num_threads: int = 8
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    S4 — Speculative ThreadPool Batch Sweep:
    Batch 1: Dispatches parallel ThreadPool reads for all coarse probe points simultaneously.
    Batch 2: Dispatches parallel ThreadPool reads for local 7-frame peak window.
    Completes in just two disk I/O round trips!
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    num_frames = max_idx + 1
    step_s = max(4, int(round(math.sqrt(num_frames))))
    coarse_indices = list(range(0, num_frames, step_s))
    if coarse_indices[-1] != max_idx:
        coarse_indices.append(max_idx)

    # Batch 1: Async parallel coarse reads
    def eval_worker(args):
        idx, stride, stage = args
        val = eval_func(idx, stride, fmo_name)
        return idx, val, stride, stage

    batch1_tasks = [(idx, 2, "batch1_coarse_parallel") for idx in coarse_indices]
    with ThreadPoolExecutor(max_workers=min(num_threads, len(batch1_tasks))) as executor:
        batch1_results = list(executor.map(eval_worker, batch1_tasks))

    coarse_scores = {}
    for idx, val, stride, stage in batch1_results:
        evals[idx] = val
        coarse_scores[idx] = val
        history.append({
            "step": len(history) + 1,
            "idx": idx,
            "score": val,
            "stride": stride,
            "stage": stage
        })

    kc = max(coarse_scores.keys(), key=lambda k: coarse_scores[k])

    # Batch 2: Async parallel fine 7-frame window
    w_start = max(0, kc - 3)
    w_end = min(max_idx, kc + 3)
    fine_indices = [idx for idx in range(w_start, w_end + 1) if idx not in evals]

    if fine_indices:
        batch2_tasks = [(idx, 1, "batch2_fine_parallel") for idx in fine_indices]
        with ThreadPoolExecutor(max_workers=min(num_threads, len(batch2_tasks))) as executor:
            batch2_results = list(executor.map(eval_worker, batch2_tasks))

        for idx, val, stride, stage in batch2_results:
            evals[idx] = val
            history.append({
                "step": len(history) + 1,
                "idx": idx,
                "score": val,
                "stride": stride,
                "stage": stage
            })

    # Pick overall highest score
    best_idx = max(evals.keys(), key=lambda k: evals[k])
    return best_idx, evals, history


def search_global_linear_scan(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    stride: int = 1,
    fmo_name: Optional[str] = None
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    Baseline: Global Exhaustive Linear Scan.
    Evaluates every frame in the focal stack sequentially.
    Establishes discrete ground truth and benchmark baseline.
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    best_idx = 0
    best_score = -float('inf')

    for idx in range(max_idx + 1):
        val = eval_func(idx, stride, fmo_name)
        evals[idx] = val
        history.append({
            "step": idx + 1,
            "idx": idx,
            "score": val,
            "stride": stride,
            "stage": "full_linear_scan"
        })
        if val > best_score:
            best_score = val
            best_idx = idx

    return best_idx, evals, history


def search_golden_section(
    eval_func: Callable[[int, int, Optional[str]], float],
    max_idx: int,
    stride: int = 1,
    fmo_name: Optional[str] = None,
    tol: float = 1.0
) -> Tuple[int, Dict[int, float], List[Dict[str, Any]]]:
    """
    Legacy Golden Section Search:
    Classic 1D bracket minimization with golden ratio phi = (sqrt(5) - 1) / 2.
    """
    history: List[Dict[str, Any]] = []
    evals: Dict[int, float] = {}

    def probe(x: float) -> float:
        idx = max(0, min(max_idx, int(round(x))))
        if idx in evals:
            return evals[idx]
        val = eval_func(idx, stride, fmo_name)
        evals[idx] = val
        history.append({
            "step": len(history) + 1,
            "idx": idx,
            "score": val,
            "stride": stride,
            "stage": "golden_section"
        })
        return val

    phi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = 0.0, float(max_idx)

    c = b - phi * (b - a)
    d = a + phi * (b - a)

    fc = probe(c)
    fd = probe(d)

    while (b - a) > tol:
        if fc > fd:
            b = d
            d = c
            fd = fc
            c = b - phi * (b - a)
            fc = probe(c)
        else:
            a = c
            c = d
            fc = fd
            d = a + phi * (b - a)
            fd = probe(d)

    best_idx = max(evals.keys(), key=lambda k: evals[k])
    return best_idx, evals, history


SEARCH_REGISTRY = {
    "s1_fibonacci": search_fibonacci,
    "s2_hybrid": search_hybrid_coarse_fine,
    "s3_pyramid": search_pyramid_bracket,
    "s4_speculative": search_speculative_parallel,
    "baseline_global": search_global_linear_scan,
    "golden_section": search_golden_section
}

SEARCH_METADATA = {
    "s1_fibonacci": {
        "id": "S1",
        "name": "Fibonacci Lattice Search",
        "complexity": "O(log_phi N)",
        "expected_reads": "11-13 frames (12%)",
        "latency_profile": "~1.8 - 3.2 ms",
        "description": "Places interior probes at Fibonacci ratios, reusing prior evaluations; minimum read count for unimodal stacks."
    },
    "s2_hybrid": {
        "id": "S2",
        "name": "Hybrid Coarse-to-Fine Sweep",
        "complexity": "O(sqrt(N) + fine)",
        "expected_reads": "16-19 frames (17%)",
        "latency_profile": "~3.0 - 5.0 ms",
        "description": "Combines wide-basin M9+M2 coarse sweep at 4x stride with high-precision fine bracket lock. Most robust against noise plateaus."
    },
    "s3_pyramid": {
        "id": "S3",
        "name": "Multi-Resolution Pyramid Bracket",
        "complexity": "O(N/16 + 5)",
        "expected_reads": "15-18 frames (16%)",
        "latency_profile": "~2.5 - 4.2 ms",
        "description": "3-tier decimation: 4x downsample across 9 global points -> 2x across 5 mid-tier points -> full resolution on peak."
    },
    "s4_speculative": {
        "id": "S4",
        "name": "Speculative Parallel ThreadPool",
        "complexity": "O(sqrt(N) / P_cores)",
        "expected_reads": "17-20 frames (18%)",
        "latency_profile": "~1.5 - 2.8 ms",
        "description": "Parallel batch execution on multi-core CPU. Completes the full search in only two disk I/O round trips."
    },
    "baseline_global": {
        "id": "Global",
        "name": "Global Full Stack Scan",
        "complexity": "O(N)",
        "expected_reads": "200 frames (100%)",
        "latency_profile": "~35 - 75 ms",
        "description": "Evaluates every frame sequentially. Provides true focal peak ground truth and reference focus curve."
    },
    "golden_section": {
        "id": "GS",
        "name": "Golden Section Search",
        "complexity": "O(log N)",
        "expected_reads": "20-25 frames (20%)",
        "latency_profile": "~4.0 - 6.5 ms",
        "description": "Standard golden ratio interval division."
    }
}
