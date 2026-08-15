from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox

from core.version import APP_VERSION

APP_NAME = "MH GeoSuite Pro"
TAGLINE = "Professional Surveying & Geospatial Engineering Suite"
LINKEDIN_URL = "https://www.linkedin.com/in/mahmoud-abdelbasit/en/"
EMAIL = "mahmoudhemida777@gmail.com"


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

        contact = QLabel(
            f"Support / Contact: {EMAIL}\n"
            f"LinkedIn: {LINKEDIN_URL}"
        )
        contact.setStyleSheet("color: #333; margin-top: 16px;")
        contact.setOpenExternalLinks(True)
        layout.addWidget(contact)

        linkedin = QPushButton("Open LinkedIn Profile")
        linkedin.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(LINKEDIN_URL)))
        layout.addWidget(linkedin)

        check = QPushButton("Check for Updates")
        check.clicked.connect(self._check_updates)
        layout.addWidget(check)
        layout.addStretch()

    def _check_updates(self) -> None:
        try:
            from core.updater import check_for_update
            update = check_for_update(APP_VERSION)
        except Exception:
            update = None
        if update:
            QMessageBox.information(self, "Update Available", f"Version {update[0]} is available. Restart the application to install it automatically.")
        else:
            QMessageBox.information(self, "MH GeoSuite Pro", "You are using the latest available version.")
