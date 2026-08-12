"""
Coordinate Converter Pro — application entry point.

NOTE ON TESTING: PySide6 is not installable in the offline sandbox this
project was authored in. This file and everything under ui/ follow the
standard PySide6 QApplication/QMainWindow pattern but have not been
executed locally. The GitHub Actions Windows-runner workflow installs
PySide6 from PyPI and runs the smoke test (scripts/smoke_test.py) that
actually launches this entry point — treat that as the first real
execution of the GUI layer.
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
logger = logging.getLogger("CoordinateConverterPro")


def main() -> int:
    logger.info("Starting Coordinate Converter Pro")
    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow
    except ImportError as exc:
        logger.exception("Failed to import PySide6/UI layer: %s", exc)
        raise

    app = QApplication(sys.argv)
    app.setApplicationName("Coordinate Converter Pro")
    app.setOrganizationName("CoordinateConverterPro")

    window = MainWindow()
    window.show()

    logger.info("Main window shown, entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
