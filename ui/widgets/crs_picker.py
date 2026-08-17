from __future__ import annotations

from PySide6.QtCore import Signal, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel

from core.crs.engine import CRSEngine


class CRSPicker(QWidget):
    """Global CRS search/selection widget backed by PROJ plus project-local CRS presets."""

    crs_selected = Signal(str, str)

    QUICK_CRS = (
        ("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)"),
        ("EPSG:4979", "WGS 84 — Geographic 3D (Latitude / Longitude / Ellipsoidal Height)"),
        ("EPSG:32638", "WGS 84 / UTM zone 38N"),
        ("EPSG:20438", "Ain el Abd 1970 / UTM zone 38N"),
        (CRSEngine.AMANAH_RIYADH, "Amanah Riyadh Local Grid 38N — Custom local CRS"),
    )

    def __init__(self, engine: CRSEngine, label: str = "") -> None:
        super().__init__()
        self._engine = engine
        self._selected_epsg: str | None = None
        self._selected_name: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if label:
            self.title_label = QLabel(label)
            self.title_label.setStyleSheet("font-size:12px;font-weight:700;color:#52627A;")
            layout.addWidget(self.title_label)

        # Keep CRS controls visually consistent with the other application pages.
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search CRS: WGS 84, EPSG:4326, UTM, Ain el Abd, Amanah Riyadh..."
        )
        self.search_box.setFixedHeight(36)
        self.search_box.setFont(QFont("Segoe UI", 9))
        self.search_box.setStyleSheet(
            "QLineEdit { padding:6px 10px; border:1px solid #C7D0DD; border-radius:6px; "
            "background:#FFFFFF; color:#172235; }"
            "QLineEdit:focus { border:1px solid #31527A; }"
        )
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.setMinimumHeight(170)
        self.results_list.setMaximumHeight(220)
        self.results_list.setUniformItemSizes(True)
        self.results_list.setSpacing(0)
        self.results_list.setFont(QFont("Segoe UI", 9))
        self.results_list.setStyleSheet(
            "QListWidget { border:1px solid #C7D0DD; border-radius:6px; background:#FFFFFF; "
            "padding:2px; }"
            "QListWidget::item { min-height:30px; padding:5px 8px; border-radius:4px; }"
            "QListWidget::item:selected { background:#E7EEF8; color:#1F3864; font-weight:600; }"
        )
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

        self.selected_label = QLabel("No CRS selected")
        self.selected_label.setMinimumHeight(32)
        self.selected_label.setWordWrap(True)
        self.selected_label.setStyleSheet(
            "color:#1F3864;font-size:9px;font-weight:700;"
            "background:#F4F6F8;border:1px solid #D6DEE9;border-radius:6px;padding:6px 8px;"
        )
        layout.addWidget(self.selected_label)

        self._show_quick_crs()

    def _show_quick_crs(self) -> None:
        self.results_list.clear()
        for code, name in self.QUICK_CRS:
            self._add_result(code, name)

    def _add_result(self, code: str, name: str) -> None:
        item = QListWidgetItem(f"{code} — {name}")
        item.setData(1000, code)
        item.setData(1001, name)
        item.setSizeHint(QSize(0, 32))
        self.results_list.addItem(item)

    def _on_search(self, text: str) -> None:
        self.results_list.clear()
        query = text.strip()
        if not query:
            self._show_quick_crs()
            return
        if len(query) < 2:
            return

        normalized = " ".join(query.lower().split())
        if normalized in {
            "wgs 84", "wgs84", "wgs 84 geographic", "latitude longitude",
            "latitude/longitude", "lat long", "lat/lon", "geographic",
        }:
            self._add_result("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)")
            self._add_result("EPSG:4979", "WGS 84 — Geographic 3D (Latitude / Longitude / Ellipsoidal Height)")

        try:
            results = self._engine.search(query, limit=50)
        except Exception:
            results = []

        existing = {self.results_list.item(i).data(1000) for i in range(self.results_list.count())}
        for r in results:
            code = r.epsg
            if code in existing:
                continue
            self._add_result(code, r.name)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.set_selected(str(item.data(1000)), str(item.data(1001)))

    def set_selected(self, epsg: str, name: str) -> None:
        epsg = epsg.strip()
        if ":" not in epsg and epsg != CRSEngine.AMANAH_RIYADH:
            epsg = f"EPSG:{epsg}"
        self._selected_epsg = epsg.upper() if epsg.startswith("epsg:") else epsg
        self._selected_name = name
        self.selected_label.setText(f"{self._selected_epsg} — {name}")
        self.search_box.setText(f"{name} / {self._selected_epsg}")
        self.crs_selected.emit(self._selected_epsg, name)

    def selected_epsg(self) -> str | None:
        return self._selected_epsg
