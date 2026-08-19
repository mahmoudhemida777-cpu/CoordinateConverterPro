import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.i18n import set_language, current_language
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_arabic_is_enabled_application_wide(qapp):
    set_language("ar")
    window = MainWindow()
    try:
        assert current_language() == "ar"
        assert qapp.layoutDirection() == Qt.LayoutDirection.RightToLeft
        sidebar = [window.sidebar.item(i).text() for i in range(window.sidebar.count())]
        assert "لوحة المعلومات" in sidebar
        assert "استيراد" in sidebar
        assert "الخريطة" in sidebar
        assert window.pages["survey"].findChildren(type(window.pages["survey"].result_labels["horizontal"]))
    finally:
        window.close()
        window.deleteLater()


def test_language_can_switch_back_to_english(qapp):
    set_language("ar")
    window = MainWindow()
    try:
        set_language("en")
        assert qapp.layoutDirection() == Qt.LayoutDirection.LeftToRight
        assert window.sidebar.item(0).text() == "Dashboard"
        assert window.sidebar.item(1).text() == "Import"
    finally:
        window.close()
        window.deleteLater()
