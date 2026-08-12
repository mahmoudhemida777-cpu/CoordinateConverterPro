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


SUPPORTED_FILTER = (
    "Supported coordinate files (*.kmz *.kml *.csv *.xlsx);;"
    "KMZ (*.kmz *.KMZ);;KML (*.kml *.KML);;"
    "CSV (*.csv *.CSV);;Excel (*.xlsx *.XLSX)"
)


class BatchPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.engine = CRSEngine()
        self.folder: str | None = None
        self.selected_files: list[Path] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)

        title = QLabel("MH GeoSuite Pro — Batch Converter")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        root.addWidget(title)

        folder_row = QHBoxLayout()
        self.choose_folder_btn = QPushButton(tr("Choose Folder"))
        self.choose_folder_btn.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.choose_folder_btn)

        self.choose_files_btn = QPushButton("Choose Files")
        self.choose_files_btn.clicked.connect(self._choose_files)
        folder_row.addWidget(self.choose_files_btn)

        self.refresh_btn = QPushButton("Refresh Scan")
        self.refresh_btn.clicked.connect(self._refresh_scan)
        folder_row.addWidget(self.refresh_btn)

        self.folder_label = QLabel("No folder/files selected")
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
        self.run_btn.setStyleSheet("background-color: #C9A227; color: white; font-weight: bold; padding: 8px 24px;")
        self.run_btn.clicked.connect(self._run_batch)
        root.addWidget(self.run_btn)

        self.progress_label = QLabel("Choose a folder or select files to begin.")
        root.addWidget(self.progress_label)
        self.progress = QProgressBar()
        root.addWidget(self.progress)

        self.results_list = QListWidget()
        root.addWidget(self.results_list)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        root.addWidget(self.summary_label)

    def _display_files(self, files: list[Path], source_text: str) -> None:
        self.selected_files = list(files)
        self.results_list.clear()
        self.progress.setValue(0)
        self.progress.setMaximum(max(len(files), 1))
        self.folder_label.setText(source_text)

        if not files:
            self.progress_label.setText(
                "0 supported files found. Supported: KMZ, KML, CSV, XLSX. "
                "Use Choose Files to select a file directly."
            )
            self.summary_label.setText("")
            return

        self.progress_label.setText(f"{len(files)} supported file(s) found")
        for path in files:
            self.results_list.addItem(QListWidgetItem(f"READY — {path.name}   |   {path}"))

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("Choose Folder"))
        if not folder:
            return
        self.folder = folder
        self._scan_folder()

    def _scan_folder(self) -> None:
        if not self.folder:
            return
        try:
            files = find_batch_files(self.folder)
        except Exception as exc:
            QMessageBox.critical(self, "Scan Error", f"Could not scan the folder:\n{exc}")
            return
        self._display_files(files, f"Folder: {self.folder}")

    def _refresh_scan(self) -> None:
        if self.folder:
            self._scan_folder()
        elif self.selected_files:
            self._display_files(self.selected_files, "Selected files")
        else:
            QMessageBox.information(self, "Nothing to refresh", "Choose a folder or files first.")

    def _choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose Coordinate Files", "", SUPPORTED_FILTER
        )
        if not paths:
            return
        self.folder = None
        files = [Path(p) for p in paths if Path(p).is_file()]
        self._display_files(files, f"Selected files: {len(files)}")

    def _parse_file(self, path: Path):
        suffix = path.suffix.casefold()
        if suffix == ".kmz":
            return kml_parser.parse_kmz_file(str(path))
        if suffix == ".kml":
            return kml_parser.parse_kml_file(str(path))
        if suffix == ".csv":
            cols = csv_parser.sniff_columns(str(path))
            if len(cols) < 3:
                raise ValueError("CSV must contain at least Name, X and Y columns")
            mapping = csv_parser.ColumnMapping(
                name_col=cols[0], x_col=cols[1], y_col=cols[2],
                z_col=cols[3] if len(cols) > 3 else None,
            )
            return csv_parser.parse_csv(str(path), mapping)
        if suffix == ".xlsx":
            cols = xlsx_parser.sniff_columns(str(path))
            if len(cols) < 3:
                raise ValueError("XLSX must contain at least Name, X and Y columns")
            mapping = xlsx_parser.ColumnMapping(
                name_col=cols[0], x_col=cols[1], y_col=cols[2],
                z_col=cols[3] if len(cols) > 3 else None,
            )
            return xlsx_parser.parse_xlsx(str(path), mapping)
        raise ValueError(f"Parser not implemented for {suffix} yet")

    def _run_batch(self) -> None:
        if self.folder:
            files = find_batch_files(self.folder)
            self.selected_files = list(files)
        else:
            files = list(self.selected_files)

        if not files:
            QMessageBox.warning(
                self, "No files",
                "No supported coordinate files are selected. "
                "Choose a folder or use Choose Files."
            )
            return

        src = self.source_picker.selected_epsg()
        tgt = self.target_picker.selected_epsg()
        if not src or not tgt:
            QMessageBox.warning(self, "No CRS", "Please select both a source and target CRS.")
            return

        self.progress.setMaximum(len(files))
        self.results_list.clear()
        self.run_btn.setEnabled(False)
        try:
            def process_one(path: Path) -> FileResult:
                try:
                    points = self._parse_file(path)
                    transformed = self.engine.transform_points(src, tgt, points)
                    out_path = path.with_name(path.stem + "_converted.xlsx")
                    export_xlsx(transformed, str(out_path), src, tgt)
                    success = sum(1 for p in transformed if p.status == "SUCCESS")
                    failed = sum(1 for p in transformed if p.status == "FAILED")
                    status = "SUCCESS" if failed == 0 else ("WARNING" if success > 0 else "FAILED")
                    return FileResult(str(path), status, len(transformed), success, failed)
                except Exception as exc:
                    return FileResult(str(path), "FAILED", message=str(exc))

            def progress_cb(i: int, total: int, path: Path) -> None:
                self.progress.setValue(i)
                self.progress_label.setText(f"File {i} / {total}: {path.name}")

            report = run_batch_from_files(files, process_one, progress_cb)
            self.results_list.clear()
            for r in report.results:
                self.results_list.addItem(QListWidgetItem(
                    f"[{r.status}] {Path(r.path).name} — "
                    f"{r.points_success}/{r.points_total} points {r.message}"
                ))
            self.summary_label.setText(
                f"Files: {len(report.results)}   Success: {report.success_count}   "
                f"Warnings: {report.warning_count}   Failed: {report.failed_count}"
            )
        finally:
            self.run_btn.setEnabled(True)


def run_batch_from_files(files: list[Path], process_one, progress_cb=None):
    """Run an already-selected file list without rescanning the filesystem."""
    from core.batch.batch_processor import BatchReport

    report = BatchReport()
    total = len(files)
    for i, path in enumerate(files, start=1):
        if progress_cb:
            progress_cb(i, total, path)
        try:
            result = process_one(path)
        except Exception as exc:
            result = FileResult(str(path), "FAILED", message=str(exc))
        report.results.append(result)
    return report
