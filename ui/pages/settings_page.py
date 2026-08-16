from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLabel, QSpinBox

from ui.i18n import tr, set_language
from ui.theme import current_theme, apply_theme

_SETTINGS = QSettings("Mahmoud Hemida", "MH GeoSuite Pro")

def current_precision() -> int:
    """Return the persisted application display/export precision."""
    try: value=int(_SETTINGS.value("precision",3))
    except (TypeError,ValueError): value=3
    return max(0,min(6,value))

class SettingsPage(QWidget):
    def __init__(self)->None:
        super().__init__()
        root=QVBoxLayout(self); root.setContentsMargins(30,30,30,30); root.setSpacing(14)
        title=QLabel(tr("Settings")); title.setStyleSheet("font-size:20px;font-weight:bold;"); root.addWidget(title)
        form=QFormLayout(); form.setVerticalSpacing(12)
        self.lang_combo=QComboBox(); self.lang_combo.addItems(["English","العربية"]); saved_lang=str(_SETTINGS.value("language","en")); self.lang_combo.setCurrentIndex(1 if saved_lang=="ar" else 0); self.lang_combo.currentIndexChanged.connect(self._on_language_changed); form.addRow("Language / اللغة:",self.lang_combo)
        self.theme_combo=QComboBox(); self.theme_combo.addItems(["Dark / داكن","Light / فاتح","Auto / تلقائي"]); saved_theme=current_theme(); self.theme_combo.setCurrentIndex({"dark":0,"light":1,"auto":2}[saved_theme]); self.theme_combo.currentIndexChanged.connect(self._on_theme_changed); form.addRow("Theme / المظهر:",self.theme_combo)
        self.precision_spin=QSpinBox(); self.precision_spin.setRange(0,6); self.precision_spin.setValue(current_precision()); self.precision_spin.valueChanged.connect(self._save_precision); form.addRow("Decimal Precision:",self.precision_spin)
        root.addLayout(form)
        hint=QLabel("Theme changes are applied immediately. Dark = professional black/navy, Light = white, Auto = follow Windows appearance."); hint.setWordWrap(True); hint.setObjectName("settingsHint"); root.addWidget(hint); root.addStretch()
    def _on_language_changed(self,index:int)->None:
        language="ar" if index==1 else "en"; _SETTINGS.setValue("language",language); _SETTINGS.sync(); set_language(language)
    def _on_theme_changed(self,index:int)->None:
        theme=("dark","light","auto")[index]; _SETTINGS.setValue("theme",theme); _SETTINGS.sync(); app=self.window().windowHandle().screen() if self.window().windowHandle() else None; qapp=self.window().findChild(QWidget)
        from PySide6.QtWidgets import QApplication
        instance=QApplication.instance()
        if instance is not None: apply_theme(instance,theme)
    def _save_precision(self,value:int)->None:
        _SETTINGS.setValue("precision",int(value)); _SETTINGS.sync()
    def precision(self)->int: return current_precision()
