from __future__ import annotations
import csv
from pathlib import Path
import openpyxl
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QFileDialog,
    QTableWidget,QTableWidgetItem,QProgressBar,QMessageBox,QGroupBox,QCheckBox,
    QComboBox,QRadioButton,QHeaderView,QSizePolicy,QSplitter,QGraphicsView,
    QGraphicsScene,QGraphicsEllipseItem,QGraphicsTextItem,QGraphicsLineItem
)
from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser,xlsx_parser,kml_parser,txt_parser
from core.exporters.dxf_exporter import export_dxf,LabelMode
from core.point_ordering import order_points
from ui.widgets.crs_picker import CRSPicker
from ui.widgets.workspace_bar import WorkspaceFileBar
from ui.pages.settings_page import current_precision

COORDINATE_FILTER="Coordinate files (*.kmz *.kml *.csv *.xlsx *.txt);;KMZ/KML (*.kmz *.kml);;CSV (*.csv);;Excel (*.xlsx);;Survey TXT (*.txt);;All files (*.*)"

class CadPage(QWidget):
    def __init__(self)->None:
        super().__init__(); self.engine=CRSEngine(); self.source_points=[]; self.result_points=[]; self.current_file=None; self.workspace_folder=None; self._detected_columns=[]; self._axis_swapped=False
        root=QVBoxLayout(self); root.setContentsMargins(20,16,20,20); root.setSpacing(10)
        title_row=QHBoxLayout(); title=QLabel("CAD / Civil 3D Converter"); title.setObjectName("pageTitle"); title_row.addWidget(title); title_row.addStretch(); self.reset_btn=QPushButton("Reset"); self.reset_btn.clicked.connect(self._reset_page); title_row.addWidget(self.reset_btn); root.addLayout(title_row)
        sub=QLabel("Convert survey points to CAD (DXF) or Civil 3D (CSV) — Smart Parsing, Axis Control and independent Grid/Zigzag ordering."); sub.setWordWrap(True); sub.setObjectName("pageSubtitle"); root.addWidget(sub)
        self.workspace_bar=WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self._load_path); root.addWidget(self.workspace_bar)
        file_row=QHBoxLayout(); self.file_status=QLabel("No coordinate file loaded"); self.file_status.setWordWrap(True); file_row.addWidget(self.file_status,1); choose=QPushButton("Open / Change File"); choose.clicked.connect(self._choose_file); file_row.addWidget(choose); root.addLayout(file_row)
        self.direct_mode=QCheckBox("DIRECT CAD EXPORT — use loaded coordinates exactly as they are (NO CRS conversion)"); self.direct_mode.stateChanged.connect(self._mode_changed); root.addWidget(self.direct_mode)

        split=QSplitter(Qt.Orientation.Horizontal); split.setChildrenCollapsible(False); root.addWidget(split,1)
        left=QWidget(); ll=QVBoxLayout(left); ll.setContentsMargins(0,0,8,0); ll.setSpacing(8)
        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(8,0,0,0); rl.setSpacing(8)

        parsing=QGroupBox("1  FILE & PARSING OPTIONS"); pg=QGridLayout(parsing); pg.setHorizontalSpacing(8); pg.setVerticalSpacing(7)
        self.parsing_engine=QComboBox(); self.parsing_engine.addItems(["Smart (Recommended)","Manual / Selected Columns"])
        self.detected_format=QComboBox(); self.detected_format.setEnabled(False)
        pg.addWidget(QLabel("Parsing Engine"),0,0); pg.addWidget(self.parsing_engine,0,1); pg.addWidget(QLabel("Detected Format"),0,2); pg.addWidget(self.detected_format,0,3)
        self.x_column=QComboBox(); self.y_column=QComboBox(); self.z_column=QComboBox(); self.name_column=QComboBox()
        for c in (self.x_column,self.y_column,self.z_column,self.name_column): c.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        pg.addWidget(QLabel("Easting / X"),1,0); pg.addWidget(self.x_column,1,1); pg.addWidget(QLabel("Northing / Y"),1,2); pg.addWidget(self.y_column,1,3)
        pg.addWidget(QLabel("Elevation / Z"),2,0); pg.addWidget(self.z_column,2,1); pg.addWidget(QLabel("Point Code / Name"),2,2); pg.addWidget(self.name_column,2,3)
        for col in (1,3): pg.setColumnStretch(col,1)
        ll.addWidget(parsing)

        axis=QGroupBox("2  AXIS ORDER — IMPORTANT"); af=QHBoxLayout(axis); self.axis_xy=QRadioButton("Easting (X) → Northing (Y)  |  Standard"); self.axis_yx=QRadioButton("Northing (Y) → Easting (X)  |  SWAP"); self.axis_xy.setChecked(True); af.addWidget(self.axis_xy); af.addWidget(self.axis_yx); ll.addWidget(axis)

        ordering=QGroupBox("3  GRID / ZIGZAG POINT NUMBERING"); og=QGridLayout(ordering); og.setVerticalSpacing(7)
        self.ordering_mode=QComboBox(); self.ordering_mode.addItem("Grid Zigzag — Start West (W → E)","GRID_ZIGZAG_WEST"); self.ordering_mode.addItem("Grid Zigzag — Start East (E → W)","GRID_ZIGZAG_EAST"); self.ordering_mode.addItem("Keep Source Order","SOURCE")
        og.addWidget(QLabel("Pattern"),0,0); og.addWidget(self.ordering_mode,0,1,1,2)
        self.group_by_name=QCheckBox("Group by Point Code / Name — each code is ordered independently"); self.group_by_name.setChecked(True); og.addWidget(self.group_by_name,1,0,1,3)
        self.auto_grid=QCheckBox("Auto-detect grid rows"); self.auto_grid.setChecked(True); og.addWidget(self.auto_grid,2,0); self.tolerance_combo=QComboBox(); self.tolerance_combo.addItems(["Auto","0.01","0.05","0.10","0.25","0.50","1.00"]); og.addWidget(QLabel("Row tolerance (m)"),2,1); og.addWidget(self.tolerance_combo,2,2)
        self.renumber_preview=QPushButton("Apply & Preview Zigzag"); self.renumber_preview.clicked.connect(self._refresh_preview); og.addWidget(self.renumber_preview,3,0,1,3)
        ll.addWidget(ordering)

        advanced=QGroupBox("4  ADVANCED OPTIONS"); ag=QHBoxLayout(advanced); self.auto_crs=QCheckBox("Auto Detect CRS"); self.auto_crs.setChecked(True); self.write_code=QCheckBox("Write Point Code to DXF"); self.write_code.setChecked(True); ag.addWidget(self.auto_crs); ag.addWidget(self.write_code); ag.addStretch(); ll.addWidget(advanced)

        crs=QGroupBox("COORDINATE REFERENCE SYSTEM"); cg=QHBoxLayout(crs); self.source_picker=CRSPicker(self.engine,"SOURCE CRS"); self.target_picker=CRSPicker(self.engine,"TARGET CRS"); cg.addWidget(self.source_picker,1); cg.addWidget(self.target_picker,1); ll.addWidget(crs)
        self.convert_btn=QPushButton("CONVERT & PREPARE FOR CAD / CIVIL 3D"); self.convert_btn.clicked.connect(self._convert); ll.addWidget(self.convert_btn)
        self.progress=QProgressBar(); self.progress.setRange(0,100); ll.addWidget(self.progress)
        summary=QHBoxLayout(); self.total=QLabel("Total: 0"); self.success=QLabel("Success: 0"); self.failed=QLabel("Failed: 0"); summary.addWidget(self.total); summary.addWidget(self.success); summary.addWidget(self.failed); summary.addStretch(); ll.addLayout(summary)
        split.addWidget(left)

        preview_box=QGroupBox("PREVIEW — POINTS / ZIGZAG PATH"); pv=QVBoxLayout(preview_box); tools=QHBoxLayout(); fit=QPushButton("Fit"); fit.clicked.connect(self._fit_scene); zoom_in=QPushButton("Zoom +"); zoom_in.clicked.connect(lambda:self.map_view.scale(1.25,1.25)); zoom_out=QPushButton("Zoom −"); zoom_out.clicked.connect(lambda:self.map_view.scale(.8,.8)); tools.addWidget(fit); tools.addWidget(zoom_in); tools.addWidget(zoom_out); tools.addStretch(); self.preview_info=QLabel("0 points"); tools.addWidget(self.preview_info); pv.addLayout(tools)
        self.scene=QGraphicsScene(); self.map_view=QGraphicsView(self.scene); self.map_view.setMinimumHeight(300); self.map_view.setRenderHint(self.map_view.renderHints()); pv.addWidget(self.map_view,1)
        legend=QLabel("Point = survey coordinate   |   Green = label   |   Blue = zigzag direction   |   Groups are independent when enabled"); legend.setWordWrap(True); pv.addWidget(legend); rl.addWidget(preview_box,1)
        export_row=QHBoxLayout(); dxf=QPushButton("EXPORT DXF"); civil=QPushButton("EXPORT CIVIL 3D CSV"); dxf.clicked.connect(self._export_dxf); civil.clicked.connect(self._export_civil3d_csv); export_row.addWidget(dxf,1); export_row.addWidget(civil,1); rl.addLayout(export_row)
        split.addWidget(right); split.setSizes([620,760])

        table_box=QGroupBox("POINTS PREVIEW TABLE"); tl=QVBoxLayout(table_box); self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(["#","Point Code / Name","Easting / X","Northing / Y","Elevation / Z","Status"]); self.table.setMinimumHeight(170); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); tl.addWidget(self.table); root.addWidget(table_box)

    def set_workspace_folder(self,folder:str):
        self.workspace_folder=folder; self.workspace_bar.set_folder(folder,self.current_file)

    def load_active_file(self,path:str)->None:
        if not path or not Path(path).is_file(): return
        if self.current_file and Path(path).resolve()==Path(self.current_file).resolve():
            self.file_status.setText(f"Selected from Dashboard: {Path(path).name} — {len(self.source_points)} points loaded"); return
        self.workspace_folder=str(Path(path).parent); self.workspace_bar.set_folder(self.workspace_folder,path); self._load_path(path)

    def _choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose Coordinate File",self.workspace_folder or "",COORDINATE_FILTER)
        if path:self._load_path(path)

    def _mode_changed(self):
        if self.direct_mode.isChecked() and self.source_points:
            self.result_points=[PointResult(p.name,p.src_x,p.src_y,p.src_z,p.src_x,p.src_y,p.src_z,status="SUCCESS",message="DIRECT — no CRS conversion") for p in self.source_points]; self._populate(); self._refresh_preview()
        elif not self.direct_mode.isChecked() and self.result_points and all("DIRECT" in (p.message or "") for p in self.result_points):
            self.result_points=[]; self._populate(); self._refresh_preview()

    @staticmethod
    def _pick_column(columns,names):
        normalized=[str(c).strip().lower() for c in columns]
        for name in names:
            if name in normalized:return normalized.index(name)
        for i,key in enumerate(normalized):
            if any(name in key for name in names):return i
        return -1

    def _populate_parsing_options(self,path,suffix):
        self._detected_columns=[]; self.detected_format.clear(); self.x_column.clear(); self.y_column.clear(); self.z_column.clear(); self.name_column.clear(); self.detected_format.addItem({".csv":"CSV (Comma delimited)",".xlsx":"Excel Workbook",".txt":"Survey TXT",".kml":"KML",".kmz":"KMZ"}.get(suffix,suffix))
        if suffix==".csv": self._detected_columns=list(csv_parser.sniff_columns(path))
        elif suffix==".xlsx": self._detected_columns=list(xlsx_parser.sniff_columns(path))
        else:return
        for c in (self.x_column,self.y_column,self.z_column,self.name_column): c.addItems(self._detected_columns)
        self.z_column.insertItem(0,"<none>"); self.name_column.insertItem(0,"<none>")
        xi=self._pick_column(self._detected_columns,("easting","east","x","longitude","lon")); yi=self._pick_column(self._detected_columns,("northing","north","y","latitude","lat")); zi=self._pick_column(self._detected_columns,("elevation","elev","height","z")); ni=self._pick_column(self._detected_columns,("point number","point_number","pointid","pointcode","code","point","name","id"))
        if xi>=0:self.x_column.setCurrentIndex(xi)
        if yi>=0:self.y_column.setCurrentIndex(yi)
        if zi>=0:self.z_column.setCurrentIndex(zi+1)
        if ni>=0:self.name_column.setCurrentIndex(ni+1)

    def _apply_manual_mapping(self):
        suffix=Path(self.current_file).suffix.casefold()
        if suffix==".csv":
            n=self.name_column.currentText(); z=self.z_column.currentText(); return csv_parser.parse_csv(self.current_file,csv_parser.ColumnMapping(None if n=="<none>" else n,self.x_column.currentText(),self.y_column.currentText(),None if z=="<none>" else z))
        if suffix==".xlsx":
            n=self.name_column.currentText(); z=self.z_column.currentText(); return xlsx_parser.parse_xlsx(self.current_file,xlsx_parser.ColumnMapping(None if n=="<none>" else n,self.x_column.currentText(),self.y_column.currentText(),None if z=="<none>" else z))
        return None

    def _apply_axis(self,points):
        if not self.axis_yx.isChecked(): self._axis_swapped=False; return points
        self._axis_swapped=True
        return [PointResult(p.name,p.src_y,p.src_x,p.src_z,p.tgt_y,p.tgt_x,p.tgt_z,status=p.status,message=(p.message or "")+" | AXIS SWAPPED") for p in points]

    def _load_path(self,path):
        file_path=Path(path)
        try:
            suffix=file_path.suffix.casefold()
            if suffix==".kmz": points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml": points=kml_parser.parse_kml_file(path)
            elif suffix==".csv": points=csv_parser.parse_csv_auto(path)
            elif suffix==".xlsx": points=xlsx_parser.parse_xlsx_auto(path)
            elif suffix==".txt": points=txt_parser.parse_txt(path)
            else: raise ValueError(f"Unsupported file type: {suffix}")
            if not points: raise ValueError("No valid X/Y coordinate points were found in the selected file.")
        except Exception as exc: QMessageBox.critical(self,"Import Error",str(exc)); return
        self.current_file=str(file_path); self.workspace_folder=str(file_path.parent); self.source_points=list(points); self.result_points=[]; self._axis_swapped=False; self.file_status.setText(f"✓ Selected file: {file_path.name}   |   {len(points)} points loaded"); self.progress.setValue(0); self._populate_parsing_options(path,suffix); self._populate(); self._refresh_preview()
        if suffix in {".kml",".kmz"}: self.source_picker.set_selected("EPSG:4326","WGS 84 — Geographic 2D (Latitude / Longitude)")

    def _refresh_preview(self):
        if not self.source_points:return
        pts=self.result_points if self.result_points else self.source_points
        mode=str(self.ordering_mode.currentData() or "GRID_ZIGZAG_WEST")
        ordered=order_points(pts,mode=mode,group_by_name=self.group_by_name.isChecked())
        self._draw_preview(ordered); self._populate_table(ordered)

    def _draw_preview(self,ordered):
        self.scene.clear(); valid=[]
        for item in ordered:
            p=item.point; x=p.tgt_x if p.tgt_x is not None else p.src_x; y=p.tgt_y if p.tgt_y is not None else p.src_y
            if x is not None and y is not None: valid.append((item,float(x),float(y)))
        if not valid:self.preview_info.setText("No valid coordinates"); return
        minx,maxx=min(v[1] for v in valid),max(v[1] for v in valid); miny,maxy=min(v[2] for v in valid),max(v[2] for v in valid); dx=max(maxx-minx,1.0); dy=max(maxy-miny,1.0); sx=700/dx; sy=500/dy; scale=min(sx,sy); ox=40-minx*scale; oy=40+maxy*scale
        colors=["#35D07F","#FFC107","#29B6F6","#AB69FF","#FF5B6E","#00BCD4","#FF8A65"]
        positions={item.number:(x*scale+ox,oy-y*scale) for item,x,y in valid}; groups={}
        for item,_,_ in valid: groups.setdefault(item.group,[]).append(item.number)
        for gi,(group,numbers) in enumerate(groups.items()):
            color=QColor(colors[gi%len(colors)]); nums=[n for n in numbers if n in positions]
            for a,b in zip(nums,nums[1:]):
                x1,y1=positions[a]; x2,y2=positions[b]; line=QGraphicsLineItem(x1,y1,x2,y2); line.setPen(QPen(color,1.6,Qt.PenStyle.DashLine)); self.scene.addItem(line)
            for n in nums:
                x,y=positions[n]; point=QGraphicsEllipseItem(x-4,y-4,8,8); point.setBrush(QBrush(color)); point.setPen(QPen(QColor("#0B1420"),1)); self.scene.addItem(point); name=next(i.point.name for i,_,_ in valid if i.number==n); text=QGraphicsTextItem(str(name or n)); text.setDefaultTextColor(color); text.setFont(QFont("Segoe UI",9,QFont.Weight.Bold)); text.setPos(x+6,y-9); self.scene.addItem(text)
        self.scene.setSceneRect(0,0,780,540); self.preview_info.setText(f"{len(valid)} points  |  {len(groups)} code/name groups"); self._fit_scene()

    def _fit_scene(self):
        if not self.scene.items():return
        self.map_view.fitInView(self.scene.itemsBoundingRect().adjusted(-20,-20,20,20),Qt.AspectRatioMode.KeepAspectRatio)

    def _populate_table(self,ordered):
        precision=current_precision(); self.table.setRowCount(len(ordered));
        for r,item in enumerate(ordered):
            p=item.point; x=p.tgt_x if p.tgt_x is not None else p.src_x; y=p.tgt_y if p.tgt_y is not None else p.src_y; z=p.tgt_z if p.tgt_z is not None else p.src_z
            vals=[item.number,p.name,"" if x is None else f"{x:.{precision}f}","" if y is None else f"{y:.{precision}f}","" if z is None else f"{z:.{precision}f}",p.status]
            for c,v in enumerate(vals):self.table.setItem(r,c,QTableWidgetItem(str(v)))

    def _populate(self):
        pts=self.result_points if self.result_points else self.source_points; self.total.setText(f"Total: {len(pts)}"); self.success.setText(f"Success: {sum(p.status=='SUCCESS' for p in pts)}"); self.failed.setText(f"Failed: {sum(p.status=='FAILED' for p in pts)}")

    def _convert(self):
        if not self.source_points: QMessageBox.warning(self,"No data","Choose a coordinate file first."); return
        if self.direct_mode.isChecked(): self._mode_changed(); return
        if self.parsing_engine.currentIndex()==1:
            try: mapped=self._apply_manual_mapping();
            except Exception as exc: QMessageBox.critical(self,"Parsing Error",str(exc)); return
            if mapped: self.source_points=self._apply_axis(mapped); self._refresh_preview()
        src=self.source_picker.selected_epsg(); tgt=self.target_picker.selected_epsg()
        if not src or not tgt: QMessageBox.warning(self,"No CRS","Select Source CRS and Target CRS, or enable DIRECT CAD EXPORT."); return
        self.result_points=[]; self.progress.setRange(0,len(self.source_points));
        for i,p in enumerate(self.source_points,1): self.result_points.append(self.engine.transform_points(src,tgt,[p])[0]); self.progress.setValue(i)
        self._populate(); self._refresh_preview()

    def _export_dxf(self):
        pts=self.result_points if not self.direct_mode.isChecked() else [PointResult(p.name,p.src_x,p.src_y,p.src_z,p.src_x,p.src_y,p.src_z,status="SUCCESS") for p in self.source_points]
        valid=[p for p in pts if p.status=="SUCCESS" and (p.tgt_x if not self.direct_mode.isChecked() else p.src_x) is not None and (p.tgt_y if not self.direct_mode.isChecked() else p.src_y) is not None]
        if not valid: QMessageBox.warning(self,"Nothing to export","No validated coordinates are available."); return
        path,_=QFileDialog.getSaveFileName(self,"Export DXF","CAD_Points.dxf","AutoCAD DXF (*.dxf)");
        if not path:return
        try:
            export_dxf(valid,path,label_mode=LabelMode.NAME if self.write_code.isChecked() else LabelMode.NUMBER,text_height=1.0,use_target_coords=not self.direct_mode.isChecked(),order_mode=str(self.ordering_mode.currentData()),group_by_name=self.group_by_name.isChecked()); QMessageBox.information(self,"DXF Exported",f"DXF created successfully:\n{path}")
        except Exception as exc: QMessageBox.critical(self,"DXF Export Error",str(exc))

    def _export_civil3d_csv(self):
        pts=self.result_points if not self.direct_mode.isChecked() else [PointResult(p.name,p.src_x,p.src_y,p.src_z,p.src_x,p.src_y,p.src_z,status="SUCCESS") for p in self.source_points]
        valid=[p for p in pts if p.status=="SUCCESS"]; path,_=QFileDialog.getSaveFileName(self,"Export Civil 3D CSV","Civil3D_Points.csv","CSV (*.csv)");
        if not path:return
        precision=current_precision(); ordered=order_points(valid,mode=str(self.ordering_mode.currentData()),group_by_name=self.group_by_name.isChecked())
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                w=csv.writer(f); w.writerow(["Point Number","Easting","Northing","Elevation","Description"])
                for item in ordered:
                    p=item.point; x=p.tgt_x if not self.direct_mode.isChecked() else p.src_x; y=p.tgt_y if not self.direct_mode.isChecked() else p.src_y; z=p.tgt_z if not self.direct_mode.isChecked() else p.src_z; w.writerow([item.number,f"{x:.{precision}f}",f"{y:.{precision}f}",f"{0 if z is None else z:.{precision}f}",p.name or ""])
            QMessageBox.information(self,"Civil 3D CSV Exported",f"File created successfully:\n{path}")
        except Exception as exc: QMessageBox.critical(self,"CSV Export Error",str(exc))

    def _reset_page(self):
        self.source_points=[]; self.result_points=[]; self.current_file=None; self.file_status.setText("No coordinate file loaded"); self.table.setRowCount(0); self.scene.clear(); self.preview_info.setText("0 points"); self.progress.setValue(0); self._populate()
