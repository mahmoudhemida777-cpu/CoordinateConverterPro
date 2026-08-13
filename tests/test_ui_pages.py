"""Integration smoke tests for the real application pages."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_contains_real_feature_pages(qapp):
    window = MainWindow()
    try:
        assert window.windowTitle() == "MH GeoSuite Pro"
        assert window.pages["dashboard"].__class__.__name__ == "DashboardPage"
        assert window.pages["survey"].__class__.__name__ == "SurveyPage"
        assert window.pages["cad"].__class__.__name__ == "CadPage"
        assert window.pages["batch"].__class__.__name__ == "BatchPage"
        assert window.pages["map"].__class__.__name__ == "MapPage"
        assert window.pages["history"].__class__.__name__ == "HistoryPage"
    finally:
        window.close()
        window.deleteLater()


def test_crs_picker_accepts_global_authority_identifier(qapp):
    window = MainWindow()
    try:
        picker = window.pages["converter"].source_picker
        picker.set_selected("ESRI:102003", "USA Contiguous Albers Equal Area")
        assert picker.selected_epsg() == "ESRI:102003"
    finally:
        window.close()
        window.deleteLater()
