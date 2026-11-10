"""Plot A: Focus curve and Coarse-to-Fine Gradient Ascent trajectory.

Styled for Fluent UI Desktop:
- Pure white background with subtle, elegant Fluent palette
- Smooth reference curve always drawn in recessive slate grey
- Phase 1: Coarse Step path in vibrant Fluent Blue (#0078d4)
- Overshoot marker in vivid Crimson (#dc2626)
- Phase 2: Fine Refinement path in warm Amber (#d97706)
- Local tangent line d(NV)/dZ at the active inspection step
- Zero text clutter on Global Scan (clean continuous trace)
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Any, Dict, List

import numpy as np
from matplotlib.figure import Figure

from app.core.experiment import GroundTruth
from app.core.run_result import RunResult
from app.plots.style import (
    INK_PRIMARY,
    INK_SECONDARY,
    INK_MUTED,
    SURFACE,
    empty_message,
    finish_figure,
)

# Refined Fluent Color Tokens
COLOR_REF_CURVE = "#94a3b8"     # Elegant slate grey for ground-truth reference curve
COLOR_COARSE = "#0078d4"        # Fluent Accent Blue for Phase 1: Coarse Step
COLOR_FINE = "#d97706"          # Warm Amber for Phase 2: Fine Refinement
COLOR_OVERSHOOT = "#dc2626"     # Crimson for Overshoot
COLOR_TANGENT = "#ef4444"       # Coral-red dashed tangent line
COLOR_PEAK = "#059669"          # Emerald green for Global Peak
COLOR_HALO = "#0067c0"          # Fluent Blue halo for active probe


def draw_focus_curve(
    figure: Figure,
    truth: Optional[GroundTruth],
    results: Sequence[RunResult] = (),
    replay_step: Optional[int] = None,
    show_global: bool = True,
) -> None:
    """Draw the smooth focus curve and coarse-to-fine trajectory with Fluent styling."""
    figure.clear()
    if truth is None:
        empty_message(
            figure,
            "No reference curve yet.\nSelect an image set to inspect its focus curve.",
        )
        return

    ax = figure.add_subplot(111)
    curve = truth.curve
    num_frames = len(curve)
    indices = np.arange(num_frames)

    # 1. Smooth reference focus curve (always underneath)
    if show_global:
        ax.plot(
            indices, curve,
            color=COLOR_REF_CURVE, linewidth=2.0, alpha=0.60, zorder=2,
            label="Reference Focus Curve",
        )

    # 2. Ground-truth Global Peak marker
    peak_idx = truth.peak_idx
    if 0 <= peak_idx < num_frames:
        peak_val = curve[peak_idx]
        ax.plot(
            [peak_idx], [peak_val],
            marker="*", markersize=13.0, color=COLOR_PEAK,
            markeredgecolor="#ffffff", markeredgewidth=1.2,
            linestyle="none", zorder=6,
            label=f"Global Peak Z={peak_idx}",
        )
        # Clean label with subtle offset
        y_span = float(np.ptp(curve)) if float(np.ptp(curve)) > 0 else 1.0
        ax.annotate(
            f"Global Peak Z={peak_idx}",
            xy=(peak_idx, peak_val),
            xytext=(peak_idx, peak_val + y_span * 0.04),
            ha="center", va="bottom",
            fontsize=8.5, fontweight="600", color=COLOR_PEAK,
            zorder=7,
        )

    # 3. Visited trajectories
    for result in results:
        _draw_result_trajectory(ax, truth, result, replay_step=replay_step)

    # 4. Fluent Axes and Typography
    measure_name = truth.measure_name if truth else "Normalized Variance"
    ax.set_title(
        f"{measure_name} Focus Curve & Coarse-to-Fine Gradient Trajectory",
        fontsize=11.0, fontweight="600", color=INK_PRIMARY, pad=12,
    )
    ax.set_xlabel("Focal Plane Z (Frame Index)", fontsize=9.5, color=INK_SECONDARY, labelpad=6)
    ylabel = "Normalized Variance NV (σ²/µ)" if "norm" in measure_name.lower() else "Focus Score"
    ax.set_ylabel(ylabel, fontsize=9.5, color=INK_SECONDARY, labelpad=6)

    # Fluent X-ticks at clean 20-frame increments
    if num_frames > 0:
        step_ticks = 20 if num_frames >= 100 else 10
        tick_locs = list(range(0, num_frames, step_ticks))
        if (num_frames - 1) not in tick_locs:
            tick_locs.append(num_frames - 1)
        ax.set_xticks(tick_locs)
        ax.set_xticklabels([f"Z={t}" for t in tick_locs], fontsize=8.5, color=INK_MUTED)

    # Soft, subtle grid and borders
    ax.grid(True, linestyle="--", alpha=0.5, color="#e5e7eb", zorder=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d1d5db")
        ax.spines[side].set_linewidth(1.0)

    # Fluent multi-column legend below the chart
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(
            by_label.values(), by_label.keys(),
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=min(5, len(by_label)),
            frameon=True,
            facecolor="#ffffff",
            edgecolor="#e5e5e5",
            fontsize=8.5,
        )

    # Clean Y-axis number formatting
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
    """Render the step-by-step search trajectory."""
    curve = truth.curve
    num_frames = len(curve)
    history: List[Dict[str, Any]] = result.extra.get("history", [])

    # Special handling for Global Scan (Exhaustive Scan)
    # NEVER draw text annotations on 199 points!
    if result.algorithm_key == "global_scan" or not history:
        visited = [idx for idx in result.visited if 0 <= idx < num_frames]
        active_visited = visited[:max(0, replay_step)] if replay_step is not None else visited
        if active_visited:
            ax.plot(
                active_visited, [curve[i] for i in active_visited],
                color=COLOR_COARSE, linewidth=2.0, linestyle="-",
                label=f"{result.algorithm} ({len(active_visited)}/{len(visited)} frames)",
                zorder=4,
            )
            # Replay active marker
            if replay_step is not None and active_visited:
                curr_idx = active_visited[-1]
                ax.plot(
                    [curr_idx], [curve[curr_idx]],
                    marker="o", markersize=10.0, color=COLOR_COARSE,
                    markeredgecolor="#ffffff", markeredgewidth=2.0, zorder=8,
                )
        return

    # Filter history up to replay_step
    active_hist = history[:replay_step] if replay_step is not None else history
    if not active_hist:
        return

    # Coarse path includes INIT, COARSE_PROBE, COARSE, and OVERSHOOT (the climb)
    coarse_pts = []
    overshoot_pt = None
    fine_pts = []

    for item in active_hist:
        z = item.get("z", item.get("idx", 0))
        score = item.get("score", curve[z] if 0 <= z < num_frames else 0.0)
        phase = item.get("phase", "COARSE")
        step_num = item.get("step", 1)

        if phase in ("INIT", "COARSE_PROBE", "COARSE"):
            coarse_pts.append((z, score, step_num))
        elif phase == "OVERSHOOT":
            overshoot_pt = (z, score, step_num)
            coarse_pts.append((z, score, step_num))
        else:  # FINE, CONVERGED
            fine_pts.append((z, score, step_num))

    # Draw Phase 1: Coarse Step line (connecting climb through overshoot)
    if coarse_pts:
        cx = [p[0] for p in coarse_pts]
        cy = [p[1] for p in coarse_pts]
        ax.plot(
            cx, cy,
            color=COLOR_COARSE, linewidth=2.2, linestyle="-",
            marker="o", markersize=6.5, markeredgecolor="#ffffff", markeredgewidth=1.2,
            zorder=4, label="Phase 1: Coarse Step",
        )
        # Annotate step numbers cleanly
        for z, score, num in coarse_pts:
            if overshoot_pt and (z, score, num) == overshoot_pt:
                continue  # Overshoot annotated separately
            ax.annotate(
                f"#{num}", (z, score),
                xytext=(0, 7), textcoords="offset points",
                fontsize=7.5, fontweight="bold", color=COLOR_COARSE,
                ha="center", va="bottom", zorder=5,
            )

    # Highlight Overshoot point in vivid Crimson
    if overshoot_pt:
        oz, osc, onum = overshoot_pt
        ax.plot(
            [oz], [osc],
            marker="o", markersize=8.5, color=COLOR_OVERSHOOT,
            markeredgecolor="#ffffff", markeredgewidth=1.5,
            linestyle="none", zorder=6, label="Overshoot",
        )
        ax.annotate(
            f"#{onum}", (oz, osc),
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
            color=COLOR_FINE, linewidth=2.2, linestyle="-",
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
        marker="o", markersize=14.0,
        color="none", markeredgecolor=COLOR_HALO,
        markeredgewidth=2.2, zorder=8,
    )

    # Local tangent line d(NV)/dZ (clean short segment around probe)
    if abs(curr_grad) > 1e-6:
        tangent_span = 8.0
        tz = np.array([max(0, curr_z - tangent_span), min(num_frames - 1, curr_z + tangent_span)])
        ty = curr_score + curr_grad * (tz - curr_z)
        ax.plot(
            tz, ty,
            color=COLOR_TANGENT, linestyle="--", linewidth=1.8,
            alpha=0.9, zorder=7, label="Tangent d(NV)/dZ",
        )
