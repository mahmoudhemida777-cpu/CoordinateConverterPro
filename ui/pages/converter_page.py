from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QGroupBox, QHeaderView, QSizePolicy, QStackedWidget,
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
    """CRS conversion workspace.

    The converter intentionally uses three internal pages so the controls never
    compete for vertical space:
      1) Source file + CRS selection
      2) Conversion results
      3) Export converted points

    Existing conversion/CAD/export logic is kept intact; only this page's
    presentation and navigation are changed.
    """

    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.source_points = []
        self.result_points = []
        self.current_file = None
        self.workspace_folder = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        title = QLabel(tr("CRS Converter"))
        title.setObjectName("pageTitle")
        title.setProperty("mhTextKey", "CRS Converter")
        title.setMinimumHeight(34)
        root.addWidget(title, 0)

        self.workspace_bar = WorkspaceFileBar()
        self.workspace_bar.file_selected.connect(self._load_path)
        self.workspace_bar.setFixedHeight(36)
        self.workspace_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(self.workspace_bar, 0)

        self._build_step_bar(root)

        self.stack = QStackedWidget()
        self.stack.setObjectName("crsConverterStack")
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(self.stack, 1)

        self._build_source_page()
        self._build_results_page()
        self._build_export_page()
        self._show_step(0)

    # ------------------------------------------------------------------
    # Three-page UI
    # ------------------------------------------------------------------
    def _build_step_bar(self, root: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(8)
        self.step_buttons = []
        labels = [
            tr("1  Source & CRS"),
            tr("2  Results"),
            tr("3  Export"),
        ]
        for index, text in enumerate(labels):
            button = QPushButton(text)
            button.setProperty("crsStep", True)
            button.setCheckable(True)
            button.setFixedHeight(36)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, i=index: self._show_step(i))
            self.step_buttons.append(button)
            bar.addWidget(button, 1)
        root.addLayout(bar, 0)

    def _show_step(self, index: int) -> None:
        index = max(0, min(index, 2))
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.step_buttons):
            button.setChecked(i == index)
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)

    def _nav_buttons(self, back_index: int, next_index: int | None):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        back = QPushButton(tr("◀ Previous"))
        back.setFixedSize(140, 38)
        back.clicked.connect(lambda: self._show_step(back_index))
        row.addWidget(back)
        row.addStretch(1)
        if next_index is not None:
            nxt = QPushButton(tr("Next ▶"))
            nxt.setObjectName("primaryButton")
            nxt.setFixedSize(140, 38)
            nxt.clicked.connect(lambda: self._show_step(next_index))
            row.addWidget(nxt)
        return row

    def _build_source_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        file_box = QGroupBox(tr("Source File"))
        file_layout = QHBoxLayout(file_box)
        file_layout.setContentsMargins(10, 10, 10, 10)
        file_layout.setSpacing(10)
        self.choose_btn = QPushButton(tr("SOURCE FILE"))
        self.choose_btn.setProperty("mhTextKey", "SOURCE FILE")
        self.choose_btn.setFixedSize(150, 40)
        self.choose_btn.clicked.connect(self._choose_file)
        file_layout.addWidget(self.choose_btn, 0)
        self.file_label = QLabel(tr("No file selected"))
        self.file_label.setProperty("mhTextKey", "No file selected")
        self.file_label.setWordWrap(False)
        self.file_label.setMinimumHeight(40)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        file_layout.addWidget(self.file_label, 1)
        layout.addWidget(file_box, 0)

        crs_row = QHBoxLayout()
        crs_row.setContentsMargins(0, 0, 0, 0)
        crs_row.setSpacing(14)
        self.source_picker = CRSPicker(self.engine, tr("SOURCE CRS"))
        self.target_picker = CRSPicker(self.engine, tr("TARGET CRS"))
        for picker in (self.source_picker, self.target_picker):
            picker.setMinimumHeight(285)
            picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            crs_row.addWidget(picker, 1)
        layout.addLayout(crs_row, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)
        self.convert_btn = QPushButton(tr("CONVERT"))
        self.convert_btn.setProperty("mhTextKey", "CONVERT")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.setFixedSize(150, 40)
        self.convert_btn.clicked.connect(self._run_conversion)
        action_row.addWidget(self.convert_btn, 0)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(8)
        action_row.addWidget(self.progress, 1)
        layout.addLayout(action_row, 0)
        layout.addLayout(self._nav_buttons(0, 1), 0)
        self.stack.addWidget(page)

    def _build_results_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        summary_box = QGroupBox()
        summary_box.setObjectName("conversionSummary")
        summary_box.setMinimumHeight(62)
        summary_layout = QHBoxLayout(summary_box)
        summary_layout.setContentsMargins(10, 6, 10, 6)
        summary_layout.setSpacing(8)
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
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setMinimumHeight(38)
            label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            summary_layout.addWidget(label, 1)
        layout.addWidget(summary_box, 0)

        self.results_table = QTableWidget(0, 9)
        self.results_table.setObjectName("conversionResultsTable")
        self.results_table.setHorizontalHeaderLabels([
            tr("Name"), tr("Src X"), tr("Src Y"), tr("Src Z"),
            tr("Tgt X"), tr("Tgt Y"), tr("Tgt Z"), tr("Status"), tr("Message"),
        ])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(90)
        self.results_table.verticalHeader().setDefaultSectionSize(28)
        self.results_table.verticalHeader().setMinimumSectionSize(28)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setWordWrap(False)
        self.results_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.results_table, 1)
        layout.addLayout(self._nav_buttons(0, 2), 0)
        self.stack.addWidget(page)

    def _build_export_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        info = QGroupBox(tr("Export Converted Points"))
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(12)
        self.export_file_label = QLabel(tr("No conversion results available."))
        self.export_file_label.setWordWrap(True)
        self.export_file_label.setMinimumHeight(46)
        info_layout.addWidget(self.export_file_label, 0)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(10)
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
            buttons_row.addWidget(button, 1)
        info_layout.addLayout(buttons_row, 0)
        layout.addWidget(info, 0)
        layout.addStretch(1)
        layout.addLayout(self._nav_buttons(1, None), 0)
        self.stack.addWidget(page)

    @staticmethod
    def _export_button(text: str, slot) -> QPushButton:
        button = QPushButton(tr(text))
        button.setProperty("mhTextKey", text)
        button.setFixedHeight(42)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(slot)
        return button

    # ------------------------------------------------------------------
    # Existing workspace/import/conversion logic
    # ------------------------------------------------------------------
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

    @staticmethod
    def _guess_dxf_crs(points):
        if not points:
            return None
        xs = [float(p.src_x) for p in points if p.src_x is not None]
        ys = [float(p.src_y) for p in points if p.src_y is not None]
        if not xs or not ys:
            return None
        if all(-180.0 <= x <= 180.0 for x in xs) and all(-90.0 <= y <= 90.0 for y in ys):
            return ("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)")
        if all(100000.0 <= x <= 900000.0 for x in xs) and all(0.0 <= y <= 10000000.0 for y in ys):
            return ("EPSG:32638", "WGS 84 / UTM zone 38N")
        return None

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
            QMessageBox.warning(self, tr("Import"), tr("No coordinate points were detected in the selected file."))
            return

        self.source_points = points
        self.result_points = []
        self.current_file = path
        self.file_label.setText(f"{Path(path).name} — {len(points)} {tr('points loaded')}")
        self.workspace_folder = str(Path(path).parent)
        self.workspace_bar.set_folder(self.workspace_folder, path)
        self.export_file_label.setText(f"{Path(path).name} — {len(points)} {tr('points loaded')}")

        if suffix in {".kml", ".kmz"}:
            self.source_picker.set_selected("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)")
        elif suffix in {".dxf", ".dwg"}:
            guessed = self._guess_dxf_crs(points)
            if guessed:
                self.source_picker.set_selected(*guessed)

        for button in (
            self.export_dxf_btn, self.export_civil_btn, self.export_xlsx_btn,
            self.export_csv_btn, self.export_txt_btn,
        ):
            button.setEnabled(False)
        self._show_step(0)

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
                self.result_points.append(self.engine.transform_points(src, tgt, [point], "auto")[0])
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

        self.export_file_label.setText(
            f"{Path(self.current_file).name if self.current_file else ''} — "
            f"{len(self.result_points)} {tr('converted points ready for export')}"
        )
        append_history({
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "file": Path(self.current_file).name if self.current_file else "",
            "source_crs": src,
            "target_crs": tgt,
            "points": len(self.result_points),
            "operation": selected_operation["description"],
            "status": "SUCCESS",
        })
        self._show_step(1)
        if zone_warnings or report.warnings:
            QMessageBox.information(self, tr("Warnings"), "\n".join(zone_warnings + [w.message for w in report.warnings]))

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
            values = [point.name, point.src_x, point.src_y, point.src_z, point.tgt_x, point.tgt_y, point.tgt_z, point.status, point.message]
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
        path, _ = QFileDialog.getSaveFileName(self, tr("Export AutoCAD / Civil 3D DXF"), "Converted_Points.dxf", "AutoCAD DXF (*.dxf)")
        if not path:
            return
        try:
            export_dxf(self.result_points, path, label_mode=LabelMode.NAME, text_height=1.0, use_target_coords=True)
            QMessageBox.information(self, tr("Export Complete"), f"{tr('DXF created successfully')}:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, tr("DXF Export Error"), str(exc))

    def _export_civil3d(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export Civil 3D PENZD"), "Civil3D_PENZD.csv", "CSV (*.csv)")
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
                    writer.writerow([i, f"{point.tgt_x:.{precision}f}", f"{point.tgt_y:.{precision}f}", f"{(point.tgt_z or 0):.{precision}f}", point.name or ""])
            QMessageBox.information(self, tr("Export Complete"), f"{tr('Civil 3D PENZD point file created')}:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, tr("Civil 3D Export Error"), str(exc))

    def _export_xlsx(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export XLSX"), "Project_Export.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        details = self.engine.get_crs_details(self.source_picker.selected_epsg())
        export_xlsx(self.result_points, path, self.source_picker.selected_epsg(), self.target_picker.selected_epsg(), details, current_precision())
        QMessageBox.information(self, tr("Exported"), f"{tr('Saved to')}: {path}")

    def _export_csv(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export CSV"), "Project_Export.csv", "CSV (*.csv)")
        if not path:
            return
        export_csv(self.result_points, path, current_precision())
        QMessageBox.information(self, tr("Exported"), f"{tr('Saved to')}: {path}")

    def _export_txt(self) -> None:
        if not self._require_results():
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export Survey TXT"), "Project_Export.txt", "Text files (*.txt)")
        if not path:
            return
        try:
            export_txt(self.result_points, path, current_precision())
            QMessageBox.information(self, tr("Export Complete"), f"{tr('TXT created successfully')}:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, tr("TXT Export Error"), str(exc))
