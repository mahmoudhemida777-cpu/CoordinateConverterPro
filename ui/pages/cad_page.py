from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox, QGroupBox,
)

from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser, xlsx_parser, kml_parser
from core.exporters.dxf_exporter import export_dxf, LabelMode
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.pages.import_page import ColumnMappingDialog


class CadPage(QWidget):
    """Convert survey coordinates and export directly to AutoCAD/Civil 3D."""

    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.source_points: list[PointResult] = []
        self.result_points: list[PointResult] = []
        self.current_file: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)

        title = QLabel("AutoCAD / Civil 3D Export")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        root.addWidget(title)
        root.addWidget(QLabel("Convert coordinates, then export a ready-to-open DXF or Civil 3D CSV point file."))

        row = QHBoxLayout()
        choose = QPushButton("Choose Coordinate File")
        choose.clicked.connect(self._choose_file)
        row.addWidget(choose)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color:#777;")
        row.addWidget(self.file_label)
        row.addStretch()
        root.addLayout(row)

        crs_row = QHBoxLayout()
        self.source_picker = CRSPicker(self.engine, tr("SOURCE CRS"))
        self.target_picker = CRSPicker(self.engine, tr("TARGET CRS"))
        crs_row.addWidget(self.source_picker)
        crs_row.addWidget(self.target_picker)
        root.addLayout(crs_row)

        convert = QPushButton("CONVERT FOR CAD / CIVIL 3D")
        convert.setStyleSheet("background-color:#C9A227;color:white;font-weight:bold;padding:9px 24px;")
        convert.clicked.connect(self._convert)
        root.addWidget(convert)

        self.progress = QProgressBar()
        root.addWidget(self.progress)

        summary = QGroupBox()
        sl = QHBoxLayout(summary)
        self.total = QLabel("Points: 0")
        self.success = QLabel("Success: 0")
        self.failed = QLabel("Failed: 0")
        for w in (self.total, self.success, self.failed):
            sl.addWidget(w)
        root.addWidget(summary)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Point", "Easting / X", "Northing / Y", "Elevation", "Status", "Message"])
        root.addWidget(self.table)

        export_row = QHBoxLayout()
        dxf = QPushButton("EXPORT DXF — AutoCAD / Civil 3D")
        dxf.clicked.connect(self._export_dxf)
        civil = QPushButton("EXPORT CSV — Civil 3D Points")
        civil.clicked.connect(self._export_civil3d_csv)
        export_row.addWidget(dxf)
        export_row.addWidget(civil)
        root.addLayout(export_row)

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Coordinate File", "",
            "Coordinate files (*.kmz *.kml *.csv *.xlsx);;All files (*.*)"
        )
        if not path:
            return
        try:
            suffix = Path(path).suffix.casefold()
            if suffix == ".kmz":
                points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml":
                points = kml_parser.parse_kml_file(path)
            elif suffix == ".csv":
                cols = csv_parser.sniff_columns(path)
                dlg = ColumnMappingDialog(cols, self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = csv_parser.parse_csv(path, csv_parser.ColumnMapping(**dlg.result_mapping()))
            elif suffix == ".xlsx":
                cols = xlsx_parser.sniff_columns(path)
                dlg = ColumnMappingDialog(cols, self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = xlsx_parser.parse_xlsx(path, xlsx_parser.ColumnMapping(**dlg.result_mapping()))
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", str(exc))
            return

        self.source_points = points
        self.result_points = []
        self.current_file = path
        self.file_label.setText(f"{Path(path).name} — {len(points)} points loaded")

    def _convert(self) -> None:
        if not self.source_points:
            QMessageBox.warning(self, "No data", "Choose a coordinate file first.")
            return
        src = self.source_picker.selected_epsg()
        tgt = self.target_picker.selected_epsg()
        if not src or not tgt:
            QMessageBox.warning(self, "No CRS", "Select both Source CRS and Target CRS.")
            return

        self.result_points = []
        self.progress.setMaximum(len(self.source_points))
        for i, point in enumerate(self.source_points, 1):
            self.result_points.append(self.engine.transform_points(src, tgt, [point])[0])
            self.progress.setValue(i)
        self._populate()

    def _populate(self) -> None:
        pts = self.result_points
        ok = sum(p.status == "SUCCESS" for p in pts)
        bad = sum(p.status == "FAILED" for p in pts)
        self.total.setText(f"Points: {len(pts)}")
        self.success.setText(f"Success: {ok}")
        self.failed.setText(f"Failed: {bad}")
        self.table.setRowCount(len(pts))
        for i, p in enumerate(pts):
            vals = [p.name, p.tgt_x, p.tgt_y, p.tgt_z, p.status, p.message]
            for j, value in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem("" if value is None else str(value)))

    def _export_dxf(self) -> None:
        if not self.result_points:
            QMessageBox.warning(self, "Nothing to export", "Run the conversion first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export DXF", "CAD_Points.dxf", "AutoCAD DXF (*.dxf)")
        if not path:
            return
        try:
            export_dxf(self.result_points, path, label_mode=LabelMode.NAME, text_height=1.0, use_target_coords=True)
            QMessageBox.information(self, "DXF Exported", f"DXF created successfully:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "DXF Export Error", str(exc))

    def _export_civil3d_csv(self) -> None:
        if not self.result_points:
            QMessageBox.warning(self, "Nothing to export", "Run the conversion first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Civil 3D CSV", "Civil3D_Points.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Point Number", "Easting", "Northing", "Elevation", "Description"])
                for i, p in enumerate(self.result_points, 1):
                    if p.tgt_x is None or p.tgt_y is None:
                        continue
                    writer.writerow([i, p.tgt_x, p.tgt_y, p.tgt_z or 0, p.name])
            QMessageBox.information(self, "Civil 3D CSV Exported", f"Civil 3D point file created:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "CSV Export Error", str(exc))
