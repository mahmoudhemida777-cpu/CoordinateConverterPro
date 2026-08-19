from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QTableWidget,QTableWidgetItem,QProgressBar,QSplitter,QMessageBox,QGroupBox
from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser,xlsx_parser,kml_parser,txt_parser
from core.cad_importer import extract_cad_points
from core.validation.validator import validate_points,validate_zone_consistency
from core.exporters.xlsx_exporter import export_xlsx
from core.exporters.csv_exporter import export_csv
from core.exporters.txt_exporter import export_txt
from core.exporters.dxf_exporter import export_dxf,LabelMode
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.widgets.workspace_bar import WorkspaceFileBar
from ui.pages.import_page import ColumnMappingDialog
from ui.pages.history_page import append_history
from ui.pages.settings_page import current_precision

class ConverterPage(QWidget):
    def __init__(self)->None:
        super().__init__(); self.engine=CRSEngine(); self.source_points=[]; self.result_points=[]; self.current_file=None; self.workspace_folder=None
        root=QVBoxLayout(self); root.setContentsMargins(30,20,30,20); title=QLabel(tr("CRS Converter")); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        self.workspace_bar=WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self._load_path); root.addWidget(self.workspace_bar)
        file_row=QHBoxLayout(); self.choose_btn=QPushButton(tr("SOURCE FILE")); self.choose_btn.clicked.connect(self._choose_file); file_row.addWidget(self.choose_btn); self.file_label=QLabel("No file selected"); self.file_label.setStyleSheet("color:#777;"); file_row.addWidget(self.file_label); file_row.addStretch(); root.addLayout(file_row)
        splitter=QSplitter(Qt.Horizontal); self.source_picker=CRSPicker(self.engine,tr("SOURCE CRS")); self.target_picker=CRSPicker(self.engine,tr("TARGET CRS")); splitter.addWidget(self.source_picker); splitter.addWidget(self.target_picker); root.addWidget(splitter)
        convert_row=QHBoxLayout(); self.convert_btn=QPushButton(tr("CONVERT")); self.convert_btn.setStyleSheet("background-color:#C9A227;color:white;font-weight:bold;padding:8px 24px;"); self.convert_btn.clicked.connect(self._run_conversion); convert_row.addWidget(self.convert_btn); convert_row.addStretch(); root.addLayout(convert_row)
        self.progress=QProgressBar(); root.addWidget(self.progress); summary_box=QGroupBox(); summary_layout=QHBoxLayout(summary_box); self.total_label=QLabel(f"{tr('Total Points')}: 0"); self.success_label=QLabel(f"{tr('Successful')}: 0"); self.failed_label=QLabel(f"{tr('Failed')}: 0"); self.warning_label=QLabel(f"{tr('Warnings')}: 0"); [summary_layout.addWidget(x) for x in (self.total_label,self.success_label,self.failed_label,self.warning_label)]; root.addWidget(summary_box)
        self.results_table=QTableWidget(0,9); self.results_table.setHorizontalHeaderLabels(["Name","Src X","Src Y","Src Z","Tgt X","Tgt Y","Tgt Z","Status","Message"]); root.addWidget(self.results_table)
        export_box=QGroupBox("Export Converted Points"); export_row=QHBoxLayout(export_box); self.export_dxf_btn=QPushButton("AutoCAD / Civil 3D — DXF"); self.export_dxf_btn.clicked.connect(self._export_dxf); self.export_civil_btn=QPushButton("Civil 3D — PENZD CSV"); self.export_civil_btn.clicked.connect(self._export_civil3d); self.export_xlsx_btn=QPushButton("Excel XLSX"); self.export_xlsx_btn.clicked.connect(self._export_xlsx); self.export_csv_btn=QPushButton("Generic CSV"); self.export_csv_btn.clicked.connect(self._export_csv); self.export_txt_btn=QPushButton("Survey TXT"); self.export_txt_btn.clicked.connect(self._export_txt); [x.setEnabled(False) or export_row.addWidget(x) for x in (self.export_dxf_btn,self.export_civil_btn,self.export_xlsx_btn,self.export_csv_btn,self.export_txt_btn)]; root.addWidget(export_box)

    def set_workspace_folder(self,folder:str): self.workspace_folder=folder; self.workspace_bar.set_folder(folder,self.current_file)
    def load_active_file(self,path:str)->None:
        if path and Path(path).is_file(): self.workspace_folder=str(Path(path).parent); self.workspace_bar.set_folder(self.workspace_folder,path); self._load_path(path)
    def _choose_file(self)->None:
        path,_=QFileDialog.getOpenFileName(self,tr("Choose File"),self.workspace_folder or "","Supported files (*.kmz *.kml *.dxf *.dwg *.csv *.xlsx *.txt);;CAD (*.dxf *.dwg);;All files (*.*)")
        if path:self._load_path(path)
    def _load_path(self,path:str)->None:
        suffix=Path(path).suffix.lower()
        try:
            if suffix in {".dxf",".dwg"}: points=extract_cad_points(path)
            elif suffix==".kmz": points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml": points=kml_parser.parse_kml_file(path)
            elif suffix==".txt": points=txt_parser.parse_txt(path)
            elif suffix==".csv":
                dlg=ColumnMappingDialog(csv_parser.sniff_columns(path),self)
                if dlg.exec()!=dlg.Accepted:return
                points=csv_parser.parse_csv(path,csv_parser.ColumnMapping(**dlg.result_mapping()))
            elif suffix==".xlsx":
                dlg=ColumnMappingDialog(xlsx_parser.sniff_columns(path),self)
                if dlg.exec()!=dlg.Accepted:return
                points=xlsx_parser.parse_xlsx(path,xlsx_parser.ColumnMapping(**dlg.result_mapping()))
            else: raise ValueError(f"Unsupported file type: {suffix}")
        except Exception as exc: QMessageBox.critical(self,"Import Error",str(exc)); return
        points=list(points or []); self.source_points=points; self.result_points=[]; self.current_file=path; self.file_label.setText(f"{Path(path).name} — {len(points)} points loaded")
        if suffix in {".kml",".kmz"}: self.source_picker.set_selected("EPSG:4326","WGS 84 — Geographic 2D (Latitude / Longitude)")
        [x.setEnabled(False) for x in (self.export_dxf_btn,self.export_civil_btn,self.export_xlsx_btn,self.export_csv_btn,self.export_txt_btn)]
    def _run_conversion(self)->None:
        if not self.source_points: QMessageBox.warning(self,"No data","Please choose a source file first."); return
        src=self.source_picker.selected_epsg(); tgt=self.target_picker.selected_epsg()
        if not src or not tgt: QMessageBox.warning(self,"No CRS","Please select both a source and target CRS."); return
        try:selected_operation=self.engine.get_selected_operation(src,tgt,"auto")
        except Exception as exc: QMessageBox.critical(self,"Transformation Error",str(exc)); return
        report=validate_points(self.source_points); zone_warnings=validate_zone_consistency(src,tgt); self.progress.setMaximum(len(self.source_points)); self.result_points=[]
        for i,p in enumerate(self.source_points,1): self.result_points.append(self.engine.transform_points(src,tgt,[p],"auto")[0]); self.progress.setValue(i)
        self._populate_results(); [x.setEnabled(bool(self.result_points)) for x in (self.export_dxf_btn,self.export_civil_btn,self.export_xlsx_btn,self.export_csv_btn,self.export_txt_btn)]; accuracy=selected_operation.get("accuracy"); accuracy_text="unknown" if accuracy is None or accuracy<0 else f"{accuracy:.3g} m"
        append_history({"time":datetime.now().astimezone().isoformat(timespec="seconds"),"file":Path(self.current_file).name if self.current_file else "","source_crs":src,"target_crs":tgt,"points":len(self.result_points),"operation":selected_operation["description"],"status":"SUCCESS"})
        if zone_warnings or report.warnings: QMessageBox.information(self,"Warnings","\n".join(zone_warnings+[w.message for w in report.warnings]))
    def _fmt(self,value): return "" if value is None else (f"{value:.{current_precision()}f}" if isinstance(value,(int,float)) else str(value))
    def _populate_results(self):
        pts=self.result_points; self.total_label.setText(f"{tr('Total Points')}: {len(pts)}"); self.success_label.setText(f"{tr('Successful')}: {sum(p.status=='SUCCESS' for p in pts)}"); self.failed_label.setText(f"{tr('Failed')}: {sum(p.status=='FAILED' for p in pts)}"); self.warning_label.setText(f"{tr('Warnings')}: {sum(p.status=='WARNING' for p in pts)}"); self.results_table.setRowCount(len(pts))
        for i,p in enumerate(pts):
            for j,v in enumerate([p.name,p.src_x,p.src_y,p.src_z,p.tgt_x,p.tgt_y,p.tgt_z,p.status,p.message]): self.results_table.setItem(i,j,QTableWidgetItem(self._fmt(v)))
    def _require_results(self):
        if not self.result_points: QMessageBox.warning(self,"Nothing to export","Run the conversion first."); return False
        return True
    def _export_dxf(self):
        if not self._require_results():return
        path,_=QFileDialog.getSaveFileName(self,"Export AutoCAD / Civil 3D DXF","Converted_Points.dxf","AutoCAD DXF (*.dxf)");
        if not path:return
        try:export_dxf(self.result_points,path,label_mode=LabelMode.NAME,text_height=1.0,use_target_coords=True);QMessageBox.information(self,"Export Complete",f"DXF created successfully:\n{path}")
        except Exception as exc:QMessageBox.critical(self,"DXF Export Error",str(exc))
    def _export_civil3d(self):
        if not self._require_results():return
        path,_=QFileDialog.getSaveFileName(self,"Export Civil 3D PENZD","Civil3D_PENZD.csv","CSV (*.csv)");
        if not path:return
        try:
            precision=current_precision()
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                writer=csv.writer(f);writer.writerow(["Point Number","Easting","Northing","Elevation","Description"])
                for i,p in enumerate(self.result_points,1):
                    if p.tgt_x is None or p.tgt_y is None:continue
                    writer.writerow([i,f"{p.tgt_x:.{precision}f}",f"{p.tgt_y:.{precision}f}",f"{(p.tgt_z or 0):.{precision}f}",p.name or ""])
            QMessageBox.information(self,"Export Complete",f"Civil 3D PENZD point file created:\n{path}")
        except Exception as exc:QMessageBox.critical(self,"Civil 3D Export Error",str(exc))
    def _export_xlsx(self):
        if not self._require_results():return
        path,_=QFileDialog.getSaveFileName(self,"Export XLSX","Project_Export.xlsx","Excel (*.xlsx)"); details=self.engine.get_crs_details(self.source_picker.selected_epsg()); export_xlsx(self.result_points,path,self.source_picker.selected_epsg(),self.target_picker.selected_epsg(),details,current_precision());QMessageBox.information(self,"Exported",f"Saved to {path}")
    def _export_csv(self):
        if not self._require_results():return
        path,_=QFileDialog.getSaveFileName(self,"Export CSV","Project_Export.csv","CSV (*.csv)");
        if not path:return
        export_csv(self.result_points,path,current_precision());QMessageBox.information(self,"Exported",f"Saved to {path}")
    def _export_txt(self):
        if not self._require_results():return
        path,_=QFileDialog.getSaveFileName(self,"Export Survey TXT","Project_Export.txt","Text files (*.txt)");
        if not path:return
        try:export_txt(self.result_points,path,current_precision());QMessageBox.information(self,"Export Complete",f"TXT created successfully:\n{path}")
        except Exception as exc:QMessageBox.critical(self,"TXT Export Error",str(exc))
