"""Tab 1: load image sets and browse their frames.

Everything else in the application depends on this tab: it is where folders
become image sets, where the working-distance geometry is set, and where the
user can step through a stack and watch the focus score rise and fall.

Main contents:
    * :class:`DatasetsTab` -- the image-set table, the frame browser and the
      working-distance settings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.dataset import (
    Dataset,
    DatasetError,
    WorkingDistanceSettings,
    detect_speed,
    discover_image_folders,
)
from app.core.focus_measures import require as require_measure
from app.ui.app_state import AppState
from app.core.focus_measures import require as require_measure
from app.ui.icons import get_fluent_icon
from app.ui.tabs.common import (
    KEY_ROLE,
    InfoPanel,
    fill_table,
    integer_cell,
    make_table,
    selected_key,
    text_cell,
)
from app.ui.widgets.image_viewer import ImageViewer

LOGGER = logging.getLogger(__name__)

#: Columns of the image-set table.
_COLUMNS = ("Label", "Speed", "Frames", "Width", "Height")

#: Explanations shown when hovering the table headers.
_TOOLTIPS = (
    "Name used everywhere else in the application.",
    "Scanning speed read from the folder name.",
    "Number of frames in the focal stack.",
    "Frame width in pixels.",
    "Frame height in pixels.",
)

#: Range of the start working distance, in millimetres.
_START_MM_RANGE = (0.0, 1000.0)

#: Range of the stage step, in micrometres.
_STEP_UM_RANGE = (0.001, 10_000.0)


class DatasetsTab(QWidget):
    """Loads image sets and lets the user browse one stack frame by frame."""

    def __init__(self, state: AppState, parent: Optional[QWidget] = None) -> None:
        """Build the tab.

        Args:
            state: Shared application state.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._current: Optional[Dataset] = None

        self._table = make_table(_COLUMNS, _TOOLTIPS)
        # Configure Fluent 2 header resizing: Stretch Label, content-fit numeric columns
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3, 4):
            self._table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setDefaultSectionSize(28)

        self._viewer = ImageViewer()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._prev_frame_btn = QPushButton()
        self._prev_frame_btn.setIcon(get_fluent_icon("prev_frame.png"))
        self._prev_frame_btn.setFixedSize(28, 24)
        self._prev_frame_btn.setToolTip("Previous frame")
        self._next_frame_btn = QPushButton()
        self._next_frame_btn.setIcon(get_fluent_icon("next_frame.png"))
        self._next_frame_btn.setFixedSize(28, 24)
        self._next_frame_btn.setToolTip("Next frame")

        self._frame_info = InfoPanel()
        self._build_settings_widgets()
        self._build_layout()
        self._connect()

        self._refresh_settings_widgets()
        self.refresh()

    # ------------------------------------------------------------------ layout

    def _build_settings_widgets(self) -> None:
        """Create the working-distance and preload controls."""
        self._start_mm = QDoubleSpinBox()
        self._start_mm.setRange(*_START_MM_RANGE)
        self._start_mm.setDecimals(4)
        self._start_mm.setSingleStep(0.1)
        self._start_mm.setSuffix(" mm")
        self._start_mm.setToolTip("Working distance of the first frame of a stack.")

        self._step_um = QDoubleSpinBox()
        self._step_um.setRange(*_STEP_UM_RANGE)
        self._step_um.setDecimals(3)
        self._step_um.setSingleStep(1.0)
        self._step_um.setSuffix(" um")
        self._step_um.setToolTip("Stage movement between two neighbouring frames.")

        self._direction = QComboBox()
        self._direction.addItem("Increasing with frame index", True)
        self._direction.addItem("Decreasing with frame index", False)
        self._direction.setToolTip(
            "Whether the working distance grows or shrinks as the frame index rises."
        )

        self._prefer_file = QCheckBox("Use the measured *.WDs.yml file when present")
        self._prefer_file.setToolTip(
            "The supplied image sets ship the working distances the microscope "
            "really used. With this on, those values win over the start and step "
            "set above."
        )

        self._preload = QCheckBox("Preload images into memory")
        self._preload.setToolTip(
            "Decode a whole stack before searching it, so a timing comparison "
            "measures the focus computation instead of the disk."
        )

    def _build_layout(self) -> None:
        """Arrange the table and the browser."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_browser_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter, stretch=1)

    def _build_left_panel(self) -> QWidget:
        """The image-set table with its load and remove buttons."""
        self._add_folder_button = QPushButton("Add folder...")
        self._add_folder_button.setObjectName("primaryButton")
        self._add_folder_button.setProperty("accent", True)
        self._add_folder_button.setToolTip("Load one folder of frames as one image set.")
        self._add_root_button = QPushButton("Add root folder...")
        self._add_root_button.setToolTip(
            "Load every sub-folder that contains frames as its own image set."
        )
        self._remove_button = QPushButton("Remove selected")
        self._clear_button = QPushButton("Clear all")
        self._rename_button = QPushButton("Rename...")

        top_row = QHBoxLayout()
        top_row.addWidget(self._add_folder_button)
        top_row.addWidget(self._add_root_button)
        top_row.addWidget(self._rename_button)
        top_row.addWidget(self._remove_button)
        top_row.addWidget(self._clear_button)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        layout.addLayout(top_row)
        layout.addWidget(self._table, stretch=1)
        return panel

    def _build_browser_panel(self) -> QWidget:
        """The frame viewer, its slider and the per-frame figures."""
        group = QGroupBox("Frame browser")
        self._slider.setMinimum(0)
        self._slider.setMaximum(0)
        self._slider.setToolTip("Step through the frames of the selected image set.")
        self._frame_info.setMinimumHeight(110)
        self._frame_info.setMaximumHeight(140)

        slider_row = QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(4)
        slider_row.addWidget(self._prev_frame_btn)
        slider_row.addWidget(self._slider, stretch=1)
        slider_row.addWidget(self._next_frame_btn)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(6)
        layout.addWidget(self._viewer, stretch=1)
        layout.addLayout(slider_row)
        layout.addWidget(self._frame_info)

        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(group)
        return panel

    def _connect(self) -> None:
        """Wire the widgets and the shared state together."""
        self._add_folder_button.clicked.connect(self.add_folder_dialog)
        self._add_root_button.clicked.connect(self.add_root_dialog)
        self._remove_button.clicked.connect(self._on_remove)
        self._clear_button.clicked.connect(self._on_clear)
        self._rename_button.clicked.connect(self._on_rename)
        self._table.itemSelectionChanged.connect(self._on_dataset_selected)
        self._slider.valueChanged.connect(self._on_frame_changed)
        self._prev_frame_btn.clicked.connect(lambda: self._slider.setValue(self._slider.value() - 1))
        self._next_frame_btn.clicked.connect(lambda: self._slider.setValue(self._slider.value() + 1))

        self._start_mm.valueChanged.connect(self._on_settings_edited)
        self._step_um.valueChanged.connect(self._on_settings_edited)
        self._direction.currentIndexChanged.connect(self._on_settings_edited)
        self._prefer_file.toggled.connect(self._on_settings_edited)
        self._preload.toggled.connect(self._state.set_preload_enabled)

        self._state.datasets_changed.connect(self.refresh)
        self._state.settings_changed.connect(self._on_frame_changed)
        self._state.measure_changed.connect(lambda _: self._on_frame_changed())

    # ------------------------------------------------------------------ loading

    @Slot()
    def add_folder_dialog(self) -> None:
        """Ask for one folder and load it as one image set."""
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder of frames")
        if not folder:
            return

        path = Path(folder)
        label = self._ask_label_if_needed(path)
        if label is None:
            return

        try:
            dataset = self._state.add_dataset(path, label=label)
        except DatasetError as exc:
            self._report_error("Could not load this folder", str(exc))
            return
        self._maybe_preload(dataset)
        self._select_dataset(dataset.key)

    def _ask_label_if_needed(self, folder: Path) -> Optional[str]:
        """Ask for a label when the folder name carries no scanning speed.

        Args:
            folder: Folder about to be loaded.

        Returns:
            The label to use, or ``None`` when the user cancelled.
        """
        if detect_speed(folder.name) is not None:
            return folder.name

        label, accepted = QInputDialog.getText(
            self,
            "Label for this image set",
            "The folder name carries no scanning speed (such as 'spd1').\n"
            "Please type a label for this image set:",
            text=folder.name,
        )
        if not accepted:
            return None
        return label.strip() or folder.name

    @Slot()
    def add_root_dialog(self) -> None:
        """Ask for a root folder and load every sub-folder that holds frames."""
        root = QFileDialog.getExistingDirectory(
            self, "Choose a root folder containing image sets"
        )
        if not root:
            return

        folders = discover_image_folders(Path(root))
        if not folders:
            self._report_error(
                "No image sets found",
                f"No folder below '{root}' contains readable images.",
            )
            return

        loaded, errors = self._state.add_datasets(folders)
        for dataset in loaded:
            self._maybe_preload(dataset)
        if errors:
            self._report_error(
                "Some folders were skipped",
                f"{len(loaded)} image set(s) loaded.\n\nSkipped:\n" + "\n".join(errors),
            )
        if loaded:
            self._select_dataset(loaded[0].key)

    def _maybe_preload(self, dataset: Dataset) -> None:
        """Decode a whole stack now, when the user asked for preloading."""
        if not self._state.preload_enabled:
            return
        try:
            dataset.preload()
        except DatasetError as exc:
            self._report_error("Could not preload this image set", str(exc))
            return
        LOGGER.info("Preloaded %d frames of '%s'.", dataset.frame_count, dataset.label)

    @Slot()
    def _on_remove(self) -> None:
        """Remove the selected image set."""
        key = selected_key(self._table)
        if key is None:
            self._report_error("Nothing selected", "Select an image set to remove first.")
            return
        self._state.remove_dataset(key)

    @Slot()
    def _on_clear(self) -> None:
        """Remove every image set, after asking."""
        if self._state.dataset_count == 0:
            return
        answer = QMessageBox.question(
            self,
            "Clear every image set",
            f"Remove all {self._state.dataset_count} image set(s), together with "
            "their results and reference curves?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._state.clear_datasets()

    @Slot()
    def _on_rename(self) -> None:
        """Rename the selected image set."""
        key = selected_key(self._table)
        dataset = self._state.dataset(key) if key else None
        if dataset is None:
            self._report_error("Nothing selected", "Select an image set to rename first.")
            return

        label, accepted = QInputDialog.getText(
            self, "Rename image set", "New label:", text=dataset.label
        )
        if accepted and label.strip():
            self._state.rename_dataset(dataset.key, label)

    # ------------------------------------------------------------------ display

    @Slot()
    def refresh(self) -> None:
        """Refill the image-set table from the shared state."""
        datasets = self._state.datasets
        rows = []
        keys = []
        for dataset in datasets:
            height, width = self._frame_size(dataset)
            rows.append(
                (
                    text_cell(dataset.label),
                    integer_cell(dataset.speed) if dataset.speed is not None else ("-", None),
                    integer_cell(dataset.frame_count),
                    integer_cell(width),
                    integer_cell(height),
                )
            )
            keys.append(dataset.key)

        fill_table(self._table, rows, keys)
        self._enable_buttons(bool(datasets))

        if self._current is not None and self._state.dataset(self._current.key) is None:
            self._current = None
        if self._current is None and datasets:
            self._select_dataset(datasets[0].key)
        elif not datasets:
            self._show_no_dataset()

    def _frame_size(self, dataset: Dataset) -> tuple[int, int]:
        """Frame size of an image set, tolerating a frame that cannot be read.

        Reading the size decodes the first frame.  A broken file must not stop
        the whole table from being drawn, so the failure is logged and the row
        simply shows a size of zero.

        Args:
            dataset: Image set to measure.

        Returns:
            The ``(height, width)`` pair, or ``(0, 0)`` when the frame is unreadable.
        """
        try:
            return dataset.image_shape
        except DatasetError as exc:
            LOGGER.error("Cannot read the first frame of '%s': %s", dataset.label, exc)
            return 0, 0

    def _enable_buttons(self, has_datasets: bool) -> None:
        """Enable the buttons that need at least one image set."""
        for button in (self._remove_button, self._clear_button, self._rename_button):
            button.setEnabled(has_datasets)

    def _select_dataset(self, key: str) -> None:
        """Select one image set in the table by its key."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(KEY_ROLE) == key:
                self._table.selectRow(row)
                return

    @Slot()
    def _on_dataset_selected(self) -> None:
        """Point the frame browser at the newly selected image set."""
        key = selected_key(self._table)
        dataset = self._state.dataset(key) if key else None
        if dataset is None:
            self._show_no_dataset()
            return

        self._current = dataset
        self._slider.blockSignals(True)
        self._slider.setMaximum(dataset.max_idx)
        # Start in the middle of the stack, which is where a search would start.
        self._slider.setValue(dataset.max_idx // 2)
        self._slider.blockSignals(False)
        self._on_frame_changed()

    def _show_no_dataset(self) -> None:
        """Empty the browser because no image set is selected."""
        self._current = None
        self._viewer.clear_frame()
        self._slider.setMaximum(0)
        self._frame_info.set_lines(
            ["No image set selected.", "Use \"Add folder...\" to load one."]
        )

    @Slot()
    def _on_frame_changed(self) -> None:
        """Show the frame the slider points at, with its figures."""
        dataset = self._current
        if dataset is None:
            return

        index = min(self._slider.value(), dataset.max_idx)
        try:
            frame = dataset.frame(index)
        except DatasetError as exc:
            self._viewer.clear_frame()
            self._frame_info.set_lines([f"Cannot read frame {index}:", str(exc)])
            LOGGER.error("Cannot read frame %d of '%s': %s", index, dataset.label, exc)
            return

        self._viewer.set_frame(frame)
        self._frame_info.set_lines(self._frame_lines(dataset, index, frame))

    def _frame_lines(self, dataset: Dataset, index: int, frame) -> list[str]:
        """Build the text block under the frame viewer with live focus score."""
        lines = [
            f"Image Set:    {dataset.label}",
            f"Frame Index:  {index} of {dataset.max_idx}",
            f"Working Dist: {dataset.working_distance(index):.5f} mm",
            f"Frame Size:   {frame.shape[1]} × {frame.shape[0]} px",
        ]
        try:
            measure = require_measure(self._state.measure_key)
            score = measure(frame)
            lines.append(f"Focus Score:  {score:.6f} ({measure.display_name})")
        except Exception:
            pass
        return lines

    # ----------------------------------------------------------------- settings

    def _refresh_settings_widgets(self) -> None:
        """Load the current settings into the editors without echoing back."""
        settings = self._state.settings
        for widget in (self._start_mm, self._step_um, self._direction, self._prefer_file):
            widget.blockSignals(True)
        self._start_mm.setValue(settings.start_mm)
        self._step_um.setValue(settings.step_um)
        self._direction.setCurrentIndex(0 if settings.increasing else 1)
        self._prefer_file.setChecked(settings.prefer_file)
        for widget in (self._start_mm, self._step_um, self._direction, self._prefer_file):
            widget.blockSignals(False)
        self._preload.setChecked(self._state.preload_enabled)

    @Slot()
    def _on_settings_edited(self) -> None:
        """Push the edited working-distance settings into the shared state."""
        self._state.set_settings(
            WorkingDistanceSettings(
                start_mm=self._start_mm.value(),
                step_um=self._step_um.value(),
                increasing=bool(self._direction.currentData()),
                prefer_file=self._prefer_file.isChecked(),
            )
        )

    def _report_error(self, title: str, message: str) -> None:
        """Log an error and show it to the user."""
        LOGGER.error("%s: %s", title, message)
        QMessageBox.warning(self, title, message)
