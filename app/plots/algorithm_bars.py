"""Cost against accuracy: Global Scan vs Gradient Search.

Three side-by-side panels answer the core questions of the comparison:
1. Frames read (beam time / exposure cost)
2. Convergence time (ms)
3. Position error (um vs reference peak)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from matplotlib.figure import Figure

from app.core.algorithms import BASELINE_KEY
from app.core.run_result import RunResult
from app.plots.style import (
    INK_SECONDARY,
    SURFACE,
    algorithm_style,
    empty_message,
    finish_figure,
    style_axes,
)

BAR_WIDTH = 0.50
HEADROOM = 1.25

ALGO_SHORT_NAMES = {
    "global_scan": "Global",
    "gradient": "Gradient",
    "gradient_modified": "Gradient (Mod)",
    "Global Scan (exhaustive)": "Global",
    "Gradient Search": "Gradient",
    "Gradient Search (Stochastic Modified)": "Gradient (Mod)",
}

PANEL_COLORS = {
    "frames": ("#0067c0", "#0078d4"),  # Fluent Blue
    "time": ("#008272", "#107c41"),    # Fluent Green
    "error": ("#d83b01", "#b83400"),   # Fluent Orange/Red
}


def draw_algorithm_bars(figure: Figure, results: Sequence[RunResult]) -> None:
    """Draw 3 side-by-side panels: frames read, run time, and position error.

    Args:
        figure: Matplotlib Figure to draw on.
        results: Runs on the active dataset.
    """
    figure.clear()
    if not results:
        empty_message(
            figure,
            "No runs for this image set yet.\nRun Global Scan and Gradient Search on the Run tab.",
        )
        return

    # Order: Baseline first, then Gradient search
    ordered = sorted(results, key=lambda r: 0 if r.algorithm_key == BASELINE_KEY else 1)
    labels = [ALGO_SHORT_NAMES.get(r.algorithm_key, r.algorithm[:10]) for r in ordered]
    positions = np.arange(len(ordered), dtype=np.float64)

    panels = (
        ("Frames Read (Lower = Better)", [float(r.frames_evaluated) for r in ordered], "frames", 0, "frames"),
        ("Convergence Time (ms)", [r.elapsed_ms for r in ordered], "ms", 0, "time"),
        ("Error vs. Reference (µm)", [r.coarse_error_um if r.coarse_error_um is not None else 0.0 for r in ordered], "µm", 2, "error"),
    )

    axes = figure.subplots(1, 3)

    for (title, values, unit, decimals, key), ax in zip(panels, axes, strict=True):
        heights = [0.0 if value is None or math.isnan(value) else float(value) for value in values]
        primary_color = PANEL_COLORS[key][0]

        # Draw bars
        bars = ax.bar(
            positions,
            heights,
            width=BAR_WIDTH,
            color=primary_color,
            edgecolor="#ffffff",
            linewidth=1.2,
            zorder=3,
        )

        # Draw value labels above each bar
        for pos, height, raw in zip(positions, heights, values, strict=True):
            text = "n/a" if raw is None or math.isnan(raw) else f"{raw:.{decimals}f}"
            ax.annotate(
                text,
                xy=(pos, height),
                xytext=(0.0, 4.0),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
                color="#1c1c1c",
            )

        tallest = max(heights) if heights else 0.0
        ax.set_ylim(0.0, (tallest * HEADROOM) if tallest > 0.0 else 1.0)
        ax.set_xlim(-0.6, len(ordered) - 0.4)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=9.0, fontweight="bold", color="#424242")
        style_axes(ax, title=title, ylabel=unit)
        ax.grid(axis="x", visible=False)

    dataset = ordered[0].dataset_label
    measure = ordered[0].measure
    finish_figure(figure)
    figure.suptitle(
        f"Algorithm Performance Comparison — {dataset} ({measure})",
        fontsize=11.0,
        fontweight="bold",
        color="#1c1c1c",
    )


@dataclass(frozen=True)
class SavingRow:
    """How much one algorithm saved against the exhaustive scan."""

    algorithm: str
    frames_evaluated: int
    baseline_frames: int
    saved_percent: float
    elapsed_ms: float
    speedup: float
    error_um: float


def frames_saved_table(results: Sequence[RunResult]) -> list[SavingRow]:
    """Turn the runs of one image set into savings rows."""
    if not results:
        return []

    baseline = next((r for r in results if r.algorithm_key == BASELINE_KEY), None)
    baseline_frames = (
        baseline.frames_evaluated if baseline else max(r.frames_evaluated for r in results)
    )
    baseline_ms = baseline.elapsed_ms if baseline else float("nan")

    rows = [
        SavingRow(
            algorithm=result.algorithm,
            frames_evaluated=result.frames_evaluated,
            baseline_frames=baseline_frames,
            saved_percent=result.frames_saved_percent(baseline_frames),
            elapsed_ms=result.elapsed_ms,
            speedup=(
                baseline_ms / result.elapsed_ms
                if not math.isnan(baseline_ms) and result.elapsed_ms > 0.0
                else float("nan")
            ),
            error_um=result.coarse_error_um if result.coarse_error_um is not None else float("nan"),
        )
        for result in results
    ]
    return sorted(rows, key=lambda row: row.frames_evaluated)
