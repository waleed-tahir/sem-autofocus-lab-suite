"""Cost against accuracy: what each algorithm paid and what it got.

Three panels answer the three questions of the comparison: how many frames did
the search read, how long did it take, and how far from the true peak did it
land.  The panels are stacked rather than put on one pair of axes, because
frames, milliseconds and micrometres share no scale.

Main contents:
    * :func:`draw_algorithm_bars` -- the three-panel comparison for one image set.
    * :func:`frames_saved_table` -- the same savings as rows for the table.
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

#: Width of a bar as a share of its slot, leaving the 2 px surface gap.
BAR_WIDTH = 0.68

#: Headroom above the tallest bar, so the value labels never touch the frame.
HEADROOM = 1.22


def draw_algorithm_bars(figure: Figure, results: Sequence[RunResult]) -> None:
    """Draw frames read, run time and position error per algorithm.

    Args:
        figure: Figure to draw on; it is cleared first.
        results: Runs on one image set, at most one per algorithm.
    """
    figure.clear()
    if not results:
        empty_message(
            figure,
            "No runs for this image set yet.\nRun some algorithms on the Run tab.",
        )
        return

    ordered = sorted(results, key=lambda r: r.algorithm)
    labels = [_wrap(result.algorithm) for result in ordered]
    colors = [algorithm_style(result.algorithm_key).color for result in ordered]
    positions = np.arange(len(ordered), dtype=np.float64)

    panels = (
        ("Frames read", [float(r.frames_evaluated) for r in ordered], "frames", 0),
        ("Run time", [r.elapsed_ms for r in ordered], "ms", 1),
        ("Position error", [r.error_um for r in ordered], "um", 2),
    )

    axes = figure.subplots(3, 1, sharex=True)
    for (title, values, unit, decimals), ax in zip(panels, axes, strict=True):
        _draw_panel(ax, positions, values, colors, title, unit, decimals)

    axes[-1].set_xticks(positions)
    axes[-1].set_xticklabels(labels, fontsize=8.0, color=INK_SECONDARY)

    dataset = ordered[0].dataset_label
    measure = ordered[0].measure
    figure.suptitle(
        f"Algorithm comparison - {dataset} ({measure})",
        fontsize=11.0, fontweight="bold", color="#0b0b0b",
    )
    finish_figure(figure)


def _draw_panel(
    ax,
    positions: np.ndarray,
    values: Sequence[float],
    colors: Sequence[str],
    title: str,
    unit: str,
    decimals: int,
) -> None:
    """Draw one of the three bar panels, with a value label on every bar.

    The labels are what satisfies the readability rule for the lighter palette
    colours: the number is always written out, never only encoded as a height.

    Args:
        ax: Axes to draw on.
        positions: X slot of every bar.
        values: Bar heights.
        colors: Bar colours, one per algorithm.
        title: Panel title.
        unit: Unit shown on the y axis and after each label.
        decimals: Digits of the value labels.
    """
    heights = [0.0 if value is None or math.isnan(value) else float(value) for value in values]
    ax.bar(
        positions, heights,
        width=BAR_WIDTH, color=list(colors), edgecolor=SURFACE, linewidth=1.5, zorder=3,
    )

    for position, height, raw in zip(positions, heights, values, strict=True):
        text = "n/a" if raw is None or math.isnan(raw) else f"{raw:.{decimals}f}"
        ax.annotate(
            text,
            xy=(position, height), xytext=(0.0, 3.0), textcoords="offset points",
            ha="center", va="bottom", fontsize=8.0, color=INK_SECONDARY,
        )

    tallest = max(heights) if heights else 0.0
    ax.set_ylim(0.0, (tallest * HEADROOM) if tallest > 0.0 else 1.0)
    style_axes(ax, title=title, ylabel=unit)
    ax.grid(axis="x", visible=False)  # Vertical grid lines add nothing to bars.


def _wrap(name: str) -> str:
    """Break a long algorithm name over two lines so the ticks stay readable."""
    if len(name) <= 18:
        return name
    words = name.split()
    middle = len(words) // 2 or 1
    return " ".join(words[:middle]) + "\n" + " ".join(words[middle:])


@dataclass(frozen=True)
class SavingRow:
    """How much one algorithm saved against the exhaustive scan.

    Attributes:
        algorithm: Display name of the algorithm.
        frames_evaluated: Distinct frames this run read.
        baseline_frames: Frames the exhaustive scan read.
        saved_percent: Share of frames avoided, in percent.
        elapsed_ms: Run time in milliseconds.
        speedup: Baseline time divided by this run's time.
        error_um: Position error in micrometres.
    """

    algorithm: str
    frames_evaluated: int
    baseline_frames: int
    saved_percent: float
    elapsed_ms: float
    speedup: float
    error_um: float


def frames_saved_table(results: Sequence[RunResult]) -> list[SavingRow]:
    """Turn the runs of one image set into savings rows.

    The baseline is the exhaustive scan when it was run, otherwise the frame
    count of the stack, which is what an exhaustive scan would have read.

    Args:
        results: Runs on one image set.

    Returns:
        One row per run, ordered by rising frame count so the cheapest search
        comes first.
    """
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
            error_um=result.error_um,
        )
        for result in results
    ]
    return sorted(rows, key=lambda row: row.frames_evaluated)
