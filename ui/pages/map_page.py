from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QGraphicsView,QGraphicsScene,QMessageBox,QSizePolicy
from core.parsers import csv_parser,xlsx_parser,kml_parser
from ui.pages.import_page import ColumnMappingDialog
from ui.i18n import tr

class MapPage(QWidget):
    """Offline point map/preview. No internet or map API is required."""
    def __init__(self)->None:
        super().__init__(); root=QVBoxLayout(self); root.setContentsMargins(20,14,20,14); root.setSpacing(10)
        title=QLabel(tr("Map — Survey Point Preview")); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        row=QHBoxLayout(); row.setSpacing(10); btn=QPushButton(tr("Open Coordinate File")); btn.setMinimumSize(150,40); btn.clicked.connect(self._open); row.addWidget(btn); self.info=QLabel(tr("No points loaded")); self.info.setMinimumHeight(36); row.addWidget(self.info); row.addStretch(); root.addLayout(row)
        self.scene=QGraphicsScene(self); self.view=QGraphicsView(self.scene); self.view.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding); self.view.setMinimumHeight(640); self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded); root.addWidget(self.view,1)
    def load_active_file(self,path:str)->None:
        if path and Path(path).is_file(): self._load_path(path)
    def _open(self)->None:
        path,_=QFileDialog.getOpenFileName(self,tr("Open Coordinate File"),"","Supported files (*.csv *.xlsx *.kml *.kmz);;All files (*.*)")
        if path:self._load_path(path)
    def _load_path(self,path:str)->None:
        try:
            suffix=Path(path).suffix.lower()
            if suffix==".kmz":points=kml_parser.parse_kmz_file(path)
            elif suffix==".kml":points=kml_parser.parse_kml_file(path)
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
        except Exception as exc:QMessageBox.critical(self,tr("Map Error"),str(exc))
    def _draw(self,points)->None:
        self.scene.clear(); min_x=min(p[1] for p in points); max_x=max(p[1] for p in points); min_y=min(p[2] for p in points); max_y=max(p[2] for p in points); dx=max(max_x-min_x,1e-9); dy=max(max_y-min_y,1e-9)
        viewport=self.view.viewport().size(); width=max(float(viewport.width()),1000.0); height=max(float(viewport.height()),700.0); margin=60.0
        for index,(name,x,y) in enumerate(points,1):
            sx=margin+(x-min_x)/dx*(width-2*margin); sy=height-(margin+(y-min_y)/dy*(height-2*margin)); radius=5.0 if len(points)<500 else 3.5
            item=self.scene.addEllipse(sx-radius,sy-radius,radius*2,radius*2,QPen(Qt.black),QBrush(Qt.black)); item.setToolTip(f"{name}\nX: {x}\nY: {y}")
        self.scene.setSceneRect(0,0,width,height); self.view.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)
