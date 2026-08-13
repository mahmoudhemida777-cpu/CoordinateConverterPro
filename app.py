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
    return 0


def main() -> int:
    if "--smoke-test" in sys.argv:
        return _smoke_test()

    logger.info("Starting MH GeoSuite Pro")
    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow
    except ImportError as exc:
        logger.exception("Failed to import PySide6/UI layer: %s", exc)
        raise

    app = QApplication(sys.argv)
    app.setApplicationName("MH GeoSuite Pro")
    app.setOrganizationName("MHGeoSuitePro")

    window = MainWindow()
    window.show()

    logger.info("Main window shown, entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
