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


def test_crs_picker_accepts_global_authority_identifier(qapp):
    window = MainWindow()
    try:
        picker = window.pages["converter"].source_picker
        picker.set_selected("ESRI:102003", "USA Contiguous Albers Equal Area")
        assert picker.selected_epsg() == "ESRI:102003"
    finally:
        window.close()
        window.deleteLater()


def test_crs_engine_resolves_non_epsg_authority():
    engine = CRSEngine()
    results = engine.search("ESRI:102003", limit=5)
    assert any(item.epsg.upper() == "ESRI:102003" for item in results)


def test_amanah_local_identity_is_exact():
    engine = CRSEngine()
    x, y, z = 500000.0, 2750000.0, 123.45
    tx, ty, tz = engine.transform_point(
        CRSEngine.AMANAH_RIYADH,
        CRSEngine.AMANAH_RIYADH,
        x, y, z,
    )
    assert math.isclose(tx, x, abs_tol=1e-9)
    assert math.isclose(ty, y, abs_tol=1e-9)
    assert math.isclose(tz, z, abs_tol=1e-9)


def test_wgs84_to_utm38_and_back():
    engine = CRSEngine()
    point = PointResult("P1", 46.6753, 24.7136, 600.0)
    converted = engine.transform_points("EPSG:4326", "EPSG:32638", [point])
    assert converted[0].status == "SUCCESS"
    assert converted[0].tgt_x is not None and converted[0].tgt_y is not None
    back = engine.transform_points(
        "EPSG:32638", "EPSG:4326",
        [PointResult("P1", converted[0].tgt_x, converted[0].tgt_y, converted[0].tgt_z)],
    )
    assert back[0].status == "SUCCESS"
    assert math.isclose(back[0].tgt_x, point.src_x, abs_tol=1e-6)
    assert math.isclose(back[0].tgt_y, point.src_y, abs_tol=1e-6)


def _write_preview_csv(tmp_path):
    path = tmp_path / "preview_test.csv"
    path.write_text(
        "Name,E,N,Z\n"
        "P1,100.0,200.0,5.0\n"
        "P2,110.0,210.0,6.0\n",
        encoding="utf-8",
    )
    return path


def _combo_index(combo, text):
    idx = combo.findText(text)
    assert idx >= 0, f"Column {text!r} was not detected"
    return idx


def _table_row_for_name(cad, name):
    for row in range(cad.table.rowCount()):
        item = cad.table.item(row, 1)
        if item and item.text() == name:
            return row
    raise AssertionError(f"Point {name!r} was not found in preview table")


def test_cad_preview_applies_manual_parsing_changes(qapp, tmp_path):
    window = MainWindow()
    try:
        cad = window.pages["cad"]
        path = _write_preview_csv(tmp_path)
        cad.load_active_file(str(path))
        row = _table_row_for_name(cad, "P1")
        assert cad.table.item(row, 2).text() == "100.000"
        assert cad.table.item(row, 3).text() == "200.000"

        cad.parsing_engine.setCurrentIndex(1)
        cad.x_column.setCurrentIndex(_combo_index(cad.x_column, "N"))
        cad.y_column.setCurrentIndex(_combo_index(cad.y_column, "E"))
        cad.preview_btn.click()

        row = _table_row_for_name(cad, "P1")
        assert cad.table.item(row, 2).text() == "200.000"
        assert cad.table.item(row, 3).text() == "100.000"
        assert "Preview updated" in cad.preview_state.text()
    finally:
        window.close()
        window.deleteLater()


def test_cad_preview_applies_axis_order_change(qapp, tmp_path):
    window = MainWindow()
    try:
        cad = window.pages["cad"]
        path = _write_preview_csv(tmp_path)
        cad.load_active_file(str(path))
        row = _table_row_for_name(cad, "P1")
        cad.axis_yx.setChecked(True)
        assert cad._preview_dirty is True

        assert cad.table.item(row, 2).text() == "100.000"
        assert cad.table.item(row, 3).text() == "200.000"

        cad.preview_again_btn.click()
        row = _table_row_for_name(cad, "P1")
        assert cad.table.item(row, 2).text() == "200.000"
        assert cad.table.item(row, 3).text() == "100.000"
        assert cad._preview_dirty is False
    finally:
        window.close()
        window.deleteLater()


def test_cad_layout_provides_dxf_label_compatibility(qapp):
    window = MainWindow()
    try:
        cad = window.pages["cad"]
        assert not hasattr(cad, "write_code")
        assert apply_cad_page_layout(window) is True
        assert hasattr(cad, "write_code")
        assert cad.write_code.isChecked() is True
    finally:
        window.close()
        window.deleteLater()
