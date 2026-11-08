"""The ``eval_func`` that every search algorithm calls.

The searches in ``autofocus.algorithms`` do not know about files or focus
measures.  They only call ``eval_func(idx, stride, fmo_name) -> float``.  This
module builds that function: it loads the frame, subsamples it, optionally adds
noise, applies the focus measure and caches the score.

Main contents:
    * :class:`Evaluator` -- the callable, its caches and its counters.
    * :func:`make_eval_func` -- factory used by the algorithm adapters.

One fresh :class:`Evaluator` is created per algorithm run, so two runs never
share focus values and the reported counters belong to a single run.
"""

from __future__ import annotations

import logging
from typing import Mapping, Optional

import numpy as np

from app.core.dataset import Dataset
from app.core.focus_measures import FocusMeasure, resolve

LOGGER = logging.getLogger(__name__)

#: Highest grey level of the 8-bit frames, used when clipping noisy pixels.
MAX_GREY_LEVEL = 255.0

#: Cache key: frame index, pixel stride and focus-measure key.
CacheKey = tuple[int, int, str]


class Evaluator:
    """Turns a frame index into a focus score, with caching and counters.

    The call signature is exactly what the searches expect.  It is also what
    the helper ``_invoke_eval`` inside ``autofocus.algorithms`` detects by
    inspection: three positional parameters, so every search passes its stride
    and its focus-measure name through.

    Attributes:
        dataset: Image set the frames come from.
        measure: Focus measure used whenever a search asks for no specific one.
        noise_sigma: Standard deviation of the optional Gaussian noise, in grey
            levels.  ``0`` disables noise injection.
    """

    def __init__(
        self,
        dataset: Dataset,
        measure: FocusMeasure,
        noise_sigma: float = 0.0,
        seed: Optional[int] = None,
    ) -> None:
        """Create an evaluator with empty caches and counters.

        Args:
            dataset: Image set to read frames from.
            measure: Focus measure selected in the GUI.
            noise_sigma: Gaussian noise standard deviation in grey levels.
            seed: Seed for the noise, so a robustness run can be repeated.
        """
        self.dataset = dataset
        self.measure = measure
        self.noise_sigma = max(0.0, float(noise_sigma))
        self._seed = seed
        self._scores: dict[CacheKey, float] = {}
        self._eval_calls = 0

    # ----------------------------------------------------------------- calling

    def __call__(self, idx: int, stride: int = 1, fmo_name: Optional[str] = None) -> float:
        """Score one frame.

        Args:
            idx: Frame index in ``[0, dataset.max_idx]``.
            stride: Pixel subsampling stride; ``1`` means full resolution.
            fmo_name: Focus measure requested by the search.  ``None`` or an
                unknown name falls back to :attr:`measure`.

        Returns:
            The focus score; higher means sharper.

        Raises:
            DatasetError: If the frame index is invalid or the file is unreadable.
        """
        self._eval_calls += 1

        measure = resolve(fmo_name) or self.measure
        if fmo_name and resolve(fmo_name) is None:
            # One search defaults to "composite_m9_m2", which has no
            # implementation; say so once instead of failing the whole run.
            LOGGER.debug(
                "Unknown focus measure '%s' requested; using '%s'.", fmo_name, measure.key
            )

        stride = max(1, int(stride))
        key: CacheKey = (int(idx), stride, measure.key)
        cached = self._scores.get(key)
        if cached is not None:
            return cached

        score = measure(self._prepare_image(int(idx), stride))
        self._scores[key] = score
        return score

    def _prepare_image(self, idx: int, stride: int) -> np.ndarray:
        """Load a frame, subsample it and add noise when requested.

        Args:
            idx: Frame index.
            stride: Pixel subsampling stride.

        Returns:
            The image the focus measure is applied to.
        """
        frame = self.dataset.frame(idx)
        view = frame[::stride, ::stride] if stride > 1 else frame
        if self.noise_sigma <= 0.0:
            # Without noise the untouched uint8 view is handed over, which keeps
            # the measures on their own fast path and copies nothing.
            return view
        return self._add_noise(view, idx)

    def _add_noise(self, view: np.ndarray, idx: int) -> np.ndarray:
        """Add Gaussian noise to one frame.

        The generator is derived from ``(seed, idx)`` so that a given frame
        always receives the same noise within a run.  Without that, two probes
        of the same frame would disagree and the measured robustness would
        depend on the probe order instead of on the noise level.

        Noise is added after subsampling: the samples are independent, so the
        statistics are the same as adding it first, at a fraction of the cost.

        Args:
            view: Subsampled frame.
            idx: Frame index, used to derive the generator.

        Returns:
            A noisy ``float32`` copy, clipped to the 8-bit range.
        """
        seed_material = [0 if self._seed is None else int(self._seed), int(idx)]
        rng = np.random.default_rng(seed_material)
        noisy = view.astype(np.float32)
        noisy += rng.normal(0.0, self.noise_sigma, size=view.shape).astype(np.float32)
        return np.clip(noisy, 0.0, MAX_GREY_LEVEL, out=noisy)

    # ---------------------------------------------------------------- counters

    @property
    def eval_calls(self) -> int:
        """How often a search asked for a score, cache hits included."""
        return self._eval_calls

    @property
    def unique_evals(self) -> int:
        """How many distinct ``(index, stride, measure)`` scores were computed."""
        return len(self._scores)

    @property
    def unique_frames(self) -> int:
        """How many distinct frames were read, which is the cost that matters."""
        return len({key[0] for key in self._scores})

    def frames_touched(self) -> set[int]:
        """Set of frame indices this evaluator computed a score for."""
        return {key[0] for key in self._scores}

    def scores_for(self, stride: int = 1, measure_key: Optional[str] = None) -> dict[int, float]:
        """Snapshot of the cached scores for one stride and measure.

        The hybrid search evaluates its coarse stage at a large stride and its
        fine stage at full resolution, so its own ``evals`` dictionary mixes two
        resolutions.  Feeding that mix into a parabola fit would distort the
        vertex.  This method hands out a single-resolution snapshot instead.

        Args:
            stride: Pixel stride to filter on.
            measure_key: Focus-measure key to filter on; defaults to :attr:`measure`.

        Returns:
            A fresh ``{frame index: score}`` dictionary.  Callers may modify it;
            the algorithms do exactly that.
        """
        wanted_measure = measure_key or self.measure.key
        wanted_stride = max(1, int(stride))
        return {
            idx: score
            for (idx, key_stride, key_measure), score in self._scores.items()
            if key_stride == wanted_stride and key_measure == wanted_measure
        }

    def all_scores(self) -> Mapping[CacheKey, float]:
        """Read-only view of the whole score cache."""
        return dict(self._scores)

    def __repr__(self) -> str:
        """Short technical description used in logs."""
        return (
            f"Evaluator(dataset={self.dataset.label!r}, measure={self.measure.key!r}, "
            f"noise_sigma={self.noise_sigma}, calls={self._eval_calls}, "
            f"unique={self.unique_evals})"
        )


def make_eval_func(
    dataset: Dataset,
    measure: FocusMeasure,
    noise_sigma: float = 0.0,
    seed: Optional[int] = None,
) -> Evaluator:
    """Build a fresh evaluation function for one algorithm run.

    Args:
        dataset: Image set to read frames from.
        measure: Focus measure selected in the GUI.
        noise_sigma: Gaussian noise standard deviation in grey levels.
        seed: Seed for the noise generator.

    Returns:
        A callable ``eval_func(idx, stride, fmo_name) -> float`` with its own
        empty cache, so this run shares no focus value with any other run.
    """
    return Evaluator(dataset, measure, noise_sigma=noise_sigma, seed=seed)
