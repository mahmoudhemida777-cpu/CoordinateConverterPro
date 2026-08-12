from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
)

from core.crs.engine import CRSEngine


class CRSPicker(QWidget):
    """
    CRS search and selection widget.

    Supports:
    - EPSG:4326
    - 4326
    - WGS 84
    - WGS 84 / EPSG:4326
    - CRS name / datum / country / projection
    """

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
        self.search_box.setPlaceholderText(
            "Search by name, EPSG code, country, datum..."
        )
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list)

        self.selected_label = QLabel("No CRS selected")
        self.selected_label.setStyleSheet(
            "color: #1F3864; font-weight: bold;"
        )
        layout.addWidget(self.selected_label)

    def _on_search(self, text: str) -> None:
        self.results_list.clear()

        query = text.strip()

        if len(query) < 2:
            return

        # Normalize common EPSG input formats.
        normalized = query.upper().replace(" ", "")

        if normalized.startswith("EPSG:"):
            code = normalized.replace("EPSG:", "", 1)

            if code.isdigit():
                query = code

        elif normalized.isdigit():
            query = normalized

        try:
            results = self._engine.search(query, limit=30)
        except Exception:
            results = []

        for r in results:
            item = QListWidgetItem(
                f"{r.epsg} — {r.name}"
            )

            item.setData(1000, r.epsg)
            item.setData(1001, r.name)

            self.results_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        epsg = str(item.data(1000))
        name = str(item.data(1001))

        self.set_selected(epsg, name)

    def set_selected(self, epsg: str, name: str) -> None:
        """
        Programmatically select a CRS.
        """

        if not epsg.upper().startswith("EPSG:"):
            epsg = f"EPSG:{epsg}"

        self._selected_epsg = epsg
        self._selected_name = name

        self.selected_label.setText(
            f"{epsg} — {name}"
        )

        self.search_box.setText(
            f"{name} / {epsg}"
        )

        self.crs_selected.emit(
            epsg,
            name,
        )

    def selected_epsg(self) -> str | None:
        return self._selected_epsg
