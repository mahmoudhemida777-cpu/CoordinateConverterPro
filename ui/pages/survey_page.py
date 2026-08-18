from __future__ import annotations

import csv
import math
import re
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QMessageBox, QGridLayout, QScrollArea, QSizePolicy,
    QPlainTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QFrame,
)


class PolygonPreview(QWidget):
    """Lightweight vector preview for the calculated polygon."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points: list[tuple[float, float]] = []
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background:#0b1624;border:1px solid #263c55;border-radius:8px;")

    def set_points(self, points: list[tuple[float, float]]):
        self.points = list(points)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(18, 18, -18, -18)
        painter.fillRect(self.rect(), QBrush("#0b1624"))

        # Grid
        grid_pen = QPen("#172a3e")
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 10):
            x = rect.left() + rect.width() * i / 10
            y = rect.top() + rect.height() * i / 10
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        if len(self.points) < 3:
            painter.setPen(QPen("#74869a"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Polygon preview will appear after calculation")
            return

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        dx = max(max_x - min_x, 1e-9)
        dy = max(max_y - min_y, 1e-9)
        scale = min((rect.width() - 40) / dx, (rect.height() - 40) / dy)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2

        def map_point(p):
            return QPointF(
                rect.center().x() + (p[0] - cx) * scale,
                rect.center().y() - (p[1] - cy) * scale,
            )

        mapped = [map_point(p) for p in self.points]
        painter.setPen(QPen("#2389ff", 2.2))
        painter.setBrush(QBrush("#16375a"))
        from PySide6.QtGui import QPolygonF
        painter.drawPolygon(QPolygonF(mapped))

        painter.setFont(QFont("Segoe UI", 8))
        for i, point in enumerate(mapped, 1):
            painter.setPen(QPen("#8bc4ff", 2))
            painter.setBrush(QBrush("#0f6fd6"))
            painter.drawEllipse(point, 5, 5)
            painter.setPen(QPen("#d8e7f5"))
            painter.drawText(point + QPointF(8, -7), str(i))

        painter.setPen(QPen("#7e93aa"))
        painter.drawText(
            rect.adjusted(0, 0, -4, -4),
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
            f"Closed automatically ({len(self.points)} → 1)",
        )


class SurveyPage(QWidget):
    """Professional COGO survey calculations with a robust polygon workflow."""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setObjectName("surveyScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("surveyContent")
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content.setStyleSheet(self._style())
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(24, 18, 24, 24)
        root.setSpacing(14)

        title = QLabel("SURVEY TOOLS — COGO / FIELD CALCULATIONS")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        sub = QLabel("Functional survey calculations: inverse, coordinate deltas, bearing/azimuth, slope, grade and polygon area.")
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        self._build_inverse(root)
        self._build_results(root)
        self._build_polygon_area(root)
        root.addStretch(1)

    @staticmethod
    def _style() -> str:
        return """
        QWidget#surveyContent { background:#08131f; color:#e7eef7; }
        QLabel#pageTitle { font-size:20px; font-weight:700; color:#f5f8fb; }
        QLabel#pageSubtitle { color:#9eb0c4; font-size:12px; }
        QGroupBox { border:1px solid #29425c; border-radius:9px; margin-top:9px; padding-top:8px; background:#101e2d; color:#f3f7fb; font-weight:700; }
        QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#f1f6fb; }
        QLineEdit, QPlainTextEdit { background:#0b1827; color:#eef5fb; border:1px solid #29435d; border-radius:6px; padding:7px 9px; selection-background-color:#176cc1; }
        QLineEdit:focus, QPlainTextEdit:focus { border:1px solid #2c91ef; }
        QPushButton { background:#142a40; color:#e8f1fa; border:1px solid #2d4863; border-radius:6px; padding:8px 14px; min-height:38px; }
        QPushButton:hover { background:#1a3b59; }
        QPushButton#primaryButton { background:#0d72d4; border-color:#248ff0; font-weight:700; }
        QPushButton#primaryButton:hover { background:#1484ed; }
        QTabWidget::pane { border:1px solid #29435d; border-radius:6px; background:#0b1827; top:-1px; }
        QTabBar::tab { background:#12263a; color:#aebfd1; border:1px solid #29435d; padding:9px 20px; min-width:120px; }
        QTabBar::tab:selected { background:#0d72d4; color:white; border-color:#2389ef; }
        QTableWidget { background:#0b1827; color:#e7eef7; gridline-color:#29435d; border:1px solid #29435d; border-radius:6px; }
        QHeaderView::section { background:#132a43; color:#eef5fb; padding:7px; border:0; font-weight:700; }
        QLabel#surveyResultValue { color:#f1f6fb; font-weight:700; }
        QLabel#metricTitle { color:#9fb1c4; font-size:11px; }
        QLabel#metricValue { color:#f5f8fb; font-size:18px; font-weight:800; }
        QLabel#metricUnit { color:#8fa4ba; font-size:10px; }
        QLabel#accepted { color:#70d48d; font-weight:700; }
        """

    def _build_inverse(self, root):
        inverse = QGroupBox("1  TWO-POINT INVERSE / COGO")
        il = QVBoxLayout(inverse)
        il.setContentsMargins(18, 24, 18, 18)
        il.setSpacing(12)
        self.x1, self.y1, self.z1 = self._create_point_panel()
        self.x2, self.y2, self.z2 = self._create_point_panel()
        il.addWidget(self._point_box("POINT 1", self.x1, self.y1, self.z1))
        il.addWidget(self._point_box("POINT 2", self.x2, self.y2, self.z2))
        calc = QPushButton("CALCULATE INVERSE")
        calc.setObjectName("primaryButton")
        calc.clicked.connect(self._calculate)
        il.addWidget(calc)
        root.addWidget(inverse)

    def _build_results(self, root):
        results = QGroupBox("2  CALCULATION RESULTS")
        rg = QGridLayout(results)
        rg.setContentsMargins(18, 24, 18, 18)
        rg.setHorizontalSpacing(12)
        rg.setVerticalSpacing(10)
        self.result_labels = {}
        items = [("Horizontal Distance", "horizontal"), ("Slope Distance", "distance"), ("Azimuth", "azimuth"), ("Bearing", "bearing"), ("ΔX", "dx"), ("ΔY", "dy"), ("ΔZ", "dz"), ("Grade", "grade")]
        for i, (label_text, key) in enumerate(items):
            r, c = divmod(i, 2)
            cell = QFrame()
            cell.setStyleSheet("QFrame{background:#0b1827;border-radius:4px;}")
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(10, 6, 10, 6)
            label = QLabel(label_text)
            label.setMinimumWidth(135)
            value = QLabel("—")
            value.setObjectName("surveyResultValue")
            value.setMinimumHeight(34)
            cl.addWidget(label)
            cl.addWidget(value, 1)
            rg.addWidget(cell, r, c)
            self.result_labels[key] = value
        root.addWidget(results)

    def _build_polygon_area(self, root):
        area_box = QGroupBox("3  POLYGON AREA")
        ag = QVBoxLayout(area_box)
        ag.setContentsMargins(18, 24, 18, 18)
        ag.setSpacing(10)

        head = QHBoxLayout()
        instruction = QLabel("Enter 3 or more polygon vertices in order (clockwise or counter-clockwise).")
        instruction.setWordWrap(True)
        head.addWidget(instruction, 1)
        help_btn = QPushButton("?  How to use")
        help_btn.setMaximumWidth(130)
        help_btn.clicked.connect(self._show_polygon_help)
        head.addWidget(help_btn)
        ag.addLayout(head)

        method = QLabel("INPUT METHOD")
        method.setStyleSheet("font-weight:700;color:#b9c9d8;")
        ag.addWidget(method)

        self.area_tabs = QTabWidget()
        self.area_tabs.setObjectName("polygonInputTabs")
        self.area_tabs.addTab(self._paste_tab(), "▣  Paste Coordinates")
        self.area_tabs.addTab(self._table_tab(), "▦  Table Input")
        self.area_tabs.addTab(self._file_tab(), "⇧  File Import")
        self.area_tabs.currentChanged.connect(self._area_tab_changed)
        ag.addWidget(self.area_tabs)

        controls = QHBoxLayout()
        calc = QPushButton("▣  CALCULATE AREA")
        calc.setObjectName("primaryButton")
        calc.clicked.connect(self._area)
        clear = QPushButton("▣  CLEAR")
        clear.clicked.connect(self._clear_polygon)
        example = QPushButton("▧  EXAMPLE")
        example.clicked.connect(self._load_example)
        controls.addWidget(calc)
        controls.addWidget(clear)
        controls.addWidget(example)
        controls.addStretch(1)
        self.area_result = QLabel("Area: —")
        self.area_result.setObjectName("surveyResultValue")
        controls.addWidget(self.area_result)
        ag.addLayout(controls)

        results_title = QLabel("CALCULATION RESULTS")
        results_title.setStyleSheet("font-weight:700;color:#dce8f3;font-size:13px;")
        ag.addWidget(results_title)
        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.metric_area = self._metric("Area", "—", "square units")
        self.metric_vertices = self._metric("Number of Vertices", "—", "vertices")
        self.metric_perimeter = self._metric("Perimeter", "—", "units")
        self.metric_centroid = self._metric("Centroid (X, Y)", "—", "")
        self.metric_orientation = self._metric("Orientation", "—", "")
        for i, widget in enumerate((self.metric_area, self.metric_vertices, self.metric_perimeter, self.metric_centroid, self.metric_orientation)):
            metrics.addWidget(widget, 0, i)
            metrics.setColumnStretch(i, 1)
        ag.addLayout(metrics)

        lower = QHBoxLayout()
        table_box = QGroupBox("Vertices")
        tl = QVBoxLayout(table_box)
        self.vertex_table = QTableWidget(0, 3)
        self.vertex_table.setHorizontalHeaderLabels(["#", "X", "Y"])
        self.vertex_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.vertex_table.setMinimumHeight(180)
        tl.addWidget(self.vertex_table)
        lower.addWidget(table_box, 1)

        preview_box = QGroupBox("Polygon Preview")
        pl = QVBoxLayout(preview_box)
        self.polygon_preview = PolygonPreview()
        pl.addWidget(self.polygon_preview)
        lower.addWidget(preview_box, 1)
        ag.addLayout(lower)
        root.addWidget(area_box)

    def _paste_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        self.area_input = QPlainTextEdit()
        self.area_input.setObjectName("polygonCoordinatesInput")
        self.area_input.setPlaceholderText("X1,Y1; X2,Y2; X3,Y3; ...  or  X1,Y1,X2,Y2,X3,Y3,...")
        self.area_input.setMinimumHeight(130)
        self.area_input.setMaximumHeight(180)
        l.addWidget(QLabel("COORDINATES INPUT"))
        l.addWidget(self.area_input)
        note = QLabel("✓ Accepted: X,Y pairs separated by commas, semicolons, spaces, or new lines.")
        note.setObjectName("accepted")
        l.addWidget(note)
        return tab

    def _table_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        self.input_table = QTableWidget(4, 2)
        self.input_table.setHorizontalHeaderLabels(["X / Easting", "Y / Northing"])
        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for r in range(4):
            for c in range(2):
                self.input_table.setItem(r, c, QTableWidgetItem(""))
        row_buttons = QHBoxLayout()
        add = QPushButton("+ Add Vertex")
        remove = QPushButton("− Remove Vertex")
        add.clicked.connect(lambda: self.input_table.insertRow(self.input_table.rowCount()))
        remove.clicked.connect(lambda: self.input_table.removeRow(self.input_table.rowCount() - 1) if self.input_table.rowCount() > 3 else None)
        row_buttons.addWidget(add); row_buttons.addWidget(remove); row_buttons.addStretch(1)
        l.addWidget(self.input_table)
        l.addLayout(row_buttons)
        return tab

    def _file_tab(self):
        tab = QWidget()
        l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        self.area_file_label = QLabel("No coordinate file selected")
        self.area_file_label.setWordWrap(True)
        open_btn = QPushButton("Open Coordinate File")
        open_btn.clicked.connect(self._open_polygon_file)
        l.addWidget(self.area_file_label)
        l.addWidget(open_btn)
        l.addStretch(1)
        return tab

    def _metric(self, title, value, unit):
        w = QFrame()
        w.setStyleSheet("QFrame{background:#102033;border:1px solid #263d56;border-radius:8px;}")
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        t = QLabel(title); t.setObjectName("metricTitle")
        v = QLabel(value); v.setObjectName("metricValue")
        u = QLabel(unit); u.setObjectName("metricUnit")
        l.addWidget(t); l.addWidget(v); l.addWidget(u)
        w.value_label = v
        return w

    @staticmethod
    def _new_input(default: str = "") -> QLineEdit:
        edit = QLineEdit(default)
        edit.setPlaceholderText("Enter numeric value")
        edit.setFixedHeight(42)
        edit.setMinimumSize(0, 42)
        edit.setMaximumHeight(42)
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return edit

    def _create_point_panel(self):
        return self._new_input(), self._new_input(), self._new_input("0")

    @staticmethod
    def _point_box(title, x, y, z):
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setContentsMargins(12, 22, 12, 12)
        grid.setHorizontalSpacing(10); grid.setVerticalSpacing(8); grid.setColumnStretch(1, 1)
        for row, (text, edit) in enumerate((("Easting / X", x), ("Northing / Y", y), ("Elevation / Z", z))):
            grid.addWidget(QLabel(text), row, 0); grid.addWidget(edit, row, 1)
        return box

    def _numbers(self):
        try:
            return tuple(float(w.text().strip()) for w in (self.x1, self.y1, self.z1, self.x2, self.y2, self.z2))
        except ValueError as exc:
            raise ValueError("Enter valid numeric coordinates for both points.") from exc

    @staticmethod
    def _bearing(dx, dy):
        if abs(dx) < 1e-12 and abs(dy) < 1e-12: return "—"
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        if dx >= 0 and dy >= 0: return f"N {angle:.6f}° E"
        if dx >= 0 and dy < 0: return f"S {180-angle:.6f}° E"
        if dx < 0 and dy < 0: return f"S {180-angle:.6f}° W"
        return f"N {angle:.6f}° W"

    def _calculate(self):
        try:
            x1, y1, z1, x2, y2, z2 = self._numbers()
            dx, dy, dz = x2-x1, y2-y1, z2-z1
            horizontal = math.hypot(dx, dy)
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            azimuth = (math.degrees(math.atan2(dx, dy)) + 360) % 360
            grade = dz / horizontal * 100 if horizontal > 1e-12 else 0
            values = {"horizontal":f"{horizontal:.3f}","distance":f"{distance:.3f}","azimuth":f"{azimuth:.6f}°","bearing":self._bearing(dx,dy),"dx":f"{dx:.3f}","dy":f"{dy:.3f}","dz":f"{dz:.3f}","grade":f"{grade:.3f}%"}
            for k, v in values.items(): self.result_labels[k].setText(v)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))

    @staticmethod
    def _parse_points(text):
        tokens = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text or "")
        if len(tokens) < 6 or len(tokens) % 2: raise ValueError
        return [(float(tokens[i]), float(tokens[i+1])) for i in range(0, len(tokens), 2)]

    def _points_from_table(self):
        pts=[]
        for r in range(self.input_table.rowCount()):
            x=self.input_table.item(r,0); y=self.input_table.item(r,1)
            if not x or not y or not x.text().strip() and not y.text().strip(): continue
            try: pts.append((float(x.text()),float(y.text())))
            except ValueError: raise ValueError
        if len(pts)<3: raise ValueError
        return pts

    def _current_polygon_points(self):
        idx = self.area_tabs.currentIndex()
        if idx == 0: return self._parse_points(self.area_input.toPlainText())
        if idx == 1: return self._points_from_table()
        return self._parse_points(getattr(self, "_file_text", ""))

    def _area(self):
        try:
            pts = self._current_polygon_points()
            area = abs(sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))/2)
            perimeter = sum(math.hypot(pts[(i+1)%len(pts)][0]-pts[i][0], pts[(i+1)%len(pts)][1]-pts[i][1]) for i in range(len(pts)))
            signed = sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))/2
            orientation = "Counter-Clockwise" if signed > 0 else "Clockwise"
            cross = sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
            if abs(cross) > 1e-12:
                cx = sum((pts[i][0]+pts[(i+1)%len(pts)][0])*(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1]) for i in range(len(pts)))/(3*cross)
                cy = sum((pts[i][1]+pts[(i+1)%len(pts)][1])*(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1]) for i in range(len(pts)))/(3*cross)
            else: cx=cy=float("nan")
            self.area_result.setText(f"Area: {area:.3f} square units — {len(pts)} vertices")
            self.metric_area.value_label.setText(f"{area:.3f}")
            self.metric_vertices.value_label.setText(str(len(pts)))
            self.metric_perimeter.value_label.setText(f"{perimeter:.3f}")
            self.metric_centroid.value_label.setText(f"{cx:.3f}\n{cy:.3f}" if math.isfinite(cx) else "—")
            self.metric_orientation.value_label.setText(orientation)
            self._fill_vertex_table(pts)
            self.polygon_preview.set_points(pts)
        except ValueError:
            QMessageBox.warning(self, "Invalid Polygon", "Enter 3 or more vertices as X,Y pairs. Example: X1,Y1; X2,Y2; X3,Y3; X4,Y4; ...")

    def _fill_vertex_table(self, pts):
        self.vertex_table.setRowCount(len(pts))
        for i,(x,y) in enumerate(pts,1):
            self.vertex_table.setItem(i-1,0,QTableWidgetItem(str(i)))
            self.vertex_table.setItem(i-1,1,QTableWidgetItem(f"{x:.3f}"))
            self.vertex_table.setItem(i-1,2,QTableWidgetItem(f"{y:.3f}"))

    def _area_tab_changed(self, index):
        if index == 0 and hasattr(self, "area_input"): return

    def _load_example(self):
        self.area_tabs.setCurrentIndex(0)
        self.area_input.setPlainText("0,0; 10,0; 10,5; 0,5")
        self._area()

    def _clear_polygon(self):
        self.area_input.clear()
        self.input_table.clearContents()
        self._file_text = ""
        self.area_file_label.setText("No coordinate file selected")
        self.vertex_table.setRowCount(0)
        self.polygon_preview.set_points([])
        self.area_result.setText("Area: —")
        for widget in (self.metric_area,self.metric_vertices,self.metric_perimeter,self.metric_centroid,self.metric_orientation): widget.value_label.setText("—")

    def _open_polygon_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Coordinate File", "", "Coordinate Files (*.csv *.txt);;All Files (*.*)")
        if not path: return
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
            # Preserve numeric coordinate pairs from common CSV/TXT survey exports.
            self._file_text = raw
            self.area_file_label.setText(f"Selected: {Path(path).name}")
            self.area_tabs.setCurrentIndex(2)
        except OSError as exc:
            QMessageBox.warning(self, "File Error", str(exc))

    def _show_polygon_help(self):
        QMessageBox.information(self, "Polygon Area — How to use", "Enter at least 3 vertices in boundary order.\n\nAccepted examples:\nX1,Y1; X2,Y2; X3,Y3; X4,Y4\n\nOr a flat list:\nX1,Y1,X2,Y2,X3,Y3,...\n\nThe polygon is closed automatically from the last vertex back to the first.")
