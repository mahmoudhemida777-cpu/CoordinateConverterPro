from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush,QPen
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QGraphicsView,QGraphicsScene,QMessageBox
from core.parsers import csv_parser,xlsx_parser,kml_parser,txt_parser
from ui.pages.import_page import ColumnMappingDialog
from ui.widgets.workspace_bar import WorkspaceFileBar

class MapPage(QWidget):
    """Offline point map/preview. Uses the shared project workspace."""
    def __init__(self)->None:
        super().__init__(); self.workspace_folder=None; root=QVBoxLayout(self); root.setContentsMargins(30,20,30,20); title=QLabel("Map — Survey Point Preview"); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        self.workspace_bar=WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self._load_path); root.addWidget(self.workspace_bar)
        row=QHBoxLayout(); btn=QPushButton("Open Coordinate File"); btn.clicked.connect(self._open); row.addWidget(btn); self.info=QLabel("No points loaded"); row.addWidget(self.info); row.addStretch(); root.addLayout(row); self.scene=QGraphicsScene(self); self.view=QGraphicsView(self.scene); root.addWidget(self.view)
    def set_workspace_folder(self,folder:str): self.workspace_folder=folder; self.workspace_bar.set_folder(folder)
    def load_active_file(self,path:str)->None:
        if path and Path(path).is_file(): self.workspace_folder=str(Path(path).parent); self.workspace_bar.set_folder(self.workspace_folder,path); self._load_path(path)
    def _open(self)->None:
        path,_=QFileDialog.getOpenFileName(self,"Open Coordinate File",self.workspace_folder or "","Supported files (*.csv *.xlsx *.kml *.kmz *.txt);;All files (*.*)")
        if path:self._load_path(path)
    def _load_path(self,path:str)->None:
        try:
            suffix=Path(path).suffix.lower()
            if suffix==".kmz":points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml":points=kml_parser.parse_kml_file(path)
            elif suffix==".txt":points=txt_parser.parse_txt(path)
            elif suffix==".csv":
                dlg=ColumnMappingDialog(csv_parser.sniff_columns(path),self)
                if dlg.exec()!=dlg.Accepted:return
                points=csv_parser.parse_csv(path,csv_parser.ColumnMapping(**dlg.result_mapping()))
            elif suffix==".xlsx":
                dlg=ColumnMappingDialog(xlsx_parser.sniff_columns(path),self)
                if dlg.exec()!=dlg.Accepted:return
                points=xlsx_parser.parse_xlsx(path,xlsx_parser.ColumnMapping(**dlg.result_mapping()))
            else:raise ValueError("Unsupported file type")
            valid=[(p.name,p.src_x,p.src_y) for p in points if p.src_x is not None and p.src_y is not None]
            if not valid:raise ValueError("No valid X/Y points found")
            self._draw(valid); self.info.setText(f"{Path(path).name} — {len(valid)} points")
        except Exception as exc:QMessageBox.critical(self,"Map Error",str(exc))
    def _draw(self,points)->None:
        self.scene.clear(); min_x=min(p[1] for p in points); max_x=max(p[1] for p in points); min_y=min(p[2] for p in points); max_y=max(p[2] for p in points); dx=max(max_x-min_x,1e-9); dy=max(max_y-min_y,1e-9); width,height,margin=900.0,600.0,40.0
        for name,x,y in points:
            sx=margin+(x-min_x)/dx*(width-2*margin); sy=height-(margin+(y-min_y)/dy*(height-2*margin)); item=self.scene.addEllipse(sx-3,sy-3,6,6,QPen(Qt.black),QBrush(Qt.black)); item.setToolTip(f"{name}\nX: {x}\nY: {y}")
        self.scene.setSceneRect(0,0,width,height); self.view.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)
