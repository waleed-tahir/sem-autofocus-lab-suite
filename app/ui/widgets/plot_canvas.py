"""An embedded high-fidelity chart canvas with modern styling.

Replaces the crude 1990s toolbar with clean Fluent action buttons:
- 'Reset View'
- 'Pan & Drag'
- 'Zoom Box'
- 'Save PNG...'
Features subtle borders, crisp Segoe UI typography, and anti-aliasing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.export import EXPORT_DPI, ExportError, safe_stem, suggest_filename

LOGGER = logging.getLogger(__name__)

DEFAULT_FIGURE_SIZE = (7.2, 4.6)
SCREEN_DPI = 110

DrawCallback = Callable[[Figure], None]


class PlotCanvas(QWidget):
    """Modernized high-contrast PlotCanvas with clean Fluent controls and zero overlap."""

    def __init__(
        self,
        title: str = "plot",
        figure_size: tuple[float, float] = DEFAULT_FIGURE_SIZE,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._draw_callback: Optional[DrawCallback] = None

        self.figure = Figure(figsize=figure_size, dpi=SCREEN_DPI, facecolor="#ffffff")
        # constrained layout with padding
        self.figure.set_layout_engine("constrained")

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(220)

        # Matplotlib toolbar kept headless for programmatic actions
        self._toolbar = NavigationToolbar2QT(self.canvas, self)
        self._toolbar.setVisible(False)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("plotCard")
        self.card.setStyleSheet(
            "QFrame#plotCard { background-color: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; }"
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(4)

        # Action bar at top
        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 2)
        header.setSpacing(4)

        # Keep title compact on card header
        clean_title = self._title.replace("_", " ").title()
        self.title_label = QLabel(clean_title)
        self.title_label.setStyleSheet(
            "font-weight: 600; font-size: 11.5px; color: #1c1c1c; border: none; background: transparent;"
        )
        header.addWidget(self.title_label)

        self.coord_label = QLabel("")
        self.coord_label.setStyleSheet(
            "font-size: 10.5px; color: #5e5e5e; padding-left: 8px; border: none; background: transparent;"
        )
        self.coord_label.hide()
        header.addWidget(self.coord_label)
        header.addStretch(1)

        self.btn_home = QPushButton("Reset")
        self.btn_home.setToolTip("Reset view")
        self.btn_home.setFixedHeight(20)
        self.btn_home.setStyleSheet("font-size: 10.5px; padding: 2px 7px;")
        self.btn_home.clicked.connect(self._toolbar.home)

        self.btn_pan = QPushButton("Pan")
        self.btn_pan.setCheckable(True)
        self.btn_pan.setToolTip("Pan with left click, zoom with right click")
        self.btn_pan.setFixedHeight(20)
        self.btn_pan.setStyleSheet("font-size: 10.5px; padding: 2px 7px;")
        self.btn_pan.clicked.connect(self._toggle_pan)

        self.btn_zoom = QPushButton("Zoom")
        self.btn_zoom.setCheckable(True)
        self.btn_zoom.setToolTip("Zoom to rectangular region")
        self.btn_zoom.setFixedHeight(20)
        self.btn_zoom.setStyleSheet("font-size: 10.5px; padding: 2px 7px;")
        self.btn_zoom.clicked.connect(self._toggle_zoom)

        self.btn_save = QPushButton("Save PNG")
        self.btn_save.setToolTip(f"Export high-resolution ({EXPORT_DPI} DPI) figure")
        self.btn_save.setFixedHeight(20)
        self.btn_save.setStyleSheet("font-size: 10.5px; padding: 2px 7px; font-weight: 500;")
        self.btn_save.clicked.connect(self._on_save_clicked)

        for btn in (self.btn_home, self.btn_pan, self.btn_zoom, self.btn_save):
            header.addWidget(btn)

        card_layout.addLayout(header)
        card_layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(self.card)

        # Wire hover coordinate tracking
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)

    def _on_hover(self, event) -> None:
        if event.inaxes and event.xdata is not None and event.ydata is not None:
            self.coord_label.setText(f"X: {event.xdata:.4f} | Y: {event.ydata:.2f}")
            self.coord_label.show()
        else:
            self.coord_label.setText("")
            self.coord_label.hide()

    def _toggle_pan(self) -> None:
        if self.btn_zoom.isChecked():
            self.btn_zoom.setChecked(False)
        self._toolbar.pan()

    def _toggle_zoom(self) -> None:
        if self.btn_pan.isChecked():
            self.btn_pan.setChecked(False)
        self._toolbar.zoom()

    @property
    def title(self) -> str:
        return self._title

    def set_draw_callback(self, callback: Optional[DrawCallback]) -> None:
        self._draw_callback = callback

    def redraw(self) -> None:
        if self._draw_callback is None:
            return
        try:
            self._draw_callback(self.figure)
        except Exception as exc:
            LOGGER.exception("Could not draw plot '%s'.", self._title)
            self.figure.clear()
            axes = self.figure.add_subplot(111)
            axes.set_axis_off()
            axes.text(0.5, 0.5, f"Could not draw plot:\n{exc}",
                      ha="center", va="center", fontsize=9.0, wrap=True)
        self.canvas.draw_idle()

    def clear(self) -> None:
        self.figure.clear()
        self.canvas.draw_idle()

    def save_png(self, path: Path, dpi: int = EXPORT_DPI) -> None:
        self.figure.savefig(path, dpi=dpi, facecolor=self.figure.get_facecolor(), bbox_inches="tight")

    def _on_save_clicked(self) -> None:
        suggested = suggest_filename(self._title, "png")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Plot",
            str(Path.home() / suggested),
            "Portable Network Graphics (*.png);;All files (*.*)",
        )
        if not file_path:
            return
        try:
            self.save_png(Path(file_path))
        except (OSError, ExportError) as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not save the plot:\n{exc}")
