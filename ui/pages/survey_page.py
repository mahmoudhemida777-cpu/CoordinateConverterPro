from __future__ import annotations

import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFormLayout, QGroupBox, QMessageBox, QGridLayout, QDoubleSpinBox,
)


class SurveyPage(QWidget):
    """Professional COGO survey calculations with explicit, live result panels."""

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 22)
        root.setSpacing(12)

        title = QLabel("SURVEY TOOLS — COGO / FIELD CALCULATIONS")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        sub = QLabel(
            "Functional survey calculations: inverse, coordinate deltas, bearing/azimuth, slope, grade and polygon area."
        )
        sub.setWordWrap(True)
        root.addWidget(sub)

        box = QGroupBox("1  TWO-POINT INVERSE / COGO")
        form = QGridLayout(box)
        form.setContentsMargins(16, 24, 16, 16)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        fields = [
            ("Point 1 — Easting / X", "x1"), ("Point 1 — Northing / Y", "y1"), ("Point 1 — Elevation / Z", "z1"),
            ("Point 2 — Easting / X", "x2"), ("Point 2 — Northing / Y", "y2"), ("Point 2 — Elevation / Z", "z2"),
        ]
        for i, (label, attr) in enumerate(fields):
            edit = QLineEdit("0" if attr in {"z1", "z2"} else "")
            edit.setPlaceholderText("Enter numeric value")
            edit.setMinimumHeight(34)
            setattr(self, attr, edit)
            r, c = divmod(i, 2)
            form.addWidget(QLabel(label), r, c * 2)
            form.addWidget(edit, r, c * 2 + 1)
        calc = QPushButton("CALCULATE INVERSE")
        calc.setObjectName("primaryButton")
        calc.setMinimumHeight(40)
        calc.clicked.connect(self._calculate)
        form.addWidget(calc, 3, 0, 1, 4)
        root.addWidget(box)

        results = QGroupBox("2  CALCULATION RESULTS")
        rg = QGridLayout(results)
        rg.setContentsMargins(16, 24, 16, 16)
        self.result_labels = {}
        result_items = [
            ("Horizontal Distance", "horizontal"), ("Slope Distance", "distance"),
            ("Azimuth", "azimuth"), ("Bearing", "bearing"),
            ("ΔX", "dx"), ("ΔY", "dy"), ("ΔZ", "dz"), ("Grade", "grade"),
        ]
        for i, (label, key) in enumerate(result_items):
            r, c = divmod(i, 4)
            rg.addWidget(QLabel(label), r * 2, c)
            value = QLabel("—")
            value.setObjectName("surveyResultValue")
            rg.addWidget(value, r * 2 + 1, c)
            self.result_labels[key] = value
        root.addWidget(results)

        area_box = QGroupBox("3  POLYGON AREA")
        ag = QVBoxLayout(area_box)
        ag.setContentsMargins(16, 24, 16, 16)
        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("x1,y1; x2,y2; x3,y3; ...")
        self.area_input.setMinimumHeight(36)
        ag.addWidget(QLabel("Enter polygon vertices in order (clockwise or counter-clockwise):"))
        ag.addWidget(self.area_input)
        area_row = QHBoxLayout()
        area_btn = QPushButton("CALCULATE AREA")
        area_btn.setObjectName("primaryButton")
        area_btn.clicked.connect(self._area)
        area_row.addWidget(area_btn)
        self.area_result = QLabel("Area: —")
        self.area_result.setObjectName("surveyResultValue")
        area_row.addWidget(self.area_result, 1)
        ag.addLayout(area_row)
        root.addWidget(area_box)
        root.addStretch(1)

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
                "horizontal": f"{horizontal:.3f}", "distance": f"{distance:.3f}",
                "azimuth": f"{azimuth:.6f}°", "bearing": self._bearing(dx, dy),
                "dx": f"{dx:.3f}", "dy": f"{dy:.3f}", "dz": f"{dz:.3f}", "grade": f"{grade:.3f}%",
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
