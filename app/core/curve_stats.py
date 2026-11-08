"""Descriptors of a focus curve.

The comparison tabs need to say more about a focus curve than "where is the
peak": how wide the peak is, how noisy the curve is, and how many false peaks a
search could get trapped in.  Those numbers are computed here, away from any
plotting code, so the plots stay pure drawing functions.

Main contents:
    * :func:`normalize` -- scale a curve to ``[0, 1]`` so two speeds can share
      one pair of axes.
    * :func:`fwhm_frames` -- width of the peak at half its height.
    * :func:`estimate_noise_sigma` -- noise level from second differences.
    * :func:`count_local_maxima` -- number of candidate peaks.
    * :class:`CurveStats` -- all of the above for one curve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

#: Half height is where the FWHM is measured, counted from the curve's floor.
HALF = 0.5

#: Variance of the second difference of white noise is 6 * sigma^2.
_SECOND_DIFFERENCE_GAIN = math.sqrt(6.0)

#: Mean absolute value of a standard normal variable, sqrt(2 / pi).
_MEAN_ABS_NORMAL = 0.7978845608


def normalize(curve: Sequence[float]) -> np.ndarray:
    """Scale a curve to ``[0, 1]``.

    Focus scores of different measures and different scanning speeds live on
    totally different scales, so they only become comparable on one plot after
    this rescaling.

    Args:
        curve: Focus values.

    Returns:
        The rescaled curve.  A flat curve becomes all zeros.
    """
    values = np.asarray(curve, dtype=np.float64)
    if values.size == 0:
        return values
    low = float(np.nanmin(values))
    high = float(np.nanmax(values))
    span = high - low
    if span <= 0.0:
        return np.zeros_like(values)
    return (values - low) / span


def fwhm_frames(curve: Sequence[float]) -> float:
    """Width of the main peak at half its height, in frames.

    Half height is taken between the curve's minimum and its maximum, and the
    two crossings are interpolated linearly, so the result is a fractional
    number of frames.  A narrow peak means the focus measure discriminates
    sharply; a wide peak means a flat, hard-to-localise optimum.

    Args:
        curve: Focus values, one per frame.

    Returns:
        The width in frames, or ``nan`` when no two crossings exist.
    """
    values = np.asarray(curve, dtype=np.float64)
    if values.size < 3:
        return float("nan")

    peak = int(np.nanargmax(values))
    level = float(np.nanmin(values)) + HALF * (float(values[peak]) - float(np.nanmin(values)))

    left = _crossing(values, peak, level, step=-1)
    right = _crossing(values, peak, level, step=+1)
    if math.isnan(left) or math.isnan(right):
        return float("nan")
    return right - left


def _crossing(values: np.ndarray, start: int, level: float, step: int) -> float:
    """Walk away from the peak until the curve drops below ``level``.

    Args:
        values: The curve.
        start: Index to start from (the peak).
        level: Height to cross.
        step: ``-1`` to walk left, ``+1`` to walk right.

    Returns:
        The fractional index of the crossing, or ``nan`` if the curve never
        drops below ``level`` on that side.
    """
    index = start
    last = values.size - 1
    while 0 <= index + step <= last:
        current, following = float(values[index]), float(values[index + step])
        if following <= level:
            # Linear interpolation between the two samples that bracket level.
            span = current - following
            fraction = 0.0 if span == 0.0 else (current - level) / span
            return float(index) + step * fraction
        index += step
    return float("nan")


def estimate_noise_sigma(curve: Sequence[float]) -> float:
    """Estimate the noise on a focus curve, in focus-score units.

    The second difference of a smooth curve is small, while for white noise it
    has a standard deviation of ``sqrt(6) * sigma``.  Using the median of the
    absolute second differences keeps the estimate from being dominated by the
    peak itself.  This is the same reasoning the gradient search uses for its
    noise-floor test.

    Args:
        curve: Focus values, one per frame.

    Returns:
        The estimated standard deviation, or ``nan`` for curves below 3 samples.
    """
    values = np.asarray(curve, dtype=np.float64)
    if values.size < 3:
        return float("nan")
    second = np.abs(values[2:] - 2.0 * values[1:-1] + values[:-2])
    median = float(np.median(second))
    return median / _SECOND_DIFFERENCE_GAIN / _MEAN_ABS_NORMAL


def count_local_maxima(curve: Sequence[float]) -> int:
    """Count strict local maxima, the false peaks a search can get stuck in.

    Args:
        curve: Focus values, one per frame.

    Returns:
        The number of samples that are strictly higher than both neighbours.
    """
    values = np.asarray(curve, dtype=np.float64)
    if values.size < 3:
        return 0
    inner = values[1:-1]
    return int(np.count_nonzero((inner > values[:-2]) & (inner > values[2:])))


def peak_contrast(curve: Sequence[float]) -> float:
    """Ratio between the peak value and the lowest value of the curve.

    Args:
        curve: Focus values.

    Returns:
        ``max / min``, or ``nan`` when the minimum is not positive.
    """
    values = np.asarray(curve, dtype=np.float64)
    if values.size == 0:
        return float("nan")
    low = float(np.nanmin(values))
    if low <= 0.0:
        return float("nan")
    return float(np.nanmax(values)) / low


@dataclass(frozen=True)
class CurveStats:
    """Every descriptor of one focus curve.

    Attributes:
        peak_idx: Index of the highest sample.
        peak_value: Value at :attr:`peak_idx`.
        fwhm: Peak width at half height, in frames.
        noise_sigma: Estimated noise in focus-score units.
        local_maxima: Number of strict local maxima.
        contrast: Peak value divided by the lowest value.
        snr: Peak height above the floor divided by the noise estimate.
    """

    peak_idx: int
    peak_value: float
    fwhm: float
    noise_sigma: float
    local_maxima: int
    contrast: float
    snr: float

    @classmethod
    def of(cls, curve: Sequence[float]) -> "CurveStats":
        """Compute every descriptor of a curve.

        Args:
            curve: Focus values, one per frame.

        Returns:
            The filled record.  Fields that need at least three samples are
            ``nan`` for shorter curves.
        """
        values = np.asarray(curve, dtype=np.float64)
        if values.size == 0:
            return cls(-1, float("nan"), float("nan"), float("nan"), 0,
                       float("nan"), float("nan"))

        peak_idx = int(np.nanargmax(values))
        peak_value = float(values[peak_idx])
        noise = estimate_noise_sigma(values)
        height = peak_value - float(np.nanmin(values))
        snr = height / noise if noise and noise > 0.0 else float("nan")
        return cls(
            peak_idx=peak_idx,
            peak_value=peak_value,
            fwhm=fwhm_frames(values),
            noise_sigma=noise,
            local_maxima=count_local_maxima(values),
            contrast=peak_contrast(values),
            snr=snr,
        )
