from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QGraphicsView, QGraphicsScene, QMessageBox
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from ui.widgets.workspace_bar import WorkspaceFileBar

SUPPORTED_FILTER = "Supported files (*.csv *.xlsx *.kml *.kmz *.txt);;All files (*.*)"

class MapPage(QWidget):
    """Real offline coordinate map connected to the shared project workspace."""
    def __init__(self) -> None:
        super().__init__()
        self.workspace_folder: str | None = None
        self.current_file: Path | None = None
        root = QVBoxLayout(self); root.setContentsMargins(30, 20, 30, 20)
        title = QLabel("Map — Survey Point Preview"); title.setStyleSheet("font-size:20px;font-weight:bold;color:#1F3864;"); root.addWidget(title)
        self.workspace_bar = WorkspaceFileBar(); self.workspace_bar.file_selected.connect(self.load_active_file); root.addWidget(self.workspace_bar)
        self.workspace_label = QLabel("PROJECT WORKSPACE: Not selected"); self.workspace_label.setStyleSheet("font-weight:bold;color:#1F3864;"); root.addWidget(self.workspace_label)
        controls = QHBoxLayout(); self.open_btn = QPushButton("Open Coordinate File"); self.open_btn.clicked.connect(self._open); controls.addWidget(self.open_btn); self.reload_btn = QPushButton("Reload Selected"); self.reload_btn.clicked.connect(self._reload_selected); controls.addWidget(self.reload_btn); self.info = QLabel("No points loaded"); controls.addWidget(self.info, 1); root.addLayout(controls)
        self.scene = QGraphicsScene(self); self.view = QGraphicsView(self.scene); root.addWidget(self.view, 1)

    def set_workspace_folder(self, folder: str | None) -> None:
        self.workspace_folder = folder
        self.workspace_label.setText(f"PROJECT WORKSPACE: {folder or 'Not selected'}")
        self.workspace_bar.set_folder(folder, self.current_file)
        if self.current_file and self.current_file.exists(): self._load_path(str(self.current_file))

    def load_active_file(self, path: str) -> None:
        if not path or not Path(path).is_file(): return
        self.current_file = Path(path).resolve(); self.workspace_folder = str(self.current_file.parent)
        self.workspace_label.setText(f"PROJECT WORKSPACE: {self.workspace_folder}")
        self.workspace_bar.set_folder(self.workspace_folder, self.current_file)
        self._load_path(str(self.current_file))

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Coordinate File", self.workspace_folder or "", SUPPORTED_FILTER)
        if path: self.load_active_file(path)

    def _reload_selected(self) -> None:
        path = self.workspace_bar.selected_file()
        if path: self.load_active_file(path)

    def _load_path(self, path: str) -> None:
        try:
            file_path = Path(path); suffix = file_path.suffix.casefold()
            if suffix == ".kmz":
                points = kml_parser.parse_kmz_file(path)
            elif suffix == ".kml":
                points = kml_parser.parse_kml_file(path)
            elif suffix == ".txt":
                points = txt_parser.parse_txt(path)
            elif suffix == ".csv":
                # Map must use the same non-interactive smart parser as Import/CAD.
                points = csv_parser.parse_csv_auto(path)
            elif suffix == ".xlsx":
                # Map must use the same non-interactive smart parser as Import/CAD.
                points = xlsx_parser.parse_xlsx_auto(path)
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
            valid = [(p.name, p.src_x, p.src_y) for p in points if p.src_x is not None and p.src_y is not None]
            if not valid:
                raise ValueError("No valid X/Y points found in this file. The automatic parser could not identify usable X/Y coordinates.")
            self.current_file = file_path.resolve(); self._draw(valid); self.info.setText(f"{file_path.name} | {len(valid)} points | X/Y loaded successfully")
        except Exception as exc:
            self.scene.clear(); self.info.setText(f"Load failed: {Path(path).name}"); QMessageBox.critical(self, "Map Error", f"Could not load {Path(path).name}:\n{exc}")

    def _draw(self, points) -> None:
        self.scene.clear(); min_x = min(p[1] for p in points); max_x = max(p[1] for p in points); min_y = min(p[2] for p in points); max_y = max(p[2] for p in points); dx = max(max_x - min_x, 1e-9); dy = max(max_y - min_y, 1e-9); width, height, margin = 1000.0, 650.0, 45.0
        for name, x, y in points:
            sx = margin + (x - min_x) / dx * (width - 2 * margin); sy = height - (margin + (y - min_y) / dy * (height - 2 * margin)); item = self.scene.addEllipse(sx - 4, sy - 4, 8, 8, QPen(Qt.black), QBrush(Qt.black)); item.setToolTip(f"{name}\nX: {x}\nY: {y}")
        self.scene.setSceneRect(0, 0, width, height); self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
