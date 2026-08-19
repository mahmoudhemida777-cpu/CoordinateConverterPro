"""Runtime AR/EN translation and layout-direction support."""
from __future__ import annotations

from typing import Callable

_CURRENT_LANG = "en"
_LISTENERS: list[Callable[[str], None]] = []

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ar": {
        "Ready": "جاهز", "Dashboard": "لوحة المعلومات", "Import": "استيراد",
        "CRS Converter": "محول الإحداثيات", "Survey Tools": "أدوات المساحة",
        "Civil / CAD": "مدني / CAD", "Batch Converter": "التحويل الجماعي",
        "Map": "الخريطة", "History": "السجل", "Settings": "الإعدادات", "About": "حول",
        "SOURCE FILE": "الملف المصدر", "SOURCE CRS": "نظام الإحداثيات المصدر",
        "TARGET CRS": "نظام الإحداثيات الهدف", "CONVERT": "تحويل",
        "Total Points": "إجمالي النقاط", "Successful": "ناجحة", "Failed": "فاشلة", "Warnings": "تحذيرات",
        "Choose File": "اختيار ملف", "Choose Folder": "اختيار مجلد",
        "Open Coordinate File": "فتح ملف الإحداثيات", "Reload Selected": "إعادة تحميل المحدد",
        "Background": "الخلفية", "Show Labels": "إظهار التسميات", "FIT ALL POINTS": "إظهار جميع النقاط",
        "Point Size": "حجم النقطة", "Label Size": "حجم التسمية", "Light": "فاتح", "Dark": "داكن",
        "ZIGZAG / GRID ORDERING": "ترتيب Zigzag / الشبكة", "Ordering": "الترتيب",
        "Group": "المجموعة", "Start": "البداية", "North-West": "شمال غرب", "North-East": "شمال شرق",
        "Reverse Each Row": "عكس كل صف", "Auto Detect Grid": "اكتشاف الشبكة تلقائيًا",
        "Source Order": "ترتيب المصدر", "Point Code / Name": "كود / اسم النقطة", "All Points": "كل النقاط",
        "Settings": "الإعدادات", "Language / اللغة:": "اللغة:", "Theme / المظهر:": "المظهر:",
        "Decimal Precision:": "الدقة العشرية:", "Load CAD File": "تحميل ملف CAD", "Export DXF": "تصدير DXF",
        "Load Excel (.XLSX)": "تحميل Excel (.XLSX)", "Load CSV (.CSV)": "تحميل CSV (.CSV)",
        "Load Survey TXT (.TXT)": "تحميل ملف المساحة (.TXT)", "No file selected": "لم يتم اختيار ملف",
        "MAP — SURVEY POINT PREVIEW": "الخريطة — معاينة نقاط المساحة",
        "MAP DISPLAY CONTROLS": "عناصر التحكم بالخريطة", "MAP VIEW — ALL LOADED POINTS": "الخريطة — جميع النقاط المحملة",
        "Civil / CAD Converter": "محول Civil / CAD", "RESET": "إعادة ضبط",
        "Load failed": "فشل التحميل", "Map Error": "خطأ في الخريطة", "Import Error": "خطأ في الاستيراد",
    }
}


def register_language_listener(callback: Callable[[str], None]) -> None:
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def set_language(lang: str) -> None:
    global _CURRENT_LANG
    _CURRENT_LANG = lang if lang in ("ar", "en") else "en"
    for callback in tuple(_LISTENERS):
        try:
            callback(_CURRENT_LANG)
        except Exception:
            pass


def current_language() -> str:
    return _CURRENT_LANG


def is_rtl() -> bool:
    return _CURRENT_LANG == "ar"


def tr(text: str) -> str:
    if _CURRENT_LANG == "en":
        return text
    return _TRANSLATIONS.get(_CURRENT_LANG, {}).get(text, text)
