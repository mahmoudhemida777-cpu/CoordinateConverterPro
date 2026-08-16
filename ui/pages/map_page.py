from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QMessageBox, QGraphicsTextItem,
    QComboBox, QCheckBox, QSpinBox, QGroupBox
)
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from ui.widgets.workspace_bar import WorkspaceFileBar

SUPPORTED_FILTER = "Supported files (*.csv *.xlsx *.kml *.kmz *.txt);;All files (*.*)"


class MapPage(QWidget):
    """High-contrast professional offline survey-point map.

    The map canvas is deliberately independent from the global application theme.
    Light mode is the default so points and labels remain visible on every machine.
    Dark mode uses bright survey symbology and never falls back to black points.
    """

    def __init__(self) -> None:
        super().__init__()
        self.workspace_folder: str | None = None
        self.current_file: Path | None = None
        self._points: list[tuple[str, float, float]] = []
        self._canvas_mode = "Light"
        self._show_labels = True
        self._point_size = 10
        self._label_size = 9

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

        controls = QHBoxLayout()
        controls.setSpacing(8)
        open_btn = QPushButton("Open Coordinate File")
        open_btn.clicked.connect(self._open)
        controls.addWidget(open_btn)
        reload_btn = QPushButton("Reload Selected")
        reload_btn.clicked.connect(self._reload_selected)
        controls.addWidget(reload_btn)
        controls.addSpacing(8)
        controls.addWidget(QLabel("Map Background"))
        self.canvas_mode = QComboBox()
        self.canvas_mode.addItems(["Light", "Dark"])
        self.canvas_mode.setCurrentText("Light")
        self.canvas_mode.currentTextChanged.connect(self._canvas_changed)
        controls.addWidget(self.canvas_mode)
        self.labels_check = QCheckBox("Show Labels")
        self.labels_check.setChecked(True)
        self.labels_check.toggled.connect(self._labels_changed)
        controls.addWidget(self.labels_check)
        controls.addWidget(QLabel("Point Size"))
        self.point_size = QSpinBox()
        self.point_size.setRange(6, 22)
        self.point_size.setValue(self._point_size)
        self.point_size.valueChanged.connect(self._point_size_changed)
        controls.addWidget(self.point_size)
        controls.addWidget(QLabel("Label Size"))
        self.label_size = QSpinBox()
        self.label_size.setRange(7, 18)
        self.label_size.setValue(self._label_size)
        self.label_size.valueChanged.connect(self._label_size_changed)
        controls.addWidget(self.label_size)
        fit_btn = QPushButton("Fit Extents")
        fit_btn.clicked.connect(self._fit)
        controls.addWidget(fit_btn)
        controls.addStretch()
        root.addLayout(controls)

        self.workspace_label = QLabel("PROJECT WORKSPACE: Not selected")
        self.workspace_label.setObjectName("pageSubtitle")
        root.addWidget(self.workspace_label)

        canvas_box = QGroupBox("MAP VIEW")
        canvas_layout = QVBoxLayout(canvas_box)
        canvas_layout.setContentsMargins(8, 20, 8, 8)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("mapCanvas")
        self.view.setRenderHints(self.view.renderHints())
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setMinimumHeight(440)
        self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        canvas_layout.addWidget(self.view, 1)
        root.addWidget(canvas_box, 1)

        self._apply_canvas_style()

    def set_workspace_folder(self, folder: str | None) -> None:
        self.workspace_folder = folder
        self.workspace_label.setText(f"PROJECT WORKSPACE: {folder or 'Not selected'}")
        self.workspace_bar.set_folder(folder, self.current_file)
        if self.current_file and self.current_file.exists():
            self._load_path(str(self.current_file))

    def load_active_file(self, path: str) -> None:
        if not path or not Path(path).is_file():
            return
        self.current_file = Path(path).resolve()
        self.workspace_folder = str(self.current_file.parent)
        self.workspace_label.setText(f"PROJECT WORKSPACE: {self.workspace_folder}")
        self.workspace_bar.set_folder(self.workspace_folder, self.current_file)
        self._load_path(str(self.current_file))

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Coordinate File", self.workspace_folder or "", SUPPORTED_FILTER
        )
        if path:
            self.load_active_file(path)

    def _reload_selected(self) -> None:
        path = self.workspace_bar.selected_file()
        if path:
            self.load_active_file(path)

    def _load_path(self, path: str) -> None:
        try:
            file_path = Path(path)
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

            valid = [
                (str(p.name or "Point"), float(p.src_x), float(p.src_y))
                for p in points
                if p.src_x is not None and p.src_y is not None
            ]
            if not valid:
                raise ValueError("No valid X/Y points found in this file.")

            self.current_file = file_path.resolve()
            self._points = valid
            self._draw(valid)
            self.info.setText(f"{file_path.name}  |  {len(valid)} points loaded")
        except Exception as exc:
            self.scene.clear()
            self.info.setText(f"Load failed: {Path(path).name}")
            QMessageBox.critical(self, "Map Error", f"Could not load {Path(path).name}:\n{exc}")

    def _canvas_changed(self, mode: str) -> None:
        self._canvas_mode = mode
        self._apply_canvas_style()
        if self._points:
            self._draw(self._points)

    def _labels_changed(self, checked: bool) -> None:
        self._show_labels = checked
        if self._points:
            self._draw(self._points)

    def _point_size_changed(self, value: int) -> None:
        self._point_size = value
        if self._points:
            self._draw(self._points)

    def _label_size_changed(self, value: int) -> None:
        self._label_size = value
        if self._points:
            self._draw(self._points)

    def _apply_canvas_style(self) -> None:
        if self._canvas_mode == "Dark":
            self.view.setStyleSheet(
                "QGraphicsView#mapCanvas { background:#0B1420; border:1px solid #31527A; border-radius:8px; }"
            )
        else:
            self.view.setStyleSheet(
                "QGraphicsView#mapCanvas { background:#F7F9FC; border:1px solid #31527A; border-radius:8px; }"
            )

    def _draw(self, points: list[tuple[str, float, float]]) -> None:
        self.scene.clear()
        min_x = min(p[1] for p in points)
        max_x = max(p[1] for p in points)
        min_y = min(p[2] for p in points)
        max_y = max(p[2] for p in points)
        dx = max(max_x - min_x, 1e-9)
        dy = max(max_y - min_y, 1e-9)
        width, height, margin = 1100.0, 680.0, 64.0

        light = self._canvas_mode == "Light"
        bg = QColor("#F7F9FC") if light else QColor("#0B1420")
        grid = QColor("#D6DEE9") if light else QColor("#263A53")
        text_color = QColor("#172235") if light else QColor("#F4F8FF")
        secondary_text = QColor("#52627A") if light else QColor("#AFC3DD")
        point_color = QColor("#1769E0") if light else QColor("#29B6FF")
        point_outline = QColor("#FFFFFF")
        zigzag_color = QColor("#005DFF") if light else QColor("#35D7FF")

        self.scene.setBackgroundBrush(QBrush(bg))
        self.scene.setSceneRect(0, 0, width, height)

        # Subtle grid, intentionally low contrast so it never competes with points.
        for i in range(1, 11):
            x = margin + i * (width - 2 * margin) / 11
            y = margin + i * (height - 2 * margin) / 11
            self.scene.addLine(x, margin, x, height - margin, QPen(grid, 0.7))
            self.scene.addLine(margin, y, width - margin, y, QPen(grid, 0.7))

        positions: list[tuple[str, float, float]] = []
        for name, x, y in points:
            sx = margin + (x - min_x) / dx * (width - 2 * margin)
            sy = height - (margin + (y - min_y) / dy * (height - 2 * margin))
            positions.append((name, sx, sy))

        if len(positions) > 1:
            pen = QPen(zigzag_color, 2.0, Qt.PenStyle.DashLine)
            for (_, x1, y1), (_, x2, y2) in zip(positions, positions[1:]):
                self.scene.addLine(x1, y1, x2, y2, pen)

        radius = self._point_size / 2.0
        for index, (name, sx, sy) in enumerate(positions, 1):
            point = self.scene.addEllipse(
                sx - radius, sy - radius, self._point_size, self._point_size,
                QPen(point_outline, 2.0), QBrush(point_color)
            )
            point.setZValue(10)
            point.setToolTip(f"{name}\nX: {points[index - 1][1]:.3f}\nY: {points[index - 1][2]:.3f}")

            if self._show_labels:
                label = QGraphicsTextItem(f"{index}. {name}")
                label.setDefaultTextColor(text_color)
                label.setFont(QFont("Segoe UI", self._label_size, QFont.Weight.Bold))
                label.setPos(sx + radius + 6, sy - self._label_size - 4)
                label.setZValue(20)
                self.scene.addItem(label)

        # Professional orientation/readout block.
        x_label = QGraphicsTextItem(f"EASTING / X   {min_x:.3f}  →  {max_x:.3f}")
        y_label = QGraphicsTextItem(f"NORTHING / Y   {min_y:.3f}  →  {max_y:.3f}")
        for item in (x_label, y_label):
            item.setDefaultTextColor(secondary_text)
            item.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            item.setZValue(30)
        x_label.setPos(margin, height - 30)
        y_label.setPos(margin, 16)
        self.scene.addItem(x_label)
        self.scene.addItem(y_label)
        self._fit()

    def _fit(self) -> None:
        if self.scene.items():
            self.view.fitInView(
                self.scene.itemsBoundingRect().adjusted(-28, -28, 28, 28),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
