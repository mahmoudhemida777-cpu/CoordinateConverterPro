from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

APP_VERSION = "1.0.0"


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Coordinate Converter Pro")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1F3864;")
        layout.addWidget(title)

        version = QLabel(f"Version {APP_VERSION}")
        version.setStyleSheet("color: #777;")
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
            "© 2026 Coordinate Converter Pro"
        )
        info.setStyleSheet("color: #555; margin-top: 16px;")
        layout.addWidget(info)
        layout.addStretch()
