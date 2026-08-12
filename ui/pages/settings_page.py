from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox, QLabel, QSpinBox,
)

from ui.i18n import tr, set_language


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)

        title = QLabel(tr("Settings"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1F3864;")
        root.addWidget(title)

        form = QFormLayout()

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "العربية"])
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        form.addRow("Language / اللغة:", self.lang_combo)

        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(0, 6)
        self.precision_spin.setValue(3)
        form.addRow("Decimal Precision:", self.precision_spin)

        root.addLayout(form)
        root.addStretch()

    def _on_language_changed(self, index: int) -> None:
        set_language("ar" if index == 1 else "en")

    def precision(self) -> int:
        return self.precision_spin.value()
