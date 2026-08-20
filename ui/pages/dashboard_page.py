from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame, QHBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from core.batch.batch_processor import find_batch_files


class MetricCard(QFrame):
    def __init__(self, title, value="0", subtitle=""):
        super().__init__()
        self.setStyleSheet("QFrame{background:#1F3864;border-radius:8px;padding:12px;} QLabel{color:white;}")
        lay = QVBoxLayout(self)
        a = QLabel(title); a.setStyleSheet("font-size:11px;font-weight:bold;")
        self.value = QLabel(value); self.value.setStyleSheet("font-size:24px;font-weight:bold;color:#C9A227;")
        b = QLabel(subtitle); b.setStyleSheet("font-size:10px;color:#E8E8E8;")
        lay.addWidget(a); lay.addWidget(self.value); lay.addWidget(b)
    def set_value(self, value): self.value.setText(value)


class DashboardPage(QWidget):
    file_selected = Signal(str)

    def __init__(self):
        super().__init__(); self.folder = None; self.active_file = None; self._highlighted_row = -1
        root = QVBoxLayout(self); root.setContentsMargins(30,24,30,24); root.setAlignment(Qt.AlignTop)
        title = QLabel("MH GeoSuite Pro"); title.setStyleSheet("font-size:24px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        root.addWidget(QLabel("Professional Surveying & Geospatial Engineering Suite"))
        actions = QHBoxLayout()
        scan = QPushButton("Scan Project Folder"); scan.clicked.connect(self._scan_folder); actions.addWidget(scan)
        refresh = QPushButton("Refresh"); refresh.clicked.connect(self.refresh); actions.addWidget(refresh)
        use = QPushButton("Use Selected File"); use.clicked.connect(self._use_selected_file); actions.addWidget(use)
        actions.addStretch(); self.status = QLabel("Ready — select a project folder to inspect it."); actions.addWidget(self.status); root.addLayout(actions)
        metrics = QGridLayout(); self.files=MetricCard("FILES FOUND","0","Supported coordinate files"); self.formats=MetricCard("FORMATS","0","File types detected"); self.points=MetricCard("ACTIVE FILE","—","Current workspace file"); self.engine=MetricCard("CRS ENGINE","PROJ","Global CRS database")
        for i,w in enumerate((self.files,self.formats,self.points,self.engine)): metrics.addWidget(w,0,i)
        root.addLayout(metrics)
        root.addWidget(QLabel("Project Files — double-click or select a row, then Use Selected File"))
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(["File","Format","Size","Modified","Path"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        for i in (1,2,3,4): self.table.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setStyleSheet("""
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background: #2B7DE0; color: white; border: 1px solid #5EA7FF; }
            QTableWidget::item:selected:active { background: #2B7DE0; color: white; }
            QTableWidget::item:selected:!active { background: #2B7DE0; color: white; }
        """)
        self.table.setMinimumHeight(260); self.table.itemClicked.connect(self._on_row_clicked); self.table.itemDoubleClicked.connect(lambda *_: self._use_selected_file()); root.addWidget(self.table)

    def _scan_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Select Project Folder")
        if folder: self.folder=folder; self.refresh()

    def _clear_row_highlight(self):
        if self._highlighted_row < 0: return
        for col in range(self.table.columnCount()):
            item = self.table.item(self._highlighted_row, col)
            if item:
                item.setBackground(QBrush())
                item.setForeground(QBrush())
        self._highlighted_row = -1

    def _highlight_row(self, row: int):
        self._clear_row_highlight()
        selected_bg = QBrush(QColor("#2B7DE0"))
        selected_fg = QBrush(QColor("#FFFFFF"))
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(selected_bg)
                item.setForeground(selected_fg)
        self._highlighted_row = row

    def refresh(self):
        if not self.folder: return
        try: files=find_batch_files(self.folder)
        except Exception as exc: self.status.setText(f"Scan error: {exc}"); return
        self._clear_row_highlight(); self.table.setRowCount(0); formats=set(); self.active_file=None
        for p in files:
            formats.add(p.suffix.lower()); row=self.table.rowCount(); self.table.insertRow(row)
            vals=[p.name,p.suffix.upper().lstrip('.'),f"{p.stat().st_size/1024:.1f} KB",datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),str(p)]
            for c,v in enumerate(vals): self.table.setItem(row,c,QTableWidgetItem(v))
        self.files.set_value(str(len(files))); self.formats.set_value(str(len(formats))); self.status.setText(f"Scanned: {len(files)} supported file(s)")

    def _on_row_clicked(self, item):
        row = item.row()
        self.table.selectRow(row)
        self._highlight_row(row)
        path_item = self.table.item(row, 4)
        if path_item:
            self.active_file = path_item.text()
            self.points.set_value(Path(self.active_file).name)
            self.status.setText(f"Selected file: {Path(self.active_file).name}")

    def _use_selected_file(self):
        row=self.table.currentRow()
        if row < 0: return
        self.table.selectRow(row); self._highlight_row(row)
        item=self.table.item(row,4)
        if not item: return
        path=item.text(); self.active_file=path; self.points.set_value(Path(path).name); self.status.setText(f"Active file: {Path(path).name}"); self.file_selected.emit(path)
