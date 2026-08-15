"""
MH GeoSuite Pro — application entry point.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("MHGeoSuitePro")


def _smoke_test() -> int:
    """Validate critical frozen imports before starting the GUI."""
    import numpy  # noqa: F401
    import ezdxf  # noqa: F401
    import pandas  # noqa: F401
    import pyproj  # noqa: F401
    import openpyxl  # noqa: F401
    from ui.main_window import MainWindow  # noqa: F401
    from core.updater import check_for_update  # noqa: F401
    return 0


def main() -> int:
    if "--smoke-test" in sys.argv:
        return _smoke_test()

    logger.info("Starting MH GeoSuite Pro")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from PySide6.QtCore import QTimer
        from ui.main_window import MainWindow
        from core.version import APP_VERSION
        from core.updater import check_for_update, install_latest_windows
    except ImportError as exc:
        logger.exception("Failed to import PySide6/UI layer: %s", exc)
        raise

    app = QApplication(sys.argv)
    app.setApplicationName("MH GeoSuite Pro")
    app.setOrganizationName("MHGeoSuitePro")

    window = MainWindow()
    window.show()

    def check_updates() -> None:
        if not getattr(sys, "frozen", False):
            return
        update = check_for_update(APP_VERSION)
        if not update:
            return
        tag, _url = update
        answer = QMessageBox.question(
            window,
            "MH GeoSuite Pro Update",
            f"A new version ({tag}) is available. Update now?\n\nThe program will close, install the update, and restart automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            if install_latest_windows(window):
                app.quit()
            else:
                QMessageBox.warning(window, "Update Failed", "The update could not be installed. You can try again later.")

    QTimer.singleShot(2500, check_updates)
    logger.info("Main window shown, entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
