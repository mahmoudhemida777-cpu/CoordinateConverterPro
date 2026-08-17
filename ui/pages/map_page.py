from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QMessageBox, QGraphicsTextItem,
    QComboBox, QCheckBox, QSpinBox, QGroupBox
)
from core.models import PointResult
from core.point_ordering import order_points
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from ui.widgets.workspace_bar import WorkspaceFileBar

SUPPORTED_FILTER = "Supported files (*.csv *.xlsx *.kml *.kmz *.txt);;All files (*.*)"


class MapPage(QWidget):
    """Survey map with true code-grouped grid/zigzag ordering.

    The important rule is that a path is calculated independently for each
    point-code group (A, KS, AS, ...). Paths are never connected across groups.
    """

    def __init__(self) -> None:
        super().__init__()
        self.workspace_folder: str | None = None
        self.current_file: Path | None = None
        self._raw_points: list[PointResult] = []
        self._points: list[tuple[str, float, float]] = []
        self._canvas_mode = "Light"
        self._show_labels = True
        self._point_size = 10
        self._label_size = 9
        self._ordering_mode = "GRID_ZIGZAG_WEST"
        self._group_by_code = True
        self._reverse_rows = False
        self._auto_grid = True

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("MAP — SURVEY POINT PREVIEW")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.info = QLabel("No points loaded")
        self.info.setObjectName("pageSubtitle")
        title_row.addWidget(self.info)
        root.addLayout(title_row)

        self.workspace_bar = WorkspaceFileBar()
        self.workspace_bar.file_selected.connect(self.load_active_file)
        root.addWidget(self.workspace_bar)

        controls = QHBoxLayout(); controls.setSpacing(8)
        open_btn = QPushButton("Open Coordinate File"); open_btn.clicked.connect(self._open); controls.addWidget(open_btn)
        reload_btn = QPushButton("Reload Selected"); reload_btn.clicked.connect(self._reload_selected); controls.addWidget(reload_btn)
        controls.addSpacing(8); controls.addWidget(QLabel("Map Background"))
        self.canvas_mode = QComboBox(); self.canvas_mode.addItems(["Light", "Dark"]); self.canvas_mode.currentTextChanged.connect(self._canvas_changed); controls.addWidget(self.canvas_mode)
        self.labels_check = QCheckBox("Show Labels"); self.labels_check.setChecked(True); self.labels_check.toggled.connect(self._labels_changed); controls.addWidget(self.labels_check)
        controls.addWidget(QLabel("Point Size")); self.point_size = QSpinBox(); self.point_size.setRange(6, 22); self.point_size.setValue(self._point_size); self.point_size.valueChanged.connect(self._point_size_changed); controls.addWidget(self.point_size)
        controls.addWidget(QLabel("Label Size")); self.label_size = QSpinBox(); self.label_size.setRange(7, 18); self.label_size.setValue(self._label_size); self.label_size.valueChanged.connect(self._label_size_changed); controls.addWidget(self.label_size)
        fit_btn = QPushButton("Fit Extents"); fit_btn.clicked.connect(self._fit); controls.addWidget(fit_btn); controls.addStretch(); root.addLayout(controls)

        self.workspace_label = QLabel("PROJECT WORKSPACE: Not selected"); self.workspace_label.setObjectName("pageSubtitle"); root.addWidget(self.workspace_label)

        canvas_box = QGroupBox("MAP VIEW")
        canvas_layout = QVBoxLayout(canvas_box); canvas_layout.setContentsMargins(8, 20, 8, 8)
        self.scene = QGraphicsScene(self); self.view = QGraphicsView(self.scene); self.view.setObjectName("mapCanvas")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setMinimumHeight(440); self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus); canvas_layout.addWidget(self.view, 1); root.addWidget(canvas_box, 1)

        # Ordering controls: these are intentionally explicit so the user can
        # verify the exact zigzag rule used to draw/export the survey path.
        ordering_box = QGroupBox("ZIGZAG / GRID ORDERING")
        ol = QVBoxLayout(ordering_box)
        row1 = QHBoxLayout(); row1.addWidget(QLabel("Ordering Method"))
        self.ordering_combo = QComboBox(); self.ordering_combo.addItems(["Zigzag (Start West)", "Zigzag (Start East)", "Source Order"]); self.ordering_combo.currentTextChanged.connect(self._ordering_changed); row1.addWidget(self.ordering_combo, 1)
        row1.addWidget(QLabel("Group By")); self.group_combo = QComboBox(); self.group_combo.addItems(["Point Code / Name", "All Points"]); self.group_combo.setCurrentIndex(0); self.group_combo.currentTextChanged.connect(self._group_changed); row1.addWidget(self.group_combo, 1)
        row1.addWidget(QLabel("Start Corner")); self.corner_combo = QComboBox(); self.corner_combo.addItems(["North-West", "North-East"]); self.corner_combo.currentTextChanged.connect(self._corner_changed); row1.addWidget(self.corner_combo, 1); ol.addLayout(row1)
        row2 = QHBoxLayout(); self.reverse_check = QCheckBox("Reverse Each Row"); self.reverse_check.toggled.connect(self._reverse_changed); row2.addWidget(self.reverse_check)
        self.grid_check = QCheckBox("Auto Detect Grid"); self.grid_check.setChecked(True); self.grid_check.toggled.connect(self._grid_changed); row2.addWidget(self.grid_check); row2.addStretch(); ol.addLayout(row2)
        self.order_status = QLabel("Zigzag ordering: each code is ordered independently."); self.order_status.setObjectName("pageSubtitle"); ol.addWidget(self.order_status)
        root.addWidget(ordering_box)

        totals = QHBoxLayout(); self.total_label = QLabel("Total Points: 0"); self.displayed_label = QLabel("Displayed: 0"); self.invalid_label = QLabel("Invalid: 0"); totals.addWidget(self.total_label); totals.addStretch(); totals.addWidget(self.displayed_label); totals.addStretch(); totals.addWidget(self.invalid_label); root.addLayout(totals)
        self._apply_canvas_style()

    def set_workspace_folder(self, folder: str | None) -> None:
        self.workspace_folder = folder; self.workspace_label.setText(f"PROJECT WORKSPACE: {folder or 'Not selected'}"); self.workspace_bar.set_folder(folder, self.current_file)
        if self.current_file and self.current_file.exists(): self._load_path(str(self.current_file))

    def load_active_file(self, path: str) -> None:
        if not path or not Path(path).is_file(): return
        self.current_file = Path(path).resolve(); self.workspace_folder = str(self.current_file.parent)
        self.workspace_label.setText(f"PROJECT WORKSPACE: {self.workspace_folder}"); self.workspace_bar.set_folder(self.workspace_folder, self.current_file); self._load_path(str(self.current_file))

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Coordinate File", self.workspace_folder or "", SUPPORTED_FILTER)
        if path: self.load_active_file(path)

    def _reload_selected(self) -> None:
        path = self.workspace_bar.selected_file()
        if path: self.load_active_file(path)

    def _load_path(self, path: str) -> None:
        try:
            file_path = Path(path); suffix = file_path.suffix.casefold()
            if suffix == ".kmz": points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml": points = kml_parser.parse_kml_file(path)
            elif suffix == ".txt": points = txt_parser.parse_txt(path)
            elif suffix == ".csv": points = csv_parser.parse_csv_auto(path)
            elif suffix == ".xlsx": points = xlsx_parser.parse_xlsx_auto(path)
            else: raise ValueError(f"Unsupported file type: {suffix}")
            self._raw_points = [p for p in points if p.src_x is not None and p.src_y is not None]
            if not self._raw_points: raise ValueError("No valid X/Y points found in this file.")
            self.current_file = file_path.resolve(); self._apply_ordering()
            self.info.setText(f"{file_path.name}  |  {len(self._raw_points)} points loaded")
        except Exception as exc:
            self.scene.clear(); self.info.setText(f"Load failed: {Path(path).name}"); QMessageBox.critical(self, "Map Error", f"Could not load {Path(path).name}:\n{exc}")

    def _ordering_changed(self, text: str) -> None:
        self._ordering_mode = "GRID_ZIGZAG_EAST" if "East" in text else ("SOURCE" if "Source" in text else "GRID_ZIGZAG_WEST"); self._apply_ordering()

    def _group_changed(self, text: str) -> None:
        self._group_by_code = text == "Point Code / Name"; self._apply_ordering()

    def _corner_changed(self, text: str) -> None:
        if self._ordering_mode.startswith("GRID_ZIGZAG"):
            self._ordering_mode = "GRID_ZIGZAG_EAST" if text == "North-East" else "GRID_ZIGZAG_WEST"
        self._apply_ordering()

    def _reverse_changed(self, checked: bool) -> None:
        self._reverse_rows = checked; self._apply_ordering()

    def _grid_changed(self, checked: bool) -> None:
        self._auto_grid = checked; self._apply_ordering()

    def _apply_ordering(self) -> None:
        if not self._raw_points: return
        tolerance = None if self._auto_grid else 0.001
        ordered = order_points(self._raw_points, mode=self._ordering_mode, tolerance=tolerance, reverse=False, group_by_name=self._group_by_code)
        if self._reverse_rows and self._ordering_mode.startswith("GRID_ZIGZAG"):
            # Reverse each detected row while retaining code-group boundaries.
            rebuilt = []
            current = None; rows = []
            for item in ordered:
                key = (item.group, item.row)
                if current is not None and key != current:
                    rows.append(current_items); current_items = []
                if current is None or key != current: current = key; current_items = []
                current_items.append(item)
            if 'current_items' in locals() and current_items: rows.append(current_items)
            ordered = [item for row in rows for item in reversed(row)]
        self._ordered = ordered
        self._points = [(item.point.name or "Point", float(item.point.src_x), float(item.point.src_y)) for item in ordered]
        self._draw(ordered)
        groups = len({item.group for item in ordered}) if self._group_by_code else 1
        self.order_status.setText(f"Zigzag ordering applied: {len(ordered)} points in {groups} independent code group(s). Paths never cross between codes.")
        self.total_label.setText(f"Total Points: {len(self._raw_points)}"); self.displayed_label.setText(f"Displayed: {len(ordered)}"); self.invalid_label.setText("Invalid: 0")

    def _canvas_changed(self, mode: str) -> None:
        self._canvas_mode = mode; self._apply_canvas_style()
        if hasattr(self, '_ordered'): self._draw(self._ordered)

    def _labels_changed(self, checked: bool) -> None:
        self._show_labels = checked
        if hasattr(self, '_ordered'): self._draw(self._ordered)

    def _point_size_changed(self, value: int) -> None:
        self._point_size = value
        if hasattr(self, '_ordered'): self._draw(self._ordered)

    def _label_size_changed(self, value: int) -> None:
        self._label_size = value
        if hasattr(self, '_ordered'): self._draw(self._ordered)

    def _apply_canvas_style(self) -> None:
        bg = "#0B1420" if self._canvas_mode == "Dark" else "#F7F9FC"; border = "#31527A"
        self.view.setStyleSheet(f"QGraphicsView#mapCanvas {{ background:{bg}; border:1px solid {border}; border-radius:8px; }}")

    def _draw(self, ordered) -> None:
        self.scene.clear()
        if not ordered: return
        min_x = min(float(item.point.src_x) for item in ordered); max_x = max(float(item.point.src_x) for item in ordered)
        min_y = min(float(item.point.src_y) for item in ordered); max_y = max(float(item.point.src_y) for item in ordered)
        dx = max(max_x - min_x, 1e-9); dy = max(max_y - min_y, 1e-9); width, height, margin = 1100.0, 680.0, 64.0
        light = self._canvas_mode == "Light"; bg = QColor("#F7F9FC") if light else QColor("#0B1420"); grid = QColor("#D6DEE9") if light else QColor("#263A53"); text_color = QColor("#172235") if light else QColor("#F4F8FF"); secondary_text = QColor("#52627A") if light else QColor("#AFC3DD"); point_color = QColor("#1769E0") if light else QColor("#29B6FF"); zigzag_color = QColor("#005DFF") if light else QColor("#35D7FF")
        self.scene.setBackgroundBrush(QBrush(bg)); self.scene.setSceneRect(0, 0, width, height)
        for i in range(1, 11):
            x = margin + i * (width - 2 * margin) / 11; y = margin + i * (height - 2 * margin) / 11
            self.scene.addLine(x, margin, x, height - margin, QPen(grid, 0.7)); self.scene.addLine(margin, y, width - margin, y, QPen(grid, 0.7))
        positions = {}
        for item in ordered:
            sx = margin + (float(item.point.src_x) - min_x) / dx * (width - 2 * margin); sy = height - (margin + (float(item.point.src_y) - min_y) / dy * (height - 2 * margin)); positions[id(item)] = (sx, sy)

        # Draw each code group's path independently. This is the critical fix:
        # no segment is ever drawn from the end of one code to the start of another.
        groups = {}
        for item in ordered: groups.setdefault(item.group, []).append(item)
        pen = QPen(zigzag_color, 2.0, Qt.PenStyle.DashLine)
        for group_items in groups.values():
            for a, b in zip(group_items, group_items[1:]):
                x1, y1 = positions[id(a)]; x2, y2 = positions[id(b)]; self.scene.addLine(x1, y1, x2, y2, pen)

        radius = self._point_size / 2.0
        for item in ordered:
            sx, sy = positions[id(item)]; point = self.scene.addEllipse(sx-radius, sy-radius, self._point_size, self._point_size, QPen(QColor("#FFFFFF"), 2.0), QBrush(point_color)); point.setZValue(10)
            point.setToolTip(f"{item.point.name}\nX: {float(item.point.src_x):.3f}\nY: {float(item.point.src_y):.3f}\nCode Group: {item.group}\nOrder: {item.number}")
            if self._show_labels:
                label = QGraphicsTextItem(f"{item.number}. {item.point.name}"); label.setDefaultTextColor(text_color); label.setFont(QFont("Segoe UI", self._label_size, QFont.Weight.Bold)); label.setPos(sx+radius+6, sy-self._label_size-4); label.setZValue(20); self.scene.addItem(label)
        x_label = QGraphicsTextItem(f"EASTING / X   {min_x:.3f}  →  {max_x:.3f}"); y_label = QGraphicsTextItem(f"NORTHING / Y   {min_y:.3f}  →  {max_y:.3f}")
        for item in (x_label, y_label): item.setDefaultTextColor(secondary_text); item.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold)); item.setZValue(30)
        x_label.setPos(margin, height-30); y_label.setPos(margin, 16); self.scene.addItem(x_label); self.scene.addItem(y_label); self._fit()

    def _fit(self) -> None:
        if self.scene.items(): self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-28,-28,28,28), Qt.AspectRatioMode.KeepAspectRatio)
