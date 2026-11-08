"""Widget pieces the tabs share.

Nine of the ten tabs need the same handful of things: a sortable read-only
table, a drop-down of the loaded image sets, a checkable list, and a monospaced
panel of label-and-value lines.  Building them once here keeps each tab short
and makes every table in the application behave the same way.

Main contents:
    * :class:`NumericItem` -- a table cell that sorts by value, not by text.
    * :func:`make_table` / :func:`fill_table` -- the shared table.
    * :func:`refresh_dataset_combo` / :func:`refresh_algorithm_combo` -- selector
      drop-downs that keep their selection across a refresh.
    * :func:`make_check_list` / :func:`checked_keys` -- multi-selection lists.
    * :class:`InfoPanel` -- the monospaced label-and-value panel.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import ALGORITHMS
from app.core.run_result import MISSING_TEXT
from app.ui.app_state import AppState

#: Role the item's numeric sort value is stored under.
SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 1

#: Role an item's own key (image-set path, algorithm key) is stored under.
KEY_ROLE = int(Qt.ItemDataRole.UserRole) + 2


class NumericItem(QTableWidgetItem):
    """A table cell that sorts by a number while showing formatted text.

    Sorting the displayed text would put ``"10"`` before ``"9"`` and would put
    every ``"-"`` in the middle of the numbers, so the value is kept separately
    and used for the comparison.
    """

    def __init__(self, text: str, value: Any) -> None:
        """Create a cell.

        Args:
            text: What the cell shows.
            value: What the cell sorts by.  Anything that is not a finite number
                sorts last.
        """
        super().__init__(text)
        self.setData(SORT_ROLE, _sortable(value))
        self.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        # Standard Fluent 2 data grid: Right-align numbers, left-align text
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            self.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        """Compare two cells by their stored sort value."""
        mine = self.data(SORT_ROLE)
        theirs = other.data(SORT_ROLE)
        if mine is None or theirs is None:
            return super().__lt__(other)
        return bool(mine < theirs)


def _sortable(value: Any) -> float:
    """Turn any cell value into a float that can be ordered.

    Args:
        value: Raw cell value.

    Returns:
        The number itself, or ``+inf`` so that unknown values sort last.
    """
    if value is None:
        return math.inf
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return math.inf if math.isnan(float(value)) else float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return math.inf
    return math.inf


def make_table(headers: Sequence[str], tooltips: Sequence[str] = ()) -> QTableWidget:
    """Create a read-only, sortable table with the shared look.

    Args:
        headers: Column headers.
        tooltips: Optional explanation per column.

    Returns:
        The configured table.
    """
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table.horizontalHeader().setStretchLastSection(True)
    table.setWordWrap(False)

    for column, tooltip in enumerate(tooltips):
        header_item = table.horizontalHeaderItem(column)
        if header_item is not None and tooltip:
            header_item.setToolTip(tooltip)
    return table


def fill_table(
    table: QTableWidget,
    rows: Sequence[Sequence[tuple[str, Any]]],
    keys: Sequence[str] = (),
) -> None:
    """Replace the contents of a table.

    Args:
        table: Table to fill.
        rows: One row per entry; each cell is a ``(text, sort value)`` pair.
        keys: Optional identifier per row, stored on the first cell so a
            selection handler can tell which entry was clicked.
    """
    # Sorting is switched off while filling: with it on, every inserted row
    # would be re-sorted immediately and the cells would land in wrong rows.
    table.setSortingEnabled(False)
    table.clearContents()
    table.setRowCount(len(rows))

    for row_index, row in enumerate(rows):
        for column, (text, value) in enumerate(row):
            item = NumericItem(text, value)
            if column == 0 and row_index < len(keys):
                item.setData(KEY_ROLE, keys[row_index])
            table.setItem(row_index, column, item)

    table.setSortingEnabled(True)
    table.resizeColumnsToContents()


def selected_key(table: QTableWidget) -> Optional[str]:
    """Identifier stored on the selected row, if any."""
    items = table.selectedItems()
    if not items:
        return None
    first = table.item(items[0].row(), 0)
    if first is None:
        return None
    key = first.data(KEY_ROLE)
    return str(key) if key is not None else None


def text_cell(text: str) -> tuple[str, Any]:
    """Build a cell that sorts alphabetically by its own text."""
    return text, text


def number_cell(value: Any, decimals: int = 3, suffix: str = "") -> tuple[str, Any]:
    """Build a numeric cell with a fixed number of decimals.

    Args:
        value: The number, or ``None``/``nan`` for an unknown value.
        decimals: Digits after the decimal point.
        suffix: Text appended after the number, for example a unit.

    Returns:
        A ``(text, sort value)`` pair.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return MISSING_TEXT, None
    return f"{float(value):.{decimals}f}{suffix}", float(value)


