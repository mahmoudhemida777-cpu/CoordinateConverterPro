"""Minimal AR/EN translation layer.

Not using Qt Linguist .ts/.qm compilation to keep the build pipeline
simple for v1 — this dict-based approach is easy to extend and test.
Switching language also flips the application layout direction for
proper Arabic RTL support.
"""
from __future__ import annotations

_CURRENT_LANG = "en"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ar": {
        "Ready": "جاهز",
        "Dashboard": "لوحة المعلومات",
        "Import": "استيراد",
        "CRS Converter": "محول الإحداثيات",
        "Survey Tools": "أدوات المساحة",
        "Civil / CAD": "مدني / CAD",
        "Batch Converter": "التحويل الجماعي",
        "Map": "الخريطة",
        "History": "السجل",
        "Settings": "الإعدادات",
        "About": "حول",
        "SOURCE FILE": "الملف المصدر",
        "SOURCE CRS": "نظام الإحداثيات المصدر",
        "TARGET CRS": "نظام الإحداثيات الهدف",
        "CONVERT": "تحويل",
        "Total Points": "إجمالي النقاط",
        "Successful": "ناجحة",
        "Failed": "فاشلة",
        "Warnings": "تحذيرات",
        "Choose File": "اختر ملفًا",
        "Choose Folder": "اختر مجلدًا",
    },
}


def set_language(lang: str) -> None:
    global _CURRENT_LANG
    _CURRENT_LANG = lang if lang in ("ar", "en") else "en"


def current_language() -> str:
    return _CURRENT_LANG


def is_rtl() -> bool:
    return _CURRENT_LANG == "ar"


def tr(text: str) -> str:
    if _CURRENT_LANG == "en":
        return text
    return _TRANSLATIONS.get(_CURRENT_LANG, {}).get(text, text)
