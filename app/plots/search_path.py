"""Plot B: which frame a search looked at, step by step.

Where the focus-curve plot shows *how many* frames a search needed, this one
shows *in what order* it needed them.  A gradient climb appears as a sequence of
shrinking jumps, a grid sweep as a staircase, and a failed verification as a
jump back out to a completely different part of the stack.

Main contents:
    * :func:`draw_search_path` -- visited frame against step number, one line
      per run.
"""

from __future__ import annotations

from typing import Sequence

from matplotlib.figure import Figure

from app.core.run_result import RunResult
from app.plots.style import (
    MARKER_EDGE_WIDTH,
    REFERENCE,
    SURFACE,
    algorithm_style,
    empty_message,
    finish_figure,
    style_axes,
)

#: Markers are drawn only while a path is short enough for them to stay apart.
MAX_STEPS_WITH_MARKERS = 60


def draw_search_path(
    figure: Figure,
    results: Sequence[RunResult],
    reference_idx: float | None = None,
    frame_count: int | None = None,
) -> None:
    """Draw the probe order of one or more runs.

    Args:
        figure: Figure to draw on; it is cleared first.
        results: Runs to draw.  Each keeps its fixed colour and marker.
        reference_idx: Ground-truth peak, drawn as a horizontal line so the
            convergence of each path is visible at a glance.
        frame_count: Number of frames in the stack, used to scale the y axis to
            the whole search range instead of just the visited part.
    """
    figure.clear()
    if not results:
        empty_message(
            figure,
            "No run selected.\nPick at least one algorithm to see the order "
            "in which it probed the frames.",
        )
        return

    ax = figure.add_subplot(111)

    for result in results:
        _draw_path(ax, result)

    if reference_idx is not None:
        ax.axhline(
            reference_idx,
            color=REFERENCE, linestyle="--", linewidth=1.4, zorder=1,
            label=f"Reference peak ({reference_idx:.2f})",
        )

    if frame_count and frame_count > 1:
        ax.set_ylim(-1.0, float(frame_count))

    style_axes(
        ax,
        title="Convergence path - probed frame per step",
        xlabel="Step number (order of evaluation)",
        ylabel="Frame index",
        legend=True,
        legend_loc="best",
    )
    finish_figure(figure)


def _draw_path(ax, result: RunResult) -> None:
    """Draw the probe order of a single run.

    Args:
        ax: Axes to draw on.
        result: Run whose ``visited`` list is drawn.
    """
    if not result.visited:
        return

    style = algorithm_style(result.algorithm_key)
    steps = range(1, len(result.visited) + 1)
    # Markers on a 200-step path would merge into a band, so they are dropped
    # for long paths and the line alone carries the shape.
    show_markers = len(result.visited) <= MAX_STEPS_WITH_MARKERS

    ax.plot(
        list(steps), list(result.visited),
        color=style.color, linewidth=1.6, alpha=0.9, zorder=3,
        linestyle=style.linestyle,
        marker=style.marker if show_markers else None,
        markersize=5.0,
        markeredgecolor=SURFACE,
        markeredgewidth=MARKER_EDGE_WIDTH if show_markers else 0.0,
        label=f"{result.algorithm} ({len(result.visited)} steps)",
    )
