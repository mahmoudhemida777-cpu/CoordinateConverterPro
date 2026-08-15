from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QComboBox, QDialog, QFormLayout, QDialogButtonBox, QMessageBox
from core.models import PointResult
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from ui.i18n import tr
from ui.widgets.workspace_bar import WorkspaceFileBar


class ColumnMappingDialog(QDialog):
    def __init__(self, columns: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Column Mapping")
        layout = QFormLayout(self)
        self.name_combo = QComboBox(); self.name_combo.addItems(["<none>"] + columns)
        self.x_combo = QComboBox(); self.x_combo.addItems(columns)
        self.y_combo = QComboBox(); self.y_combo.addItems(columns)
        self.z_combo = QComboBox(); self.z_combo.addItems(["<none>"] + columns)
        layout.addRow("Point Name →", self.name_combo); layout.addRow("X / Easting / Longitude →", self.x_combo); layout.addRow("Y / Northing / Latitude →", self.y_combo); layout.addRow("Z / Elevation →", self.z_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addRow(buttons)

    def result_mapping(self) -> dict:
        return {"name_col": None if self.name_combo.currentText() == "<none>" else self.name_combo.currentText(), "x_col": self.x_combo.currentText(), "y_col": self.y_combo.currentText(), "z_col": None if self.z_combo.currentText() == "<none>" else self.z_combo.currentText()}


class ImportPage(QWidget):
    points_imported = Signal(list)

    def __init__(self) -> None:
        super().__init__(); self.points: list[PointResult] = []; self.active_path: str | None = None; self.workspace_folder=None
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel(tr("Import")); title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;"); layout.addWidget(title)
        self.workspace_bar=WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self._import_path); layout.addWidget(self.workspace_bar)
        btn_row = QHBoxLayout(); self.excel_btn = QPushButton("Load Excel (.XLSX)"); self.excel_btn.clicked.connect(self._choose_excel); self.csv_btn = QPushButton("Load CSV (.CSV)"); self.csv_btn.clicked.connect(self._choose_csv); self.txt_btn = QPushButton("Load Survey TXT (.TXT)"); self.txt_btn.clicked.connect(self._choose_txt); self.choose_btn = QPushButton(tr("Choose File")); self.choose_btn.clicked.connect(self._choose_file); [btn_row.addWidget(b) for b in (self.excel_btn,self.csv_btn,self.txt_btn,self.choose_btn)]; btn_row.addStretch(); layout.addLayout(btn_row)
        self.file_label = QLabel("No file selected"); self.file_label.setStyleSheet("color: #777; margin-top: 6px;"); layout.addWidget(self.file_label)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["Name", "X", "Y", "Z"]); layout.addWidget(self.table)

    def set_workspace_folder(self, folder: str):
        self.workspace_folder=folder; self.workspace_bar.set_folder(folder, self.active_path)

    def load_active_file(self, path: str) -> None:
        if path and Path(path).is_file():
            self.workspace_folder=str(Path(path).parent); self.workspace_bar.set_folder(self.workspace_folder,path); self._import_path(path)

    def _choose_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Excel", self.workspace_folder or "", "Excel files (*.xlsx)");
        if path: self._import_path(path)
    def _choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", self.workspace_folder or "", "CSV files (*.csv)");
        if path: self._import_path(path)
    def _choose_txt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Survey TXT", self.workspace_folder or "", "Survey TXT files (*.txt);;Text files (*.txt)");
        if path: self._import_path(path)
    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Choose File"), self.workspace_folder or "", "Supported files (*.kmz *.kml *.csv *.xlsx *.txt);;KMZ (*.kmz);;KML (*.kml);;CSV (*.csv);;Excel (*.xlsx);;Survey TXT (*.txt)");
        if path: self._import_path(path)

    def _import_path(self, path: str) -> None:
        suffix = Path(path).suffix.lower()
        try:
            if suffix == ".kmz": points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml": points = kml_parser.parse_kml_file(path)
            elif suffix == ".csv": points = csv_parser.parse_csv_auto(path)
            elif suffix == ".xlsx":
                mapping = self._ask_mapping(xlsx_parser.sniff_columns(path));
                if mapping is None: return
                points = xlsx_parser.parse_xlsx(path, xlsx_parser.ColumnMapping(**mapping))
            elif suffix == ".txt": points = txt_parser.parse_txt(path)
            else: QMessageBox.warning(self, "Unsupported", f"Unsupported file type: {suffix}"); return
        except Exception as exc: QMessageBox.critical(self, "Import Error", str(exc)); return
        self.active_path = path; self.points = points; self.file_label.setText(path); self._populate_table(points); self.points_imported.emit(points)
        if self.workspace_folder != str(Path(path).parent): self.workspace_folder=str(Path(path).parent); self.workspace_bar.set_folder(self.workspace_folder,path)

    def _ask_mapping(self, columns: list[str]) -> dict | None:
        dlg = ColumnMappingDialog(columns, self); result = dlg.exec(); accepted = getattr(QDialog.DialogCode, "Accepted", 1); return dlg.result_mapping() if result == accepted else None

    def _populate_table(self, points: list[PointResult]) -> None:
        self.table.setRowCount(len(points))
        for i, p in enumerate(points):
            self.table.setItem(i, 0, QTableWidgetItem(p.name)); self.table.setItem(i, 1, QTableWidgetItem("" if p.src_x is None else str(p.src_x))); self.table.setItem(i, 2, QTableWidgetItem("" if p.src_y is None else str(p.src_y))); self.table.setItem(i, 3, QTableWidgetItem("" if p.src_z is None else str(p.src_z)))
