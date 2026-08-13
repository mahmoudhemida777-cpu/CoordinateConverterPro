from __future__ import annotations

import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout, QGroupBox, QMessageBox


class SurveyPage(QWidget):
    """Practical COGO survey calculations: distance, azimuth, delta and area."""

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        title = QLabel("Survey Tools — COGO")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;")
        root.addWidget(title)
        root.addWidget(QLabel("Calculate survey distances, azimuths, coordinate differences and polygon area."))

        box = QGroupBox("Two Point Calculation")
        form = QFormLayout(box)
        self.x1 = QLineEdit(); self.y1 = QLineEdit(); self.z1 = QLineEdit("0")
        self.x2 = QLineEdit(); self.y2 = QLineEdit(); self.z2 = QLineEdit("0")
        for w in (self.x1, self.y1, self.z1, self.x2, self.y2, self.z2):
            w.setPlaceholderText("numeric")
        form.addRow("Point 1 Easting / X", self.x1)
        form.addRow("Point 1 Northing / Y", self.y1)
        form.addRow("Point 1 Elevation", self.z1)
        form.addRow("Point 2 Easting / X", self.x2)
        form.addRow("Point 2 Northing / Y", self.y2)
        form.addRow("Point 2 Elevation", self.z2)
        calc = QPushButton("Calculate")
        calc.clicked.connect(self._calculate)
        form.addRow(calc)
        root.addWidget(box)

        self.result = QLabel("Distance: —\nHorizontal Distance: —\nAzimuth: —\nΔX: —   ΔY: —   ΔZ: —")
        self.result.setStyleSheet("font-size:15px;padding:12px;background:#F4F6F8;")
        root.addWidget(self.result)

        area_box = QGroupBox("Polygon Area")
        area_layout = QVBoxLayout(area_box)
        self.area_input = QLineEdit()
        self.area_input.setPlaceholderText("x1,y1; x2,y2; x3,y3; ...")
        area_layout.addWidget(self.area_input)
        area_btn = QPushButton("Calculate Area")
        area_btn.clicked.connect(self._area)
        area_layout.addWidget(area_btn)
        self.area_result = QLabel("Area: —")
        area_layout.addWidget(self.area_result)
        root.addWidget(area_box)
        root.addStretch()

    def _numbers(self):
        return tuple(float(w.text().strip()) for w in (self.x1, self.y1, self.z1, self.x2, self.y2, self.z2))

    def _calculate(self) -> None:
        try:
            x1, y1, z1, x2, y2, z2 = self._numbers()
            dx, dy, dz = x2-x1, y2-y1, z2-z1
            horizontal = math.hypot(dx, dy)
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            azimuth = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
            self.result.setText(f"Distance: {distance:.3f}\nHorizontal Distance: {horizontal:.3f}\nAzimuth: {azimuth:.6f}°\nΔX: {dx:.3f}   ΔY: {dy:.3f}   ΔZ: {dz:.3f}")
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Enter valid numeric coordinates.")

    def _area(self) -> None:
        try:
            pts = []
            for token in self.area_input.text().split(';'):
                x, y = [float(v.strip()) for v in token.split(',')]
                pts.append((x, y))
            if len(pts) < 3:
                raise ValueError
            area = abs(sum(pts[i][0]*pts[(i+1)%len(pts)][1] - pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts))) / 2.0)
            self.area_result.setText(f"Area: {area:.3f} square units")
        except ValueError:
            QMessageBox.warning(self, "Invalid polygon", "Use at least 3 points in the format: x,y; x,y; x,y")
