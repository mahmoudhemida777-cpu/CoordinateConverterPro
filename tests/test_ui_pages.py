"""Integration smoke tests for the real application pages and CRS picker."""
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QScrollArea

from core.crs.engine import CRSEngine
from core.models import PointResult
from ui.main_window import MainWindow
from ui.cad_layout_fix import apply_cad_page_layout
from ui.pages.import_page import ImportPage


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_contains_real_feature_pages(qapp):
    window = MainWindow()
    try:
        assert window.windowTitle() == "MH - Coordinate"
        assert window.pages["dashboard"].__class__.__name__ == "DashboardPage"
        assert window.pages["survey"].__class__.__name__ == "SurveyPage"
        assert window.pages["cad"].__class__.__name__ == "CadPage"
        assert window.pages["batch"].__class__.__name__ == "BatchPage"
        assert window.pages["map"].__class__.__name__ == "MapPage"
        assert window.pages["history"].__class__.__name__ == "HistoryPage"
        assert window.pages["cad"].table.columnCount() == 6
        assert hasattr(window.pages["cad"], "preview_btn")
        assert hasattr(window.pages["cad"], "preview_again_btn")
        assert window.pages["cad"].findChild(QScrollArea) is not None
    finally:
        window.close()
        window.deleteLater()


def test_map_canvas_is_large_enough_for_full_point_preview(qapp):
    window = MainWindow()
    try:
        canvas = window.pages["map"].view
        assert canvas.minimumHeight() >= 650
        assert window.pages["map"].minimumWidth() >= 0
    finally:
        window.close()
        window.deleteLater()


def test_import_shared_file_guard_prevents_recursive_reload(qapp, tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("Point,X,Y\nP1,1,2\n", encoding="utf-8")
    page = ImportPage()
    try:
        page.active_path = str(path)
        called = []
        page._import_path = lambda value: called.append(value)
        page.load_active_file(str(path))
        assert called == []
    finally:
        page.deleteLater()
