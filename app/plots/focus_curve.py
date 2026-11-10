"""Plot A: Focus curve and Coarse-to-Fine Gradient Ascent trajectory.

Renders:
1. Global Reference Focus Curve (exhaustive sweep ground truth)
2. Phase 1: Coarse Step trajectory (cyan line and circular markers #1, #2, ...)
3. Phase 2: Fine Refinement trajectory (amber/orange line and markers)
4. Overshoot detection marker (vivid red)
5. Local tangent line d(NV)/dZ at the active inspection step
6. Global Peak marker and annotation
7. Active probe halo indicator
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Any, Dict, List

import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from app.core.experiment import GroundTruth
from app.core.run_result import RunResult
from app.plots.style import (
    INK_PRIMARY,
    INK_SECONDARY,
    SURFACE,
    empty_message,
    finish_figure,
    frame_index_axis,
    style_axes,
)

# Color tokens strictly aligned with lab reference HUD
COLOR_SWEEP = "#64748b"        # Slate grey for global sweep
COLOR_COARSE = "#00b4d8"       # Cyan for Phase 1: Coarse Step
COLOR_FINE = "#f59e0b"         # Amber/orange for Phase 2: Fine Refinement
COLOR_OVERSHOOT = "#ef233c"    # Vivid red for Overshoot
COLOR_TANGENT = "#ef233c"      # Red dashed tangent line
COLOR_PEAK = "#10b981"         # Emerald green for Global Peak
COLOR_HALO = "#0284c7"         # Active probe highlight


def draw_focus_curve(
    figure: Figure,
    truth: Optional[GroundTruth],
    results: Sequence[RunResult] = (),
    replay_step: Optional[int] = None,
    show_global: bool = True,
) -> None:
    """Draw the focus curve with visited search probes and coarse-to-fine trajectory."""
    figure.clear()
    if truth is None:
        empty_message(
            figure,
            "No reference curve yet.\nPress \"Compute reference curve\" or run a search.",
        )
        return

    ax = figure.add_subplot(111)
    wd_mm = truth.wd_mm
    curve = truth.curve
    num_frames = len(curve)
    indices = np.arange(num_frames)

    # 1. Global sweep curve
    if show_global:
        ax.plot(
            indices, curve,
            color=COLOR_SWEEP, linewidth=1.8, alpha=0.55, zorder=2,
            label="Show Global Sweep Curve",
        )

    # 2. Ground-truth Global Peak marker
    peak_idx = truth.peak_idx
    if 0 <= peak_idx < num_frames:
        peak_val = curve[peak_idx]
        ax.plot(
            [peak_idx], [peak_val],
            marker="o", markersize=9.0, color=COLOR_PEAK,
            markeredgecolor="#ffffff", markeredgewidth=1.8,
            linestyle="none", zorder=6,
            label=f"Global Peak Z={peak_idx}",
        )
        ax.annotate(
            f"Global Peak Z={peak_idx}",
            xy=(peak_idx, peak_val),
            xytext=(peak_idx, peak_val + (np.ptp(curve) * 0.05 if np.ptp(curve) > 0 else 0.5)),
            ha="center", va="bottom",
            fontsize=8.5, fontweight="bold", color=COLOR_PEAK,
            zorder=7,
        )

    # 3. Visited trajectories
    for result in results:
        _draw_result_trajectory(ax, truth, result, replay_step=replay_step)

    # 4. Axes and titles styling
    measure_name = truth.measure_name if truth else "Normalized Variance"
    ax.set_title(
        f"{measure_name} Focus Curve & Coarse-to-Fine Gradient Trajectory",
        fontsize=11.5, fontweight="bold", color=INK_PRIMARY, pad=10,
    )
    ax.set_xlabel("Focal Plane Z (Index)", fontsize=9.5, color=INK_SECONDARY, labelpad=6)
    ylabel = "Normalized Variance NV (σ²/µ)" if "norm" in measure_name.lower() else "Focus Score"
    ax.set_ylabel(ylabel, fontsize=9.5, color=INK_SECONDARY, labelpad=6)

    # Custom ticks to show Z indices clearly
    if num_frames > 0:
        step_ticks = max(10, num_frames // 10)
        tick_locs = list(range(0, num_frames, step_ticks))
        if (num_frames - 1) not in tick_locs:
            tick_locs.append(num_frames - 1)
        ax.set_xticks(tick_locs)
        ax.set_xticklabels([f"Z={t}" for t in tick_locs], fontsize=8.0, color=INK_SECONDARY)

    ax.grid(True, linestyle="--", alpha=0.35, color="#cbd5e1", zorder=1)
    for spine in ax.spines.values():
        spine.set_color("#cbd5e1")
        spine.set_linewidth(0.8)

    # Clean legend above or below
    handles, labels = ax.get_legend_handles_labels()
    # Filter duplicate labels
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(
            by_label.values(), by_label.keys(),
            loc="upper center",
            bbox_to_anchor=(0.5, -0.14),
            ncol=min(5, len(by_label)),
            frameon=True,
            facecolor="#ffffff",
            edgecolor="#e2e8f0",
            fontsize=8.5,
        )

    # Y-axis formatter
    y_min, y_max = ax.get_ylim()
    y_span = abs(y_max - y_min)
    if y_span < 5:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.2f}")
    elif y_span < 50:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.1f}")
    else:
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:.0f}")

    finish_figure(figure)


def _draw_result_trajectory(
    ax,
    truth: GroundTruth,
    result: RunResult,
    replay_step: Optional[int] = None,
) -> None:
    """Render the step-by-step coarse-to-fine trajectory."""
    history: List[Dict[str, Any]] = result.extra.get("history", [])
    curve = truth.curve
    num_frames = len(curve)

    # Fallback to standard visited indices if no history
    if not history:
        visited = [idx for idx in result.visited if 0 <= idx < num_frames]
        if replay_step is not None:
            visited = visited[:max(0, replay_step)]
        if visited:
            ax.plot(
                visited, [curve[i] for i in visited],
                color=COLOR_COARSE, marker="o", markersize=6,
                linewidth=1.8, label=f"{result.algorithm} ({len(visited)} probes)",
                zorder=4,
            )
        return

    # Filter history up to replay_step
    active_hist = history[:replay_step] if replay_step is not None else history
    if not active_hist:
        return

    # Separate coarse vs fine probes
    coarse_pts = []
    fine_pts = []
    overshoot_pts = []

    for item in active_hist:
        z = item.get("z", item.get("idx", 0))
        score = item.get("score", curve[z] if 0 <= z < num_frames else 0.0)
        phase = item.get("phase", "COARSE")
        step_num = item.get("step", len(coarse_pts) + len(fine_pts) + 1)

        if phase in ("INIT", "COARSE_PROBE", "COARSE"):
            coarse_pts.append((z, score, step_num))
        elif phase == "OVERSHOOT":
            overshoot_pts.append((z, score, step_num))
        else:  # FINE, CONVERGED
            fine_pts.append((z, score, step_num))

    # Draw Phase 1: Coarse Step line and markers
    if coarse_pts:
        cx = [p[0] for p in coarse_pts]
        cy = [p[1] for p in coarse_pts]
        ax.plot(
            cx, cy,
            color=COLOR_COARSE, linewidth=2.0, linestyle="-",
            marker="o", markersize=6.5, markeredgecolor="#ffffff", markeredgewidth=1.2,
            zorder=4, label="Phase 1: Coarse Step",
        )
        for z, score, num in coarse_pts:
            ax.annotate(
                f"#{num}", (z, score),
                xytext=(0, 7), textcoords="offset points",
                fontsize=7.5, fontweight="bold", color=COLOR_COARSE,
                ha="center", va="bottom", zorder=5,
            )

    # Draw Overshoot marker
    for z, score, num in overshoot_pts:
        ax.plot(
            [z], [score],
            marker="o", markersize=8.0, color=COLOR_OVERSHOOT,
            markeredgecolor="#ffffff", markeredgewidth=1.5,
            linestyle="none", zorder=6, label="Overshoot",
        )
        ax.annotate(
            f"#{num}", (z, score),
            xytext=(0, 7), textcoords="offset points",
            fontsize=7.5, fontweight="bold", color=COLOR_OVERSHOOT,
            ha="center", va="bottom", zorder=6,
        )

    # Draw Phase 2: Fine Refinement line and markers
    if fine_pts:
        fx = [p[0] for p in fine_pts]
        fy = [p[1] for p in fine_pts]
        ax.plot(
            fx, fy,
            color=COLOR_FINE, linewidth=2.0, linestyle="-",
            marker="o", markersize=6.5, markeredgecolor="#ffffff", markeredgewidth=1.2,
            zorder=5, label="Phase 2: Fine Refinement",
        )
        for z, score, num in fine_pts:
            ax.annotate(
                f"#{num}", (z, score),
                xytext=(0, 7), textcoords="offset points",
                fontsize=7.5, fontweight="bold", color=COLOR_FINE,
                ha="center", va="bottom", zorder=6,
            )

    # Draw active probe highlight & local tangent line
    current_rec = active_hist[-1]
    curr_z = current_rec.get("z", current_rec.get("idx", 0))
    curr_score = current_rec.get("score", curve[curr_z] if 0 <= curr_z < num_frames else 0.0)
    curr_grad = float(current_rec.get("gradient", 0.0) or 0.0)

    # Halo on current probe
    ax.plot(
        [curr_z], [curr_score],
        marker="o", markersize=13.0,
        color="none", markeredgecolor=COLOR_HALO,
        markeredgewidth=2.4, zorder=8,
    )

    # Tangent line d(NV)/dZ
    if abs(curr_grad) > 1e-6:
        tangent_span = 12.0
        tz = np.array([curr_z - tangent_span, curr_z + tangent_span])
        ty = curr_score + curr_grad * (tz - curr_z)
        ax.plot(
            tz, ty,
            color=COLOR_TANGENT, linestyle="--", linewidth=1.8,
            alpha=0.85, zorder=7, label="Tangent d(NV)/dZ",
        )
