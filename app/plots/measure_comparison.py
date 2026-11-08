"""How the five focus measures see the same frames.

Every measure is scanned over the same stack, so the comparison is about shape
rather than about value: where each measure puts the peak, how sharply it peaks,
how many false peaks it offers a search, and what it costs to compute.  The
curves are rescaled to ``[0, 1]`` because a Laplacian variance is orders of
magnitude larger than a normalised variance.

Main contents:
    * :func:`draw_measure_curves` -- one normalised curve per focus measure.
    * :func:`measure_rows` -- peak, width, false peaks and cost as table rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from matplotlib.figure import Figure

from app.core.curve_stats import normalize
from app.core.experiment import GroundTruth
from app.core.focus_measures import keys as measure_keys
from app.plots.style import (
    MARKER_EDGE_WIDTH,
    PEAK_MARKER_SIZE,
    SURFACE,
    empty_message,
    finish_figure,
    frame_index_axis,
    measure_style,
    style_axes,
)


def _ordered(truths: Sequence[GroundTruth]) -> list[GroundTruth]:
    """Order reference curves the way the registry does, so colours stay stable."""
    order = {key: position for position, key in enumerate(measure_keys())}
    return sorted(truths, key=lambda truth: order.get(truth.measure_key, len(order)))


def draw_measure_curves(figure: Figure, truths: Sequence[GroundTruth]) -> None:
    """Draw one normalised focus curve per focus measure.

    Args:
        figure: Figure to draw on; it is cleared first.
        truths: Reference curves of one image set, one per focus measure.
    """
    figure.clear()
    if not truths:
        empty_message(
            figure,
            "No focus-measure curves yet.\nPress \"Compare focus measures\" to scan "
            "this image set with all five measures.",
        )
        return

    ax = figure.add_subplot(111)
    ordered = _ordered(truths)

    for truth in ordered:
        style = measure_style(truth.measure_key)
        scaled = normalize(truth.curve)
        ax.plot(
            truth.wd_mm, scaled,
            color=style.color, linewidth=1.8, alpha=0.95, zorder=3,
            label=f"{truth.measure_name} (peak frame {truth.peak_idx})",
        )
        ax.plot(
            [truth.peak_wd_mm], [scaled[truth.peak_idx]],
            marker=style.marker, markersize=PEAK_MARKER_SIZE * 0.6, color=style.color,
            markeredgecolor=SURFACE, markeredgewidth=MARKER_EDGE_WIDTH,
            linestyle="none", zorder=4,
        )

    style_axes(
        ax,
        title=f"Focus measure comparison - {ordered[0].dataset_label}",
        xlabel="Working distance (mm)",
        ylabel="Focus score, scaled to [0, 1]",
        legend=False,
    )
    frame_index_axis(ax, ordered[0].wd_mm)

    # Position clean legend outside at the bottom or top left without blocking curve peaks
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


@dataclass(frozen=True)
class MeasureRow:
    """Everything the focus-measure table shows for one measure.

    Attributes:
        measure: Display name of the focus measure.
        measure_key: Registry key of the focus measure.
        peak_idx: Peak frame of this measure's curve.
        peak_wd_mm: Working distance of that frame.
        fine_idx: Sub-frame peak of this measure's curve.
        fine_wd_mm: Working distance of that sub-frame peak.
        peak_value: Raw focus score at the peak.
        fwhm: Peak width at half height, in frames; smaller is sharper.
        local_maxima: Strict local maxima, the false peaks a search can hit.
        snr: Peak height above the floor divided by the noise estimate.
        contrast: Peak value divided by the lowest value.
        compute_ms: Mean time to score one frame, in milliseconds.
        total_s: Time the whole scan took.
    """

    measure: str
    measure_key: str
    peak_idx: int
    peak_wd_mm: float
    fine_idx: float
    fine_wd_mm: float
    peak_value: float
    fwhm: float
    local_maxima: int
    snr: float
    contrast: float
    compute_ms: float
    total_s: float


def measure_rows(truths: Sequence[GroundTruth]) -> list[MeasureRow]:
    """Turn the focus-measure curves of one image set into table rows.

    Args:
        truths: Reference curves of one image set, one per focus measure.

    Returns:
        One row per measure, in registry order.
    """
    rows: list[MeasureRow] = []
    for truth in _ordered(truths):
        frames = max(1, truth.frame_count)
        rows.append(
            MeasureRow(
                measure=truth.measure_name,
                measure_key=truth.measure_key,
                peak_idx=truth.peak_idx,
                peak_wd_mm=truth.peak_wd_mm,
                fine_idx=truth.reference_idx,
                fine_wd_mm=truth.reference_wd_mm,
                peak_value=truth.peak_value,
                fwhm=truth.stats.fwhm,
                local_maxima=truth.stats.local_maxima,
                snr=truth.stats.snr,
                contrast=truth.stats.contrast,
                # The scan reads every frame once, so its total time divided by
                # the frame count is the per-frame cost of this measure.
                compute_ms=truth.elapsed_s / frames * 1.0e3,
                total_s=truth.elapsed_s,
            )
        )
    return rows
