"""What the SEM scanning speed does to the focus curve.

Clean, high-visibility plots formatted for compact displays:
- Normalised focus curve comparison
- Multi-panel metric bar charts with clean headroom, non-overlapping titles,
  and values labeled above each bar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from matplotlib.figure import Figure

from app.core.curve_stats import normalize
from app.core.experiment import GroundTruth
from app.plots.style import (
    INK_PRIMARY,
    INK_SECONDARY,
    MARKER_EDGE_WIDTH,
    PEAK_MARKER_SIZE,
    SURFACE,
    empty_message,
    finish_figure,
    frame_index_axis,
    speed_color,
    style_axes,
)

BAR_WIDTH = 0.55
HEADROOM = 1.30


def _sorted_by_speed(truths: Sequence[GroundTruth]) -> list[GroundTruth]:
    return sorted(
        truths,
        key=lambda truth: (truth.speed is None, truth.speed or 0, truth.dataset_label),
    )


def _speed_label(truth: GroundTruth) -> str:
    if truth.speed is None:
        return truth.dataset_label
    return f"Speed {truth.speed} ({truth.dataset_label})"


def draw_speed_curves(figure: Figure, truths: Sequence[GroundTruth]) -> None:
    figure.clear()
    if not truths:
        empty_message(
            figure,
            "No reference curves yet.\nPress \"Compute reference curves\" to scan "
            "every loaded image set.",
        )
        return

    ax = figure.add_subplot(111)
    ordered = _sorted_by_speed(truths)

    for truth in ordered:
        color = speed_color(truth.speed)
        scaled = normalize(truth.curve)
        ax.plot(
            truth.wd_mm, scaled,
            color=color, linewidth=2.0, alpha=0.95, zorder=3,
            label=_speed_label(truth),
        )
        ax.plot(
            [truth.peak_wd_mm], [scaled[truth.peak_idx]],
            marker="*", markersize=PEAK_MARKER_SIZE, color=color,
            markeredgecolor=SURFACE, markeredgewidth=MARKER_EDGE_WIDTH,
            linestyle="none", zorder=4,
        )

    measure = ordered[0].measure_name
    style_axes(
        ax,
        title=f"Focus Curve per Scanning Speed ({measure})",
        xlabel="Working distance (mm)",
        ylabel="Focus score [0, 1]",
        legend=True,
        legend_loc="upper left",
    )
    frame_index_axis(ax, ordered[0].wd_mm)
    finish_figure(figure)


def draw_speed_metrics(figure: Figure, truths: Sequence[GroundTruth]) -> None:
    """Draw peak width, noise level and peak contrast per scanning speed.
    
    Sub-panels are individually titled without collision, and suptitle is omitted
    since the card header already clearly identifies the panel.
    """
    figure.clear()
    if not truths:
        empty_message(figure, "No reference curves yet.")
        return

    ordered = _sorted_by_speed(truths)
    labels = [
        f"Speed {truth.speed}" if truth.speed is not None else truth.dataset_label
        for truth in ordered
    ]
    colors = [speed_color(truth.speed) for truth in ordered]
    positions = np.arange(len(ordered), dtype=np.float64)

    panels = (
        ("Peak width (FWHM)", [truth.stats.fwhm for truth in ordered], "frames", 1),
        ("Local maxima count", [float(truth.stats.local_maxima) for truth in ordered], "count", 0),
        ("Peak-to-noise ratio (SNR)", [truth.stats.snr for truth in ordered], "ratio", 0),
    )

    # Prevent layout collapse with defined vertical spacing
    axes = figure.subplots(3, 1, sharex=True, gridspec_kw={"hspace": 0.35})
    for (title, values, unit, decimals), ax in zip(panels, axes, strict=True):
        _draw_metric_panel(ax, positions, values, colors, title, unit, decimals)

    axes[-1].set_xticks(positions)
    axes[-1].set_xticklabels(labels, fontsize=8.5, color=INK_SECONDARY)
    finish_figure(figure)


def _draw_metric_panel(
    ax,
    positions: np.ndarray,
    values: Sequence[float],
    colors: Sequence[str],
    title: str,
    unit: str,
    decimals: int,
) -> None:
    heights = [0.0 if value is None or math.isnan(value) else float(value) for value in values]
    ax.bar(
        positions, heights,
        width=BAR_WIDTH, color=list(colors), edgecolor=SURFACE, linewidth=1.2, zorder=3,
    )
    for position, height, raw in zip(positions, heights, values, strict=True):
        if raw is None or math.isnan(raw):
            text = "n/a"
        elif raw >= 1e6:
            text = f"{raw/1e6:.1f}M"
        else:
            text = f"{raw:.{decimals}f}"
        ax.annotate(
            text, xy=(position, height), xytext=(0.0, 3.0), textcoords="offset points",
            ha="center", va="bottom", fontsize=8.0, color=INK_PRIMARY, weight="500",
        )

    tallest = max(heights) if heights else 0.0
    ax.set_ylim(0.0, (tallest * HEADROOM) if tallest > 0.0 else 1.0)
    style_axes(ax, title=title, ylabel=unit)
    ax.grid(axis="x", visible=False)


@dataclass(frozen=True)
class SpeedRow:
    label: str
    speed: Optional[int]
    frames: int
    coarse_idx: int
    coarse_wd_mm: float
    fine_idx: float
    fine_wd_mm: float
    peak_value: float
    fwhm: float
    noise_sigma: float
    snr: float
    local_maxima: int
    contrast: float
    elapsed_s: float


def speed_rows(truths: Sequence[GroundTruth]) -> list[SpeedRow]:
    ordered = _sorted_by_speed(truths)
    return [
        SpeedRow(
            label=truth.dataset_label,
            speed=truth.speed,
            frames=truth.frame_count,
            coarse_idx=truth.peak_idx,
            coarse_wd_mm=truth.peak_wd_mm,
            fine_idx=truth.reference_idx,
            fine_wd_mm=truth.reference_wd_mm,
            peak_value=truth.peak_value,
            fwhm=truth.stats.fwhm,
            noise_sigma=truth.stats.noise_sigma,
            snr=truth.stats.snr,
            local_maxima=truth.stats.local_maxima,
            contrast=truth.stats.contrast,
            elapsed_s=truth.elapsed_s,
        )
        for truth in ordered
    ]
