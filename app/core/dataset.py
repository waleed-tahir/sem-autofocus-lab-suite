"""Image sets: folder scanning, lazy frame loading and working-distance geometry.

This is the only module that reads microscope frames from disk.  It stays free of
Qt so it can be used from the worker thread and from plain scripts.

Main contents:
    * :class:`WorkingDistanceSettings` -- maps a frame index to a physical
      working distance in millimetres.
    * :class:`Dataset` -- one image set (one folder): natural-sorted frame paths,
      a small LRU image cache, the working-distance array and the scan speed.
    * :func:`discover_image_folders` -- every sub-folder of a root that holds
      frames, used by the "Add root folder" action.
    * :func:`read_working_distance_file` -- reads the ``*.WDs.yml`` files that
      ship with the SEM image sets.

The GUI keeps one :class:`Dataset` per loaded image set; the evaluator asks it
for frames by index.
"""

from __future__ import annotations

import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Sequence

import cv2
import numpy as np

LOGGER = logging.getLogger(__name__)

#: Frame file types the loader accepts (lower case, including the dot).
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".png", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp")

#: Suffix of the working-distance side-car files delivered with the image sets.
WD_FILE_PATTERN = "*.WDs.yml"

#: Assignment default: the first frame sits at 10 mm working distance.
DEFAULT_START_MM = 10.0

#: Assignment default: the stage advances 10 um between two frames.
DEFAULT_STEP_UM = 10.0

#: Millimetres per micrometre, used for every step conversion.
MM_PER_UM = 1.0e-3

#: How many decoded frames stay in memory when preloading is off.
DEFAULT_CACHE_CAPACITY = 48

#: A quadratic fit needs at least five samples, so a stack below this is useless.
MIN_USABLE_FRAMES = 5


class DatasetError(RuntimeError):
    """Raised when an image set cannot be scanned or a frame cannot be decoded."""


