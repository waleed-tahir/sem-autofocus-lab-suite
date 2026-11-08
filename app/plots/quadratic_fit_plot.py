"""The fine fit: zoomed parabolic polynomial around the coarse peak.

Redesigned with high readability:
- Clean parabola fitted through the measured window.
- The raw formula box in the corner is removed to prevent chart clutter (already in side panel).
- Clean legend placed outside/bottom to stop burying curves.
- Large, high-visibility vertex and ground-truth comparison markers.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from matplotlib.figure import Figure

from app.core.experiment import GroundTruth
from app.core.run_result import RunResult
from app.plots.style import (
    INK_PRIMARY,
    INK_SECONDARY,
    MARKER_EDGE_WIDTH,
    PEAK_MARKER_SIZE,
    REFERENCE,
    REFERENCE_LINE_WIDTH,
    SURFACE,
    algorithm_style,
    empty_message,
    finish_figure,
    frame_index_axis,
    style_axes,
)

PARABOLA_SAMPLES = 250
CONTEXT_FRAMES = 3


def draw_quadratic_fit(
    figure: Figure,
    result: Optional[RunResult],
    truth: Optional[GroundTruth] = None,
) -> None:
    figure.clear()
    if result is None:
        empty_message(figure, "No run selected.")
        return
    if result.fit_window is None:
        empty_message(
            figure,
            f"{result.algorithm} returned no quadratic fit.\n"
            "Enable \"Apply the quadratic fit to every algorithm\" on the Run tab.",
        )
        return

    ax = figure.add_subplot(111)
    lo, hi = result.fit_window
    style = algorithm_style(result.algorithm_key)
    wd_mm = truth.wd_mm if truth is not None else None

    # 1. Reference scan context curve underneath
    if truth is not None:
        _draw_reference_window(ax, truth, lo, hi)

    # 2. Measured sample points
    frames = sorted(result.fit_points)
    positions = _positions(frames, wd_mm)
    scores = [result.fit_points[frame] for frame in frames]

    ax.plot(
        positions, scores,
        linestyle="none", marker="o", markersize=6.5,
        color=style.color, markeredgecolor="#ffffff",
        markeredgewidth=1.2, zorder=4,
        label=f"Sampled points ({len(frames)} frames)",
    )

    # 3. Fitted smooth parabola
    _draw_parabola(ax, result, positions, style.color)

    # 4. Parabola vertex (sub-frame peak)
    _draw_vertex(ax, result, style.color, wd_mm)

    unit = "Working distance (mm)" if wd_mm is not None else "Frame index"
    style_axes(
        ax,
        title=f"Sub-Frame Quadratic Fit Zoom — {result.algorithm} ({result.dataset_label})",
        xlabel=unit,
        ylabel="Focus score",
        legend=False,
    )
    if wd_mm is not None:
        frame_index_axis(ax, wd_mm)
        _limit_to_window(ax, wd_mm, lo, hi)

    # Adaptive, highly readable Y-axis formatting to eliminate duplicate rounded numbers
    y_min, y_max = ax.get_ylim()
    y_range = abs(y_max - y_min)
    if y_range < 5:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.2f}")
    elif y_range < 50:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.1f}")
    elif abs(y_max) >= 1000:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x/1000:.1f}k")
    else:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0f}")

    # Clean legend positioned outside at the bottom
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(
            handles, labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=min(3, len(handles)),
            frameon=True,
            facecolor="#ffffff",
            edgecolor="#e5e5e5",
            fontsize=8.5,
        )

    finish_figure(figure)


def _positions(frames: list[int], wd_mm: Optional[np.ndarray]) -> list[float]:
    if wd_mm is None:
        return [float(frame) for frame in frames]
    return [float(wd_mm[frame]) for frame in frames]


def _draw_reference_window(ax, truth: GroundTruth, lo: int, hi: int) -> None:
    low = max(0, lo - CONTEXT_FRAMES)
    high = min(truth.curve.size - 1, hi + CONTEXT_FRAMES)
    window = np.arange(low, high + 1)
    ax.plot(
        truth.wd_mm[window], truth.curve[window],
        color="#8c8c8c", linewidth=2.0, zorder=2,
        label="Reference curve",
    )
    ax.axvline(
        truth.reference_wd_mm,
        color="#8c8c8c", linestyle="--", linewidth=1.4, zorder=3,
        label=f"Reference peak ({truth.reference_wd_mm:.4f} mm)",
    )


def _draw_parabola(ax, result: RunResult, positions: list[float], color: str) -> None:
    if result.fit_coeffs is None or not positions:
        return

    a0, a1, a2 = result.fit_coeffs
    centre = _centre_position(result, positions)
    span = np.linspace(min(positions), max(positions), PARABOLA_SAMPLES)
    offsets = span - centre
    values = a0 + a1 * offsets + a2 * offsets**2

    r2_str = f"R² = {result.fit_r2:.3f}" if not math.isnan(result.fit_r2) else ""
    ax.plot(
        span, values,
        color=color, linewidth=2.2, alpha=0.95, zorder=5,
        label=f"Fitted parabola ({r2_str})" if r2_str else "Fitted parabola",
    )


def _centre_position(result: RunResult, positions: list[float]) -> float:
    frames = sorted(result.fit_points)
    if result.coarse_idx in frames:
        return positions[frames.index(result.coarse_idx)]
    return positions[len(positions) // 2]


def _draw_vertex(
    ax, result: RunResult, color: str, wd_mm: Optional[np.ndarray]
) -> None:
    if not result.fit_ok or math.isnan(result.fine_idx):
        return

    x = result.fine_wd_mm if wd_mm is not None else result.fine_idx
    if math.isnan(x):
        return

    ax.axvline(x, color=color, linestyle="--", linewidth=1.6, zorder=6)
    if not math.isnan(result.fine_value):
        ax.plot(
            [x], [result.fine_value],
            marker="*", markersize=16.0, color="#d83b01",
            markeredgecolor="#ffffff", markeredgewidth=1.4,
            linestyle="none", zorder=7,
            label=f"Fitted peak: frame {result.fine_idx:.2f} ({result.fine_wd_mm:.4f} mm)",
        )


def _limit_to_window(ax, wd_mm: np.ndarray, lo: int, hi: int) -> None:
    low = max(0, lo - CONTEXT_FRAMES)
    high = min(wd_mm.size - 1, hi + CONTEXT_FRAMES)
    left, right = float(wd_mm[low]), float(wd_mm[high])
    ax.set_xlim(min(left, right), max(left, right))


def fit_summary_lines(result: Optional[RunResult]) -> list[str]:
    if result is None:
        return ["No run selected."]
    if result.fit_window is None:
        return [f"{result.algorithm}: no quadratic fit was applied."]

    lo, hi = result.fit_window
    lines = [
        f"Algorithm:       {result.algorithm}",
        f"Image set:       {result.dataset_label}",
        f"Focus measure:   {result.measure}",
        "",
        f"Coarse peak:     frame {result.coarse_idx} ({result.coarse_wd_mm:.4f} mm)",
        f"Refined fine:    frame {result.fine_idx:.3f} ({result.fine_wd_mm:.5f} mm)",
        f"Fit window:      frames {lo} to {hi} ({len(result.fit_points)} points)",
        f"Fit status:      {result.fit_status}",
        f"R² correlation:  {result.fit_r2:.4f}",
    ]
    if result.fit_coeffs is not None:
        a0, a1, a2 = result.fit_coeffs
        lines.extend([
            "",
            "Parabola coefficients:",
            f"  A0 = {a0:.5g}",
            f"  A1 = {a1:.5g}",
            f"  A2 = {a2:.5g}",
        ])
    if result.error_um is not None and not math.isnan(result.error_um):
        lines.extend([
            "",
            f"Error vs Ref:    {result.error_um:.3f} µm",
        ])
    return lines
