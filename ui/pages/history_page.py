from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox


HISTORY_FILE = Path.home() / ".mh_geosuite_pro_history.json"


def append_history(entry: dict) -> None:
    try:
        data = []
        if HISTORY_FILE.exists():
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        data.append(entry)
        HISTORY_FILE.write_text(json.dumps(data[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 20, 30, 20)
        title = QLabel("History — Conversion Log")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;")
        root.addWidget(title)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self._load)
        clear = QPushButton("Clear History")
        clear.clicked.connect(self._clear)
        row.addWidget(refresh); row.addWidget(clear); row.addStretch()
        root.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date/Time", "Source File", "Source CRS", "Target CRS", "Points"])
        root.addWidget(self.table)
        self._load()

    def _load(self) -> None:
        self.table.setRowCount(0)
        if not HISTORY_FILE.exists():
            return
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            for entry in reversed(data):
                r = self.table.rowCount(); self.table.insertRow(r)
                vals = [entry.get("time", ""), entry.get("file", ""), entry.get("source_crs", ""), entry.get("target_crs", ""), entry.get("points", "")]
                for c, v in enumerate(vals): self.table.setItem(r, c, QTableWidgetItem(str(v)))
        except Exception as exc:
            QMessageBox.warning(self, "History Error", str(exc))

    def _clear(self) -> None:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        self._load()
