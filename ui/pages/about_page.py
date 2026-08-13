from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

APP_VERSION = "1.1.0"
APP_NAME = "MH GeoSuite Pro"
TAGLINE = "Professional Surveying & Geospatial Engineering Suite"


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1F3864;")
        layout.addWidget(title)
        tagline = QLabel(TAGLINE)
        tagline.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(tagline)
        version = QLabel(f"Version {APP_VERSION}")
        version.setStyleSheet("color: #777; margin-top: 8px;")
        layout.addWidget(version)

        try:
            from core.crs.engine import CRSEngine
            proj_ver = CRSEngine().proj_version()
        except Exception:
            proj_ver = "unavailable"

        info = QLabel(
            f"CRS Engine: pyproj / PROJ {proj_ver}\n"
            "UI Framework: PySide6 (Qt for Python)\n"
            "License: Commercial\n"
            "Developed by Mahmoud Hemida\n"
            "© 2026 Mahmoud Hemida"
        )
        info.setStyleSheet("color: #555; margin-top: 16px;")
        layout.addWidget(info)
        layout.addStretch()
