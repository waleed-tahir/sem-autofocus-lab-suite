"""An embedded matplotlib figure with a toolbar and a "Save PNG" button.

Every plot in the application sits in one of these.  The widget owns the figure
and knows how to redraw and how to export it; the actual drawing is done by the
pure functions in :mod:`app.plots`, which this widget calls through a callback.

Main contents:
    * :class:`PlotCanvas` -- the figure, the toolbar and the save button.
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
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.export import EXPORT_DPI, ExportError, safe_stem, suggest_filename
from app.plots.style import SURFACE

LOGGER = logging.getLogger(__name__)

#: Default figure size in inches; the canvas rescales it with the window.
DEFAULT_FIGURE_SIZE = (7.2, 4.6)

#: Screen resolution of the embedded figure.  The export uses 300 dpi instead.
SCREEN_DPI = 100

#: Signature of the function a tab hands over to draw the plot.
DrawCallback = Callable[[Figure], None]


class PlotCanvas(QWidget):
    """A matplotlib figure embedded in the window.

    A tab sets :meth:`set_draw_callback` once and calls :meth:`redraw` whenever
    its data changes.  The callback receives the figure and nothing else, which
    is what keeps the drawing code free of Qt.
    """

    def __init__(
        self,
        title: str = "plot",
        figure_size: tuple[float, float] = DEFAULT_FIGURE_SIZE,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Create an empty canvas.

        Args:
            title: Name used for the suggested PNG file name.
            figure_size: Initial figure size in inches.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._draw_callback: Optional[DrawCallback] = None

        self.figure = Figure(figsize=figure_size, dpi=SCREEN_DPI, facecolor=SURFACE)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(220)

        self._toolbar = NavigationToolbar2QT(self.canvas, self)
        self._save_button = QPushButton("Save PNG...")
        self._save_button.setToolTip(f"Save this plot as a {EXPORT_DPI} dpi PNG file.")
        self._save_button.clicked.connect(self._on_save_clicked)

        self._build_layout()

    def _build_layout(self) -> None:
        """Put the toolbar above the figure, with the save button beside it."""
        toolbar_row = QHBoxLayout()
        toolbar_row.setContentsMargins(0, 0, 0, 0)
        toolbar_row.addWidget(self._toolbar, stretch=1)
        toolbar_row.addWidget(self._save_button, alignment=Qt.AlignmentFlag.AlignRight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(toolbar_row)
        layout.addWidget(self.canvas, stretch=1)

    # -------------------------------------------------------------- drawing

    @property
    def title(self) -> str:
        """Name used for the suggested file name of an export."""
        return self._title

    def set_draw_callback(self, callback: Optional[DrawCallback]) -> None:
        """Set the function that draws this plot.

        Args:
            callback: ``(figure) -> None``; it should clear the figure itself.
        """
        self._draw_callback = callback

    def redraw(self) -> None:
        """Run the draw callback and repaint the canvas.

        A failure while drawing is reported in the log and left on screen as an
        empty figure; it must not take the window down.
        """
        if self._draw_callback is None:
            return
        try:
            self._draw_callback(self.figure)
        except Exception as exc:  # noqa: BLE001 - a bad plot must not kill the GUI.
            LOGGER.exception("Could not draw the plot '%s'.", self._title)
            self.figure.clear()
            axes = self.figure.add_subplot(111)
            axes.set_axis_off()
            axes.text(0.5, 0.5, f"Could not draw this plot:\n{exc}",
                      ha="center", va="center", fontsize=9.0, wrap=True)
        self.canvas.draw_idle()

    def clear(self) -> None:
        """Empty the figure and repaint."""
        self.figure.clear()
        self.canvas.draw_idle()

    # --------------------------------------------------------------- export

    def save_png(self, path: Path, dpi: int = EXPORT_DPI) -> None:
        """Write the current figure to a PNG file.

        Args:
            path: File to write.
            dpi: Resolution; 300 dpi is the print-quality default.

        Raises:
            ExportError: If the file cannot be written.
        """
        try:
            self.figure.savefig(path, dpi=dpi, facecolor=SURFACE, bbox_inches="tight")
        except (OSError, ValueError) as exc:
            raise ExportError(f"Cannot save the plot to '{path}': {exc}") from exc
        LOGGER.info("Saved plot '%s' to %s", self._title, path)

    def _on_save_clicked(self) -> None:
        """Ask for a file name and save the figure there."""
        suggested = suggest_filename(safe_stem(self._title), ".png", Path.home())
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save plot as PNG", str(suggested), "PNG image (*.png)"
        )
        if not chosen:
            return
        try:
            self.save_png(Path(chosen))
        except ExportError as exc:
            LOGGER.error("%s", exc)
            QMessageBox.critical(self, "Could not save the plot", str(exc))
        else:
            QMessageBox.information(
                self, "Plot saved", f"Saved to:\n{chosen}\n\nResolution: {EXPORT_DPI} dpi."
            )
