from __future__ import annotations

from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QProgressBar, QListWidget, QListWidgetItem, QMessageBox
from core.crs.engine import CRSEngine
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from core.exporters.xlsx_exporter import export_xlsx
from core.batch.batch_processor import find_batch_files, FileResult
from ui.i18n import tr
from ui.widgets.crs_picker import CRSPicker
from ui.pages.history_page import append_history
from ui.pages.settings_page import current_precision

SUPPORTED_FILTER = "Supported coordinate files (*.kmz *.kml *.csv *.xlsx *.txt);;KMZ/KML (*.kmz *.kml);;CSV (*.csv);;Excel (*.xlsx);;Survey TXT (*.txt)"


class BatchPage(QWidget):
    batch_completed = Signal(list, str, str)

    def __init__(self):
        super().__init__(); self.engine=CRSEngine(); self.folder=None; self.selected_files=[]; self.active_file=None; self.last_output_paths=[]
        root=QVBoxLayout(self); root.setContentsMargins(30,20,30,20)
        title=QLabel("MH GeoSuite Pro — Batch Converter"); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        row=QHBoxLayout()
        for text,fn in (("Choose Folder",self._choose_folder),("Choose Files",self._choose_files),("Use Active File",self._use_active_file),("Refresh Scan",self._refresh_scan)):
            b=QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        self.folder_label=QLabel("No folder/files selected"); row.addWidget(self.folder_label); row.addStretch(); root.addLayout(row)
        self.workspace_label=QLabel("Workspace: no active file"); self.workspace_label.setStyleSheet("color:#1F3864;font-weight:bold;"); root.addWidget(self.workspace_label)
        crs=QHBoxLayout(); self.source_picker=CRSPicker(self.engine,tr("SOURCE CRS")); self.target_picker=CRSPicker(self.engine,tr("TARGET CRS")); crs.addWidget(self.source_picker); crs.addWidget(self.target_picker); root.addLayout(crs)
        self.run_btn=QPushButton("CONVERT"); self.run_btn.setStyleSheet("background-color:#C9A227;color:white;font-weight:bold;padding:8px 24px;"); self.run_btn.clicked.connect(self._run_batch); root.addWidget(self.run_btn)
        self.progress_label=QLabel("Choose a folder, files, or use the Dashboard Active File."); root.addWidget(self.progress_label)
        self.progress=QProgressBar(); root.addWidget(self.progress); self.results_list=QListWidget(); root.addWidget(self.results_list); self.summary_label=QLabel(""); root.addWidget(self.summary_label)

    def load_active_file(self,path:str):
        p=Path(path)
        if p.is_file():
            self.active_file=p
            # Dashboard selection should seed Batch with the whole containing folder,
            # so Batch can process every supported file in that project in one run.
            self.folder=p.parent
            files=find_batch_files(str(self.folder))
            self._display_files(files, f"Project Folder: {self.folder}")
            self.workspace_label.setText(f"Workspace Active File: {p.name} | Batch folder: {self.folder}")
        else:
            self.active_file=None; self.folder=None; self.workspace_label.setText("Workspace: active file not found")

    def _use_active_file(self):
        if self.active_file and self.active_file.is_file():
            self.folder=self.active_file.parent
            files=find_batch_files(str(self.folder))
            self._display_files(files, f"Project Folder: {self.folder}")
        else:
            QMessageBox.information(self,"No Active File","Select a file in Dashboard first.")

    def _display_files(self,files,source):
        self.selected_files=list(files); self.results_list.clear(); self.progress.setValue(0); self.progress.setMaximum(max(len(files),1)); self.folder_label.setText(source); self.progress_label.setText(f"{len(files)} file(s) ready for CRS conversion")
        for p in files:self.results_list.addItem(QListWidgetItem(f"READY — {p.name} | {p}"))

    def _choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,tr("Choose Folder"))
        if folder:
            self.folder=folder; self.active_file=None; self._scan_folder()

    def _scan_folder(self):
        if not self.folder:return
        try:self._display_files(find_batch_files(str(self.folder)),f"Project Folder: {self.folder}")
        except Exception as e:QMessageBox.critical(self,"Scan Error",str(e))

    def _refresh_scan(self):
        if self.folder:self._scan_folder()
        elif self.selected_files:self._display_files(self.selected_files,"Selected files")
        elif self.active_file:self._use_active_file()

    def _choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Choose Coordinate Files","",SUPPORTED_FILTER)
        if paths:
            self.folder=None; self.active_file=None
            files=[Path(p) for p in paths if Path(p).is_file()]
            self._display_files(files,f"Selected files: {len(files)}")

    def _parse_file(self,path):
        s=path.suffix.casefold()
        if s==".kmz":return kml_parser.parse_kmz_file(str(path))
        if s==".kml":return kml_parser.parse_kml_file(str(path))
        if s==".csv":return csv_parser.parse_csv_auto(str(path))
        if s==".xlsx":
            c=xlsx_parser.sniff_columns(str(path)); return xlsx_parser.parse_xlsx(str(path),xlsx_parser.ColumnMapping(c[0],c[1],c[2],c[3] if len(c)>3 else None))
        if s==".txt":return txt_parser.parse_txt(str(path))
        raise ValueError(f"Unsupported file type: {s}")

    def _source_for_file(self, path: Path, selected_source: str) -> str:
        """KML/KMZ coordinates are defined as longitude/latitude (WGS84)."""
        if path.suffix.casefold() in {".kml", ".kmz"}:
            self.source_picker.set_selected("EPSG:4326", "WGS 84 — Geographic 2D (Latitude / Longitude)")
            return "EPSG:4326"
        return selected_source

    def _run_batch(self):
        files=find_batch_files(str(self.folder)) if self.folder else list(self.selected_files)
        if not files:QMessageBox.warning(self,"No files","No supported coordinate files selected."); return
        selected_src=self.source_picker.selected_epsg(); tgt=self.target_picker.selected_epsg()
        if not selected_src or not tgt:QMessageBox.warning(self,"No CRS","Select both Source CRS and Target CRS."); return
        self.results_list.clear(); self.progress.setMaximum(len(files)); self.run_btn.setEnabled(False); outputs=[]; results=[]
        try:
            for i,path in enumerate(files,1):
                self.progress.setValue(i); self.progress_label.setText(f"File {i} / {len(files)}: {path.name}")
                try:
                    src=self._source_for_file(path, selected_src)
                    points=self._parse_file(path)
                    if not points: raise ValueError("No coordinate points were found in the file.")
                    transformed=self.engine.transform_points(src,tgt,points)
                    ok=sum(p.status=="SUCCESS" for p in transformed); bad=sum(p.status=="FAILED" for p in transformed)
                    if ok==0:
                        first_error=next((p.message for p in transformed if p.message),"No valid points were produced.")
                        raise ValueError(f"CRS/coordinate validation failed for all points. {first_error}")
                    out=path.with_name(path.stem+"_converted.xlsx")
                    export_xlsx(transformed,str(out),src,tgt,precision=current_precision())
                    status="SUCCESS" if bad==0 else "WARNING"; r=FileResult(str(path),status,len(transformed),ok,bad,message=str(out)); results.append(r); outputs.append(str(out))
                    append_history({"time":datetime.now().astimezone().isoformat(timespec="seconds"),"file":path.name,"source_crs":src,"target_crs":tgt,"points":len(transformed),"operation":"Batch Conversion","status":status,"output":str(out)})
                except Exception as e: results.append(FileResult(str(path),"FAILED",message=str(e)))
            for r in results:self.results_list.addItem(QListWidgetItem(f"[{r.status}] {Path(r.path).name} — {r.points_success}/{r.points_total} points {r.message}"))
            good=sum(r.status=="SUCCESS" for r in results); bad=sum(r.status=="FAILED" for r in results); warn=sum(r.status=="WARNING" for r in results)
            self.summary_label.setText(f"Files: {len(results)}   Success: {good}   Warnings: {warn}   Failed: {bad}"); self.last_output_paths=outputs
            if outputs:self.batch_completed.emit(outputs,tgt,selected_src); self.progress_label.setText(f"Batch complete — {len(outputs)} converted file(s) propagated to CAD/Civil 3D.")
        finally:self.run_btn.setEnabled(True)
