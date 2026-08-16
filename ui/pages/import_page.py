from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QTableWidget,QTableWidgetItem,QComboBox,QDialog,QFormLayout,QDialogButtonBox,QMessageBox
from core.models import PointResult
from core.parsers import csv_parser,xlsx_parser,kml_parser,txt_parser
from ui.i18n import tr
from ui.widgets.workspace_bar import WorkspaceFileBar

class ColumnMappingDialog(QDialog):
    Accepted=QDialog.DialogCode.Accepted
    def __init__(self,columns:list[str],parent=None):
        super().__init__(parent);self.setWindowTitle("Column Mapping");self.columns=list(columns)
        layout=QFormLayout(self);self.name_combo=QComboBox();self.name_combo.addItems(["<none>"]+self.columns);self.x_combo=QComboBox();self.x_combo.addItems(self.columns or ["Column 1"]);self.y_combo=QComboBox();self.y_combo.addItems(self.columns or ["Column 2"]);self.z_combo=QComboBox();self.z_combo.addItems(["<none>"]+self.columns)
        layout.addRow("Point Name →",self.name_combo);layout.addRow("X / Easting / Longitude →",self.x_combo);layout.addRow("Y / Northing / Latitude →",self.y_combo);layout.addRow("Z / Elevation →",self.z_combo);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addRow(buttons);self._infer()
    def _infer(self):
        def norm(v):return "".join(c for c in str(v).lower() if c.isalnum())
        vals=[norm(v) for v in self.columns]
        def pick(aliases,default=None):
            for a in aliases:
                if a in vals:return vals.index(a)
            for i,v in enumerate(vals):
                if any(a in v for a in aliases):return i
            return default
        xi=pick(("easting","east","x","xcoord","xcoordinate","longitude","lon"),0 if vals else None);yi=pick(("northing","north","y","ycoord","ycoordinate","latitude","lat"),1 if len(vals)>1 else None);zi=pick(("elevation","elev","height","z","zcoord","zcoordinate"));ni=pick(("pointnumber","pointno","pointid","point","name","id","number"))
        if xi is not None:self.x_combo.setCurrentIndex(xi)
        if yi is not None:self.y_combo.setCurrentIndex(yi)
        if zi is not None:self.z_combo.setCurrentIndex(zi+1)
        if ni is not None:self.name_combo.setCurrentIndex(ni+1)
    def exec(self):
        self.accept();return QDialog.DialogCode.Accepted
    def result_mapping(self):return {"name_col":None if self.name_combo.currentText()=="<none>" else self.name_combo.currentText(),"x_col":self.x_combo.currentText(),"y_col":self.y_combo.currentText(),"z_col":None if self.z_combo.currentText()=="<none>" else self.z_combo.currentText()}

class ImportPage(QWidget):
    points_imported=Signal(list)
    def __init__(self):
        super().__init__();self.points:list[PointResult]=[];self.active_path=None;self.workspace_folder=None;layout=QVBoxLayout(self);layout.setContentsMargins(30,30,30,30);title=QLabel(tr("Import"));title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;");layout.addWidget(title);self.workspace_bar=WorkspaceFileBar();self.workspace_bar.file_selected.connect(self._import_path);layout.addWidget(self.workspace_bar)
        row=QHBoxLayout();self.excel_btn=QPushButton("Load Excel (.XLSX)");self.excel_btn.clicked.connect(self._choose_excel);self.csv_btn=QPushButton("Load CSV (.CSV)");self.csv_btn.clicked.connect(self._choose_csv);self.txt_btn=QPushButton("Load Survey TXT (.TXT)");self.txt_btn.clicked.connect(self._choose_txt);self.choose_btn=QPushButton(tr("Choose File"));self.choose_btn.clicked.connect(self._choose_file);[row.addWidget(b) for b in (self.excel_btn,self.csv_btn,self.txt_btn,self.choose_btn)];row.addStretch();layout.addLayout(row);self.file_label=QLabel("No file selected");layout.addWidget(self.file_label);self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(["Name","X","Y","Z"]);layout.addWidget(self.table)
    def set_workspace_folder(self,folder):self.workspace_folder=folder;self.workspace_bar.set_folder(folder,self.active_path)
    def load_active_file(self,path):
        if path and Path(path).is_file():self.workspace_folder=str(Path(path).parent);self.workspace_bar.set_folder(self.workspace_folder,path);self._import_path(path)
    def _choose_excel(self):self._choose("Excel files (*.xlsx)")
    def _choose_csv(self):self._choose("CSV files (*.csv)")
    def _choose_txt(self):self._choose("Survey TXT files (*.txt)")
    def _choose(self,flt):
        path,_=QFileDialog.getOpenFileName(self,tr("Choose File"),self.workspace_folder or "",flt)
        if path:self._import_path(path)
    def _choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,tr("Choose File"),self.workspace_folder or "","Supported files (*.kmz *.kml *.csv *.xlsx *.txt);;All files (*.*)")
        if path:self._import_path(path)
    def _import_path(self,path):
        suffix=Path(path).suffix.lower()
        try:
            if suffix==".kmz":points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml":points=kml_parser.parse_kml_file(path)
            elif suffix==".csv":points=csv_parser.parse_csv_auto(path)
            elif suffix==".xlsx":points=xlsx_parser.parse_xlsx_auto(path)
            elif suffix==".txt":points=txt_parser.parse_txt(path)
            else:raise ValueError(f"Unsupported file type: {suffix}")
        except Exception as exc:QMessageBox.critical(self,"Import Error",str(exc));return
        if not points:QMessageBox.warning(self,"Import","No coordinate points were detected in this file.");return
        self.active_path=path;self.points=points;self.file_label.setText(f"{path} — {len(points)} points");self._populate_table(points);self.points_imported.emit(points);self.workspace_folder=str(Path(path).parent);self.workspace_bar.set_folder(self.workspace_folder,path)
    def _populate_table(self,points):
        self.table.setRowCount(len(points))
        for i,p in enumerate(points):self.table.setItem(i,0,QTableWidgetItem(str(p.name)));self.table.setItem(i,1,QTableWidgetItem("" if p.src_x is None else str(p.src_x)));self.table.setItem(i,2,QTableWidgetItem("" if p.src_y is None else str(p.src_y)));self.table.setItem(i,3,QTableWidgetItem("" if p.src_z is None else str(p.src_z)))
