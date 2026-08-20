from __future__ import annotations

from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel, QSizePolicy

from core.crs.engine import CRSEngine
from ui.i18n import tr


class CRSPicker(QWidget):
    """Responsive CRS search/selection widget with stable row sizing."""

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
        layout.setSpacing(8)

        self.title_label = QLabel(label)
        self.title_label.setObjectName("crsPickerTitle")
        self.title_label.setProperty("mhTextKey", label)
        self.title_label.setMinimumHeight(28)
        layout.addWidget(self.title_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr("Search CRS: WGS 84, EPSG:4326, UTM, Ain el Abd, Amanah Riyadh..."))
        self.search_box.setProperty("mhPlaceholderKey", "Search CRS: WGS 84, EPSG:4326, UTM, Ain el Abd, Amanah Riyadh...")
        self.search_box.setMinimumHeight(42)
        self.search_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_box.setFont(QFont("Segoe UI", 10))
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.results_list = QListWidget()
        self.results_list.setMinimumHeight(210)
        self.results_list.setMaximumHeight(235)
        self.results_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.results_list.setUniformItemSizes(True)
        self.results_list.setSpacing(2)
        self.results_list.setFont(QFont("Segoe UI", 10))
        self.results_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_list.setStyleSheet(
            "QListWidget { border:1px solid #C7D0DD; border-radius:7px; background:#FFFFFF; padding:4px; }"
            "QListWidget::item { min-height:38px; padding:6px 10px; border-radius:5px; }"
            "QListWidget::item:selected { background:#E7EEF8; color:#1F3864; font-weight:600; }"
        )
        self.results_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.results_list, 1)

        self.selected_label = QLabel(tr("No CRS selected"))
        self.selected_label.setObjectName("crsSelectedLabel")
        self.selected_label.setProperty("mhTextKey", "No CRS selected")
        self.selected_label.setMinimumHeight(48)
        self.selected_label.setMaximumHeight(58)
        self.selected_label.setWordWrap(False)
        self.selected_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.selected_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.selected_label)

        self._show_quick_crs()

    def _show_quick_crs(self) -> None:
        self.results_list.clear()
        for code, name in self.QUICK_CRS:
            self._add_result(code, name)

    def _add_result(self, code: str, name: str) -> None:
        item = QListWidgetItem(f"{code} — {name}")
        item.setData(Qt.ItemDataRole.UserRole, code)
        item.setData(Qt.ItemDataRole.UserRole + 1, name)
        item.setSizeHint(QSize(0, 40))
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
        if normalized in {"wgs 84", "wgs84", "wgs 84 geographic", "latitude longitude", "latitude/longitude", "lat long", "lat/lon", "geographic"}:
            self._add_result("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)")
            self._add_result("EPSG:4979", "WGS 84 — Geographic 3D (Latitude / Longitude / Ellipsoidal Height)")

        try:
            results = self._engine.search(query, limit=50)
        except Exception:
            results = []

        existing = {self.results_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.results_list.count())}
        for result in results:
            code = result.epsg
            if code in existing:
                continue
            self._add_result(code, result.name)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.set_selected(str(item.data(Qt.ItemDataRole.UserRole)), str(item.data(Qt.ItemDataRole.UserRole + 1)))

    def set_selected(self, epsg: str, name: str) -> None:
        epsg = epsg.strip()
        if ":" not in epsg and epsg != CRSEngine.AMANAH_RIYADH:
            epsg = f"EPSG:{epsg}"
        self._selected_epsg = epsg.upper() if epsg.lower().startswith("epsg:") else epsg
        self._selected_name = name
        self.selected_label.setText(f"{self._selected_epsg} — {name}")
        self.search_box.blockSignals(True)
        self.search_box.setText(f"{name} / {self._selected_epsg}")
        self.search_box.blockSignals(False)
        self.crs_selected.emit(self._selected_epsg, name)

    def selected_epsg(self) -> str | None:
        return self._selected_epsg
