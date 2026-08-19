import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_cad_importer_extracts_dxf_points_and_polyline_vertices(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    from core.cad_importer import extract_cad_points

    path = tmp_path / "survey.dxf"
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_point((100, 200, 7))
    msp.add_lwpolyline([(110, 210), (120, 220), (130, 230)], dxfattribs={"elevation": 8})
    doc.saveas(path)

    points = extract_cad_points(path)
    assert len(points) == 4
    assert points[0].src_x == 100.0
    assert points[0].src_y == 200.0
    assert points[0].src_z == 7.0
    assert points[-1].src_x == 130.0
    assert points[-1].src_y == 230.0
    assert points[-1].src_z == 8.0


def test_arabic_language_sets_rtl(qtbot):
    PySide6 = pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.i18n import set_language
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    qtbot.addWidget(window)
    set_language("ar")
    assert app.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert window.sidebar.item(0).text() == "لوحة المعلومات"
    set_language("en")
    assert app.layoutDirection() == Qt.LayoutDirection.LeftToRight
    window.close()
