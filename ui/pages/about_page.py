from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox

from core.version import APP_VERSION

APP_NAME = "MH - Coordinate"
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
            from core.updater import check_for_update, install_latest_windows
            import sys

            if not getattr(sys, "frozen", False):
                QMessageBox.information(
                    self,
                    "MH - Coordinate",
                    "Update installation is available in the Windows standalone version."
                )
                return

            update = check_for_update(APP_VERSION)
            if not update:
                QMessageBox.information(
                    self,
                    "MH - Coordinate",
                    "You are using the latest available version."
                )
                return

            version, _page_url = update
            answer = QMessageBox.question(
                self,
                "Update Available",
                f"A new version ({version}) is available.\n\n"
                "Download and install it now? The program will close and restart automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

            if install_latest_windows(self):
                # The updater process waits for this application to exit,
                # replaces the EXE, then starts the updated version.
                from PySide6.QtWidgets import QApplication
                QApplication.instance().quit()
            else:
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    "The update could not be installed. Check your internet connection and try again."
                )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Update Error",
                f"Unable to check for updates.\n\n{exc}"
            )
