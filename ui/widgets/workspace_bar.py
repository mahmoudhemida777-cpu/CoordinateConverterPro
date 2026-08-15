from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox
from core.batch.batch_processor import find_batch_files


class WorkspaceFileBar(QWidget):
    """Shared project-folder navigator used by all file-based pages."""

    file_selected = Signal(str)
    folder_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder: Path | None = None
        self.files: list[Path] = []
        self.current_path: Path | None = None
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel("PROJECT FILE:"))
        self.combo = QComboBox()
        self.combo.setMinimumWidth(320)
        self.combo.currentIndexChanged.connect(self._combo_changed)
        row.addWidget(self.combo, 1)
        self.prev_btn = QPushButton("◀ Previous")
        self.next_btn = QPushButton("Next ▶")
        self.load_btn = QPushButton("LOAD SELECTED")
        self.prev_btn.clicked.connect(self.previous)
        self.next_btn.clicked.connect(self.next)
        self.load_btn.clicked.connect(self.load_selected)
        row.addWidget(self.prev_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.load_btn)
        self._update_buttons()

    def set_folder(self, folder: str | Path | None, current: str | Path | None = None):
        self.folder = Path(folder).expanduser() if folder else None
        self.files = find_batch_files(str(self.folder)) if self.folder else []
        self.combo.blockSignals(True)
        self.combo.clear()
        for p in self.files:
            self.combo.addItem(p.name, str(p))
        self.combo.blockSignals(False)
        self.current_path = Path(current) if current else (self.files[0] if self.files else None)
        if self.current_path:
            idx = next((i for i, p in enumerate(self.files) if p.resolve() == self.current_path.resolve()), 0)
            self.combo.setCurrentIndex(idx)
        self._update_buttons()
        if self.folder:
            self.folder_changed.emit(str(self.folder))

    def refresh(self):
        self.set_folder(self.folder, self.current_path)

    def _combo_changed(self, index: int):
        if 0 <= index < len(self.files):
            self.current_path = self.files[index]
        self._update_buttons()

    def _update_buttons(self):
        has = bool(self.files)
        idx = self.combo.currentIndex()
        self.prev_btn.setEnabled(has and idx > 0)
        self.next_btn.setEnabled(has and idx >= 0 and idx < len(self.files) - 1)
        self.load_btn.setEnabled(has and idx >= 0)

    def previous(self):
        idx = self.combo.currentIndex()
        if idx > 0:
            self.combo.setCurrentIndex(idx - 1)
            self.load_selected()

    def next(self):
        idx = self.combo.currentIndex()
        if idx < len(self.files) - 1:
            self.combo.setCurrentIndex(idx + 1)
            self.load_selected()

    def load_selected(self):
        idx = self.combo.currentIndex()
        if 0 <= idx < len(self.files):
            self.current_path = self.files[idx]
            self.file_selected.emit(str(self.current_path))

    def selected_file(self) -> str | None:
        idx = self.combo.currentIndex()
        return str(self.files[idx]) if 0 <= idx < len(self.files) else None
