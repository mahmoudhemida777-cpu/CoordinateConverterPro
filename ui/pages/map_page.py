from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QMessageBox, QGraphicsTextItem,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QGridLayout, QSizePolicy,
)

from core.models import PointResult
from core.point_ordering import order_points
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from ui.widgets.workspace_bar import WorkspaceFileBar

SUPPORTED_FILTER = "Supported files (*.csv *.xlsx *.kml *.kmz *.txt);;All files (*.*)"
GROUP_COLORS = [
    "#1769E0", "#E53935", "#00A878", "#8E44AD", "#F39C12",
    "#00A6A6", "#D81B60", "#6D4C41", "#3949AB", "#7CB342",
    "#FB8C00", "#00897B", "#5E35B1", "#C0CA33", "#F4511E",
]


class MapPage(QWidget):
    """Survey map with readable responsive controls and complete point loading."""

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
        self._fit_pending = False

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("MAP — SURVEY POINT PREVIEW")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.info = QLabel("No points loaded")
        self.info.setObjectName("pageSubtitle")
        self.info.setWordWrap(True)
        title_row.addWidget(self.info)
        root.addLayout(title_row)

        self.workspace_bar = WorkspaceFileBar()
        self.workspace_bar.file_selected.connect(self.load_active_file)
        root.addWidget(self.workspace_bar)

        controls_box = QGroupBox("MAP DISPLAY CONTROLS")
        controls_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        controls = QGridLayout(controls_box)
        controls.setContentsMargins(12, 20, 12, 12)
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(8)
        controls.setColumnStretch(0, 0)
        controls.setColumnStretch(1, 0)
        controls.setColumnStretch(2, 0)
        controls.setColumnStretch(3, 1)
        controls.setColumnStretch(4, 0)
        controls.setColumnStretch(5, 0)
        controls.setColumnStretch(6, 0)

        open_btn = self._control_button("Open Coordinate File", 170)
        open_btn.clicked.connect(self._open)
        controls.addWidget(open_btn, 0, 0, 1, 2)

        reload_btn = self._control_button("Reload Selected", 150)
        reload_btn.clicked.connect(self._reload_selected)
        controls.addWidget(reload_btn, 0, 2)

        bg_label = self._control_label("Background")
        controls.addWidget(bg_label, 0, 3, Qt.AlignmentFlag.AlignRight)
        self.canvas_mode = QComboBox()
        self.canvas_mode.addItems(["Light", "Dark"])
        self.canvas_mode.setMinimumWidth(90)
        self.canvas_mode.setMinimumHeight(40)
        self.canvas_mode.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.canvas_mode.currentTextChanged.connect(self._canvas_changed)
        controls.addWidget(self.canvas_mode, 0, 4)

        self.labels_check = QCheckBox("Show Labels")
        self.labels_check.setChecked(True)
        self.labels_check.setMinimumHeight(40)
        self.labels_check.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.labels_check.toggled.connect(self._labels_changed)
        controls.addWidget(self.labels_check, 0, 5)

        fit_btn = self._control_button("FIT ALL POINTS", 150)
        fit_btn.clicked.connect(self._fit)
        controls.addWidget(fit_btn, 0, 6)

        point_label = self._control_label("Point Size")
        controls.addWidget(point_label, 1, 0)
        self.point_size = QSpinBox()
        self.point_size.setRange(4, 18)
        self.point_size.setValue(self._point_size)
        self.point_size.setSuffix(" px")
        self.point_size.setMinimumWidth(100)
        self.point_size.setMinimumHeight(40)
        self.point_size.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.point_size.valueChanged.connect(self._point_size_changed)
        controls.addWidget(self.point_size, 1, 1)

        label_label = self._control_label("Label Size")
        controls.addWidget(label_label, 1, 2)
        self.label_size = QSpinBox()
        self.label_size.setRange(7, 16)
        self.label_size.setValue(self._label_size)
        self.label_size.setSuffix(" pt")
        self.label_size.setMinimumWidth(100)
        self.label_size.setMinimumHeight(40)
        self.label_size.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.label_size.valueChanged.connect(self._label_size_changed)
        controls.addWidget(self.label_size, 1, 3)

        hint = QLabel("All controls resize cleanly; point and label sizes are independent.")
        hint.setObjectName("pageSubtitle")
        hint.setWordWrap(True)
        controls.addWidget(hint, 1, 4, 1, 3)
        root.addWidget(controls_box)

        canvas_box = QGroupBox("MAP VIEW — ALL LOADED POINTS")
        canvas_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(6, 16, 6, 6)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("mapCanvas")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setMinimumHeight(480)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        canvas_layout.addWidget(self.view, 1)
        root.addWidget(canvas_box, 1)

        ordering_box = QGroupBox("ZIGZAG / GRID ORDERING")
        ol = QVBoxLayout(ordering_box)
        ol.setContentsMargins(10, 16, 10, 8)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(self._control_label("Ordering"))
        self.ordering_combo = QComboBox()
        self.ordering_combo.addItems(["Zigzag (Start West)", "Zigzag (Start East)", "Source Order"])
        self.ordering_combo.setMinimumWidth(170)
        self.ordering_combo.setMinimumHeight(40)
        self.ordering_combo.currentTextChanged.connect(self._ordering_changed)
        row1.addWidget(self.ordering_combo)
        row1.addWidget(self._control_label("Group"))
        self.group_combo = QComboBox()
        self.group_combo.addItems(["Point Code / Name", "All Points"])
        self.group_combo.setCurrentIndex(0)
        self.group_combo.setMinimumWidth(150)
        self.group_combo.setMinimumHeight(40)
        self.group_combo.currentTextChanged.connect(self._group_changed)
        row1.addWidget(self.group_combo)
        row1.addWidget(self._control_label("Start"))
        self.corner_combo = QComboBox()
        self.corner_combo.addItems(["North-West", "North-East"])
        self.corner_combo.setMinimumWidth(115)
        self.corner_combo.setMinimumHeight(40)
        self.corner_combo.currentTextChanged.connect(self._corner_changed)
        row1.addWidget(self.corner_combo)
        self.reverse_check = QCheckBox("Reverse Each Row")
        self.reverse_check.setMinimumHeight(40)
        self.reverse_check.toggled.connect(self._reverse_changed)
        row1.addWidget(self.reverse_check)
        self.grid_check = QCheckBox("Auto Detect Grid")
        self.grid_check.setChecked(True)
        self.grid_check.setMinimumHeight(40)
        self.grid_check.toggled.connect(self._grid_changed)
        row1.addWidget(self.grid_check)
        row1.addStretch(1)
        ol.addLayout(row1)
        self.order_status = QLabel("Zigzag is optional. Select Source Order to disable it.")
        self.order_status.setObjectName("pageSubtitle")
        self.order_status.setWordWrap(True)
        ol.addWidget(self.order_status)
        self.legend = QLabel("Code colors will appear here after loading points.")
        self.legend.setWordWrap(True)
        ol.addWidget(self.legend)
        root.addWidget(ordering_box, 0)

        totals = QHBoxLayout()
        self.total_label = QLabel("Total Points: 0")
        self.displayed_label = QLabel("Displayed: 0")
        self.invalid_label = QLabel("Invalid: 0")
        totals.addWidget(self.total_label)
        totals.addStretch(1)
        totals.addWidget(self.displayed_label)
        totals.addStretch(1)
        totals.addWidget(self.invalid_label)
        root.addLayout(totals)
        self._apply_canvas_style()

    @staticmethod
    def _control_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setMinimumHeight(40)
        label.setStyleSheet("font-size:12pt; padding:4px 6px;")
        return label

    @staticmethod
    def _control_button(text: str, minimum_width: int) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumWidth(minimum_width)
        button.setMinimumHeight(40)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet("font-size:12pt; padding:6px 12px;")
        return button

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._ordered:
            self._fit_pending = True
            QTimer.singleShot(0, self._fit)

    def set_workspace_folder(self, folder: str | None) -> None:
        self.workspace_folder = folder
        self.workspace_bar.set_folder(folder, self.current_file)
        selected = self.current_file if self.current_file and self.current_file.exists() else None
        if selected is None:
            selected = self.workspace_bar.selected_file()
        if selected and Path(selected).is_file():
            self.load_active_file(str(selected))

    def load_active_file(self, path: str) -> None:
        if path and Path(path).is_file():
            self.current_file = Path(path).resolve()
            self.workspace_folder = str(self.current_file.parent)
            self.workspace_bar.set_folder(self.workspace_folder, self.current_file)
            self._load_path(str(self.current_file))

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Coordinate File", self.workspace_folder or "", SUPPORTED_FILTER)
        if path:
            self.load_active_file(path)

    def _reload_selected(self) -> None:
        path = self.workspace_bar.selected_file()
        if path:
            self.load_active_file(path)

    def _load_path(self, path: str) -> None:
        file_path = Path(path)
        try:
            suffix = file_path.suffix.casefold()
            if suffix == ".kmz":
                points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml":
                points = kml_parser.parse_kml_file(path)
            elif suffix == ".txt":
                points = txt_parser.parse_txt(path)
            elif suffix == ".csv":
                points = csv_parser.parse_csv_auto(path)
            elif suffix == ".xlsx":
                points = xlsx_parser.parse_xlsx_auto(path)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")

            points = list(points or [])
            self._invalid_count = sum(1 for p in points if p.src_x is None or p.src_y is None)
            self._raw_points = [p for p in points if p.src_x is not None and p.src_y is not None]
            if not self._raw_points:
                raise ValueError("No valid X/Y points found in this file.")

            self.current_file = file_path.resolve()
            self._apply_ordering()
            self.info.setText(
                f"{file_path.name} | {len(self._raw_points)} points loaded"
                f" | {self._invalid_count} invalid"
            )
            self._fit_pending = True
            QTimer.singleShot(0, self._fit)
        except Exception as exc:
            self._raw_points = []
            self._ordered = []
            self._invalid_count = 0
            self.scene.clear()
            self.info.setText(f"Load failed: {file_path.name}")
            QMessageBox.critical(self, "Map Error", f"Could not load {file_path.name}:\n{exc}")

    def _ordering_changed(self, text: str) -> None:
        self._ordering_mode = "GRID_ZIGZAG_EAST" if "East" in text else ("SOURCE" if "Source" in text else "GRID_ZIGZAG_WEST")
        self._apply_ordering()

    def _group_changed(self, text: str) -> None:
        self._group_by_code = text == "Point Code / Name"
        self._apply_ordering()

    def _corner_changed(self, text: str) -> None:
        if self._ordering_mode.startswith("GRID_ZIGZAG"):
            self._ordering_mode = "GRID_ZIGZAG_EAST" if text == "North-East" else "GRID_ZIGZAG_WEST"
            self.ordering_combo.blockSignals(True)
            self.ordering_combo.setCurrentIndex(1 if text == "North-East" else 0)
            self.ordering_combo.blockSignals(False)
        self._apply_ordering()

    def _reverse_changed(self, checked: bool) -> None:
        self._reverse_rows = checked
        self._apply_ordering()

    def _grid_changed(self, checked: bool) -> None:
        self._auto_grid = checked
        self._apply_ordering()

    def _apply_ordering(self) -> None:
        if not self._raw_points:
            return
        tolerance = None if self._auto_grid else 0.001
        ordered = order_points(
            self._raw_points,
            mode=self._ordering_mode,
            tolerance=tolerance,
            reverse=False,
            group_by_name=self._group_by_code,
        )
        if self._reverse_rows and self._ordering_mode.startswith("GRID_ZIGZAG"):
            rows, current_key, current_items = [], None, []
            for item in ordered:
                key = (item.group, item.row)
                if current_key is not None and key != current_key:
                    rows.append(current_items)
                    current_items = []
                current_key = key
                current_items.append(item)
            if current_items:
                rows.append(current_items)
            ordered = [item for row in rows for item in reversed(row)]
        self._ordered = ordered
        self._draw(ordered)
        groups = len({item.group for item in ordered}) if self._group_by_code else 1
        if self._ordering_mode == "SOURCE":
            status = "Zigzag disabled — source order is used."
        else:
            status = f"Zigzag enabled — {len(ordered)} points in {groups} independent code group(s)."
        self.order_status.setText(status + " Each code has its own color; paths never connect different codes.")
        self.total_label.setText(f"Total Points: {len(self._raw_points)}")
        self.displayed_label.setText(f"Displayed: {len(ordered)}")
        self.invalid_label.setText(f"Invalid: {self._invalid_count}")

    def _canvas_changed(self, mode: str) -> None:
        self._canvas_mode = mode
        self._apply_canvas_style()
        if self._ordered:
            self._draw(self._ordered)

    def _labels_changed(self, checked: bool) -> None:
        self._show_labels = checked
        if self._ordered:
            self._draw(self._ordered)

    def _point_size_changed(self, value: int) -> None:
        self._point_size = value
        if self._ordered:
            self._draw(self._ordered)

    def _label_size_changed(self, value: int) -> None:
        self._label_size = value
        if self._ordered:
            self._draw(self._ordered)

    def _apply_canvas_style(self) -> None:
        bg = "#0B1420" if self._canvas_mode == "Dark" else "#F7F9FC"
        self.view.setStyleSheet(
            f"QGraphicsView#mapCanvas {{ background:{bg}; border:1px solid #31527A; border-radius:8px; }}"
        )

    def _draw(self, ordered) -> None:
        self.scene.clear()
        if not ordered:
            return

        min_x = min(float(item.point.src_x) for item in ordered)
        max_x = max(float(item.point.src_x) for item in ordered)
        min_y = min(float(item.point.src_y) for item in ordered)
        max_y = max(float(item.point.src_y) for item in ordered)
        dx = max(max_x - min_x, 1e-9)
        dy = max(max_y - min_y, 1e-9)
        width, height, margin = 1600.0, 1000.0, 90.0
        light = self._canvas_mode == "Light"
        bg = QColor("#F7F9FC") if light else QColor("#0B1420")
        grid = QColor("#D6DEE9") if light else QColor("#263A53")
        text_color = QColor("#172235") if light else QColor("#F4F8FF")
        secondary_text = QColor("#52627A") if light else QColor("#AFC3DD")
        self.scene.setBackgroundBrush(QBrush(bg))
        self.scene.setSceneRect(QRectF(0, 0, width, height))

        for i in range(1, 12):
            x = margin + i * (width - 2 * margin) / 13
            y = margin + i * (height - 2 * margin) / 13
            self.scene.addLine(x, margin, x, height - margin, QPen(grid, 0.7))
            self.scene.addLine(margin, y, width - margin, y, QPen(grid, 0.7))

        positions = {}
        for item in ordered:
            sx = margin + (float(item.point.src_x) - min_x) / dx * (width - 2 * margin)
            sy = height - (margin + (float(item.point.src_y) - min_y) / dy * (height - 2 * margin))
            positions[id(item)] = (sx, sy)

        groups: dict[str, list] = {}
        for item in ordered:
            groups.setdefault(str(item.group), []).append(item)
        color_map = {group: GROUP_COLORS[i % len(GROUP_COLORS)] for i, group in enumerate(groups)}
        legend_parts = []
        for group, group_items in groups.items():
            color = QColor(color_map[group])
            if self._ordering_mode != "SOURCE":
                pen = QPen(color, 2.6, Qt.PenStyle.DashLine)
                for a, b in zip(group_items, group_items[1:]):
                    x1, y1 = positions[id(a)]
                    x2, y2 = positions[id(b)]
                    self.scene.addLine(x1, y1, x2, y2, pen)
            legend_parts.append(f'<span style="color:{color.name()};"><b>●</b> {group}</span>')

        self.legend.setText("&nbsp;&nbsp;".join(legend_parts) if legend_parts else "No code groups")
        radius = self._point_size / 2.0
        for item in ordered:
            sx, sy = positions[id(item)]
            group_color = QColor(color_map[str(item.group)])
            point = self.scene.addEllipse(
                sx - radius, sy - radius, self._point_size, self._point_size,
                QPen(QColor("#FFFFFF"), 1.5), QBrush(group_color)
            )
            point.setZValue(10)
            point.setToolTip(
                f"{item.point.name}\n"
                f"X: {float(item.point.src_x):.3f}\n"
                f"Y: {float(item.point.src_y):.3f}\n"
                f"Code: {item.group}\n"
                f"Order: {item.number}"
            )
            if self._show_labels:
                label = QGraphicsTextItem(f"{item.number}. {item.point.name}")
                label.setDefaultTextColor(text_color)
                label.setFont(QFont("Segoe UI", self._label_size, QFont.Weight.Bold))
                label.setPos(sx + radius + 6, sy - self._label_size - 4)
                label.setZValue(20)
                self.scene.addItem(label)

        x_label = QGraphicsTextItem(f"EASTING / X   {min_x:.3f}  →  {max_x:.3f}")
        y_label = QGraphicsTextItem(f"NORTHING / Y   {min_y:.3f}  →  {max_y:.3f}")
        for label in (x_label, y_label):
            label.setDefaultTextColor(secondary_text)
            label.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            label.setZValue(30)
        x_label.setPos(margin, height - 30)
        y_label.setPos(margin, 16)
        self.scene.addItem(x_label)
        self.scene.addItem(y_label)
        self._fit_pending = True
        QTimer.singleShot(0, self._fit)

    def _fit(self) -> None:
        if not self._ordered or self.view.viewport().width() <= 0 or self.view.viewport().height() <= 0:
            return
        target = self.scene.sceneRect().adjusted(18, 18, -18, -18)
        self.view.resetTransform()
        self.view.fitInView(target, Qt.AspectRatioMode.KeepAspectRatio)
        self._fit_pending = False
