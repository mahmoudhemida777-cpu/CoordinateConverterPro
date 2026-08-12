from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QProgressBar, QListWidget, QListWidgetItem, QMessageBox,
)

from core.crs.engine import CRSEngine
from core.parsers import csv_parser, xlsx_parser, kml_parser
from core.exporters.xlsx_exporter import export_xlsx
from core.batch.batch_processor import find_batch_files, run_batch, FileResult
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker


class BatchPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.folder: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)

        title = QLabel(tr("Batch Converter"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        root.addWidget(title)

        folder_row = QHBoxLayout()
        self.choose_folder_btn = QPushButton(tr("Choose Folder"))
        self.choose_folder_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.choose_folder_btn)
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color: #777;")
        folder_row.addWidget(self.folder_label)
        folder_row.addStretch()
        root.addLayout(folder_row)

        crs_row = QHBoxLayout()
        self.source_picker = CRSPicker(self.engine, tr("SOURCE CRS"))
        self.target_picker = CRSPicker(self.engine, tr("TARGET CRS"))
        crs_row.addWidget(self.source_picker)
        crs_row.addWidget(self.target_picker)
        root.addLayout(crs_row)

        self.run_btn = QPushButton(tr("CONVERT"))
        self.run_btn.setStyleSheet(
            "background-color: #C9A227; color: white; font-weight: bold; padding: 8px 24px;"
        )
        self.run_btn.clicked.connect(self._run_batch)
        root.addWidget(self.run_btn)

        self.progress_label = QLabel("")
        root.addWidget(self.progress_label)
        self.progress = QProgressBar()
        root.addWidget(self.progress)

        self.results_list = QListWidget()
        root.addWidget(self.results_list)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        root.addWidget(self.summary_label)

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("Choose Folder"))
        if folder:
            self.folder = folder
            self.folder_label.setText(folder)
            n = len(find_batch_files(folder))
            self.progress_label.setText(f"{n} supported file(s) found")

    def _parse_file(self, path: Path):
        suffix = path.suffix.lower()
        if suffix == ".kmz":
            return kml_parser.parse_kmz_file(str(path))
        if suffix == ".kml":
            return kml_parser.parse_kml_file(str(path))
        if suffix == ".csv":
            cols = csv_parser.sniff_columns(str(path))
            mapping = csv_parser.ColumnMapping(
                name_col=cols[0] if cols else None,
                x_col=cols[1] if len(cols) > 1 else cols[0],
                y_col=cols[2] if len(cols) > 2 else cols[0],
                z_col=cols[3] if len(cols) > 3 else None,
            )
            return csv_parser.parse_csv(str(path), mapping)
        if suffix == ".xlsx":
            cols = xlsx_parser.sniff_columns(str(path))
            mapping = xlsx_parser.ColumnMapping(
                name_col=cols[0] if cols else None,
                x_col=cols[1] if len(cols) > 1 else cols[0],
                y_col=cols[2] if len(cols) > 2 else cols[0],
                z_col=cols[3] if len(cols) > 3 else None,
            )
            return xlsx_parser.parse_xlsx(str(path), mapping)
        raise ValueError(f"Unsupported extension: {suffix}")

    def _run_batch(self) -> None:
        if not self.folder:
            QMessageBox.warning(self, "No folder", "Please choose a folder first.")
            return
        src = self.source_picker.selected_epsg()
        tgt = self.target_picker.selected_epsg()
        if not src or not tgt:
            QMessageBox.warning(self, "No CRS", "Please select both a source and target CRS.")
            return

        files = find_batch_files(self.folder)
        self.progress.setMaximum(len(files))
        self.results_list.clear()

        def process_one(path: Path) -> FileResult:
            points = self._parse_file(path)
            transformed = self.engine.transform_points(src, tgt, points)
            out_path = path.with_name(path.stem + "_converted.xlsx")
            export_xlsx(transformed, str(out_path), src, tgt)
            success = sum(1 for p in transformed if p.status == "SUCCESS")
            failed = sum(1 for p in transformed if p.status == "FAILED")
            status = "SUCCESS" if failed == 0 else ("WARNING" if success > 0 else "FAILED")
            return FileResult(str(path), status, len(transformed), success, failed)

        def progress_cb(i: int, total: int, path: Path) -> None:
            self.progress.setValue(i)
            self.progress_label.setText(f"File {i} / {total}: {path.name}")

        report = run_batch(self.folder, process_one, progress_cb)

        for r in report.results:
            item = QListWidgetItem(
                f"[{r.status}] {Path(r.path).name} — {r.points_success}/{r.points_total} points  {r.message}"
            )
            self.results_list.addItem(item)

        self.summary_label.setText(
            f"Success: {report.success_count}   Warnings: {report.warning_count}   Failed: {report.failed_count}"
        )
