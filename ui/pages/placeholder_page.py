from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class PlaceholderPage(QWidget):
    """Used for architecture-ready-but-not-yet-implemented tools (Survey
    Tools, Civil/CAD extras, Map, History). Explicitly labeled so nothing
    is presented as working when it isn't — per project quality rules."""

    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 13px; color: #555555; margin-top: 12px;")
        layout.addWidget(desc_label)
