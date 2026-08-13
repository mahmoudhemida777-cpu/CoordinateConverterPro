from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel

from core.crs.engine import CRSEngine


class CRSPicker(QWidget):
    """Global CRS search/selection widget backed by PROJ, with visible geographic presets."""

    crs_selected = Signal(str, str)

    # Always-visible essentials so a new user can immediately choose
    # Latitude/Longitude without having to know EPSG codes.
    QUICK_CRS = (
        ("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)"),
        ("EPSG:4979", "WGS 84 — Geographic 3D (Latitude / Longitude / Ellipsoidal Height)"),
        ("EPSG:32638", "WGS 84 / UTM zone 38N"),
        ("EPSG:20438", "Ain el Abd 1970 / UTM zone 38N"),
    )

    def __init__(self, engine: CRSEngine, label: str = "") -> None:
        super().__init__()
        self._engine = engine
        self._selected_epsg: str | None = None
        self._selected_name: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if label:
            layout.addWidget(QLabel(label))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search: WGS 84, Latitude/Longitude, EPSG:4326, UTM, Ain el Abd..."
        )
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

        self.selected_label = QLabel("No CRS selected")
        self.selected_label.setStyleSheet("color:#1F3864;font-weight:bold;")
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
        self.results_list.addItem(item)

    def _on_search(self, text: str) -> None:
        self.results_list.clear()
        query = text.strip()
        if not query:
            self._show_quick_crs()
            return
        if len(query) < 2:
            return

        # Friendly direct aliases for the most common geographic input.
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
            if r.epsg in existing:
                continue
            self._add_result(r.epsg, r.name)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.set_selected(str(item.data(1000)), str(item.data(1001)))

    def set_selected(self, epsg: str, name: str) -> None:
        """Select any authority identifier (EPSG, ESRI, IGNF, OGC, etc.)."""
        epsg = epsg.strip()
        if ":" not in epsg:
            epsg = f"EPSG:{epsg}"

        self._selected_epsg = epsg.upper()
        self._selected_name = name
        self.selected_label.setText(f"{self._selected_epsg} — {name}")
        self.search_box.setText(f"{name} / {self._selected_epsg}")
        self.crs_selected.emit(self._selected_epsg, name)

    def selected_epsg(self) -> str | None:
        return self._selected_epsg
