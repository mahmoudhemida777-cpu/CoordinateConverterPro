from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame

from ui.i18n import tr


def _card(title: str, subtitle: str) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background-color: #1F3864; border-radius: 6px; padding: 16px; }"
    )
    layout = QVBoxLayout(frame)
    t = QLabel(title)
    t.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
    s = QLabel(subtitle)
    s.setStyleSheet("color: #C9A227; font-size: 11px;")
    layout.addWidget(t)
    layout.addWidget(s)
    return frame


class DashboardPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel(tr("Dashboard"))
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1F3864;")
        layout.addWidget(title)

        subtitle = QLabel("Coordinate Converter Pro — Any CRS to Any CRS")
        subtitle.setStyleSheet("color: #777; margin-bottom: 16px;")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.addWidget(_card("Import", "KMZ · KML · CSV · XLSX"), 0, 0)
        grid.addWidget(_card("CRS Converter", "Any CRS → Any CRS via PROJ/pyproj"), 0, 1)
        grid.addWidget(_card("Batch Converter", "Convert an entire folder at once"), 1, 0)
        grid.addWidget(_card("Export", "XLSX · CSV · DXF (AutoCAD / Civil 3D)"), 1, 1)
        layout.addLayout(grid)

        hint = QLabel(
            "Use the CRS Converter page to select a file, pick a source and "
            "target CRS by searching name / EPSG code / country / datum, "
            "then click CONVERT."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; margin-top: 24px;")
        layout.addWidget(hint)
