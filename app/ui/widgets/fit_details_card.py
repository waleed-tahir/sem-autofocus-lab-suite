"""Modern Fluent KPI Summary Card for Quadratic Fit Details.

Replaces the raw plain-text ASCII formula dump with clean, native KPI metric tiles,
dynamic semantic R^2 goodness of fit badges, and Cascadia Code typography.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.core.run_result import RunResult


class FitDetailsCard(QWidget):
    """card displaying structured KPI metrics for sub-frame quadratic fits."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("fitDetailsCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Header info block
        self._header_label = QLabel("No Run Selected")
        self._header_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1c1c1c;")
        layout.addWidget(self._header_label)

        self._meta_label = QLabel("Select an image set and algorithm to view fit metrics.")
        self._meta_label.setStyleSheet("font-size: 11px; color: #5e5e5e;")
        layout.addWidget(self._meta_label)

        # Divider
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("color: #e5e5e5; background: #e5e5e5; max-height: 1px;")
        layout.addWidget(line1)

        # 2. Hero KPI Tile: Refined Working Distance
        hero_tile = QFrame()
        hero_tile.setStyleSheet(
            "background: #f8fbfd; border: 1px solid #cce4f7; border-radius: 6px;"
        )
        hero_layout = QVBoxLayout(hero_tile)
        hero_layout.setContentsMargins(12, 10, 12, 10)
        hero_layout.setSpacing(3)

        lbl_hero = QLabel("REFINED FOCUS WORKING DISTANCE")
        lbl_hero.setStyleSheet("font-size: 9.5px; font-weight: 600; color: #005a9e; letter-spacing: 0.5px; border: none; background: transparent;")
        self._fine_wd_val = QLabel("- mm")
        self._fine_wd_val.setStyleSheet("font-size: 20px; font-weight: 700; color: #0067c0; font-family: 'Segoe UI'; border: none; background: transparent;")
        self._fine_idx_val = QLabel("Sub-frame index: -")
        self._fine_idx_val.setStyleSheet("font-size: 11px; color: #424242; border: none; background: transparent;")

        hero_layout.addWidget(lbl_hero)
        hero_layout.addWidget(self._fine_wd_val)
        hero_layout.addWidget(self._fine_idx_val)
        layout.addWidget(hero_tile)

        # 3. Supporting Metrics Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(self._create_field_label("Coarse peak:"), 0, 0)
        self._coarse_val = QLabel("-")
        self._coarse_val.setStyleSheet("font-size: 11.5px; font-weight: 500; color: #1c1c1c;")
        grid.addWidget(self._coarse_val, 0, 1)

        grid.addWidget(self._create_field_label("Window points:"), 1, 0)
        self._points_val = QLabel("-")
        self._points_val.setStyleSheet("font-size: 11.5px; color: #424242;")
        grid.addWidget(self._points_val, 1, 1)

        grid.addWidget(self._create_field_label("Fit status:"), 2, 0)
        self._status_badge = QLabel("Idle")
        self._status_badge.setStyleSheet(
            "padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #f0f0f0; color: #5e5e5e;"
        )
        grid.addWidget(self._status_badge, 2, 1)
        layout.addLayout(grid)

        # 4. R^2 Quality Bar
        r2_box = QVBoxLayout()
        r2_box.setSpacing(4)
        r2_header = QHBoxLayout()
        r2_header.addWidget(self._create_field_label("R² Correlation Quality:"))
        self._r2_text = QLabel("-")
        self._r2_text.setStyleSheet("font-size: 11px; font-weight: 700; color: #5e5e5e;")
        r2_header.addWidget(self._r2_text, 0, Qt.AlignmentFlag.AlignRight)
        r2_box.addLayout(r2_header)

        self._r2_bar = QProgressBar()
        self._r2_bar.setRange(0, 100)
        self._r2_bar.setValue(0)
        self._r2_bar.setTextVisible(False)
        self._r2_bar.setFixedHeight(4)
        self._r2_bar.setStyleSheet("""
            QProgressBar {
                background-color: #ebebeb;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0067c0;
                border-radius: 2px;
            }
        """)
        r2_box.addWidget(self._r2_bar)
        layout.addLayout(r2_box)

        # 5. Coefficients & Error (Cascadia Code)
        self._math_box = QLabel("")
        self._math_box.setStyleSheet(
            "font-family: 'Cascadia Code', 'Segoe UI Variable', 'Consolas', monospace; "
            "font-size: 10.5px; color: #333333; background: #f7f7f7; "
            "border: 1px solid #e5e5e5; border-radius: 6px; padding: 8px 10px;"
        )
        layout.addWidget(self._math_box)

        layout.addStretch(1)

    def _create_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 11px; color: #5e5e5e;")
        return lbl

    def _apply_r2_style(self, r2: float) -> None:
        """Apply dynamic Fluent 2 semantic colors based on fit quality."""
        if r2 >= 0.95:
            color = "#107c41"  # Success green
        elif r2 >= 0.80:
            color = "#0067c0"  # Accent blue
        elif r2 >= 0.60:
            color = "#d83b01"  # Warning amber
        else:
            color = "#c42b1c"  # Danger red

        self._r2_text.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color};")
        self._r2_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #ebebeb;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)

    def set_result(self, result: Optional[RunResult]) -> None:
        """Populate the card with run result parameters."""
        if result is None:
            self._header_label.setText("No Run Selected")
            self._meta_label.setText("Select an image set and algorithm to view fit metrics.")
            self._fine_wd_val.setText("- mm")
            self._fine_idx_val.setText("Sub-frame index: -")
            self._coarse_val.setText("-")
            self._points_val.setText("-")
            self._status_badge.setText("Idle")
            self._status_badge.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #f0f0f0; color: #616161;")
            self._r2_text.setText("-")
            self._r2_bar.setValue(0)
            self._math_box.setText("")
            return

        self._header_label.setText(result.algorithm)
        self._meta_label.setText(f"{result.dataset_label} • {result.measure}")

        if result.fit_window is None:
            self._fine_wd_val.setText("No Fit Applied")
            self._fine_idx_val.setText("Sub-frame fit not requested")
            self._coarse_val.setText(f"frame {result.coarse_idx} ({result.coarse_wd_mm:.4f} mm)")
            self._points_val.setText("0 points")
            self._status_badge.setText("Skipped")
            self._status_badge.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #fff4ce; color: #795b00;")
            self._r2_text.setText("-")
            self._r2_bar.setValue(0)
            self._math_box.setText("No parabolic fit was requested for this run.")
            return

        lo, hi = result.fit_window
        self._fine_wd_val.setText(f"{result.fine_wd_mm:.5f} mm")
        self._fine_idx_val.setText(f"Sub-frame index: frame {result.fine_idx:.3f}")
        self._coarse_val.setText(f"frame {result.coarse_idx} ({result.coarse_wd_mm:.4f} mm)")
        self._points_val.setText(f"frames {lo}..{hi} ({len(result.fit_points)} points)")

        status = result.fit_status
        if status.startswith("ok"):
            self._status_badge.setText("Optimal (ok)")
            self._status_badge.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #dff6dd; color: #107c41;")
        else:
            self._status_badge.setText(status)
            self._status_badge.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #fde7e9; color: #a80000;")

        r2 = max(0.0, min(1.0, result.fit_r2))
        self._r2_text.setText(f"{r2:.4f} ({r2*100:.1f}%)")
        self._r2_bar.setValue(int(r2 * 100))
        self._apply_r2_style(r2)

        math_text = []
        if result.fit_coeffs is not None:
            a0, a1, a2 = result.fit_coeffs
            math_text.append(f"Parabola: f(d) = A0 + A1·d + A2·d²\n  A0 = {a0:.5g}\n  A1 = {a1:.5g}\n  A2 = {a2:.5g}")
        if result.error_um is not None and not math.isnan(result.error_um):
            math_text.append(f"Residual Error vs Ref: {result.error_um:.3f} µm")

        self._math_box.setText("\n".join(math_text))
