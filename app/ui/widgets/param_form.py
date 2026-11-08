"""Builds an editor form out of a list of parameter specifications.

Each algorithm declares its parameters as :class:`~app.core.algorithms.ParamSpec`
entries.  This widget turns that list into the matching editors, so adding a
parameter to an algorithm needs no change in the GUI code at all.

Main contents:
    * :class:`ParamForm` -- the generated form, with "Reset defaults".
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.algorithms import ParamSpec

LOGGER = logging.getLogger(__name__)

#: Bounds used when a numeric specification leaves them open.
_INT_LIMITS = (-1_000_000, 1_000_000)
_FLOAT_LIMITS = (-1.0e9, 1.0e9)


class ParamForm(QWidget):
    """An editor per parameter, generated from the specifications.

    Signals:
        values_changed: Any editor changed; carries the full value dictionary.
    """

    values_changed = Signal(dict)

    def __init__(
        self,
        specs: Sequence[ParamSpec] = (),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._specs: tuple[ParamSpec, ...] = ()
        self._editors: dict[str, QWidget] = {}

        self._form_layout = QFormLayout()
        self._form_layout.setContentsMargins(2, 4, 2, 4)
        self._form_layout.setHorizontalSpacing(10)
        self._form_layout.setVerticalSpacing(7)
        self._form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._empty_label = QLabel("This algorithm has no parameters.")
        self._empty_label.setStyleSheet("color: #757575; font-style: italic; font-size: 11px;")
        self._empty_label.setEnabled(False)

        self._reset_button = QPushButton("Reset defaults")
        self._reset_button.setToolTip("Put every parameter back to its default value.")
        self._reset_button.setFixedHeight(26)
        self._reset_button.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                padding: 3px 10px;
                background-color: #fafafa;
                border: 1px solid #d5d5d5;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #0067c0;
            }
        """)
        self._reset_button.clicked.connect(self.reset_defaults)

        self._build_layout()
        self.set_specs(specs)

    def _build_layout(self) -> None:
        """Stack the generated form above the reset button."""
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addStretch(1)
        button_row.addWidget(self._reset_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._empty_label)
        layout.addLayout(self._form_layout)
        layout.addLayout(button_row)

    # ------------------------------------------------------------------ setup

    def set_specs(self, specs: Sequence[ParamSpec]) -> None:
        """Replace the form with editors for a new set of parameters.

        Args:
            specs: Parameters to show.
        """
        self._clear_editors()
        self._specs = tuple(specs)
        self._empty_label.setVisible(not self._specs)

        for spec in self._specs:
            editor = self._build_editor(spec)
            if editor is None:
                continue
            editor.setToolTip(spec.tooltip)
            label = QLabel(spec.label)
            label.setStyleSheet("color: #424242; font-size: 11px; font-weight: 500;")
            label.setToolTip(spec.tooltip)
            self._form_layout.addRow(label, editor)
            self._editors[spec.name] = editor

        self._reset_button.setVisible(bool(self._specs))

    def _clear_editors(self) -> None:
        """Remove every row of the form."""
        while self._form_layout.rowCount():
            self._form_layout.removeRow(0)
        self._editors.clear()

    def _build_editor(self, spec: ParamSpec) -> Optional[QWidget]:
        """Create the editor that matches one specification.

        Args:
            spec: The parameter to build an editor for.

        Returns:
            The editor, or ``None`` when the kind is unknown.
        """
        if spec.kind == "int":
            return self._build_int(spec)
        if spec.kind == "float":
            return self._build_float(spec)
        if spec.kind == "bool":
            return self._build_bool(spec)
        if spec.kind == "choice":
            return self._build_choice(spec)

        LOGGER.error("Parameter '%s' has the unknown kind '%s'.", spec.name, spec.kind)
        return None

    def _build_int(self, spec: ParamSpec) -> QSpinBox:
        """Create a whole-number editor."""
        editor = QSpinBox()
        low = int(spec.minimum) if spec.minimum is not None else _INT_LIMITS[0]
        high = int(spec.maximum) if spec.maximum is not None else _INT_LIMITS[1]
        editor.setRange(low, high)
        editor.setSingleStep(int(spec.step or 1))
        editor.setValue(int(spec.default))
        editor.valueChanged.connect(self._emit_values)
        return editor

    def _build_float(self, spec: ParamSpec) -> QDoubleSpinBox:
        """Create a decimal-number editor."""
        editor = QDoubleSpinBox()
        low = float(spec.minimum) if spec.minimum is not None else _FLOAT_LIMITS[0]
        high = float(spec.maximum) if spec.maximum is not None else _FLOAT_LIMITS[1]
        editor.setDecimals(spec.decimals)
        editor.setRange(low, high)
        editor.setSingleStep(float(spec.step or 1.0))
        editor.setValue(float(spec.default))
        editor.valueChanged.connect(self._emit_values)
        return editor

    def _build_bool(self, spec: ParamSpec) -> QCheckBox:
        """Create a switch."""
        editor = QCheckBox()
        editor.setChecked(bool(spec.default))
        editor.toggled.connect(self._emit_values)
        return editor

    def _build_choice(self, spec: ParamSpec) -> QComboBox:
        """Create a drop-down of fixed options."""
        editor = QComboBox()
        editor.addItems(list(spec.choices))
        if spec.default in spec.choices:
            editor.setCurrentIndex(list(spec.choices).index(spec.default))
        editor.currentTextChanged.connect(self._emit_values)
        return editor

    # ------------------------------------------------------------------ values

    def values(self) -> dict[str, Any]:
        """Current value of every parameter.

        Returns:
            A ``{parameter name: value}`` dictionary, typed as the
            specification declared it.
        """
        collected: dict[str, Any] = {}
        for spec in self._specs:
            editor = self._editors.get(spec.name)
            if editor is None:
                collected[spec.name] = spec.default
            elif isinstance(editor, (QSpinBox, QDoubleSpinBox)):
                # Both spin boxes answer value(); the int one returns an int.
                collected[spec.name] = editor.value()
            elif isinstance(editor, QCheckBox):
                collected[spec.name] = editor.isChecked()
            elif isinstance(editor, QComboBox):
                collected[spec.name] = editor.currentText()
        return collected

    def set_values(self, values: Mapping[str, Any]) -> None:
        """Load values into the editors, ignoring names the form does not have.

        Args:
            values: ``{parameter name: value}``, for example from a session file.
        """
        for name, value in values.items():
            editor = self._editors.get(name)
            if editor is None:
                continue
            # Signals are blocked so that loading a whole set of values emits
            # one change at the end instead of one per editor.
            editor.blockSignals(True)
            try:
                self._apply_value(editor, value)
            except (TypeError, ValueError) as exc:
                LOGGER.warning("Ignoring the value of '%s': %s", name, exc)
            finally:
                editor.blockSignals(False)
        self._emit_values()

    @staticmethod
    def _apply_value(editor: QWidget, value: Any) -> None:
        """Write one value into one editor.

        Raises:
            TypeError: If the value does not fit the editor.
            ValueError: If the value cannot be converted.
        """
        if isinstance(editor, QSpinBox):
            editor.setValue(int(value))
        elif isinstance(editor, QDoubleSpinBox):
            editor.setValue(float(value))
        elif isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))
        elif isinstance(editor, QComboBox):
            editor.setCurrentText(str(value))

    def reset_defaults(self) -> None:
        """Put every editor back to the default from its specification."""
        self.set_values({spec.name: spec.default for spec in self._specs})

    def _emit_values(self) -> None:
        """Announce the current values to whoever is listening."""
        self.values_changed.emit(self.values())
