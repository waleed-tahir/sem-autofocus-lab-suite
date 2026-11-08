"""How far a search drifts when the frames get noisier.

Gaussian noise is added to every frame before it is scored, and the searches are
re-run at rising noise levels.  Two panels tell the story: how large the
position error becomes, and how often the search still lands within one frame of
the true peak.  The reference peak stays the one from the clean scan, because the
question is how much noise costs in accuracy.

Main contents:
    * :func:`draw_robustness` -- error and success rate against the noise level.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from matplotlib.figure import Figure

from app.core.experiment import SUCCESS_TOLERANCE_FRAMES, RobustnessPoint
from app.plots.style import (
    MARKER_EDGE_WIDTH,
    SURFACE,
    algorithm_style,
    empty_message,
    finish_figure,
    style_axes,
)

#: Success rate is a share, so its axis is fixed to the full 0-100 % range.
PERCENT_LIMITS = (-5.0, 105.0)


def draw_robustness(figure: Figure, points: Sequence[RobustnessPoint]) -> None:
    """Draw position error and success rate against the injected noise.

    Args:
        figure: Figure to draw on; it is cleared first.
        points: Aggregated robustness figures, as produced by
            :func:`app.core.experiment.summarise_robustness`.
    """
    figure.clear()
    if not points:
        empty_message(
            figure,
            "No robustness data yet.\nPick the algorithms and a maximum noise "
            "level, then press \"Run robustness sweep\".",
        )
        return

    error_ax, success_ax = figure.subplots(2, 1, sharex=True)
    by_algorithm = _group(points)

    for key, series in by_algorithm.items():
        style = algorithm_style(key)
        sigmas = [point.noise_sigma for point in series]
        name = series[0].algorithm

        error_ax.plot(
            sigmas, [point.mean_error_um for point in series],
            color=style.color, marker=style.marker, markersize=6.0,
            markeredgecolor=SURFACE, markeredgewidth=MARKER_EDGE_WIDTH,
            linewidth=1.8, zorder=3, label=name,
        )
        success_ax.plot(
            sigmas, [point.success_rate * 100.0 for point in series],
            color=style.color, marker=style.marker, markersize=6.0,
            markeredgecolor=SURFACE, markeredgewidth=MARKER_EDGE_WIDTH,
            linewidth=1.8, zorder=3, label=name,
        )

    repeats = max(point.runs for point in points)
    style_axes(
        error_ax,
        title=f"Position error against injected noise (mean of {repeats} run(s))",
        ylabel="Mean error (um)",
        legend=True,
        legend_loc="upper left",
    )
    _set_error_limits(error_ax, points)

    success_ax.set_ylim(*PERCENT_LIMITS)
    style_axes(
        success_ax,
        title=f"Share of runs landing within {SUCCESS_TOLERANCE_FRAMES:g} frame "
              f"of the reference peak",
        xlabel="Injected noise sigma (grey levels)",
        ylabel="Success rate (%)",
        legend=False,
    )
    finish_figure(figure)


def _group(points: Sequence[RobustnessPoint]) -> dict[str, list[RobustnessPoint]]:
    """Group the points by algorithm, each series ordered by rising noise."""
    grouped: dict[str, list[RobustnessPoint]] = {}
    for point in points:
        grouped.setdefault(point.algorithm_key, []).append(point)
    for series in grouped.values():
        series.sort(key=lambda point: point.noise_sigma)
    return grouped


def _set_error_limits(ax, points: Sequence[RobustnessPoint]) -> None:
    """Start the error axis at zero, which is where a perfect search sits."""
    errors = [point.mean_error_um for point in points if not math.isnan(point.mean_error_um)]
    if not errors:
        return
    ax.set_ylim(0.0, max(float(np.max(errors)) * 1.15, 1.0))
