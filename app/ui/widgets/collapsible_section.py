"""Collapsible Section Widget.

Provides an accordion-style collapsible card with full width, native styling,
and exclusive single-open accordion support.
Uses clean Fluent icons without emoji characters.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import get_icon_path


class CollapsibleSection(QWidget):
    """A clean Fluent collapsible card section."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        content_widget: QWidget,
        initially_expanded: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._content = content_widget
        self._is_expanded = initially_expanded

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._build_ui()
        self.set_expanded(self._is_expanded)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container card wrapping header and content together
        self.card = QFrame()
        self.card.setObjectName("collapsibleCard")
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header button spanning 100% width
        self.header_btn = QPushButton()
        self.header_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header_btn.setFixedHeight(34)
        self.header_btn.setCheckable(True)
        self.header_btn.setChecked(self._is_expanded)
        self.header_btn.clicked.connect(self._on_header_clicked)
        self.header_btn.setIconSize(QSize(14, 14))

        # Content container
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        self.content_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        c_layout = QVBoxLayout(self.content_frame)
        c_layout.setContentsMargins(10, 10, 10, 10)
        c_layout.addWidget(self._content)

        card_layout.addWidget(self.header_btn)
        card_layout.addWidget(self.content_frame)
        layout.addWidget(self.card)

    def _on_header_clicked(self) -> None:
        self.set_expanded(not self._is_expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._is_expanded = expanded
        self.header_btn.setChecked(expanded)
        self.content_frame.setVisible(expanded)

        # Use clean vector icon path without emoji
        icon_file = "chevron_down_active.png" if expanded else "chevron_right.png"
        self.header_btn.setIcon(QIcon(get_icon_path(icon_file)))
        self.header_btn.setText(f"  {self._title}")

        if expanded:
            self.header_btn.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #dcdcdc;
                    border-bottom: 1px solid #e8e8e8;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    background-color: #f7f7f7;
                    color: #0067c0;
                    font-size: 11.5px;
                    font-weight: 600;
                    padding-left: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
                """
            )
            self.content_frame.setStyleSheet(
                """
                QFrame#contentFrame {
                    border: 1px solid #dcdcdc;
                    border-top: none;
                    border-bottom-left-radius: 6px;
                    border-bottom-right-radius: 6px;
                    background-color: #ffffff;
                }
                """
            )
        else:
            self.header_btn.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #dcdcdc;
                    border-radius: 6px;
                    background-color: #ffffff;
                    color: #1c1c1c;
                    font-size: 11.5px;
                    font-weight: 500;
                    padding-left: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #f5f5f5;
                    border-color: #c0c0c0;
                }
                """
            )

        self.toggled.emit(expanded)

    @property
    def is_expanded(self) -> bool:
        return self._is_expanded
