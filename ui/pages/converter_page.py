from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QSplitter, QMessageBox,
    QGroupBox, QComboBox,
)

from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser, xlsx_parser, kml_parser
from core.validation.validator import validate_points, validate_zone_consistency
from core.exporters.xlsx_exporter import export_xlsx
from core.exporters.csv_exporter import export_csv
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.pages.import_page import ColumnMappingDialog


class ConverterPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.source_points: list[PointResult] = []
        self.result_points: list[PointResult] = []
        self.current_file: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)

        title = QLabel(tr("CRS Converter"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        root.addWidget(title)

        # ---- File row ----
        file_row = QHBoxLayout()
        self.choose_btn = QPushButton(tr("SOURCE FILE"))
        self.choose_btn.clicked.connect(self._choose_file)
        file_row.addWidget(self.choose_btn)
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #777;")
        file_row.addWidget(self.file_label)
        file_row.addStretch()
        root.addLayout(file_row)

        # ---- CRS pickers ----
        splitter = QSplitter(Qt.Horizontal)
        self.source_picker = CRSPicker(self.engine, tr("SOURCE CRS"))
        self.target_picker = CRSPicker(self.engine, tr("TARGET CRS"))
        splitter.addWidget(self.source_picker)
        splitter.addWidget(self.target_picker)
        root.addWidget(splitter)

        # ---- Convert button + progress ----
        convert_row = QHBoxLayout()
        self.convert_btn = QPushButton(tr("CONVERT"))
        self.convert_btn.setStyleSheet(
            "background-color: #C9A227; color: white; font-weight: bold; padding: 8px 24px;"
        )
        self.convert_btn.clicked.connect(self._run_conversion)
        convert_row.addWidget(self.convert_btn)
        convert_row.addStretch()
        root.addLayout(convert_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)

        # ---- Summary ----
        summary_box = QGroupBox()
        summary_layout = QHBoxLayout(summary_box)
        self.total_label = QLabel(f"{tr('Total Points')}: 0")
        self.success_label = QLabel(f"{tr('Successful')}: 0")
        self.failed_label = QLabel(f"{tr('Failed')}: 0")
        self.warning_label = QLabel(f"{tr('Warnings')}: 0")
        for lbl in (self.total_label, self.success_label, self.failed_label, self.warning_label):
            summary_layout.addWidget(lbl)
        root.addWidget(summary_box)

        # ---- Results table ----
        self.results_table = QTableWidget(0, 9)
        self.results_table.setHorizontalHeaderLabels(
            ["Name", "Src X", "Src Y", "Src Z", "Tgt X", "Tgt Y", "Tgt Z", "Status", "Message"]
        )
        root.addWidget(self.results_table)

        # ---- Export row ----
        export_row = QHBoxLayout()
        self.export_xlsx_btn = QPushButton("Export XLSX")
        self.export_xlsx_btn.clicked.connect(self._export_xlsx)
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self._export_csv)
        export_row.addWidget(self.export_xlsx_btn)
        export_row.addWidget(self.export_csv_btn)
        export_row.addStretch()
        root.addLayout(export_row)

    # ------------------------------------------------------------------
    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose File"), "",
            "Supported files (*.kmz *.kml *.csv *.xlsx)"
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        try:
            if suffix == ".kmz":
                points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml":
                points = kml_parser.parse_kml_file(path)
            elif suffix == ".csv":
                columns = csv_parser.sniff_columns(path)
                dlg = ColumnMappingDialog(columns, self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = csv_parser.parse_csv(path, csv_parser.ColumnMapping(**dlg.result_mapping()))
            elif suffix == ".xlsx":
                columns = xlsx_parser.sniff_columns(path)
                dlg = ColumnMappingDialog(columns, self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = xlsx_parser.parse_xlsx(path, xlsx_parser.ColumnMapping(**dlg.result_mapping()))
            else:
                QMessageBox.warning(self, "Unsupported", f"Unsupported file type: {suffix}")
                return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Import Error", str(exc))
            return

        self.source_points = points
        self.current_file = path
        self.file_label.setText(Path(path).name)

    def _run_conversion(self) -> None:
        if not self.source_points:
            QMessageBox.warning(self, "No data", "Please choose a source file first.")
            return
        src = self.source_picker.selected_epsg()
        tgt = self.target_picker.selected_epsg()
        if not src or not tgt:
            QMessageBox.warning(self, "No CRS", "Please select both a source and target CRS.")
            return

        report = validate_points(self.source_points)
        zone_warnings = validate_zone_consistency(src, tgt)

        self.progress.setMaximum(len(self.source_points))
        self.result_points = []
        for i, p in enumerate(self.source_points, start=1):
            transformed = self.engine.transform_points(src, tgt, [p])[0]
            self.result_points.append(transformed)
            self.progress.setValue(i)

        self._populate_results()

        if zone_warnings or report.warnings:
            msg = "\n".join(zone_warnings + [w.message for w in report.warnings])
            QMessageBox.information(self, "Warnings", msg)

    def _populate_results(self) -> None:
        pts = self.result_points
        total = len(pts)
        success = sum(1 for p in pts if p.status == "SUCCESS")
        failed = sum(1 for p in pts if p.status == "FAILED")
        warnings = sum(1 for p in pts if p.status == "WARNING")

        self.total_label.setText(f"{tr('Total Points')}: {total}")
        self.success_label.setText(f"{tr('Successful')}: {success}")
        self.failed_label.setText(f"{tr('Failed')}: {failed}")
        self.warning_label.setText(f"{tr('Warnings')}: {warnings}")

        self.results_table.setRowCount(total)
        for i, p in enumerate(pts):
            values = [p.name, p.src_x, p.src_y, p.src_z, p.tgt_x, p.tgt_y, p.tgt_z, p.status, p.message]
            for j, v in enumerate(values):
                self.results_table.setItem(i, j, QTableWidgetItem("" if v is None else str(v)))

    def _export_xlsx(self) -> None:
        if not self.result_points:
            QMessageBox.warning(self, "Nothing to export", "Run a conversion first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export XLSX", "Project_Export.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        details = self.engine.get_crs_details(self.source_picker.selected_epsg())
        export_xlsx(
            self.result_points, path,
            self.source_picker.selected_epsg(), self.target_picker.selected_epsg(),
            details,
        )
        QMessageBox.information(self, "Exported", f"Saved to {path}")

    def _export_csv(self) -> None:
        if not self.result_points:
            QMessageBox.warning(self, "Nothing to export", "Run a conversion first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "Project_Export.csv", "CSV (*.csv)")
        if not path:
            return
        export_csv(self.result_points, path)
        QMessageBox.information(self, "Exported", f"Saved to {path}")
