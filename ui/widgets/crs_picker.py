from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel

from core.crs.engine import CRSEngine


class CRSPicker(QWidget):
    """Global CRS search/selection widget backed by the local PROJ catalog."""

    crs_selected = Signal(str, str)

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
        self.search_box.setPlaceholderText("Search name, authority:code, EPSG code, datum, country, projection...")
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

        self.selected_label = QLabel("No CRS selected")
        self.selected_label.setStyleSheet("color:#1F3864;font-weight:bold;")
        layout.addWidget(self.selected_label)

    def _on_search(self, text: str) -> None:
        self.results_list.clear()
        query = text.strip()
        if len(query) < 2:
            return

        try:
            results = self._engine.search(query, limit=50)
        except Exception:
            results = []

        for r in results:
            item = QListWidgetItem(f"{r.epsg} — {r.name}")
            item.setData(1000, r.epsg)
            item.setData(1001, r.name)
            self.results_list.addItem(item)

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
