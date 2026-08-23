import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from ui.pages.converter_page import ConverterPage


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_crs_converter_uses_three_internal_pages(qapp):
    page = ConverterPage()
    try:
        assert page.stack.count() == 3
        assert page.source_picker.minimumHeight() >= 285
        assert page.target_picker.minimumHeight() >= 285
        assert page.results_table.sizePolicy().verticalPolicy().name == "Expanding"
        assert page.export_dxf_btn.height() == 42
        assert len(page.step_buttons) == 3
        page._show_step(1)
        assert page.stack.currentIndex() == 1
        page._show_step(2)
        assert page.stack.currentIndex() == 2
    finally:
        page.deleteLater()
