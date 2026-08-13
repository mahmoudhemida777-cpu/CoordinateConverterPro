from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtCore import QEvent
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
        HISTORY_FILE.write_text(
            json.dumps(data[-200:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        # History must never break the conversion workflow.
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
        row.addWidget(refresh)
        row.addWidget(clear)
        row.addStretch()
        root.addLayout(row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Date/Time", "Source File", "Source CRS", "Target CRS", "Points"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        root.addWidget(self.table)
        self._load()

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        # Reload every time the user opens History so conversions made on
        # another page (including Batch) appear immediately.
        self._load()

    def _load(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        if not HISTORY_FILE.exists():
            self.table.setSortingEnabled(True)
            return
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
            for entry in reversed(data):
                if not isinstance(entry, dict):
                    continue
                r = self.table.rowCount()
                self.table.insertRow(r)
                vals = [
                    entry.get("time", ""),
                    entry.get("file", ""),
                    entry.get("source_crs", ""),
                    entry.get("target_crs", ""),
                    entry.get("points", ""),
                ]
                for c, v in enumerate(vals):
                    self.table.setItem(r, c, QTableWidgetItem(str(v)))
        except Exception as exc:
            QMessageBox.warning(self, "History Error", str(exc))
        finally:
            self.table.setSortingEnabled(True)
            self.table.resizeColumnsToContents()

    def _clear(self) -> None:
        if HISTORY_FILE.exists():
            try:
                HISTORY_FILE.unlink()
            except OSError as exc:
                QMessageBox.warning(self, "History Error", str(exc))
                return
        self._load()
