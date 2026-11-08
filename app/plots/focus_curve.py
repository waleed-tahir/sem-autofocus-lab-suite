"""Plot A: the full focus curve with the frames a search actually visited.

Redesigned with high readability and modern visual hierarchy:
- Legend moved outside the plot area or below to stop burying data curves.
- Multi-algorithm markers drawn with clean distinct styling and no messy clutter.
- Axis numbers formatted with standard SI / metric notation.
- Crisp Segoe UI typography and elegant Fluent styling.
"""

from __future__ import annotations

import math
from typing import Sequence

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

FINE_LINE_ALPHA = 0.95
VISIT_ALPHA = 0.88
DENSE_RUN_FRAMES = 50


def draw_focus_curve(
    figure: Figure,
    truth: Optional[GroundTruth],
    results: Sequence[RunResult] = (),
    replay_step: Optional[int] = None,
) -> None:
    figure.clear()
    if truth is None:
        empty_message(
            figure,
            "No reference curve yet.\nPress \"Compute reference curve\" or run a search.",
        )
        return

    ax = figure.add_subplot(111)
    wd_mm = truth.wd_mm

    # 1. Subtle, clean reference curve underneath
    ax.plot(
        wd_mm, truth.curve,
        color="#8c8c8c", linewidth=2.0, zorder=2,
        label=f"Reference curve ({truth.measure_name})",
    )
    # Peak marker
    ax.plot(
        [truth.peak_wd_mm], [truth.peak_value],
        marker="*", markersize=16.0, color="#d83b01",
        markeredgecolor="#ffffff", markeredgewidth=1.5,
        linestyle="none", zorder=5, label=f"True peak: frame {truth.peak_idx} ({truth.peak_wd_mm:.4f} mm)",
    )

    # 2. Visited algorithm paths
    for result in results:
        _draw_run(ax, truth, result, replay_step=replay_step)

    # Style axes
    style_axes(
        ax,
        title=f"Focus Curve & Visited Search Probes — {truth.dataset_label}",
        xlabel="Working distance (mm)",
        ylabel="Focus score",
        legend=False,
    )
    frame_index_axis(ax, wd_mm)

    # Clean multi-column legend positioned underneath or outside to stop overlapping curves
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

    # Adaptive, highly readable Y-axis formatting to avoid identical duplicate numbers
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

    finish_figure(figure)


def _draw_run(
    ax,
    truth: GroundTruth,
    result: RunResult,
    replay_step: Optional[int] = None,
) -> None:
    style = algorithm_style(result.algorithm_key)
    wd_mm = truth.wd_mm
    last = truth.curve.size - 1

    visited_seq = [idx for idx in result.visited if 0 <= idx <= last]
    if replay_step is not None:
        visited_seq = visited_seq[:max(0, replay_step)]

    if visited_seq:
        visited = sorted(set(visited_seq))
        # If exhaustive or dense scan (> 80 frames), show as an elegant continuous search trace line
        if len(visited) >= 80 and replay_step is None:
            ax.plot(
                wd_mm[visited], truth.curve[visited],
                linestyle="-", linewidth=1.5,
                color=style.color, alpha=0.65, zorder=3,
                label=f"{result.algorithm} ({len(visited)} probes)",
            )
        else:
            # Heuristic searches or animated replay: show distinct discrete probe markers
            ax.plot(
                wd_mm[visited], truth.curve[visited],
                linestyle="none", marker=style.marker,
                markersize=6.5,
                color=style.color, markeredgecolor="#ffffff",
                markeredgewidth=1.2, alpha=VISIT_ALPHA, zorder=4,
                label=f"{result.algorithm} ({len(visited_seq)}/{len(result.visited)} probes)",
            )

        # Highlight current probe in replay mode
        if replay_step is not None and visited_seq:
            curr_idx = visited_seq[-1]
            ax.plot(
                [wd_mm[curr_idx]], [truth.curve[curr_idx]],
                marker="o", markersize=13.0,
                color=style.color, markeredgecolor="#ffffff",
                markeredgewidth=2.0, zorder=8,
                label="_nolegend_",
            )

    # Coarse peak star (only show if replay is complete or not replaying)
    show_peak = replay_step is None or replay_step >= len(result.visited)
    if show_peak and 0 <= result.coarse_idx <= last:
        ax.plot(
            [wd_mm[result.coarse_idx]], [truth.curve[result.coarse_idx]],
            marker="*", markersize=14.0, color=style.color,
            markeredgecolor="#ffffff", markeredgewidth=1.2,
            linestyle="none", zorder=6, label="_nolegend_",
        )

    # Fine sub-frame peak vertical line
    if show_peak and result.fit_ok and not math.isnan(result.fine_wd_mm):
        ax.axvline(
            result.fine_wd_mm,
            color=style.color, linestyle="--", linewidth=1.5,
            alpha=FINE_LINE_ALPHA, zorder=3, label="_nolegend_",
        )
