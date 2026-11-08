"""Fluent Icon and SVG asset generator.

Generates clean, native vector icons (chevrons, playback controls, navigation arrows)
without relying on OS emojis or missing fonts.
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICONS_DIR = Path(__file__).parent / "assets" / "icons"


def ensure_icon_assets() -> None:
    """Generate clean PNG icon assets for QSS and UI buttons."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    _save_chevron("chevron_down.png", direction="down", color="#5e5e5e")
    _save_chevron("chevron_down_hover.png", direction="down", color="#1c1c1c")
    _save_chevron("chevron_down_active.png", direction="down", color="#0067c0")

    _save_chevron("chevron_up.png", direction="up", color="#5e5e5e")
    _save_chevron("chevron_up_hover.png", direction="up", color="#1c1c1c")
    _save_chevron("chevron_up_active.png", direction="up", color="#0067c0")

    _save_chevron("chevron_right.png", direction="right", color="#5e5e5e")
    _save_chevron("chevron_right_hover.png", direction="right", color="#0067c0")

    _save_checkmark("checkmark.png", color="#ffffff")

    # Fluent Playback and Navigation Icons
    _save_play("play.png", color="#1c1c1c")
    _save_pause("pause.png", color="#1c1c1c")
    _save_step("step_forward.png", color="#1c1c1c")
    _save_reset("reset_view.png", color="#1c1c1c")
    _save_arrow("prev_frame.png", direction="left", color="#1c1c1c")
    _save_arrow("next_frame.png", direction="right", color="#1c1c1c")


def _save_checkmark(filename: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(QPointF(4.0, 8.5), QPointF(6.8, 11.5))
    p.drawLine(QPointF(6.8, 11.5), QPointF(12.0, 4.5))
    p.end()
    pm.save(str(target), "PNG")


def _save_chevron(filename: str, direction: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if direction == "down":
        p.drawLine(QPointF(4.5, 6.5), QPointF(8.0, 10.0))
        p.drawLine(QPointF(8.0, 10.0), QPointF(11.5, 6.5))
    elif direction == "up":
        p.drawLine(QPointF(4.5, 9.5), QPointF(8.0, 6.0))
        p.drawLine(QPointF(8.0, 6.0), QPointF(11.5, 9.5))
    elif direction == "right":
        p.drawLine(QPointF(6.5, 4.5), QPointF(10.0, 8.0))
        p.drawLine(QPointF(10.0, 8.0), QPointF(6.5, 11.5))

    p.end()
    pm.save(str(target), "PNG")


def _save_play(filename: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.moveTo(5.0, 3.5)
    path.lineTo(12.5, 8.0)
    path.lineTo(5.0, 12.5)
    path.closeSubpath()
    p.fillPath(path, QBrush(QColor(color)))
    p.end()
    pm.save(str(target), "PNG")


def _save_pause(filename: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(4.0, 3.5, 2.8, 9.0), 0.8, 0.8)
    p.drawRoundedRect(QRectF(9.2, 3.5, 2.8, 9.0), 0.8, 0.8)
    p.end()
    pm.save(str(target), "PNG")


def _save_step(filename: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.moveTo(4.0, 3.5)
    path.lineTo(10.5, 8.0)
    path.lineTo(4.0, 12.5)
    path.closeSubpath()
    p.fillPath(path, QBrush(QColor(color)))
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(11.5, 3.5, 2.0, 9.0), 0.6, 0.6)
    p.end()
    pm.save(str(target), "PNG")


def _save_reset(filename: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    path = QPainterPath()
    path.arcMoveTo(QRectF(3.0, 3.0, 10.0, 10.0), 60)
    path.arcTo(QRectF(3.0, 3.0, 10.0, 10.0), 60, 270)
    p.drawPath(path)
    p.drawLine(QPointF(8.0, 2.0), QPointF(8.0, 4.5))
    p.drawLine(QPointF(8.0, 2.0), QPointF(10.5, 2.0))
    p.end()
    pm.save(str(target), "PNG")


def _save_arrow(filename: str, direction: str, color: str, size: int = 16) -> None:
    target = ICONS_DIR / filename
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    if direction == "left":
        p.drawLine(QPointF(10.0, 4.0), QPointF(5.5, 8.0))
        p.drawLine(QPointF(5.5, 8.0), QPointF(10.0, 12.0))
    elif direction == "right":
        p.drawLine(QPointF(6.0, 4.0), QPointF(10.5, 8.0))
        p.drawLine(QPointF(10.5, 8.0), QPointF(6.0, 12.0))
    p.end()
    pm.save(str(target), "PNG")


def get_icon_path(filename: str) -> str:
    """Get forward-slash normalized absolute path of an icon asset."""
    ensure_icon_assets()
    return str((ICONS_DIR / filename).resolve()).replace("\\", "/")


def get_fluent_icon(filename: str) -> QIcon:
    """Return a native QIcon from generated asset."""
    path = get_icon_path(filename)
    return QIcon(path)
