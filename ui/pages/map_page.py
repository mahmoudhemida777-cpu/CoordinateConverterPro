from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QMessageBox, QGraphicsTextItem,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QGridLayout, QSizePolicy,
    QScrollArea, QFrame,
)

from core.models import PointResult
from core.point_ordering import order_points
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from core.cad_importer import extract_cad_points
from ui.widgets.workspace_bar import WorkspaceFileBar

SUPPORTED_FILTER = "Coordinate/CAD files (*.csv *.xlsx *.kml *.kmz *.txt *.dxf *.dwg);;All files (*.*)"
GROUP_COLORS = [
    "#1769E0", "#E53935", "#00A878", "#8E44AD", "#F39C12", "#00A6A6",
    "#D81B60", "#6D4C41", "#3949AB", "#7CB342", "#FB8C00", "#00897B",
    "#5E35B1", "#C0CA33", "#F4511E",
]


class MapPage(QWidget):
    """Survey map workbench: readable side controls + large all-points canvas."""

    def __init__(self) -> None:
        super().__init__()
        self.workspace_folder: str | None = None
        self.current_file: Path | None = None
        self._raw_points: list[PointResult] = []
        self._ordered = []
        self._canvas_mode = "Light"
        self._show_labels = True
        self._point_size = 10
        self._label_size = 9
        self._ordering_mode = "GRID_ZIGZAG_WEST"
        self._group_by_code = True
        self._reverse_rows = False
        self._auto_grid = True
        self._invalid_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)
        title_row = QHBoxLayout()
        title = QLabel("MAP — SURVEY POINT PREVIEW"); title.setObjectName("pageTitle")
        title_row.addWidget(title); title_row.addStretch(1)
        self.info = QLabel("No points loaded"); self.info.setObjectName("pageSubtitle"); self.info.setWordWrap(True)
        title_row.addWidget(self.info); root.addLayout(title_row)

        self.workspace_bar = WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self.load_active_file); root.addWidget(self.workspace_bar)

        workbench = QHBoxLayout(); workbench.setSpacing(10)
        panel = QScrollArea(); panel.setWidgetResizable(True); panel.setFrameShape(QFrame.Shape.NoFrame); panel.setFixedWidth(330); panel.setObjectName("mapControlPanel")
        panel_content = QWidget(); panel_layout = QVBoxLayout(panel_content); panel_layout.setContentsMargins(0, 0, 4, 0); panel_layout.setSpacing(8)

        display = QGroupBox("MAP DISPLAY CONTROLS"); dg = QGridLayout(display); dg.setContentsMargins(12, 22, 12, 12); dg.setHorizontalSpacing(8); dg.setVerticalSpacing(8)
        open_btn = self._control_button("Open Coordinate File"); open_btn.clicked.connect(self._open); dg.addWidget(open_btn, 0, 0, 1, 2)
        reload_btn = self._control_button("Reload Selected"); reload_btn.clicked.connect(self._reload_selected); dg.addWidget(reload_btn, 1, 0, 1, 2)
        fit_btn = self._control_button("FIT ALL POINTS"); fit_btn.clicked.connect(self._fit); dg.addWidget(fit_btn, 2, 0, 1, 2)
        dg.addWidget(self._control_label("Background"), 3, 0); self.canvas_mode = QComboBox(); self.canvas_mode.addItems(["Light", "Dark"]); self.canvas_mode.setMinimumHeight(40); self.canvas_mode.currentTextChanged.connect(self._canvas_changed); dg.addWidget(self.canvas_mode, 3, 1)
        dg.addWidget(self._control_label("Point Size"), 4, 0); self.point_size = QSpinBox(); self.point_size.setRange(4, 18); self.point_size.setValue(self._point_size); self.point_size.setSuffix(" px"); self.point_size.setMinimumHeight(40); self.point_size.valueChanged.connect(self._point_size_changed); dg.addWidget(self.point_size, 4, 1)
        dg.addWidget(self._control_label("Label Size"), 5, 0); self.label_size = QSpinBox(); self.label_size.setRange(7, 16); self.label_size.setValue(self._label_size); self.label_size.setSuffix(" pt"); self.label_size.setMinimumHeight(40); self.label_size.valueChanged.connect(self._label_size_changed); dg.addWidget(self.label_size, 5, 1)
        self.labels_check = QCheckBox("Show Labels"); self.labels_check.setChecked(True); self.labels_check.setMinimumHeight(40); self.labels_check.toggled.connect(self._labels_changed); dg.addWidget(self.labels_check, 6, 0, 1, 2)
        panel_layout.addWidget(display)

        ordering_box = QGroupBox("ZIGZAG / GRID ORDERING"); og = QGridLayout(ordering_box); og.setContentsMargins(12, 22, 12, 12); og.setHorizontalSpacing(8); og.setVerticalSpacing(8)
        og.addWidget(self._control_label("Ordering"), 0, 0, 1, 2); self.ordering_combo = QComboBox(); self.ordering_combo.addItems(["Zigzag (Start West)", "Zigzag (Start East)", "Source Order"]); self.ordering_combo.setMinimumHeight(40); self.ordering_combo.currentTextChanged.connect(self._ordering_changed); og.addWidget(self.ordering_combo, 1, 0, 1, 2)
        og.addWidget(self._control_label("Group"), 2, 0, 1, 2); self.group_combo = QComboBox(); self.group_combo.addItems(["Point Code / Name", "All Points"]); self.group_combo.setMinimumHeight(40); self.group_combo.currentTextChanged.connect(self._group_changed); og.addWidget(self.group_combo, 3, 0, 1, 2)
        og.addWidget(self._control_label("Start"), 4, 0, 1, 2); self.corner_combo = QComboBox(); self.corner_combo.addItems(["North-West", "North-East"]); self.corner_combo.setMinimumHeight(40); self.corner_combo.currentTextChanged.connect(self._corner_changed); og.addWidget(self.corner_combo, 5, 0, 1, 2)
        self.reverse_check = QCheckBox("Reverse Each Row"); self.reverse_check.setMinimumHeight(40); self.reverse_check.toggled.connect(self._reverse_changed); og.addWidget(self.reverse_check, 6, 0, 1, 2)
        self.grid_check = QCheckBox("Auto Detect Grid"); self.grid_check.setChecked(True); self.grid_check.setMinimumHeight(40); self.grid_check.toggled.connect(self._grid_changed); og.addWidget(self.grid_check, 7, 0, 1, 2)
        panel_layout.addWidget(ordering_box)
        self.order_status = QLabel("Zigzag is optional. Select Source Order to disable it."); self.order_status.setObjectName("pageSubtitle"); self.order_status.setWordWrap(True); panel_layout.addWidget(self.order_status)
        self.legend = QLabel("Code colors will appear here after loading points."); self.legend.setWordWrap(True); panel_layout.addWidget(self.legend)
        self.total_label = QLabel("Total Points: 0"); self.displayed_label = QLabel("Displayed: 0"); self.invalid_label = QLabel("Invalid: 0")
        for label in (self.total_label, self.displayed_label, self.invalid_label): label.setMinimumHeight(30); panel_layout.addWidget(label)
        panel_layout.addStretch(1); panel.setWidget(panel_content)
        workbench.addWidget(panel, 0)

        # Only the map viewport is enlarged; the rest of the Map page remains unchanged.
        canvas_box = QGroupBox("MAP VIEW — ALL LOADED POINTS"); canvas_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); canvas_box.setMinimumHeight(820); canvas_layout = QVBoxLayout(canvas_box); canvas_layout.setContentsMargins(6, 16, 6, 6)
        self.scene = QGraphicsScene(self); self.view = QGraphicsView(self.scene); self.view.setObjectName("mapCanvas"); self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); self.view.setMinimumHeight(760); self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter); self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter); canvas_layout.addWidget(self.view, 1); workbench.addWidget(canvas_box, 1)
        root.addLayout(workbench, 1)
        self._apply_canvas_style()

    @staticmethod
    def _control_label(text: str) -> QLabel:
        label = QLabel(text); label.setMinimumHeight(40); label.setWordWrap(True); return label

    @staticmethod
    def _control_button(text: str) -> QPushButton:
        button = QPushButton(text); button.setMinimumHeight(45); button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed); return button

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._ordered: QTimer.singleShot(0, self._fit)

    def set_workspace_folder(self, folder: str | None) -> None:
        self.workspace_folder = folder; self.workspace_bar.set_folder(folder, self.current_file)
        selected = self.current_file if self.current_file and self.current_file.exists() else self.workspace_bar.selected_file()
        if selected and Path(selected).is_file(): self.load_active_file(str(selected))

    def load_active_file(self, path: str) -> None:
        if path and Path(path).is_file():
            self.current_file = Path(path).resolve(); self.workspace_folder = str(self.current_file.parent); self.workspace_bar.set_folder(self.workspace_folder, self.current_file); self._load_path(str(self.current_file))

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Coordinate File", self.workspace_folder or "", SUPPORTED_FILTER)
        if path: self.load_active_file(path)

    def _reload_selected(self) -> None:
        path = self.workspace_bar.selected_file()
        if path: self.load_active_file(path)

    def _load_path(self, path: str) -> None:
        file_path = Path(path)
        try:
            suffix = file_path.suffix.casefold()
            if suffix in {".dxf", ".dwg", ".kmz", ".kml"}:
                points = extract_cad_points(path)
            elif suffix == ".txt": points = txt_parser.parse_txt(path)
            elif suffix == ".csv": points = csv_parser.parse_csv_auto(path)
            elif suffix == ".xlsx": points = xlsx_parser.parse_xlsx_auto(path)
            else: raise ValueError(f"Unsupported file type: {suffix}")
            points = list(points or [])
            self._invalid_count = sum(1 for p in points if p.src_x is None or p.src_y is None)
            self._raw_points = [p for p in points if p.src_x is not None and p.src_y is not None]
            if not self._raw_points: raise ValueError("No valid X/Y points found in this file.")
            self.current_file = file_path.resolve(); self._apply_ordering(); self.info.setText(f"{file_path.name} | {len(self._raw_points)} points loaded | {self._invalid_count} invalid"); QTimer.singleShot(0, self._fit)
        except Exception as exc:
            self._raw_points=[]; self._ordered=[]; self._invalid_count=0; self.scene.clear(); self.info.setText(f"Load failed: {file_path.name}"); QMessageBox.critical(self, "Map Error", f"Could not load {file_path.name}:\n{exc}")

    def _ordering_changed(self, text: str) -> None:
        self._ordering_mode = "GRID_ZIGZAG_EAST" if "East" in text else ("SOURCE" if "Source" in text else "GRID_ZIGZAG_WEST"); self._apply_ordering()
    def _group_changed(self, text: str) -> None: self._group_by_code = text == "Point Code / Name"; self._apply_ordering()
    def _corner_changed(self, text: str) -> None:
        if self._ordering_mode.startswith("GRID_ZIGZAG"):
            self._ordering_mode = "GRID_ZIGZAG_EAST" if text == "North-East" else "GRID_ZIGZAG_WEST"; self.ordering_combo.blockSignals(True); self.ordering_combo.setCurrentIndex(1 if text == "North-East" else 0); self.ordering_combo.blockSignals(False)
        self._apply_ordering()
    def _reverse_changed(self, checked: bool) -> None: self._reverse_rows = checked; self._apply_ordering()
    def _grid_changed(self, checked: bool) -> None: self._auto_grid = checked; self._apply_ordering()

    def _apply_ordering(self) -> None:
        if not self._raw_points: return
        tolerance = None if self._auto_grid else 0.001
        ordered = order_points(self._raw_points, mode=self._ordering_mode, tolerance=tolerance, reverse=False, group_by_name=self._group_by_code)
        if self._reverse_rows and self._ordering_mode.startswith("GRID_ZIGZAG"):
            rows=[]; current_key=None; current_items=[]
            for item in ordered:
                key=(item.group,item.row)
                if current_key is not None and key != current_key: rows.append(current_items); current_items=[]
                current_key=key; current_items.append(item)
            if current_items: rows.append(current_items)
            ordered=[item for row in rows for item in reversed(row)]
        self._ordered=ordered; self._draw(ordered)
        groups=len({item.group for item in ordered}) if self._group_by_code else 1
        status="Zigzag disabled — source order is used." if self._ordering_mode == "SOURCE" else f"Zigzag enabled — {len(ordered)} points in {groups} independent code group(s)."
        self.order_status.setText(status + " Each code has its own color; paths never connect different codes.")
        self.total_label.setText(f"Total Points: {len(self._raw_points)}"); self.displayed_label.setText(f"Displayed: {len(ordered)}"); self.invalid_label.setText(f"Invalid: {self._invalid_count}")

    def _canvas_changed(self, mode: str) -> None: self._canvas_mode=mode; self._apply_canvas_style(); self._draw(self._ordered) if self._ordered else None
    def _labels_changed(self, checked: bool) -> None: self._show_labels=checked; self._draw(self._ordered) if self._ordered else None
    def _point_size_changed(self, value: int) -> None: self._point_size=value; self._draw(self._ordered) if self._ordered else None
    def _label_size_changed(self, value: int) -> None: self._label_size=value; self._draw(self._ordered) if self._ordered else None

    def _apply_canvas_style(self) -> None:
        bg="#0B1420" if self._canvas_mode == "Dark" else "#F7F9FC"; self.view.setStyleSheet(f"QGraphicsView#mapCanvas {{ background:{bg}; border:1px solid #31527A; border-radius:8px; }}")

    def _draw(self, ordered) -> None:
        self.scene.clear()
        if not ordered: return
        min_x=min(float(item.point.src_x) for item in ordered); max_x=max(float(item.point.src_x) for item in ordered); min_y=min(float(item.point.src_y) for item in ordered); max_y=max(float(item.point.src_y) for item in ordered)
        dx=max(max_x-min_x,1e-9); dy=max(max_y-min_y,1e-9); width,height,margin=1600.0,1000.0,90.0; light=self._canvas_mode=="Light"; bg=QColor("#F7F9FC") if light else QColor("#0B1420"); grid=QColor("#D6DEE9") if light else QColor("#263A53"); text_color=QColor("#172235") if light else QColor("#F4F8FF"); secondary_text=QColor("#52627A") if light else QColor("#AFC3DD")
        self.scene.setBackgroundBrush(QBrush(bg)); self.scene.setSceneRect(QRectF(0,0,width,height))
        for i in range(1,12):
            x=margin+i*(width-2*margin)/13; y=margin+i*(height-2*margin)/13; self.scene.addLine(x,margin,x,height-margin,QPen(grid,0.7)); self.scene.addLine(margin,y,width-margin,y,QPen(grid,0.7))
        positions={}
        for item in ordered:
            sx=margin+(float(item.point.src_x)-min_x)/dx*(width-2*margin); sy=height-(margin+(float(item.point.src_y)-min_y)/dy*(height-2*margin)); positions[id(item)]=(sx,sy)
        groups={}
        for item in ordered: groups.setdefault(item.group,[]).append(item)
        for gi,(group,items) in enumerate(groups.items()):
            color=QColor(GROUP_COLORS[gi%len(GROUP_COLORS)]); pen=QPen(color,1.4)
            for a,b in zip(items,items[1:]): self.scene.addLine(positions[id(a)][0],positions[id(a)][1],positions[id(b)][0],positions[id(b)][1],pen)
            for idx,item in enumerate(items,1):
                x,y=positions[id(item)]; r=self._point_size/2; self.scene.addEllipse(x-r,y-r,2*r,2*r,QPen(color,1),QBrush(color));
                if self._show_labels:
                    text=QGraphicsTextItem(str(item.point.name or item.group or idx)); text.setDefaultTextColor(text_color); text.setFont(QFont("Arial",self._label_size)); text.setPos(x+r+3,y-r-4); self.scene.addItem(text)
        self.legend.setText("  ".join(f"■ {g}" for g in groups.keys()))

    def _fit(self) -> None:
        if self.scene.sceneRect().isNull(): return
        rect=self.scene.itemsBoundingRect()
        if rect.isNull(): rect=self.scene.sceneRect()
        self.view.fitInView(rect.adjusted(-40,-40,40,40), Qt.AspectRatioMode.KeepAspectRatio)
