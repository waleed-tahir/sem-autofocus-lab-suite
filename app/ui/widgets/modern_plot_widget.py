"""Modern PyQtGraph widgets with native Fluent aesthetic.

Provides high-performance interactive bar charts with:
- Horizontal, non-tilted category labels
- Authentic Fluent 2 color palette (Accent Blue, Jade Green, Amber Orange)
- Subtle gridlines and zero chart overlapping
- Value callout annotations above bars
- Restored baseline line and tick marks
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from app.core.run_result import RunResult

LOGGER = logging.getLogger(__name__)

# Configure PyQtGraph global options for modern Fluent light styling
pg.setConfigOption("background", "#ffffff")
pg.setConfigOption("foreground", "#1c1c1c")
pg.setConfigOption("antialias", True)

# Short clean algorithm labels that fit horizontally on compact screens
ALGO_ABBR = {
    "global_scan": "Global",
    "coarse_and_fine": "Hybrid",
    "gradient": "Gradient",
    "coarse_quadratic_gradient": "Grad+Fit",
    "coarse_quadratic_grid": "Grid+Fit",
    "Global Scan (exhaustive)": "Global",
    "Coarse-and-Fine Hybrid": "Hybrid",
    "Gradient Search": "Gradient",
    "Coarse (gradient) + Quadratic Fit": "Grad+Fit",
    "Coarse (grid) + Quadratic Fit": "Grid+Fit",
    "Coarse Quadratic Gradient": "Grad+Fit",
    "Coarse Quadratic Grid": "Grid+Fit",
    "Coarse And Fine": "Hybrid",
}


class HorizontalCategoryAxisItem(pg.AxisItem):
    """Clean, horizontal category labels with restored baseline and ticks."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setHeight(28)

    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs) -> None:
        p.save()
        p.setRenderHint(p.RenderHint.Antialiasing, True)
        p.setRenderHint(p.RenderHint.TextAntialiasing, True)

        # 1. Draw subtle horizontal axis baseline line
        pen, p1, p2 = axisSpec
        p.setPen(QPen(QColor("#d1d1d1"), 1.0))
        p.drawLine(p1, p2)

        # 2. Draw subtle tick marks
        for pen_tick, p1_tick, p2_tick in tickSpecs:
            p.drawLine(p1_tick, p2_tick)

        # 3. Draw clean, non-overlapping horizontal category labels
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.setPen(QColor("#5e5e5e"))

        for rect, flags, text in textSpecs:
            p.drawText(rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)

        p.restore()


class ModernAlgorithmBarChart(QWidget):
    """PyQtGraph modern triple-metric bar chart with value callout annotations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Card frame
        self.card = QFrame()
        self.card.setObjectName("modernPlotCard")
        self.card.setStyleSheet(
            "QFrame#modernPlotCard { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; }"
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(6, 6, 6, 6)

        self.gl_widget = pg.GraphicsLayoutWidget()
        self.gl_widget.setBackground("#ffffff")
        card_layout.addWidget(self.gl_widget)
        layout.addWidget(self.card)

        # 1. Frames Read Plot
        axis_frames = HorizontalCategoryAxisItem(orientation="bottom")
        self.p_frames = self.gl_widget.addPlot(
            axisItems={"bottom": axis_frames},
            title="<b style='color:#1c1c1c; font-size:11px; font-family:Segoe UI;'>Frames Acquired (Lower = Better)</b>",
        )
        self.p_frames.showGrid(x=False, y=True, alpha=0.2)
        self.p_frames.setMouseEnabled(x=False, y=False)

        # 2. Time ms Plot
        axis_time = HorizontalCategoryAxisItem(orientation="bottom")
        self.p_time = self.gl_widget.addPlot(
            axisItems={"bottom": axis_time},
            title="<b style='color:#1c1c1c; font-size:11px; font-family:Segoe UI;'>Convergence Time (ms)</b>",
        )
        self.p_time.showGrid(x=False, y=True, alpha=0.2)
        self.p_time.setMouseEnabled(x=False, y=False)

        # 3. Position Error Plot
        axis_error = HorizontalCategoryAxisItem(orientation="bottom")
        self.p_error = self.gl_widget.addPlot(
            axisItems={"bottom": axis_error},
            title="<b style='color:#1c1c1c; font-size:11px; font-family:Segoe UI;'>Error vs. Ground Truth (µm)</b>",
        )
        self.p_error.showGrid(x=False, y=True, alpha=0.2)
        self.p_error.setMouseEnabled(x=False, y=False)

    def set_results(self, results: Sequence[RunResult]) -> None:
        self.p_frames.clear()
        self.p_time.clear()
        self.p_error.clear()

        if not results:
            return

        names = [
            ALGO_ABBR.get(r.algorithm_key, ALGO_ABBR.get(r.algorithm, r.algorithm[:8]))
            for r in results
        ]
        frames = [r.frames_evaluated for r in results]
        times = [r.elapsed_ms for r in results]
        errors = [r.coarse_error_um if r.coarse_error_um is not None else 0.0 for r in results]

        x = np.arange(len(results), dtype=np.float64)
        width = 0.45

        ticks = [list(zip(x, names))]
        for plot in (self.p_frames, self.p_time, self.p_error):
            ax = plot.getAxis("bottom")
            ax.setTicks(ticks)

        # Crisp Fluent brushes with subtle matching border
        pen_frames = pg.mkPen(QColor(0, 90, 158), width=1.0)
        pen_time = pg.mkPen(QColor(0, 110, 98), width=1.0)
        pen_error = pg.mkPen(QColor(184, 52, 0), width=1.0)

        bar_frames = pg.BarGraphItem(x=x, height=frames, width=width, brush=pg.mkBrush(QColor(0, 103, 192, 220)), pen=pen_frames)
        bar_time = pg.BarGraphItem(x=x, height=times, width=width, brush=pg.mkBrush(QColor(0, 130, 114, 220)), pen=pen_time)
        bar_error = pg.BarGraphItem(x=x, height=errors, width=width, brush=pg.mkBrush(QColor(216, 59, 1, 220)), pen=pen_error)

        self.p_frames.addItem(bar_frames)
        self.p_time.addItem(bar_time)
        self.p_error.addItem(bar_error)

        # Add readable value callouts above each bar
        for xi, val in zip(x, frames):
            txt = pg.TextItem(f"{val}", color="#1c1c1c", anchor=(0.5, 1.25))
            txt.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            txt.setPos(xi, val)
            self.p_frames.addItem(txt)

        for xi, val in zip(x, times):
            txt = pg.TextItem(f"{val:.0f}", color="#1c1c1c", anchor=(0.5, 1.25))
            txt.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            txt.setPos(xi, val)
            self.p_time.addItem(txt)

        for xi, val in zip(x, errors):
            txt = pg.TextItem(f"{val:.2f}", color="#1c1c1c", anchor=(0.5, 1.25))
            txt.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            txt.setPos(xi, val)
            self.p_error.addItem(txt)

        # Clean y-range headroom
        max_f = max(frames) if frames else 10
        self.p_frames.setYRange(0, max_f * 1.35)
        self.p_frames.setXRange(-0.5, len(results) - 0.5)

        max_t = max(times) if times else 10
        self.p_time.setYRange(0, max_t * 1.35)
        self.p_time.setXRange(-0.5, len(results) - 0.5)

        max_e = max(errors) if any(errors) else 1.0
        self.p_error.setYRange(0, max_e * 1.35)
        self.p_error.setXRange(-0.5, len(results) - 0.5)
