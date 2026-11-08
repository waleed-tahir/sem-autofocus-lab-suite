"""Shows one grayscale frame, scaled to fit the available space.

The Datasets tab uses it to browse the stack and the Results tab uses it to show
the sharpest frame large.  The widget keeps the aspect ratio and rescales on
every resize, so a 1024x768 SEM frame stays readable in a docked panel.

Main contents:
    * :class:`ImageViewer` -- the label that holds the pixmap.
    * :func:`grayscale_to_pixmap` -- numpy array to ``QPixmap``.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

LOGGER = logging.getLogger(__name__)

#: Smallest size the viewer asks for, so it never collapses to nothing.
MIN_SIZE = (320, 240)

#: Text shown while no frame is loaded.
PLACEHOLDER_TEXT = "No frame to show."


def grayscale_to_pixmap(frame: np.ndarray) -> QPixmap:
    """Convert a 2-D grayscale array into a ``QPixmap``.

    Args:
        frame: 2-D array.  Anything that is not ``uint8`` is rescaled to the
            8-bit range first, which is what the noisy ``float32`` frames need.

    Returns:
        The pixmap.

    Raises:
        ValueError: If the array is not two-dimensional.
    """
    if frame.ndim != 2:
        raise ValueError(f"Expected a 2-D grayscale frame, got shape {frame.shape}.")

    data = frame if frame.dtype == np.uint8 else _to_uint8(frame)
    # A copy guarantees the buffer is contiguous and outlives the QImage, which
    # does not own the memory it is handed.
    data = np.ascontiguousarray(data)
    height, width = data.shape
    image = QImage(data.data, width, height, width, QImage.Format.Format_Grayscale8)
    return QPixmap.fromImage(image.copy())


def _to_uint8(frame: np.ndarray) -> np.ndarray:
    """Rescale any numeric array into the 8-bit grey range."""
    values = frame.astype(np.float64)
    low = float(np.nanmin(values))
    high = float(np.nanmax(values))
    if high <= low:
        return np.zeros(frame.shape, dtype=np.uint8)
    return ((values - low) / (high - low) * 255.0).astype(np.uint8)


class ImageViewer(QLabel):
    """A label that shows one frame, always scaled to fit.

    The original pixmap is kept so that repeated resizes rescale from the full
    resolution instead of from an already shrunken copy.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Create an empty viewer."""
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(*MIN_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            "QLabel { background: #1c1c1e; color: #8e8e93; border: 1px solid #dcdcdc; border-radius: 6px; font-size: 11.5px; }"
        )
        self.setText(PLACEHOLDER_TEXT)

    def set_frame(self, frame: Optional[np.ndarray]) -> None:
        """Show a frame, or the placeholder when there is none.

        Args:
            frame: 2-D grayscale array, or ``None`` to clear the viewer.
        """
        if frame is None:
            self.clear_frame()
            return
        try:
            self._pixmap = grayscale_to_pixmap(frame)
        except ValueError as exc:
            LOGGER.error("Cannot show the frame: %s", exc)
            self.clear_frame()
            self.setText(f"Cannot show this frame:\n{exc}")
            return
        self._rescale()

    def clear_frame(self) -> None:
        """Drop the frame and show the placeholder text."""
        self._pixmap = None
        super().clear()
        self.setText(PLACEHOLDER_TEXT)

    @property
    def has_frame(self) -> bool:
        """Whether a frame is currently shown."""
        return self._pixmap is not None

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt naming.
        """Rescale the frame whenever the widget changes size."""
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        """Fit the stored pixmap into the current widget size."""
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
