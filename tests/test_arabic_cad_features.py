import os
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
    assert points[0].src_x == 100.0 and points[0].src_y == 200.0 and points[0].src_z == 7.0
    assert points[-1].src_x == 130.0 and points[-1].src_y == 230.0 and points[-1].src_z == 8.0


def test_cad_importer_falls_back_to_insert_block_points(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")
    from core.cad_importer import extract_cad_points
    path = tmp_path / "cogo_blocks.dxf"
    doc = ezdxf.new("R2010")
    doc.blocks.new(name="COGO_POINT")
    msp = doc.modelspace()
    msp.add_blockref("COGO_POINT", (500000, 2750000, 12.5))
    msp.add_blockref("COGO_POINT", (500010, 2750010, 13.0))
    doc.saveas(path)
    points = extract_cad_points(path)
    assert len(points) == 2
    assert (points[0].src_x, points[0].src_y) == (500000.0, 2750000.0)


def test_arabic_language_sets_rtl_and_converter_headers():
    pytest.importorskip("PySide6")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.i18n import set_language
    from ui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    try:
        set_language("ar")
        assert app.layoutDirection() == Qt.LayoutDirection.RightToLeft
        assert window.sidebar.item(0).text() == "لوحة المعلومات"
        headers = [window.pages["converter"].results_table.horizontalHeaderItem(i).text() for i in range(9)]
        assert headers[:4] == ["الاسم", "X المصدر", "Y المصدر", "Z المصدر"]
        assert window.pages["converter"].export_dxf_btn.text() == "AutoCAD / Civil 3D — DXF"
        assert window.pages["converter"].findChild(type(window.pages["converter"].results_table)) is not None
    finally:
        set_language("en")
        window.close()
