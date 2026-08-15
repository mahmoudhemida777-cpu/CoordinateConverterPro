from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)

HISTORY_FILE = Path.home() / ".mh_geosuite_pro_history.json"


def append_history(entry: dict) -> None:
    try:
        data = []
        if HISTORY_FILE.exists():
            try:
                loaded = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    data = loaded
            except (json.JSONDecodeError, OSError):
                data = []
        data.append(entry)
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(data[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class HistoryPage(QWidget):
    file_reloaded = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self); root.setContentsMargins(30, 20, 30, 20)
        title = QLabel("History — Conversion Log")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)

        row = QHBoxLayout()
        refresh = QPushButton("Refresh"); refresh.clicked.connect(self._load)
        self.reload_btn = QPushButton("Load Selected File")
        self.reload_btn.setStyleSheet("background-color:#C9A227;color:white;font-weight:bold;padding:7px 16px;")
        self.reload_btn.clicked.connect(self._reload_selected)
        self.open_folder_btn = QPushButton("Open File Folder"); self.open_folder_btn.clicked.connect(self._open_selected_folder)
        clear = QPushButton("Clear History"); clear.clicked.connect(self._clear)
        for b in (refresh, self.reload_btn, self.open_folder_btn, clear): row.addWidget(b)
        row.addStretch(); root.addLayout(row)

        self.status = QLabel("Select a history record to reload its source file and continue editing/conversion.")
        self.status.setStyleSheet("color:#666;"); root.addWidget(self.status)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date/Time", "Source File", "Source CRS", "Target CRS", "Points"])
        self.table.setAlternatingRowColors(True); self.table.setSortingEnabled(True); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemDoubleClicked.connect(lambda *_: self._reload_selected())
        header = self.table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeToContents); header.setStretchLastSection(True)
        root.addWidget(self.table); self._load()

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event); self._load()

    def _read_history(self):
        if not HISTORY_FILE.exists(): return []
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception: return []

    def _load(self) -> None:
        self.table.setSortingEnabled(False); self.table.setRowCount(0)
        for entry in reversed(self._read_history()):
            if not isinstance(entry, dict): continue
            r=self.table.rowCount(); self.table.insertRow(r)
            vals=[entry.get("time",""),entry.get("file",""),entry.get("source_crs",""),entry.get("target_crs",""),entry.get("points","")]
            for c,v in enumerate(vals): self.table.setItem(r,c,QTableWidgetItem(str(v)))
        self.table.setSortingEnabled(True); self.table.resizeColumnsToContents()
        self.reload_btn.setEnabled(self.table.rowCount()>0)

    def _selected_entry(self):
        row=self.table.currentRow()
        if row<0: return None
        visible=list(reversed(self._read_history()))
        # Sorting is temporarily disabled while loading; current row maps to this visible order.
        return visible[row] if 0<=row<len(visible) else None

    def _reload_selected(self):
        entry=self._selected_entry()
        if not entry:
            QMessageBox.information(self,"History","Select a conversion record first."); return
        path=entry.get("file")
        if not path or not Path(path).is_file():
            QMessageBox.warning(self,"File Not Found",f"The original file is no longer available at:\n{path or 'Unknown path'}\n\nUse 'Open File Folder' if you need to locate it manually."); return
        self.file_reloaded.emit(str(Path(path).resolve()))
        self.status.setText(f"Loaded: {Path(path).name} — ready for further conversion/export.")

    def _open_selected_folder(self):
        entry=self._selected_entry()
        if not entry: return
        path=entry.get("file")
        if not path: return
        p=Path(path)
        folder=p.parent if p.exists() else p.parent
        try:
            import os
            os.startfile(str(folder))
        except Exception as exc:
            QMessageBox.warning(self,"Open Folder",f"Could not open folder:\n{exc}")

    def _clear(self) -> None:
        if HISTORY_FILE.exists():
            try: HISTORY_FILE.unlink()
            except OSError as exc: QMessageBox.warning(self,"History Error",str(exc)); return
        self._load()
