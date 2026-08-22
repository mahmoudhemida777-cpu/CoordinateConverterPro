from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QSplitter, QMessageBox,
    QGroupBox, QHeaderView, QSizePolicy,
)

from core.crs.engine import CRSEngine
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from core.validation.validator import validate_points, validate_zone_consistency
from core.exporters.xlsx_exporter import export_xlsx
from core.exporters.csv_exporter import export_csv
from core.exporters.txt_exporter import export_txt
from core.exporters.dxf_exporter import export_dxf, LabelMode
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.widgets.workspace_bar import WorkspaceFileBar
from ui.pages.import_page import ColumnMappingDialog
from ui.pages.history_page import append_history
from ui.pages.settings_page import current_precision
from core.cad_importer import extract_cad_points


class ConverterPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.source_points = []
        self.result_points = []
        self.current_file = None
        self.workspace_folder = None

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 10, 18, 12)
        root.setSpacing(8)

        title = QLabel(tr("CRS Converter"))
        title.setObjectName("pageTitle")
        title.setProperty("mhTextKey", "CRS Converter")
        title.setMinimumHeight(32)
        root.addWidget(title)

        self.workspace_bar = WorkspaceFileBar()
        self.workspace_bar.file_selected.connect(self._load_path)
        root.addWidget(self.workspace_bar)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self.choose_btn = QPushButton(tr("SOURCE FILE"))
        self.choose_btn.setProperty("mhTextKey", "SOURCE FILE")
        self.choose_btn.setMinimumWidth(145)
        self.choose_btn.setMinimumHeight(42)
        self.choose_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.choose_btn.clicked.connect(self._choose_file)
        file_row.addWidget(self.choose_btn, 0)
        self.file_label = QLabel(tr("No file selected"))
        self.file_label.setProperty("mhTextKey", "No file selected")
        self.file_label.setWordWrap(False)
        self.file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_row.addWidget(self.file_label, 1)
        root.addLayout(file_row)

        # Two equal responsive CRS panels. They grow to the reference size on
        # large displays and shrink safely on 768p displays without overlap.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setMinimumHeight(225)
        splitter.setMaximumHeight(305)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.source_picker = CRSPicker(self.engine, tr("SOURCE CRS"))
        self.target_picker = CRSPicker(self.engine, tr("TARGET CRS"))
        for picker in (self.source_picker, self.target_picker):
            picker.setMinimumHeight(225)
            picker.setMaximumHeight(305)
            picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            splitter.addWidget(picker)

        splitter.setSizes([1, 1])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 0)

        convert_row = QHBoxLayout()
        convert_row.setSpacing(10)
        self.convert_btn = QPushButton(tr("CONVERT"))
        self.convert_btn.setProperty("mhTextKey", "CONVERT")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.setMinimumHeight(42)
        self.convert_btn.setMinimumWidth(155)
        self.convert_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.convert_btn.clicked.connect(self._run_conversion)
        convert_row.addWidget(self.convert_btn, 0)
        convert_row.addStretch(1)
        root.addLayout(convert_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMinimumHeight(12)
        self.progress.setMaximumHeight(12)
        root.addWidget(self.progress)

        summary_box = QGroupBox()
        summary_box.setObjectName("conversionSummary")
        summary_box.setMinimumHeight(56)
        summary_box.setMaximumHeight(64)
        summary_layout = QHBoxLayout(summary_box)
        summary_layout.setContentsMargins(16, 7, 16, 7)
        summary_layout.setSpacing(18)
        self.total_label = QLabel(f"{tr('Total Points')}: 0")
        self.success_label = QLabel(f"{tr('Successful')}: 0")
        self.failed_label = QLabel(f"{tr('Failed')}: 0")
        self.warning_label = QLabel(f"{tr('Warnings')}: 0")
        for label, key in (
            (self.total_label, "Total Points"),
            (self.success_label, "Successful"),
            (self.failed_label, "Failed"),
            (self.warning_label, "Warnings"),
        ):
            label.setProperty("mhTextKey", key)
            label.setMinimumHeight(32)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            summary_layout.addWidget(label, 1)
        root.addWidget(summary_box, 0)

        self.results_table = QTableWidget(0, 9)
        self.results_table.setObjectName("conversionResultsTable")
        self.results_table.setHorizontalHeaderLabels([
            tr("Name"), tr("Src X"), tr("Src Y"), tr("Src Z"),
            tr("Tgt X"), tr("Tgt Y"), tr("Tgt Z"), tr("Status"), tr("Message"),
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setMinimumSectionSize(88)
        self.results_table.verticalHeader().setDefaultSectionSize(29)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setWordWrap(False)
        self.results_table.setMinimumHeight(90)
        self.results_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.results_table, 1)

        export_box = QGroupBox(tr("Export Converted Points"))
        export_box.setProperty("mhTitleKey", "Export Converted Points")
        export_box.setMinimumHeight(76)
        export_box.setMaximumHeight(94)
        export_row = QHBoxLayout(export_box)
        export_row.setContentsMargins(10, 10, 10, 9)
        export_row.setSpacing(8)
        self.export_dxf_btn = self._export_button("AutoCAD / Civil 3D — DXF", self._export_dxf)
        self.export_civil_btn = self._export_button("Civil 3D — PENZD CSV", self._export_civil3d)
        self.export_xlsx_btn = self._export_button("Excel XLSX", self._export_xlsx)
        self.export_csv_btn = self._export_button("Generic CSV", self._export_csv)
        self.export_txt_btn = self._export_button("Survey TXT", self._export_txt)
        for button in (
            self.export_dxf_btn, self.export_civil_btn, self.export_xlsx_btn,
            self.export_csv_btn, self.export_txt_btn,
        ):
            button.setEnabled(False)
            button.setMinimumHeight(44)
            button.setMaximumHeight(54)
            export_row.addWidget(button, 1)
        root.addWidget(export_box, 0)

    @staticmethod
    def _export_button(text: str, slot) -> QPushButton:
        button = QPushButton(tr(text))
        button.setProperty("mhTextKey", text)
        button.setMinimumHeight(44)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(slot)
        return button

    def set_workspace_folder(self, folder: str) -> None:
        self.workspace_folder = folder
        self.workspace_bar.set_folder(folder, self.current_file)

    def load_active_file(self, path: str) -> None:
        if path and Path(path).is_file():
            self.workspace_folder = str(Path(path).parent)
            self.workspace_bar.set_folder(self.workspace_folder, path)
            self._load_path(path)

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Choose File"),
            self.workspace_folder or "",
            "Supported coordinate/CAD (*.kmz *.kml *.dxf *.dwg *.csv *.xlsx *.txt);;"
            "CAD (*.dxf *.dwg);;Coordinate (*.csv *.xlsx *.txt *.kml *.kmz);;All files (*.*)",
        )
        if path:
            self._load_path(path)

    def _load_path(self, path: str) -> None:
        suffix = Path(path).suffix.casefold()
        try:
            if suffix in {".dxf", ".dwg"}:
                points = extract_cad_points(path)
            elif suffix == ".kmz":
                points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml":
                points = kml_parser.parse_kml_file(path)
            elif suffix == ".txt":
                points = txt_parser.parse_txt(path)
            elif suffix == ".csv":
                dlg = ColumnMappingDialog(csv_parser.sniff_columns(path), self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = csv_parser.parse_csv(path, csv_parser.ColumnMapping(**dlg.result_mapping()))
            elif suffix == ".xlsx":
                dlg = ColumnMappingDialog(xlsx_parser.sniff_columns(path), self)
                if dlg.exec() != dlg.Accepted:
                    return
                points = xlsx_parser.parse_xlsx(path, xlsx_parser.ColumnMapping(**dlg.result_mapping()))
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
        except Exception as exc:
            QMessageBox.critical(self, tr("Import Error"), str(exc))
            return

        points = list(points or [])
        if not points:
            QMessageBox.warning(
                self,
                tr("Import"),
                tr("No coordinate points were detected in the selected file."),
            )
            return

        self.source_points = points
        self.result_points = []
        self.current_file = path
        self.file_label.setProperty("mhTextKey", "")
        self.file_label.setText(f"{Path(path).name} — {len(points)} {tr('points loaded')}")
        self.workspace_folder = str(Path(path).parent)
        self.workspace_bar.set_folder(self.workspace_folder, path)

        if suffix in {".kml", ".kmz"}:
            self.source_picker.set_selected(
                "EPSG:4326",
                "WGS 84 — Geographic 2D (Latitude / Longitude)",
            )

        for button in (
            self.export_dxf_btn, self.export_civil_btn, self.export_xlsx_btn,
            self.export_csv_btn, self.export_txt_btn,
        ):
            button.setEnabled(False)

    def _run_conversion(self) -> None:
        if not self.source_points:
            QMessageBox.warning(self, tr("No data"), tr("Please choose a source file first."))
            return

        src = self.source_picker.selected_epsg()
        tgt = self.target_picker.selected_epsg()
        if not src or not tgt:
            QMessageBox.warning(self, tr("No CRS"), tr("Select both Source CRS and Target CRS."))
            return

        try:
            selected_operation = self.engine.get_selected_operation(src, tgt, "auto")
        except Exception as exc:
            QMessageBox.critical(self, tr("Transformation Error"), str(exc))
            return

        report = validate_points(self.source_points)
        zone_warnings = validate_zone_consistency(src, tgt)
        self.progress.setVisible(True)
        self.progress.setMaximum(len(self.source_points))
        self.progress.setValue(0)
        self.result_points = []

        try:
            for i, point in enumerate(self.source_points, 1):
                self.result_points.append(
                    self.engine.transform_points(src, tgt, [point], "auto")[0]
                )
                self.progress.setValue(i)
        finally:
            self.progress.setVisible(False)

        self._populate_results()
        enabled = bool(self.result_points)
        for button in (
            self.export_dxf_btn, self.export_civil_btn, self.export_xlsx_btn,
            self.export_csv_btn, self.export_txt_btn,
        ):
            button.setEnabled(enabled)

        append_history({
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "file": Path(self.current_file).name if self.current_file else "",
            "source_crs": src,
            "target_crs": tgt,
            "points": len(self.result_points),
            "operation": selected_operation["description"],
            "status": "SUCCESS",
        })

        if zone_warnings or report.warnings:
            QMessageBox.information(
                self,
                tr("Warnings"),
                "\n".join(zone_warnings + [w.message for w in report.warnings]),
            )

    def _fmt(self, value):
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return f"{value:.{current_precision()}f}"
        return str(value)

    def _populate_results(self) -> None:
        pts = self.result_points
        self.total_label.setText(f"{tr('Total Points')}: {len(pts)}")
        self.success_label.setText(f"{tr('Successful')}: {sum(p.status == 'SUCCESS' for p in pts)}")
        self.failed_label.setText(f"{tr('Failed')}: {sum(p.status == 'FAILED' for p in pts)}")
        self.warning_label.setText(f"{tr('Warnings')}: {sum(p.status == 'WARNING' for p in pts)}")
        self.results_table.setRowCount(len(pts))

        for i, point in enumerate(pts):
            values = [
                point.name, point.src_x, point.src_y, point.src_z,
                point.tgt_x, point.tgt_y, point.tgt_z, point.status, point.message,
            ]
            for j, value in enumerate(values):
                self.results_table.setItem(i, j, QTableWidgetItem(self._fmt(value)))

    def _require_results(self) -> bool:
        if not self.result_points:
            QMessageBox.warning(self, tr("Nothing to export"), tr("Run the conversion first."))
            return False
        return True

    def _export_dxf(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export AutoCAD / Civil 3D DXF"),
            "Converted_Points.dxf",
            "AutoCAD DXF (*.dxf)",
        )
        if not path:
            return
        try:
            export_dxf(
                self.result_points,
                path,
                label_mode=LabelMode.NAME,
                text_height=1.0,
                use_target_coords=True,
            )
            QMessageBox.information(
                self,
                tr("Export Complete"),
                f"{tr('DXF created successfully')}:\n{path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, tr("DXF Export Error"), str(exc))

    def _export_civil3d(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Civil 3D PENZD"),
            "Civil3D_PENZD.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            precision = current_precision()
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Point Number", "Easting", "Northing", "Elevation", "Description"])
                for i, point in enumerate(self.result_points, 1):
                    if point.tgt_x is None or point.tgt_y is None:
                        continue
                    writer.writerow([
                        i,
                        f"{point.tgt_x:.{precision}f}",
                        f"{point.tgt_y:.{precision}f}",
                        f"{(point.tgt_z or 0):.{precision}f}",
                        point.name or "",
                    ])
            QMessageBox.information(
                self,
                tr("Export Complete"),
                f"{tr('Civil 3D PENZD point file created')}:\n{path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, tr("Civil 3D Export Error"), str(exc))

    def _export_xlsx(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export XLSX"),
            "Project_Export.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        details = self.engine.get_crs_details(self.source_picker.selected_epsg())
        export_xlsx(
            self.result_points,
            path,
            self.source_picker.selected_epsg(),
            self.target_picker.selected_epsg(),
            details,
            current_precision(),
        )
        QMessageBox.information(self, tr("Exported"), f"{tr('Saved to')}: {path}")

    def _export_csv(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export CSV"),
            "Project_Export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        export_csv(self.result_points, path, current_precision())
        QMessageBox.information(self, tr("Exported"), f"{tr('Saved to')}: {path}")

    def _export_txt(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Survey TXT"),
            "Project_Export.txt",
            "Text files (*.txt)",
        )
        if not path:
            return
        try:
            export_txt(self.result_points, path, current_precision())
            QMessageBox.information(
                self,
                tr("Export Complete"),
                f"{tr('TXT created successfully')}:\n{path}",
            )
        except Exception as exc:
            QMessageBox.critical(self, tr("TXT Export Error"), str(exc))
