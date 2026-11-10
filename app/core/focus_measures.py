"""Registry of the focus measures offered in the GUI.

Every entry points straight at a function of the ``autofocus.algorithms`` package;
this module gives them a stable key, a display name, and a short explanation for the GUI.

Lab Submission Edition:
- Normalized Variance: Var(I) / Mean(I)
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping, Optional

import numpy as np

from autofocus.algorithms import (
    normalized_variance,
)

#: Signature every focus measure shares: one grayscale image in, one score out.
MeasureFunc = Callable[[np.ndarray], float]

#: Normalized Variance is the primary measure.
DEFAULT_MEASURE_KEY = "normalized_variance"


@dataclass(frozen=True)
class FocusMeasure:
    """One selectable focus measure.

    Attributes:
        key: Stable identifier, also used as the ``fmo_name`` of the searches.
        display_name: Text shown in the GUI.
        func: The scoring function from ``autofocus.algorithms``.
        formula: Short formula shown as a tooltip and in plot subtitles.
        description: One sentence on what the measure reacts to.
    """

    key: str
    display_name: str
    func: MeasureFunc
    formula: str
    description: str

    def __call__(self, image: np.ndarray) -> float:
        """Score one image.

        Args:
            image: Grayscale frame.

        Returns:
            The focus score; higher means sharper.
        """
        return float(self.func(image))


_MEASURES: tuple[FocusMeasure, ...] = (
    FocusMeasure(
        key="normalized_variance",
        display_name="Normalized Variance",
        func=normalized_variance,
        formula="Var(I) / Mean(I)",
        description=(
            "Intensity spread divided by mean brightness, so brighter frames "
            "do not score higher by themselves."
        ),
    ),
)

#: Read-only mapping of key -> :class:`FocusMeasure`, in GUI order.
FOCUS_MEASURES: Mapping[str, FocusMeasure] = MappingProxyType(
    {measure.key: measure for measure in _MEASURES}
)


def default_measure() -> FocusMeasure:
    """Return the measure the GUI starts with (Normalized Variance)."""
    return FOCUS_MEASURES[DEFAULT_MEASURE_KEY]


def resolve(name: Optional[str]) -> Optional[FocusMeasure]:
    """Look a focus measure up by key or by display name."""
    if not name:
        return None
    if name in FOCUS_MEASURES:
        return FOCUS_MEASURES[name]
    lowered = name.strip().lower()
    for measure in _MEASURES:
        if lowered in (measure.key.lower(), measure.display_name.lower()):
            return measure
    return None


def require(name: str) -> FocusMeasure:
    """Look a focus measure up and fail loudly when it is unknown."""
    measure = resolve(name)
    if measure is None:
        known = ", ".join(FOCUS_MEASURES)
        raise KeyError(f"Unknown focus measure '{name}'. Known measures: {known}.")
    return measure


def display_names() -> list[str]:
    """Display names of every measure, in GUI order."""
    return [measure.display_name for measure in _MEASURES]


def keys() -> list[str]:
    """Keys of every measure, in GUI order."""
    return [measure.key for measure in _MEASURES]
