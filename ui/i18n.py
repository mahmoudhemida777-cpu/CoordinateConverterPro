"""Minimal AR/EN translation layer.

The stable UI structure is intentionally preserved; this module only translates
existing labels and switches the application direction for Arabic.
"""
from __future__ import annotations

_CURRENT_LANG = "en"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ar": {
        "Ready": "جاهز", "Dashboard": "لوحة المعلومات", "Import": "استيراد",
        "CRS Converter": "محول الإحداثيات", "Survey Tools": "أدوات المساحة",
        "Civil / CAD": "مدني / CAD", "Batch Converter": "التحويل الجماعي",
        "Map": "الخريطة", "History": "السجل", "Settings": "الإعدادات", "About": "حول",
        "SOURCE FILE": "الملف المصدر", "SOURCE CRS": "نظام الإحداثيات المصدر",
        "TARGET CRS": "نظام الإحداثيات الهدف", "CONVERT": "تحويل", "Total Points": "إجمالي النقاط",
        "Successful": "ناجحة", "Failed": "فاشلة", "Warnings": "تحذيرات", "Choose File": "اختر ملفًا",
        "Choose Folder": "اختر مجلدًا", "Map — Survey Point Preview": "الخريطة — معاينة نقاط المساحة",
        "Open Coordinate File": "فتح ملف الإحداثيات", "No points loaded": "لم يتم تحميل أي نقاط",
        "Map Error": "خطأ في الخريطة", "points": "نقاط", "POINT": "نقطة", "Point": "نقطة",
        "Label": "التسمية", "Show Labels": "إظهار التسميات", "Point Size": "حجم النقطة",
        "Background": "الخلفية", "FIT ALL POINTS": "إظهار جميع النقاط", "MAP VIEW - ALL LOADED POINTS": "عرض الخريطة — جميع النقاط المحملة",
        "Loaded": "تم تحميل", "No valid X/Y points found": "لم يتم العثور على إحداثيات X/Y صالحة",
        "Unsupported file type": "نوع الملف غير مدعوم",
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
