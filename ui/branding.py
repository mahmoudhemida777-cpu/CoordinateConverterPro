from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

NAVY = QColor("#1F3864")
GOLD = QColor("#C9A227")
WHITE = QColor("#FFFFFF")
LIGHT = QColor("#F4F6F9")


def create_logo_pixmap(size: int = 256) -> QPixmap:
    """Create the MH GeoSuite Pro brand mark without external image files."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    margin = size * 0.08
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    p.setBrush(NAVY)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect, size * 0.14, size * 0.14)

    cx = cy = size / 2
    radius = size * 0.30
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(GOLD, max(3, size * 0.025)))
    p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

    p.setPen(QPen(WHITE, max(3, size * 0.018)))
    p.drawLine(cx - radius * 0.82, cy, cx + radius * 0.82, cy)
    p.drawLine(cx, cy - radius * 0.82, cx, cy + radius * 0.82)

    # Surveying / geospatial diamond pointer.
    p.setBrush(GOLD)
    p.setPen(Qt.PenStyle.NoPen)
    points = [
        (cx, cy - radius * 0.72),
        (cx + radius * 0.22, cy),
        (cx, cy + radius * 0.72),
        (cx - radius * 0.22, cy),
    ]
    from PySide6.QtGui import QPolygonF
    from PySide6.QtCore import QPointF
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    p.end()
    return px


def app_icon() -> QIcon:
    return QIcon(create_logo_pixmap(256))


def create_splash_pixmap(width: int = 760, height: int = 430) -> QPixmap:
    """Create the startup screen used while the application initializes."""
    px = QPixmap(width, height)
    px.fill(LIGHT)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Header panel.
    p.setBrush(NAVY)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(0, 0, width, int(height * 0.67))

    logo = create_logo_pixmap(170)
    p.drawPixmap(int(width / 2 - 85), 48, logo)

    p.setPen(WHITE)
    font = p.font(); font.setPointSize(25); font.setBold(True); p.setFont(font)
    p.drawText(QRectF(0, 225, width, 40), Qt.AlignmentFlag.AlignCenter, "MH GeoSuite Pro")

    p.setPen(QColor("#DDE6F4"))
    font = p.font(); font.setPointSize(11); font.setBold(False); p.setFont(font)
    p.drawText(QRectF(0, 270, width, 28), Qt.AlignmentFlag.AlignCenter, "Professional Surveying & Geospatial Engineering Suite")

    p.setPen(NAVY)
    font = p.font(); font.setPointSize(11); font.setBold(True); p.setFont(font)
    p.drawText(QRectF(45, 318, width - 90, 28), Qt.AlignmentFlag.AlignLeft, "Initializing workspace...")

    p.setBrush(QColor("#D9DEE7"))
    p.drawRoundedRect(QRectF(45, 360, width - 90, 9), 4, 4)
    p.setBrush(GOLD)
    p.drawRoundedRect(QRectF(45, 360, (width - 90) * 0.62, 9), 4, 4)

    p.setPen(QColor("#6B7280"))
    font = p.font(); font.setPointSize(9); font.setBold(False); p.setFont(font)
    p.drawText(QRectF(45, 382, width - 90, 22), Qt.AlignmentFlag.AlignLeft, "CRS Engine  •  PROJ  •  CAD / Civil 3D")
    p.end()
    return px
