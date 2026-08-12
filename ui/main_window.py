"""Main application window: sidebar + stacked pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QStyle,
)

from ui.pages.dashboard_page import DashboardPage
from ui.pages.import_page import ImportPage
from ui.pages.converter_page import ConverterPage
from ui.pages.batch_page import BatchPage
from ui.pages.settings_page import SettingsPage
from ui.pages.about_page import AboutPage
from ui.pages.placeholder_page import PlaceholderPage
from ui.i18n import tr

APP_NAME = "MH GeoSuite Pro"
APP_TAGLINE = "Professional Surveying & Geospatial Engineering Suite"

SIDEBAR_ITEMS = [
    ("dashboard", "Dashboard"),
    ("import", "Import"),
    ("converter", "CRS Converter"),
    ("survey", "Survey Tools"),
    ("cad", "Civil / CAD"),
    ("batch", "Batch Converter"),
    ("map", "Map"),
    ("history", "History"),
    ("settings", "Settings"),
    ("about", "About"),
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        # QCommonStyle does not expose SP_ComputerIcon directly; the
        # standard pixmap enum belongs to QStyle. This works across the
        # supported PySide6 builds, including the frozen Windows EXE.
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("sidebar")
        for key, label in SIDEBAR_ITEMS:
            item = QListWidgetItem(tr(label))
            item.setData(Qt.UserRole, key)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)

        self.stack = QStackedWidget()
        self.pages = {
            "dashboard": DashboardPage(),
            "import": ImportPage(),
            "converter": ConverterPage(),
            "survey": PlaceholderPage(
                "Survey Tools",
                "Distance, Bearing, Azimuth, Area, Perimeter, Coordinate "
                "Difference, Offset, Point Renumbering, Grid, COGO — "
                "architecture ready, tools shipping incrementally in "
                "upcoming releases.",
            ),
            "cad": PlaceholderPage(
                "Civil / CAD",
                "Additional Civil 3D / AutoCAD integration tools — "
                "coming in a future release. DXF export is already "
                "available today from the CRS Converter and Batch pages.",
            ),
            "batch": BatchPage(),
            "map": PlaceholderPage(
                "Map Preview",
                "Offline-friendly map preview (no paid API) is planned "
                "for a future release. It is optional by design and the "
                "application works fully offline without it.",
            ),
            "history": PlaceholderPage(
                "History",
                "Conversion history log — coming in a future release.",
            ),
            "settings": SettingsPage(),
            "about": AboutPage(),
        }
        for key, _ in SIDEBAR_ITEMS:
            self.stack.addWidget(self.pages[key])

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack)
        self.sidebar.setCurrentRow(0)
        self.statusBar().showMessage(tr("Ready"))

    def _on_sidebar_changed(self, row: int) -> None:
        key, _ = SIDEBAR_ITEMS[row]
        self.stack.setCurrentWidget(self.pages[key])
