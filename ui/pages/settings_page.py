from __future__ import annotations
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLabel, QSpinBox, QApplication
from ui.i18n import tr, set_language
from ui.theme import current_theme, apply_theme

_SETTINGS = QSettings("Mahmoud Hemida", "MH GeoSuite Pro")


def current_precision() -> int:
    try:
        value = int(_SETTINGS.value("precision", 3))
    except (TypeError, ValueError):
        value = 3
    return max(0, min(6, value))


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(14)

        title = QLabel(tr("Settings"))
        title.setObjectName("pageTitle")
        title.setProperty("mhTextKey", "Settings")
        root.addWidget(title)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(14)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "العربية"])
        self.lang_combo.setItemData(0, "English", Qt.ItemDataRole.UserRole + 1)
        self.lang_combo.setItemData(1, "العربية", Qt.ItemDataRole.UserRole + 1)
        saved_lang = str(_SETTINGS.value("language", "ar") or "ar")
        self.lang_combo.setCurrentIndex(1 if saved_lang == "ar" else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        form.addRow(tr("Language / اللغة:"), self.lang_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark / داكن", "Light / فاتح", "Auto / تلقائي"])
        for i, key in enumerate(("Dark / داكن", "Light / فاتح", "Auto / تلقائي")):
            self.theme_combo.setItemData(i, key, Qt.ItemDataRole.UserRole + 1)
        saved_theme = current_theme()
        self.theme_combo.setCurrentIndex({"dark": 0, "light": 1, "auto": 2}[saved_theme])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow(tr("Theme / المظهر:"), self.theme_combo)

        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(0, 6)
        self.precision_spin.setValue(current_precision())
        self.precision_spin.valueChanged.connect(self._save_precision)
        form.addRow(tr("Decimal Precision:"), self.precision_spin)

        hint = QLabel(tr("Theme and language changes are applied immediately. Decimal precision is persisted for all pages that use current_precision()."))
        hint.setWordWrap(True)
        hint.setObjectName("settingsHint")
        hint.setProperty("mhTextKey", "Theme and language changes are applied immediately. Decimal precision is persisted for all pages that use current_precision().")
        root.addLayout(form)
        root.addWidget(hint)
        root.addStretch()

    def _on_language_changed(self, index: int) -> None:
        language = "ar" if index == 1 else "en"
        _SETTINGS.setValue("language", language)
        _SETTINGS.sync()
        set_language(language)
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft if language == "ar" else Qt.LayoutDirection.LeftToRight
            )

    def _on_theme_changed(self, index: int) -> None:
        theme = ("dark", "light", "auto")[index]
        _SETTINGS.setValue("theme", theme)
        _SETTINGS.sync()
        instance = QApplication.instance()
        if instance is not None:
            apply_theme(instance, theme)

    def _save_precision(self, value: int) -> None:
        _SETTINGS.setValue("precision", int(value))
        _SETTINGS.sync()

    def precision(self) -> int:
        return current_precision()
