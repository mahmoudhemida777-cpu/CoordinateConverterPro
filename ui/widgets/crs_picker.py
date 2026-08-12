from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel,
)

from core.crs.engine import CRSEngine


class CRSPicker(QWidget):
    """Search box + results list for CRS discovery by name, EPSG code,
    country, datum, or projection (spec section 5). Example: typing
    'Ain el Abd' should surface EPSG:20438."""

    crs_selected = Signal(str, str)  # epsg_code, display_name

    def __init__(self, engine: CRSEngine, label: str = "") -> None:
        super().__init__()
        self._engine = engine
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if label:
            layout.addWidget(QLabel(label))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name, EPSG code, country, datum…")
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

        self.selected_label = QLabel("No CRS selected")
        self.selected_label.setStyleSheet("color: #1F3864; font-weight: bold;")
        layout.addWidget(self.selected_label)

    def _on_search(self, text: str) -> None:
        self.results_list.clear()
        if len(text.strip()) < 2:
            return
        try:
            results = self._engine.search(text, limit=30)
        except Exception:  # noqa: BLE001
            results = []
        for r in results:
            item = QListWidgetItem(f"{r.epsg} — {r.name}")
            item.setData(1000, r.epsg)
            item.setData(1001, r.name)
            self.results_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        epsg = item.data(1000)
        name = item.data(1001)
        self.selected_label.setText(f"{epsg} — {name}")
        self.crs_selected.emit(epsg, name)

    def selected_epsg(self) -> str | None:
        text = self.selected_label.text()
        if text.startswith("No CRS"):
            return None
        return text.split(" — ")[0]
