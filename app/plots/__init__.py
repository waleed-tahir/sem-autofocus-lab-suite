"""Matplotlib and plotting functions.

Lab Submission Edition:
- :mod:`app.plots.style` -- Fluent colors, markers and axis styling.
- :mod:`app.plots.focus_curve` -- Reference curve with visited frames and replay probes.
- :mod:`app.plots.algorithm_bars` -- Frame counts, runtime, and accuracy per algorithm.
"""

from __future__ import annotations

from .style import configure_matplotlib
from .focus_curve import draw_focus_curve
from .algorithm_bars import draw_algorithm_bars, frames_saved_table

__all__ = [
    "configure_matplotlib",
    "draw_focus_curve",
    "draw_algorithm_bars",
    "frames_saved_table",
]
