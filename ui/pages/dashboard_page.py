from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame, QHBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView
from core.batch.batch_processor import find_batch_files

class MetricCard(QFrame):
    def __init__(self, title, value="0", subtitle=""):
        super().__init__()
        self.setStyleSheet("QFrame{background:#1F3864;border-radius:8px;padding:12px;} QLabel{color:white;}")
        lay=QVBoxLayout(self)
        a=QLabel(title); a.setStyleSheet("font-size:11px;font-weight:bold;")
        self.value=QLabel(value); self.value.setStyleSheet("font-size:24px;font-weight:bold;color:#C9A227;")
        b=QLabel(subtitle); b.setStyleSheet("font-size:10px;color:#E8E8E8;")
        lay.addWidget(a); lay.addWidget(self.value); lay.addWidget(b)
    def set_value(self,value): self.value.setText(value)

class DashboardPage(QWidget):
    """Live project dashboard; no static feature placeholders."""
    def __init__(self):
        super().__init__(); self.folder=None
        root=QVBoxLayout(self); root.setContentsMargins(30,24,30,24); root.setAlignment(Qt.AlignTop)
        title=QLabel("MH GeoSuite Pro"); title.setStyleSheet("font-size:24px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        sub=QLabel("Professional Surveying & Geospatial Engineering Suite"); sub.setStyleSheet("color:#777;"); root.addWidget(sub)
        actions=QHBoxLayout(); scan=QPushButton("Scan Project Folder"); scan.clicked.connect(self._scan_folder); actions.addWidget(scan)
        refresh=QPushButton("Refresh"); refresh.clicked.connect(self.refresh); actions.addWidget(refresh); actions.addStretch()
        self.status=QLabel("Ready — select a project folder to inspect it."); actions.addWidget(self.status); root.addLayout(actions)
        metrics=QGridLayout(); self.files=MetricCard("FILES FOUND","0","Supported coordinate files"); self.formats=MetricCard("FORMATS","0","File types detected"); self.points=MetricCard("POINTS","—","Current scan"); self.engine=MetricCard("CRS ENGINE","PROJ","Global CRS database")
        for i,w in enumerate((self.files,self.formats,self.points,self.engine)): metrics.addWidget(w,0,i)
        root.addLayout(metrics)
        root.addWidget(QLabel("Project Files"))
        self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["File","Format","Size","Modified"]); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for i in (1,2,3): self.table.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(260); root.addWidget(self.table)
        note=QLabel("Live dashboard: scan a folder to inspect actual project files. Conversion and CAD/Civil 3D export are available from the dedicated tools."); note.setWordWrap(True); note.setStyleSheet("color:#555;margin-top:10px;"); root.addWidget(note)
    def _scan_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Select Project Folder")
        if folder: self.folder=folder; self.refresh()
    def refresh(self):
        if not self.folder: return
        try: files=find_batch_files(self.folder)
        except Exception as exc: self.status.setText(f"Scan error: {exc}"); return
        self.table.setRowCount(0); formats=set()
        for p in files:
            formats.add(p.suffix.lower()); row=self.table.rowCount(); self.table.insertRow(row)
            vals=[p.name,p.suffix.upper().lstrip('.'),f"{p.stat().st_size/1024:.1f} KB",datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')]
            for c,v in enumerate(vals): self.table.setItem(row,c,QTableWidgetItem(v))
        self.files.set_value(str(len(files))); self.formats.set_value(str(len(formats))); self.points.set_value("—"); self.status.setText(f"Scanned: {len(files)} supported file(s)")