def integer_cell(value: Any, suffix: str = "") -> tuple[str, Any]:
    """Build a whole-number cell."""
    if value is None:
        return MISSING_TEXT, None
    return f"{int(value)}{suffix}", int(value)


def refresh_dataset_combo(combo: QComboBox, state: AppState) -> None:
    """Refill a drop-down with the loaded image sets, keeping the selection.

    Args:
        combo: Drop-down to refill.  Item data holds the image-set key.
        state: Application state to read the image sets from.
    """
    previous = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for dataset in state.datasets:
        label = dataset.label
        if dataset.speed is not None:
            label = f"{dataset.label}  (speed {dataset.speed})"
        combo.addItem(label, dataset.key)
    combo.blockSignals(False)

    index = combo.findData(previous)
    combo.setCurrentIndex(index if index >= 0 else (0 if combo.count() else -1))


def refresh_algorithm_combo(combo: QComboBox, keys: Iterable[str]) -> None:
    """Refill a drop-down with algorithms, keeping the selection.

    Args:
        combo: Drop-down to refill.  Item data holds the algorithm key.
        keys: Algorithm keys to offer, in display order.
    """
    previous = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for key in keys:
        spec = ALGORITHMS.get(key)
        combo.addItem(spec.display_name if spec else key, key)
    combo.blockSignals(False)

    index = combo.findData(previous)
    combo.setCurrentIndex(index if index >= 0 else (0 if combo.count() else -1))


def make_check_list(height: int = 150) -> QListWidget:
    """Create a list whose entries carry a check box.

    Args:
        height: Minimum height in pixels.

    Returns:
        The configured list.
    """
    widget = QListWidget()
    widget.setMinimumHeight(height)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    return widget


def set_check_items(
    widget: QListWidget,
    entries: Sequence[tuple[str, str]],
    checked: Optional[Iterable[str]] = None,
) -> None:
    """Refill a checkable list, keeping which entries were checked.

    Args:
        widget: List to refill.
        entries: ``(key, label)`` pairs.
        checked: Keys to tick.  When ``None``, whatever was ticked before stays
            ticked, and brand-new entries start ticked.
    """
    previously_checked = set(checked) if checked is not None else set(checked_keys(widget))
    is_first_fill = widget.count() == 0 and checked is None
    known = {widget.item(row).data(KEY_ROLE) for row in range(widget.count())}

    widget.clear()
    for key, label in entries:
        item = QListWidgetItem(label)
        item.setData(KEY_ROLE, key)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        should_check = key in previously_checked or (key not in known and checked is None)
        if is_first_fill:
            should_check = True
        item.setCheckState(
            Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
        )
        widget.addItem(item)


def checked_keys(widget: QListWidget) -> list[str]:
    """Keys of every ticked entry, in list order."""
    keys: list[str] = []
    for row in range(widget.count()):
        item = widget.item(row)
        if item.checkState() == Qt.CheckState.Checked:
            key = item.data(KEY_ROLE)
            if key is not None:
                keys.append(str(key))
    return keys


def set_all_checked(widget: QListWidget, checked: bool) -> None:
    """Tick or untick every entry of a checkable list."""
    state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
    for row in range(widget.count()):
        widget.item(row).setCheckState(state)


def monospace_font(point_size: int = 9) -> QFont:
    """A fixed-width font, so numbers line up in the info panels."""
    font = QFont("monospace", point_size)
    font.setStyleHint(QFont.StyleHint.TypeWriter)
    return font


class InfoPanel(QWidget):
    """A clean, readable monospaced panel of label-and-value lines with comfortable spacing.

    Used wherever a tab has to state numbers precisely, such as the coarse and
    fine positions in the Results tab.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Create an empty panel."""
        super().__init__(parent)
        self._label = QLabel("")
        self._label.setFont(monospace_font())
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self._label.setWordWrap(False)
        self._label.setStyleSheet("line-height: 1.3; font-size: 11px; border: none; background: transparent;")

        area = QScrollArea()
        area.setWidget(self._label)
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(area)
        self.setMinimumHeight(200)

    def set_lines(self, lines: Sequence[str]) -> None:
        """Show a block of text, one entry per line."""
        self._label.setText("\n".join(lines))

    def clear(self) -> None:
        """Empty the panel."""
        self._label.setText("")
