"""
MH - Coordinate — application entry point.
"""
from __future__ import annotations

import logging
import math
import sys
import tempfile
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
logger = logging.getLogger("MH-Coordinate")


def _smoke_test() -> int:
    """Run lightweight but real functional checks inside the frozen EXE."""
    import numpy  # noqa: F401
    import ezdxf
    import pandas  # noqa: F401
    import pyproj  # noqa: F401
    import openpyxl  # noqa: F401
    from ui.main_window import MainWindow  # noqa: F401
    from ui.branding import app_icon, create_splash_pixmap  # noqa: F401
    from core.updater import check_for_update  # noqa: F401
    from core.crs.engine import CRSEngine
    from core.models import PointResult
    from core.exporters.dxf_exporter import export_dxf

    engine = CRSEngine()
    source = PointResult("SMOKE-1", 46.6753, 24.7136, 600.0)
    converted = engine.transform_points("EPSG:4326", "EPSG:32638", [source])
    if not converted or converted[0].status != "SUCCESS":
        raise RuntimeError(f"Frozen CRS conversion failed: {converted[0].message if converted else 'no result'}")
    result = converted[0]
    if result.tgt_x is None or result.tgt_y is None:
        raise RuntimeError("Frozen CRS conversion returned empty projected coordinates")

    back = engine.transform_points(
        "EPSG:32638",
        "EPSG:4326",
        [PointResult("SMOKE-1", result.tgt_x, result.tgt_y, result.tgt_z)],
    )
    if not back or back[0].status != "SUCCESS":
        raise RuntimeError(f"Frozen inverse CRS conversion failed: {back[0].message if back else 'no result'}")
    if not math.isclose(back[0].tgt_x, source.src_x, abs_tol=1e-6):
        raise RuntimeError("Frozen longitude round-trip exceeded tolerance")
    if not math.isclose(back[0].tgt_y, source.src_y, abs_tol=1e-6):
        raise RuntimeError("Frozen latitude round-trip exceeded tolerance")

    with tempfile.TemporaryDirectory(prefix="mh_coordinate_smoke_") as tmp:
        dxf_path = Path(tmp) / "smoke.dxf"
        export_dxf(converted, str(dxf_path))
        if not dxf_path.is_file() or dxf_path.stat().st_size <= 0:
            raise RuntimeError("Frozen DXF export did not create a valid file")
        ezdxf.readfile(dxf_path)

    logger.info("Frozen functional smoke test passed: imports + CRS round-trip + DXF export")
    return 0


def main() -> int:
    if "--smoke-test" in sys.argv:
        return _smoke_test()

    logger.info("Starting MH - Coordinate")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
        from PySide6.QtCore import Qt, QTimer
        from ui.branding import app_icon, create_splash_pixmap
        from core.version import APP_VERSION
        from core.updater import check_for_update, install_latest_windows
    except ImportError as exc:
        logger.exception("Failed to import startup layer: %s", exc)
        raise

    app = QApplication(sys.argv)
    app.setApplicationName("MH - Coordinate")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("MH-Coordinate")
    app.setWindowIcon(app_icon())

    splash = QSplashScreen(
        create_splash_pixmap(),
        Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
    )
    splash.setWindowIcon(app_icon())
    splash.show()
    app.processEvents()

    window = None
    try:
        splash.showMessage(
            "Loading core modules...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        app.processEvents()
        from ui.main_window import MainWindow
        from ui.cad_layout_fix import apply_cad_page_layout

        splash.showMessage(
            "Preparing CRS engine and workspace...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        app.processEvents()
        window = MainWindow()
        window.setWindowIcon(app_icon())
        apply_cad_page_layout(window)

        splash.showMessage(
            "Opening MH - Coordinate...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        app.processEvents()
        window.show()
        app.processEvents()
    finally:
        if window is not None:
            splash.finish(window)
        else:
            splash.close()

    def check_updates() -> None:
        if not getattr(sys, "frozen", False):
            return
        update = check_for_update(APP_VERSION)
        if not update:
            return
        tag, _url = update
        answer = QMessageBox.question(
            window,
            "MH - Coordinate Update",
            f"A new version ({tag}) is available. Update now?\n\nThe program will close, install the update, and restart automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            if install_latest_windows(window):
                app.quit()
            else:
                QMessageBox.warning(
                    window,
                    "Update Failed",
                    "The update could not be installed. You can try again later.",
                )

    QTimer.singleShot(2500, check_updates)
    logger.info("Main window shown, entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
