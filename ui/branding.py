from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

NAVY = QColor("#1F3864")
GOLD = QColor("#C9A227")
WHITE = QColor("#FFFFFF")
LIGHT = QColor("#F4F6F9")
MUTED = QColor("#6B7280")
APP_NAME = "MH - Coordinate"
TAGLINE = "Professional Surveying & Geospatial Engineering Suite"


def create_logo_pixmap(size: int = 256) -> QPixmap:
    """Create the MH - Coordinate brand mark without external image files."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    margin = size * 0.08
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    p.setBrush(NAVY); p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect, size * 0.14, size * 0.14)
    cx = cy = size / 2; radius = size * 0.30
    p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(GOLD, max(3, size * 0.025)))
    p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
    p.setPen(QPen(WHITE, max(3, size * 0.018)))
    p.drawLine(cx - radius * 0.82, cy, cx + radius * 0.82, cy)
    p.drawLine(cx, cy - radius * 0.82, cx, cy + radius * 0.82)
    p.setBrush(GOLD); p.setPen(Qt.PenStyle.NoPen)
    points = [(cx, cy - radius * 0.72), (cx + radius * 0.22, cy), (cx, cy + radius * 0.72), (cx - radius * 0.22, cy)]
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points])); p.end()
    return px


def app_icon() -> QIcon:
    return QIcon(create_logo_pixmap(256))


def create_splash_pixmap(width: int = 820, height: int = 520) -> QPixmap:
    """Create a spacious startup screen with dedicated readable status/footer areas."""
    px = QPixmap(width, height); px.fill(LIGHT)
    p = QPainter(px); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    header_h = 335
    p.setBrush(NAVY); p.setPen(Qt.PenStyle.NoPen); p.drawRect(0, 0, width, header_h)
    logo_size = 155; p.drawPixmap(int(width / 2 - logo_size / 2), 32, create_logo_pixmap(logo_size))
    p.setPen(WHITE); font = p.font(); font.setPointSize(27); font.setBold(True); p.setFont(font)
    p.drawText(QRectF(30, 205, width - 60, 45), Qt.AlignmentFlag.AlignCenter, APP_NAME)
    p.setPen(QColor("#DDE6F4")); font = p.font(); font.setPointSize(12); font.setBold(False); p.setFont(font)
    p.drawText(QRectF(30, 258, width - 60, 32), Qt.AlignmentFlag.AlignCenter, TAGLINE)
    p.setPen(GOLD); font = p.font(); font.setPointSize(10); font.setBold(True); p.setFont(font)
    p.drawText(QRectF(30, 305, width - 60, 22), Qt.AlignmentFlag.AlignCenter, "SURVEY • GIS • CRS • CAD / CIVIL 3D")

    p.setBrush(WHITE); p.drawRoundedRect(QRectF(28, 365, width - 56, 105), 12, 12)
    p.setPen(NAVY); font = p.font(); font.setPointSize(11); font.setBold(True); p.setFont(font)
    p.drawText(QRectF(52, 382, width - 104, 24), Qt.AlignmentFlag.AlignLeft, "Starting application")
    p.setBrush(QColor("#D9DEE7")); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(QRectF(52, 420, width - 104, 9), 4, 4)
    p.setBrush(GOLD); p.drawRoundedRect(QRectF(52, 420, (width - 104) * 0.62, 9), 4, 4)
    p.setPen(MUTED); font = p.font(); font.setPointSize(9); font.setBold(False); p.setFont(font)
    p.drawText(QRectF(52, 440, width - 104, 20), Qt.AlignmentFlag.AlignLeft, "CRS Engine  •  PROJ  •  CAD / Civil 3D")
    p.setPen(QColor("#8A93A3")); font = p.font(); font.setPointSize(8); font.setBold(False); p.setFont(font)
    p.drawText(QRectF(30, 488, width - 60, 18), Qt.AlignmentFlag.AlignCenter, "© MH - Coordinate")
    p.end(); return px
