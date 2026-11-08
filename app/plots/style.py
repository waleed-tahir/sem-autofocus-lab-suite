"""The one place that decides how every plot looks.

Styled with the Fluent aesthetic:
- Clean pure white background (#ffffff)
- Segoe UI Variable typography
- Refined Fluent color palette for algorithms, focus measures, and speeds
- Elegant subtle grid lines and recessive axes borders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

LOGGER = logging.getLogger(__name__)

# --- Chart chrome (Fluent) ---------------------------------------

#: Background of every figure and of every set of axes.
SURFACE = "#ffffff"

#: Colour of titles and of anything that must read as the main text.
INK_PRIMARY = "#1c1c1c"

#: Colour of axis labels and legend text.
INK_SECONDARY = "#5e5e5e"

#: Colour of tick labels and of other text that should stay in the background.
INK_MUTED = "#8a8a8a"

#: Colour of the grid, which must never compete with the data.
GRID = "#eeeeee"

#: Colour of the axis lines.
AXIS = "#d1d1d1"

#: Colour of the exhaustive reference curve.
REFERENCE = "#767676"

# --- Series colours (Fluent Accent Palette) ---------------------------------

_ALGORITHM_COLORS: Mapping[str, str] = {
    "global_scan": "#0067c0",               # Windows Accent Blue
    "coarse_and_fine": "#d83b01",           # Warm Amber
    "gradient": "#008272",                  # Jade Teal
    "coarse_quadratic_gradient": "#744da9", # Vibrant Purple
    "coarse_quadratic_grid": "#ea005e",     # Magenta
}

_ALGORITHM_MARKERS: Mapping[str, str] = {
    "global_scan": "o",
    "coarse_and_fine": "s",
    "gradient": "^",
    "coarse_quadratic_gradient": "D",
    "coarse_quadratic_grid": "v",
}

_ALGORITHM_LINESTYLES: Mapping[str, object] = {
    "global_scan": "solid",
    "coarse_and_fine": (0, (5, 2)),
    "gradient": (0, (1, 1.5)),
    "coarse_quadratic_gradient": (0, (6, 2, 1, 2)),
    "coarse_quadratic_grid": (0, (3, 1, 1, 1, 1, 1)),
}

_MEASURE_COLORS: Mapping[str, str] = {
    "normalized_variance": "#0067c0",
    "mean_normalized_variance": "#d83b01",
    "variance_of_laplacian": "#008272",
    "laplacian_of_gaussian": "#744da9",
    "modified_laplacian": "#ea005e",
}

_MEASURE_MARKERS: Mapping[str, str] = {
    "normalized_variance": "o",
    "mean_normalized_variance": "s",
    "variance_of_laplacian": "^",
    "laplacian_of_gaussian": "D",
    "modified_laplacian": "v",
}

_SPEED_COLORS: Mapping[int, str] = {
    1: "#0067c0",  # Sharp Blue
    2: "#008272",  # Jade
    3: "#d83b01",  # Amber
    4: "#744da9",  # Purple
    5: "#c42b1c",  # Dark Crimson
    6: "#ea005e",  # Magenta
    7: "#5c2d91",  # Deep Violet
    8: "#4a4a4a",  # Neutral Dark
}

FALLBACK_COLOR = "#0067c0"
FALLBACK_MARKER = "o"

LINE_WIDTH = 2.2
REFERENCE_LINE_WIDTH = 1.8
MARKER_SIZE = 6.5
PEAK_MARKER_SIZE = 14.0
MARKER_EDGE_WIDTH = 1.2


@dataclass(frozen=True)
class SeriesStyle:
    color: str
    marker: str
    linestyle: object = "solid"


def configure_matplotlib() -> None:
    """Apply the application-wide modern matplotlib defaults."""
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
            "font.size": 9.0,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.titlecolor": INK_PRIMARY,
            "axes.labelsize": 9.0,
            "axes.labelweight": "normal",
            "axes.labelcolor": INK_SECONDARY,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "grid.alpha": 0.8,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "legend.frameon": True,
            "legend.framealpha": 0.95,
            "legend.edgecolor": "#e5e5e5",
            "legend.facecolor": "#ffffff",
            "legend.labelcolor": INK_PRIMARY,
            "figure.autolayout": False,
            "lines.linewidth": LINE_WIDTH,
            "lines.markersize": MARKER_SIZE,
        }
    )


def algorithm_style(key: str) -> SeriesStyle:
    return SeriesStyle(
        color=_ALGORITHM_COLORS.get(key, FALLBACK_COLOR),
        marker=_ALGORITHM_MARKERS.get(key, FALLBACK_MARKER),
        linestyle=_ALGORITHM_LINESTYLES.get(key, "solid"),
    )


def measure_style(key: str) -> SeriesStyle:
    return SeriesStyle(
        color=_MEASURE_COLORS.get(key, FALLBACK_COLOR),
        marker=_MEASURE_MARKERS.get(key, FALLBACK_MARKER),
    )


def speed_color(speed: Optional[int]) -> str:
    if speed is None:
        return FALLBACK_COLOR
    return _SPEED_COLORS.get(int(speed), FALLBACK_COLOR)


def style_axes(
    ax: Axes,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    legend: bool = False,
    legend_loc: str = "best",
) -> None:
    if title:
        ax.set_title(title, color=INK_PRIMARY, pad=10.0, weight="600")
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_SECONDARY, labelpad=6.0)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK_SECONDARY, labelpad=6.0)

    ax.grid(True, color=GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(1.0)

    if legend and ax.get_legend_handles_labels()[0]:
        ax.legend(loc=legend_loc, frameon=True, edgecolor="#e5e5e5")


def frame_index_axis(ax: Axes, wd_mm: Sequence[float]) -> None:
    positions = np.asarray(wd_mm, dtype=np.float64)
    if positions.size < 2:
        return

    start = float(positions[0])
    step = (float(positions[-1]) - start) / (positions.size - 1)
    if step == 0.0:
        return

    def to_index(value: np.ndarray) -> np.ndarray:
        return (np.asarray(value, dtype=np.float64) - start) / step

    def to_wd(value: np.ndarray) -> np.ndarray:
        return start + np.asarray(value, dtype=np.float64) * step

    secondary = ax.secondary_xaxis("top", functions=(to_index, to_wd))
    secondary.set_xlabel("Frame index", color=INK_SECONDARY, fontsize=9.0, labelpad=5.0)
    secondary.tick_params(colors=INK_MUTED, labelsize=8.0)


def finish_figure(figure: Figure) -> None:
    figure.set_facecolor(SURFACE)
    try:
        figure.set_layout_engine("constrained")
    except (ValueError, RuntimeError) as exc:
        LOGGER.debug("Skipped constrained layout: %s", exc)


def empty_message(figure: Figure, message: str) -> None:
    figure.clear()
    figure.set_facecolor(SURFACE)
    ax = figure.add_subplot(111)
    ax.set_axis_off()
    ax.text(
        0.5, 0.5, message,
        ha="center", va="center", color=INK_MUTED, fontsize=10.0, wrap=True,
        transform=ax.transAxes,
    )


def value_label_formatter(decimals: int) -> Callable[[float], str]:
    def formatter(value: float) -> str:
        return "" if value is None or np.isnan(value) else f"{value:.{decimals}f}"
    return formatter
