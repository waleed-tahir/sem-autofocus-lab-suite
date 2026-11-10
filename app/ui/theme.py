"""Fluent theme and styles for PySide6."""

from __future__ import annotations

from app.ui.icons import get_icon_path


def build_qss() -> str:
    chevron_down = get_icon_path("chevron_down.png")
    chevron_down_hover = get_icon_path("chevron_down_hover.png")
    chevron_up = get_icon_path("chevron_up.png")
    chevron_up_hover = get_icon_path("chevron_up_hover.png")
    checkmark = get_icon_path("checkmark.png")

    return f"""
/* ==========================================================================
   Fluent Desktop Theme for PySide6 / Qt
   Optimized for Native Desktop Displays
   ========================================================================== */

/* Base font and text color only - DO NOT set a global background color on QWidget!
   In Qt, setting background-color on generic QWidget causes every child QWidget,
   QLabel, QScrollArea, container, and form row to paint an opaque grey rectangle. */
QWidget {{
    color: #1c1c1c;
    font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 12px;
}}

QMainWindow {{
    background-color: #f3f3f3;
}}

/* Base canvas fill for tab contents and dialogs */
QDialog {{
    background-color: #f3f3f3;
}}

/* Ensure transparent backgrounds and no borders for labels, scroll widgets, and intermediate layouts */
QLabel, QFrame QLabel {{
    background-color: transparent;
    border: none;
    outline: none;
}}

QScrollArea {{
    background-color: transparent;
    border: none;
}}

/* Segmented Navigation Bar */
QTabWidget#mainTabs::pane {{
    border: 1px solid #e5e5e5;
    background-color: #ffffff;
    top: -1px;
    border-radius: 6px;
}}

QTabWidget#mainTabs > QTabBar::tab {{
    background: transparent;
    color: #5e5e5e;
    padding: 8px 18px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid transparent;
}}

QTabWidget#mainTabs > QTabBar::tab:hover {{
    background: rgba(0, 0, 0, 0.04);
    color: #1c1c1c;
}}

QTabWidget#mainTabs > QTabBar::tab:selected {{
    background: #ffffff;
    color: #0067c0;
    font-weight: 600;
    border: 1px solid #e5e5e5;
    border-bottom: 2px solid #0067c0;
}}

/* Sub-tabs / Nested Tabs (Pill style) */
QTabWidget#subTabs::pane {{
    border: none;
    background-color: transparent;
}}

QTabWidget#subTabs > QTabBar::tab {{
    background: #ebebeb;
    color: #5e5e5e;
    padding: 6px 16px;
    margin-right: 4px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 6px;
    border: 1px solid transparent;
}}

QTabWidget#subTabs > QTabBar::tab:hover {{
    background: #e2e2e2;
    color: #1c1c1c;
}}

QTabWidget#subTabs > QTabBar::tab:selected {{
    background: #0067c0;
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #005a9e;
}}

/* Push Buttons */
QPushButton {{
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 5px 14px;
    font-weight: 500;
    color: #1c1c1c;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: #f8f8f8;
    border-color: #bcbcbc;
}}

QPushButton:pressed {{
    background-color: #f0f0f0;
    border-color: #a0a0a0;
}}

QPushButton:checked {{
    background-color: #ebf3fc;
    border: 1.5px solid #0067c0;
    color: #0067c0;
    font-weight: 600;
}}

QPushButton:disabled {{
    background-color: #f9f9f9;
    border-color: #e5e5e5;
    color: #a6a6a6;
}}

QPushButton#primaryButton, QPushButton[accent="true"] {{
    background-color: #0067c0;
    color: #ffffff;
    border: 1px solid #005a9e;
    font-weight: 600;
}}

QPushButton#primaryButton:hover, QPushButton[accent="true"]:hover {{
    background-color: #005a9e;
}}

QPushButton#primaryButton:pressed, QPushButton[accent="true"]:pressed {{
    background-color: #004c87;
}}

QPushButton#primaryButton:disabled, QPushButton[accent="true"]:disabled {{
    background-color: #9ac2e6;
    border: 1px solid #8ab8df;
    color: #ffffff;
}}

/* Authentic ComboBox */
QComboBox {{
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 4px 10px;
    padding-right: 26px;
    color: #1c1c1c;
    min-height: 22px;
    font-size: 12px;
}}

QComboBox:hover {{
    border-color: #9d9d9d;
    background-color: #fafafa;
}}

QComboBox:focus {{
    border: 1px solid #0067c0;
    border-bottom: 2px solid #0067c0;
    background-color: #ffffff;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

QComboBox::down-arrow {{
    image: url({chevron_down});
    width: 14px;
    height: 14px;
}}

QComboBox QAbstractItemView,
QComboBox QListView {{
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #ebf3fc;
    selection-color: #0067c0;
    outline: none;
}}

QComboBox QAbstractItemView::item,
QComboBox QListView::item {{
    min-height: 26px;
    padding: 4px 10px;
    color: #1e293b;
    background-color: #ffffff;
    border-radius: 4px;
}}

QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover {{
    background-color: #f1f5f9;
    color: #0f172a;
}}

QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected {{
    background-color: #ebf3fc;
    color: #0067c0;
    font-weight: 600;
}}

/* Authentic Fluent QSpinBox & QDoubleSpinBox */
QSpinBox, QDoubleSpinBox,
QFrame#contentFrame QSpinBox, QFrame#contentFrame QDoubleSpinBox {{
    background-color: #ffffff;
    border: 1px solid #d1d1d1;
    border-radius: 4px;
    padding: 3px 22px 3px 8px;
    color: #1c1c1c;
    min-height: 24px;
    font-size: 11.5px;
}}

QSpinBox:hover, QDoubleSpinBox:hover,
QFrame#contentFrame QSpinBox:hover, QFrame#contentFrame QDoubleSpinBox:hover {{
    border: 1px solid #9d9d9d;
    background-color: #fafafa;
}}

QSpinBox:focus, QDoubleSpinBox:focus,
QFrame#contentFrame QSpinBox:focus, QFrame#contentFrame QDoubleSpinBox:focus {{
    border: 1px solid #0067c0;
    border-bottom: 2px solid #0067c0;
    background-color: #ffffff;
}}

QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{
    background-color: transparent;
    border: none;
    color: #1c1c1c;
    padding: 0;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    margin: 1px 1px 0px 0px;
    border: none;
    border-left: 1px solid #e5e5e5;
    border-bottom: 1px solid #f0f0f0;
    border-top-right-radius: 3px;
    background-color: #fafafa;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
    background-color: #f0f0f0;
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
    background-color: #e5e5e5;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({chevron_up});
    width: 8px;
    height: 8px;
}}

QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    image: url({chevron_up_hover});
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    width: 18px;
    margin: 0px 1px 1px 0px;
    border: none;
    border-left: 1px solid #e5e5e5;
    border-bottom-right-radius: 3px;
    background-color: #fafafa;
}}

QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: #f0f0f0;
}}

QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: #e5e5e5;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url({chevron_down});
    width: 8px;
    height: 8px;
}}

QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    image: url({chevron_down_hover});
}}

/* Clean Lists & Checkboxes */
QListWidget {{
    background-color: #ffffff;
    border: 1px solid #dcdcdc;
    border-radius: 5px;
    padding: 3px;
    outline: none;
}}

QListWidget::item {{
    padding: 4px 6px;
    border-radius: 3px;
    color: #1c1c1c;
}}

QListWidget::item:hover {{
    background-color: #f3f3f3;
}}

QListWidget::item:selected {{
    background-color: #ebf3fc;
    color: #0067c0;
}}

QCheckBox {{
    spacing: 7px;
    font-size: 12px;
    background-color: transparent;
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #a0a0a0;
    background-color: #ffffff;
}}

QCheckBox::indicator:hover {{
    border-color: #0067c0;
}}

QCheckBox::indicator:checked {{
    background-color: #0067c0;
    border-color: #0067c0;
    image: url({checkmark});
}}

/* Ensure container cards have clean backgrounds */
QFrame#contentFrame {{
    background-color: #ffffff;
    border: 1px solid #dcdcdc;
    border-top: none;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
}}

/* Native Tables */
QTableWidget, QTableView {{
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    gridline-color: #f0f0f0;
    font-size: 11.5px;
    alternate-background-color: #fcfcfc;
}}

QHeaderView::section {{
    background-color: #f7f7f7;
    color: #5e5e5e;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid #e5e5e5;
    border-bottom: 1px solid #e5e5e5;
    font-weight: 600;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: #ebf3fc;
    color: #0067c0;
}}

/* Fluent 2 Modern QGroupBox */
QGroupBox {{
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px;
    font-size: 12px;
    font-weight: 600;
    color: #1c1c1c;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    left: 8px;
    color: #1c1c1c;
    background-color: transparent;
}}

/* Fluent 2 Slider Styling */
QSlider::groove:horizontal {{
    height: 4px;
    background: #d1d1d1;
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: #0067c0;
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid #0067c0;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: #0067c0;
    border: 2px solid #005a9e;
}}

QSlider::handle:horizontal:disabled {{
    background: #cccccc;
    border: 2px solid #cccccc;
}}

/* Fluent 2 Surface Card for Fit Details */
QWidget#fitDetailsCard {{
    background-color: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 6px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: #ebebeb;
    border: none;
    border-radius: 2px;
    text-align: center;
    font-size: 10px;
    color: #5e5e5e;
}}

QProgressBar::chunk {{
    background-color: #0067c0;
    border-radius: 2px;
}}

/* Splitters */
QSplitter::handle {{
    background-color: #e5e5e5;
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: #f7f7f7;
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #cdcdcd;
    min-height: 24px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: #a6a6a6;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #f7f7f7;
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: #cdcdcd;
    min-width: 24px;
    border-radius: 4px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #a6a6a6;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def apply_theme(app) -> None:
    """Apply the Fluent QSS stylesheet and light palette to the application."""
    from PySide6.QtGui import QColor, QPalette
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0067c0"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    app.setStyleSheet(build_qss())