def natural_sort_key(name: str) -> tuple[object, ...]:
    """Build a sort key that orders embedded numbers by value.

    This keeps ``frame2.png`` in front of ``frame10.png``, which a plain
    alphabetical sort would get wrong.

    Args:
        name: File or folder name to convert.

    Returns:
        A tuple of alternating lower-case text and integer parts.
    """
    parts = re.split(r"(\d+)", name)
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def detect_speed(folder_name: str) -> Optional[int]:
    """Read the SEM scanning speed out of a folder name.

    Recognises the naming scheme of the supplied image sets, for example
    ``pollen.spd1`` -> ``1``.

    Args:
        folder_name: Name of the image-set folder (not the full path).

    Returns:
        The speed number, or ``None`` when the name carries no speed.
    """
    match = re.search(r"spd[\s._-]*(\d+)", folder_name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def read_working_distance_file(folder: Path) -> Optional[np.ndarray]:
    """Read the working distances from a ``*.WDs.yml`` side-car file.

    The microscope writes an OpenCV YAML file that holds one flat ``WD`` list in
    millimetres.  A tiny regular-expression parser is enough here and avoids a
    PyYAML dependency, which would also choke on the ``%YAML:1.0`` header that
    OpenCV emits.

    Args:
        folder: Image-set folder to look in.

    Returns:
        The working distances in millimetres, or ``None`` when no file is found.

    Raises:
        DatasetError: If a file exists but holds no readable ``WD`` list.
    """
    candidates = sorted(folder.glob(WD_FILE_PATTERN))
    if not candidates:
        return None

    path = candidates[0]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise DatasetError(f"Cannot read working-distance file '{path}': {exc}") from exc

    # Keep only what follows the opening bracket of the WD list.
    marker = re.search(r"WD\s*:\s*\[", text)
    if marker is None:
        raise DatasetError(f"No 'WD: [ ... ]' list found in '{path}'.")
    body = text[marker.end():].split("]", 1)[0]

    values = [float(token) for token in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", body)]
    if not values:
        raise DatasetError(f"The 'WD' list in '{path}' is empty.")

    LOGGER.info("Read %d working distances from %s", len(values), path.name)
    return np.asarray(values, dtype=np.float64)


def folder_has_frames(folder: Path) -> bool:
    """Tell whether a folder directly contains at least one supported image."""
    try:
        return any(p.suffix.lower() in SUPPORTED_EXTENSIONS for p in folder.iterdir())
    except OSError as exc:  # Unreadable folders are reported, never swallowed.
        LOGGER.warning("Skipping unreadable folder '%s': %s", folder, exc)
        return False


def discover_image_folders(root: Path) -> list[Path]:
    """Collect every folder below ``root`` that directly holds frames.

    The supplied image sets are nested unevenly (some frames sit one level
    deeper than others), so the walk is recursive and includes ``root`` itself.

    Args:
        root: Folder to walk.

    Returns:
        Naturally sorted list of folders that contain at least one image.
    """
    found: list[Path] = []
    if folder_has_frames(root):
        found.append(root)
    for path in sorted(root.rglob("*")):
        if path.is_dir() and folder_has_frames(path):
            found.append(path)
    return sorted(set(found), key=lambda p: natural_sort_key(str(p)))


@dataclass(frozen=True)
class WorkingDistanceSettings:
    """How a frame index becomes a physical working distance.

    Attributes:
        start_mm: Working distance of the first frame, in millimetres.
        step_um: Stage step between two neighbouring frames, in micrometres.
        increasing: ``True`` when the working distance grows with the frame
            index, ``False`` when the stage moves the other way.
        prefer_file: When ``True`` and the image set ships a ``*.WDs.yml`` file,
            the measured distances from that file win over ``start_mm``/``step_um``.
    """

    start_mm: float = DEFAULT_START_MM
    step_um: float = DEFAULT_STEP_UM
    increasing: bool = True
    prefer_file: bool = True

    @property
    def step_mm(self) -> float:
        """Signed step between two frames, in millimetres."""
        return (self.step_um * MM_PER_UM) * (1.0 if self.increasing else -1.0)

    def positions(self, frame_count: int) -> np.ndarray:
        """Build the working-distance array for ``frame_count`` frames.

        Args:
            frame_count: Number of frames in the image set.

        Returns:
            Array of working distances in millimetres, one per frame.
        """
        return self.start_mm + np.arange(frame_count, dtype=np.float64) * self.step_mm


class _FrameCache:
    """Small least-recently-used cache for decoded frames.

    Frames are 1024x768 bytes each, so a whole image set costs about 150 MB.
    The cache keeps the GUI responsive while browsing without holding every set
    in memory at once.
    """

    def __init__(self, capacity: int) -> None:
        """Create a cache that keeps at most ``capacity`` frames (0 disables it)."""
        self._capacity = max(0, int(capacity))
        self._items: "OrderedDict[int, np.ndarray]" = OrderedDict()

    @property
    def capacity(self) -> int:
        """Maximum number of frames held at once."""
        return self._capacity

    def set_capacity(self, capacity: int) -> None:
        """Change the capacity and drop whatever no longer fits."""
        self._capacity = max(0, int(capacity))
        self._evict()

    def get(self, index: int) -> Optional[np.ndarray]:
        """Return a cached frame and mark it as recently used."""
        if index not in self._items:
            return None
        self._items.move_to_end(index)
        return self._items[index]

    def put(self, index: int, frame: np.ndarray) -> None:
        """Insert a frame, evicting the least recently used ones if needed."""
        if self._capacity == 0:
            return
        self._items[index] = frame
        self._items.move_to_end(index)
        self._evict()

    def clear(self) -> None:
        """Drop every cached frame."""
        self._items.clear()

    def __len__(self) -> int:
        """Number of frames currently cached."""
        return len(self._items)

    def _evict(self) -> None:
        """Remove the oldest entries until the cache fits its capacity."""
        while len(self._items) > self._capacity:
            self._items.popitem(last=False)


class Dataset:
    """One image set: the frames of a single focal stack plus its geometry.

    Frames are decoded on demand and cached.  Decoding goes through
    ``cv2.imdecode(np.fromfile(...))`` instead of ``cv2.imread`` because
    ``cv2.imread`` cannot open paths that contain non-ASCII characters on
    Windows.

    Attributes:
        folder: Folder the frames were read from.
        label: Name shown in the GUI.
        speed: SEM scanning speed taken from the folder name, or ``None``.
        paths: Naturally sorted frame paths.
    """

    def __init__(
        self,
        folder: Path,
        label: Optional[str] = None,
        settings: Optional[WorkingDistanceSettings] = None,
        cache_capacity: int = DEFAULT_CACHE_CAPACITY,
    ) -> None:
        """Scan a folder and prepare an image set.

        Args:
            folder: Folder that directly holds the frames.
            label: Name for the GUI.  Defaults to the folder name.
            settings: Working-distance settings.  Defaults to the assignment values.
            cache_capacity: How many decoded frames to keep in memory.

        Raises:
            DatasetError: If the folder is missing or holds too few images.
        """
        self.folder = Path(folder).resolve()
        if not self.folder.is_dir():
            raise DatasetError(f"'{self.folder}' is not a folder.")

        self.paths = self._scan_frames(self.folder)
        if len(self.paths) < MIN_USABLE_FRAMES:
            raise DatasetError(
                f"'{self.folder.name}' holds {len(self.paths)} image(s); "
                f"at least {MIN_USABLE_FRAMES} are needed for a focus search."
            )

        self.label = label or self.folder.name
        self.speed = detect_speed(self.folder.name)
        self._settings = settings or WorkingDistanceSettings()
        self._cache = _FrameCache(cache_capacity)
        self._file_wd = self._load_file_working_distances()
        self._image_shape: Optional[tuple[int, int]] = None

    # ----------------------------------------------------------------- scanning

    @staticmethod
    def _scan_frames(folder: Path) -> list[Path]:
        """List the supported images of a folder in natural order.

        Raises:
            DatasetError: If the folder cannot be listed.
        """
        try:
            entries = [p for p in folder.iterdir() if p.is_file()]
        except OSError as exc:
            raise DatasetError(f"Cannot list '{folder}': {exc}") from exc
        images = [p for p in entries if p.suffix.lower() in SUPPORTED_EXTENSIONS]
        return sorted(images, key=lambda p: natural_sort_key(p.name))

    def _load_file_working_distances(self) -> Optional[np.ndarray]:
        """Read the side-car working distances, tolerating a missing file."""
        try:
            return read_working_distance_file(self.folder)
        except DatasetError as exc:
            # A broken side-car must not stop the image set from loading; the
            # computed start/step geometry is a perfectly good fallback.
            LOGGER.warning("%s - falling back to start/step geometry.", exc)
            return None

    # ------------------------------------------------------------------ geometry

    @property
    def key(self) -> str:
        """Stable identifier of this image set (its resolved folder path)."""
        return str(self.folder)

    @property
    def frame_count(self) -> int:
        """Number of frames in the stack."""
        return len(self.paths)

    @property
    def max_idx(self) -> int:
        """Highest valid frame index; the searches take this bound inclusively."""
        return len(self.paths) - 1

    @property
    def settings(self) -> WorkingDistanceSettings:
        """Current working-distance settings."""
        return self._settings

    @settings.setter
    def settings(self, value: WorkingDistanceSettings) -> None:
        """Replace the working-distance settings."""
        self._settings = value

    @property
    def has_working_distance_file(self) -> bool:
        """Whether a usable ``*.WDs.yml`` file was found next to the frames."""
        return self._file_wd is not None

    @property
    def uses_working_distance_file(self) -> bool:
        """Whether the measured file distances are what :meth:`working_distances` returns."""
        return self._file_wd is not None and self._settings.prefer_file

    def working_distances(self) -> np.ndarray:
        """Working distance of every frame, in millimetres.

        The measured side-car values win when they exist and are enabled,
        because they describe what the microscope really did.  Otherwise the
        distances follow ``start_mm + i * step``.

        Returns:
            Array of length :attr:`frame_count`, in millimetres.
        """
        if self.uses_working_distance_file:
            assert self._file_wd is not None  # Guarded by uses_working_distance_file.
            if len(self._file_wd) >= self.frame_count:
                # The supplied files list one more position than there are
                # frames, so the surplus tail is dropped.
                return np.array(self._file_wd[: self.frame_count], dtype=np.float64)
            LOGGER.warning(
                "%s: the working-distance file holds %d values for %d frames; "
                "using the start/step geometry instead.",
                self.label, len(self._file_wd), self.frame_count,
            )
        return self._settings.positions(self.frame_count)

    def working_distance(self, index: int) -> float:
        """Working distance of one frame, in millimetres."""
        return float(self.working_distances()[self._checked_index(index)])

    def measured_step_um(self) -> float:
        """Average step between two frames of :meth:`working_distances`, in micrometres."""
        positions = self.working_distances()
        if len(positions) < 2:
            return abs(self._settings.step_um)
        span = float(positions[-1] - positions[0]) / (len(positions) - 1)
        return abs(span) / MM_PER_UM

    # ------------------------------------------------------------------- frames

    @property
    def image_shape(self) -> tuple[int, int]:
        """Frame size as ``(height, width)``, read from the first frame."""
        if self._image_shape is None:
            self._image_shape = tuple(self.frame(0).shape[:2])  # type: ignore[assignment]
        return self._image_shape  # type: ignore[return-value]

    def frame(self, index: int) -> np.ndarray:
        """Return one grayscale frame, decoding it only if it is not cached.

        Args:
            index: Frame index in ``[0, max_idx]``.

        Returns:
            A 2-D ``uint8`` array.  The array is shared with the cache and must
            not be modified in place by callers.

        Raises:
            DatasetError: If the index is out of range or the file is unreadable.
        """
        index = self._checked_index(index)
        cached = self._cache.get(index)
        if cached is not None:
            return cached
        frame = self._decode(self.paths[index])
        self._cache.put(index, frame)
        return frame

    @staticmethod
    def _decode(path: Path) -> np.ndarray:
        """Decode one grayscale image file.

        Raises:
            DatasetError: If the bytes cannot be read or are not a valid image.
        """
        try:
            raw = np.fromfile(str(path), dtype=np.uint8)
        except OSError as exc:
            raise DatasetError(f"Cannot read '{path.name}': {exc}") from exc
        if raw.size == 0:
            raise DatasetError(f"'{path.name}' is empty.")

        frame = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
        if frame is None:
            raise DatasetError(f"'{path.name}' is not a readable image.")
        return frame

    def preload(self, progress: Optional[object] = None) -> None:
        """Decode every frame into the cache.

        Preloading makes a timing comparison measure the focus computation
        instead of the disk, which is what the speed and algorithm comparisons
        are about.

        Args:
            progress: Optional callable ``(done, total) -> None``; when it
                returns ``False`` the preload stops early.

        Raises:
            DatasetError: If a frame cannot be decoded.
        """
        self._cache.set_capacity(self.frame_count)
        for index in range(self.frame_count):
            self.frame(index)
            if callable(progress) and progress(index + 1, self.frame_count) is False:
                LOGGER.info("Preload of '%s' stopped at frame %d.", self.label, index)
                return

    @property
    def is_preloaded(self) -> bool:
        """Whether every frame currently sits in the cache."""
        return len(self._cache) >= self.frame_count

    def release(self) -> None:
        """Drop cached frames and shrink the cache back to its default size."""
        self._cache.clear()
        self._cache.set_capacity(DEFAULT_CACHE_CAPACITY)

    def indices(self) -> Iterator[int]:
        """Iterate over every valid frame index."""
        return iter(range(self.frame_count))

    def _checked_index(self, index: int) -> int:
        """Validate a frame index.

        Raises:
            DatasetError: If the index lies outside ``[0, max_idx]``.
        """
        value = int(index)
        if not 0 <= value <= self.max_idx:
            raise DatasetError(
                f"Frame index {value} is outside [0, {self.max_idx}] for '{self.label}'."
            )
        return value

    def __repr__(self) -> str:
        """Short technical description used in logs."""
        return (
            f"Dataset(label={self.label!r}, frames={self.frame_count}, "
            f"speed={self.speed}, folder={str(self.folder)!r})"
        )


def unique_label(base: str, taken: Sequence[str]) -> str:
    """Make a label that is not in ``taken`` by adding a numeric suffix.

    Args:
        base: Preferred label.
        taken: Labels already in use.

    Returns:
        ``base`` itself when it is free, otherwise ``base (2)``, ``base (3)``, ...
    """
    if base not in taken:
        return base
    suffix = 2
    while f"{base} ({suffix})" in taken:
        suffix += 1
    return f"{base} ({suffix})"
