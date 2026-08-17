from __future__ import annotations

import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QMessageBox, QGridLayout, QScrollArea, QSizePolicy,
)


class SurveyPage(QWidget):
    """Professional COGO survey calculations with a robust responsive layout."""

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
        # Explicit page-local stylesheet: the application-wide QLineEdit rule
        # must not reduce the Survey Tools input touch target below 38 px.
        content.setStyleSheet("QLineEdit { min-height: 38px; }")
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(24, 18, 24, 24)
        root.setSpacing(14)

        title = QLabel("SURVEY TOOLS — COGO / FIELD CALCULATIONS")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        sub = QLabel(
            "Functional survey calculations: inverse, coordinate deltas, bearing/azimuth, slope, grade and polygon area."
        )
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        inverse = QGroupBox("1  TWO-POINT INVERSE / COGO")
        inverse.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        inverse_layout = QVBoxLayout(inverse)
        inverse_layout.setContentsMargins(18, 24, 18, 18)
        inverse_layout.setSpacing(14)

        points_row = QHBoxLayout()
        points_row.setSpacing(14)
        inverse_layout.addLayout(points_row)

        self.x1, self.y1, self.z1 = self._create_point_panel("POINT 1")
        self.x2, self.y2, self.z2 = self._create_point_panel("POINT 2")

        p1_box = self._point_box("POINT 1", self.x1, self.y1, self.z1)
        p2_box = self._point_box("POINT 2", self.x2, self.y2, self.z2)
        points_row.addWidget(p1_box, 1)
        points_row.addWidget(p2_box, 1)

        calc = QPushButton("CALCULATE INVERSE")
        calc.setObjectName("primaryButton")
        calc.setMinimumHeight(42)
        calc.setMaximumHeight(44)
        calc.clicked.connect(self._calculate)
        inverse_layout.addWidget(calc)
        root.addWidget(inverse)

        results = QGroupBox("2  CALCULATION RESULTS")
        results.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        rg = QGridLayout(results)
        rg.setContentsMargins(18, 24, 18, 18)
        rg.setHorizontalSpacing(14)
        rg.setVerticalSpacing(10)
        rg.setColumnStretch(0, 1)
        rg.setColumnStretch(1, 1)
        self.result_labels = {}
        result_items = [
            ("Horizontal Distance", "horizontal"),
            ("Slope Distance", "distance"),
            ("Azimuth", "azimuth"),
            ("Bearing", "bearing"),
            ("ΔX", "dx"),
            ("ΔY", "dy"),
            ("ΔZ", "dz"),
            ("Grade", "grade"),
        ]
        for i, (label_text, key) in enumerate(result_items):
            r, c = divmod(i, 2)
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(10, 6, 10, 6)
            cell_layout.setSpacing(10)
            label = QLabel(label_text)
            label.setMinimumWidth(135)
            value = QLabel("—")
            value.setObjectName("surveyResultValue")
            value.setMinimumHeight(34)
            value.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            cell_layout.addWidget(label)
            cell_layout.addWidget(value, 1)
            rg.addWidget(cell, r, c)
            self.result_labels[key] = value
        root.addWidget(results)

        area_box = QGroupBox("3  POLYGON AREA")
        area_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        ag = QVBoxLayout(area_box)
        ag.setContentsMargins(18, 24, 18, 18)
        ag.setSpacing(10)

        area_label = QLabel("Enter polygon vertices in order (clockwise or counter-clockwise):")
        area_label.setWordWrap(True)
        ag.addWidget(area_label)

        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("x1,y1; x2,y2; x3,y3; ...")
        self.area_input.setMinimumHeight(38)
        # Do not cap the maximum height: the page-local stylesheet adds
        # vertical padding to the minimum height, so a 42 px maximum can
        # become smaller than the effective minimum and fail the layout contract.
        ag.addWidget(self.area_input)

        area_row = QHBoxLayout()
        area_row.setSpacing(14)
        area_btn = QPushButton("CALCULATE AREA")
        area_btn.setObjectName("primaryButton")
        area_btn.setMinimumHeight(42)
        area_btn.setMaximumHeight(44)
        area_btn.clicked.connect(self._area)
        area_row.addWidget(area_btn, 0)

        self.area_result = QLabel("Area: —")
        self.area_result.setObjectName("surveyResultValue")
        self.area_result.setMinimumHeight(36)
        self.area_result.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        area_row.addWidget(self.area_result, 1)
        ag.addLayout(area_row)
        root.addWidget(area_box)
        root.addStretch(1)

    @staticmethod
    def _new_input(default: str = "") -> QLineEdit:
        edit = QLineEdit(default)
        edit.setPlaceholderText("Enter numeric value")
        edit.setFixedHeight(42)
        edit.setMinimumSize(0, 42)
        edit.setMaximumHeight(42)
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return edit

    def _create_point_panel(self, _title: str):
        return self._new_input(), self._new_input(), self._new_input("0")

    @staticmethod
    def _point_box(title: str, x: QLineEdit, y: QLineEdit, z: QLineEdit) -> QGroupBox:
        box = QGroupBox(title)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        grid = QGridLayout(box)
        grid.setContentsMargins(12, 22, 12, 12)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        for row, (text, edit) in enumerate((
            ("Easting / X", x),
            ("Northing / Y", y),
            ("Elevation / Z", z),
        )):
            label = QLabel(text)
            grid.addWidget(label, row, 0)
            grid.addWidget(edit, row, 1)
        return box

    def _numbers(self):
        try:
            return tuple(float(w.text().strip()) for w in (self.x1, self.y1, self.z1, self.x2, self.y2, self.z2))
        except ValueError as exc:
            raise ValueError("Enter valid numeric coordinates for both points.") from exc

    @staticmethod
    def _bearing(dx: float, dy: float) -> str:
        if abs(dx) < 1e-12 and abs(dy) < 1e-12:
            return "—"
        angle = math.degrees(math.atan2(abs(dx), abs(dy)))
        if dx >= 0 and dy >= 0:
            return f"N {angle:.6f}° E"
        if dx >= 0 and dy < 0:
            return f"S {180-angle:.6f}° E"
        if dx < 0 and dy < 0:
            return f"S {180-angle:.6f}° W"
        return f"N {angle:.6f}° W"

    def _calculate(self) -> None:
        try:
            x1, y1, z1, x2, y2, z2 = self._numbers()
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            horizontal = math.hypot(dx, dy)
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)
            azimuth = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            grade = (dz / horizontal * 100.0) if horizontal > 1e-12 else 0.0
            values = {
                "horizontal": f"{horizontal:.3f}",
                "distance": f"{distance:.3f}",
                "azimuth": f"{azimuth:.6f}°",
                "bearing": self._bearing(dx, dy),
                "dx": f"{dx:.3f}",
                "dy": f"{dy:.3f}",
                "dz": f"{dz:.3f}",
                "grade": f"{grade:.3f}%",
            }
            for key, value in values.items():
                self.result_labels[key].setText(value)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Input", str(exc))

    def _area(self) -> None:
        try:
            pts = []
            for token in self.area_input.text().split(';'):
                token = token.strip()
                if not token:
                    continue
                parts = [v.strip() for v in token.split(',')]
                if len(parts) != 2:
                    raise ValueError
                pts.append((float(parts[0]), float(parts[1])))
            if len(pts) < 3:
                raise ValueError
            area = abs(sum(
                pts[i][0] * pts[(i + 1) % len(pts)][1] -
                pts[(i + 1) % len(pts)][0] * pts[i][1]
                for i in range(len(pts))
            ) / 2.0)
            self.area_result.setText(f"Area: {area:.3f} square units")
        except ValueError:
            QMessageBox.warning(self, "Invalid Polygon", "Use at least 3 vertices: x,y; x,y; x,y")
