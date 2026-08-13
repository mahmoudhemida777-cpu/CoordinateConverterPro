from __future__ import annotations
import csv
from pathlib import Path
import openpyxl
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QTableWidget,QTableWidgetItem,QProgressBar,QMessageBox,QGroupBox
from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser,xlsx_parser,kml_parser
from core.exporters.dxf_exporter import export_dxf,LabelMode
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.pages.import_page import ColumnMappingDialog
from ui.pages.settings_page import current_precision

class CadPage(QWidget):
    def __init__(self)->None:
        super().__init__(); self.engine=CRSEngine(); self.source_points=[]; self.result_points=[]; self.current_file=None; self.batch_converted=False
        root=QVBoxLayout(self); root.setContentsMargins(30,20,30,20); title=QLabel("AutoCAD / Civil 3D Export"); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title); root.addWidget(QLabel("Batch-converted files are loaded as final target coordinates; no second CRS conversion is required."))
        row=QHBoxLayout(); choose=QPushButton("Choose Coordinate File"); choose.clicked.connect(self._choose_file); row.addWidget(choose); self.file_label=QLabel("No file selected"); self.file_label.setStyleSheet("color:#777;"); row.addWidget(self.file_label); row.addStretch(); root.addLayout(row)
        crs_row=QHBoxLayout(); self.source_picker=CRSPicker(self.engine,tr("SOURCE CRS")); self.target_picker=CRSPicker(self.engine,tr("TARGET CRS")); crs_row.addWidget(self.source_picker); crs_row.addWidget(self.target_picker); root.addLayout(crs_row)
        convert=QPushButton("CONVERT FOR CAD / CIVIL 3D"); convert.setStyleSheet("background-color:#C9A227;color:white;font-weight:bold;padding:9px 24px;"); convert.clicked.connect(self._convert); root.addWidget(convert); self.progress=QProgressBar(); root.addWidget(self.progress)
        summary=QGroupBox(); sl=QHBoxLayout(summary); self.total=QLabel("Points: 0"); self.success=QLabel("Success: 0"); self.failed=QLabel("Failed: 0"); [sl.addWidget(w) for w in (self.total,self.success,self.failed)]; root.addWidget(summary)
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["Point","Easting / X","Northing / Y","Elevation","Status","Message"]); root.addWidget(self.table)
        export_row=QHBoxLayout(); dxf=QPushButton("EXPORT DXF — AutoCAD / Civil 3D"); dxf.clicked.connect(self._export_dxf); civil=QPushButton("EXPORT CSV — Civil 3D Points"); civil.clicked.connect(self._export_civil3d_csv); export_row.addWidget(dxf); export_row.addWidget(civil); root.addLayout(export_row)

    def load_active_file(self,path:str)->None:
        if path and Path(path).is_file(): self._load_path(path)
    def _choose_file(self)->None:
        path,_=QFileDialog.getOpenFileName(self,"Choose Coordinate File","","Coordinate files (*.kmz *.kml *.csv *.xlsx);;All files (*.*)")
        if path:self._load_path(path)
    def _load_path(self,path:str)->None:
        if Path(path).stem.endswith("_converted") and Path(path).suffix.casefold()==".xlsx":
            if self._load_batch_converted_xlsx(path): return
        try:
            suffix=Path(path).suffix.casefold()
            if suffix==".kmz": points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml": points=kml_parser.parse_kml_file(path)
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
        self.batch_converted=False; self.source_points=points; self.result_points=[]; self.current_file=path; self.file_label.setText(f"{Path(path).name} — {len(points)} points loaded"); self.table.setRowCount(0); self.total.setText(f"Points: {len(points)}"); self.success.setText("Success: 0"); self.failed.setText("Failed: 0")
    def _load_batch_converted_xlsx(self,path:str)->bool:
        try:
            wb=openpyxl.load_workbook(path,read_only=True,data_only=True); ws=wb["Points"] if "Points" in wb.sheetnames else wb.active; rows=list(ws.iter_rows(values_only=True)); info=wb["Project Info"] if "Project Info" in wb.sheetnames else None; target_crs=None
            if info:
                for row in info.iter_rows(values_only=True):
                    if row and str(row[0]).strip()=="Target CRS": target_crs=str(row[1]).strip() if row[1] else None; break
            wb.close()
            if not rows:return False
            headers=[str(x).strip() if x is not None else "" for x in rows[0]]; idx={h:i for i,h in enumerate(headers)}
            if not {"Point Name","Target X","Target Y"}.issubset(idx):return False
            pts=[]
            for n,row in enumerate(rows[1:],1):
                try:
                    x=float(row[idx["Target X"]]); y=float(row[idx["Target Y"]]); z=float(row[idx["Target Z"]]) if "Target Z" in idx and row[idx["Target Z"]] is not None else None; name=str(row[idx["Point Name"]]) if row[idx["Point Name"]] is not None else f"PT-{n}"; status=str(row[idx["Status"]]) if "Status" in idx else "SUCCESS"; pts.append(PointResult(name,x,y,z,x,y,z,status=status))
                except (TypeError,ValueError,IndexError):continue
            if not pts:return False
            self.batch_converted=True; self.source_points=pts; self.result_points=pts; self.current_file=path; label=f"{Path(path).name} — {len(pts)} points — ALREADY CONVERTED" + (f" — {target_crs}" if target_crs else ""); self.file_label.setText(label); self._set_crs_both(target_crs); self.progress.setMaximum(len(pts)); self.progress.setValue(len(pts)); self._populate(); return True
        except Exception as exc: QMessageBox.critical(self,"Batch Result Error",f"Could not load batch-converted file:\n{exc}"); return False
    def _set_crs_both(self,epsg):
        if not epsg:return
        try: info=self.engine.get_crs_info(epsg); name=getattr(info,"name",epsg)
        except Exception:name=epsg
        self.source_picker.set_selected(epsg,name); self.target_picker.set_selected(epsg,name)
    def _convert(self)->None:
        if self.batch_converted: QMessageBox.information(self,"Already Converted","This file was produced by Batch Converter and is already in the target CRS. Export it directly to DXF or Civil 3D CSV."); return
        if not self.source_points: QMessageBox.warning(self,"No data","Choose a coordinate file first."); return
        src=self.source_picker.selected_epsg(); tgt=self.target_picker.selected_epsg()
        if not src or not tgt: QMessageBox.warning(self,"No CRS","Select both Source CRS and Target CRS."); return
        self.result_points=[]; self.progress.setMaximum(len(self.source_points))
        for i,point in enumerate(self.source_points,1): self.result_points.append(self.engine.transform_points(src,tgt,[point])[0]); self.progress.setValue(i)
        self._populate()
    def _populate(self):
        pts=self.result_points; precision=current_precision(); self.total.setText(f"Points: {len(pts)}"); self.success.setText(f"Success: {sum(p.status=='SUCCESS' for p in pts)}"); self.failed.setText(f"Failed: {sum(p.status=='FAILED' for p in pts)}"); self.table.setRowCount(len(pts))
        def fmt(v): return "" if v is None else (f"{v:.{precision}f}" if isinstance(v,(int,float)) else str(v))
        for i,p in enumerate(pts):
            for j,value in enumerate([p.name,p.tgt_x,p.tgt_y,p.tgt_z,p.status,p.message]): self.table.setItem(i,j,QTableWidgetItem(fmt(value)))
    def _export_dxf(self)->None:
        if not self.result_points: QMessageBox.warning(self,"Nothing to export","Run the conversion first or load a Batch result."); return
        path,_=QFileDialog.getSaveFileName(self,"Export DXF","CAD_Points.dxf","AutoCAD DXF (*.dxf)")
        if not path:return
        try: export_dxf(self.result_points,path,label_mode=LabelMode.NAME,text_height=1.0,use_target_coords=True); QMessageBox.information(self,"DXF Exported",f"DXF created successfully:\n{path}")
        except Exception as exc: QMessageBox.critical(self,"DXF Export Error",str(exc))
    def _export_civil3d_csv(self)->None:
        if not self.result_points: QMessageBox.warning(self,"Nothing to export","Run the conversion first or load a Batch result."); return
        path,_=QFileDialog.getSaveFileName(self,"Export Civil 3D CSV","Civil3D_Points.csv","CSV (*.csv)")
        if not path:return
        try:
            precision=current_precision()
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                writer=csv.writer(f); writer.writerow(["Point Number","Easting","Northing","Elevation","Description"])
                for i,p in enumerate(self.result_points,1):
                    if p.tgt_x is None or p.tgt_y is None:continue
                    writer.writerow([i,f"{p.tgt_x:.{precision}f}",f"{p.tgt_y:.{precision}f}",f"{(p.tgt_z or 0):.{precision}f}",p.name])
            QMessageBox.information(self,"Civil 3D CSV Exported",f"Civil 3D point file created:\n{path}")
        except Exception as exc: QMessageBox.critical(self,"CSV Export Error",str(exc))
