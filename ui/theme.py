"""MH GeoSuite Pro professional theme system."""
from __future__ import annotations
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel
from PySide6.QtCore import QTimer, QSettings

DARK = {
    "BG":"#0B1420","SURFACE":"#111E2D","SURFACE_2":"#16263A","BORDER":"#2A4058",
    "TEXT":"#E8EEF5","MUTED":"#9BAFC3","BLUE":"#1976D2","BLUE_HOVER":"#2587E8",
    "GOLD":"#C9A227","SUCCESS":"#35D07F","DANGER":"#F05B5B","BASE":"#0E1926",
}
LIGHT = {
    "BG":"#F4F7FB","SURFACE":"#FFFFFF","SURFACE_2":"#EAF0F7","BORDER":"#C8D4E2",
    "TEXT":"#172B45","MUTED":"#5F7186","BLUE":"#1769D1","BLUE_HOVER":"#2B7DE0",
    "GOLD":"#B38300","SUCCESS":"#158A52","DANGER":"#C83D3D","BASE":"#FFFFFF",
}

_SETTINGS = QSettings("Mahmoud Hemida", "MH GeoSuite Pro")

def current_theme() -> str:
    value=str(_SETTINGS.value("theme", "dark") or "dark").lower()
    return value if value in {"dark","light","auto"} else "dark"

def _colors_for(app: QApplication, theme: str) -> dict[str,str]:
    if theme == "light": return LIGHT
    if theme == "auto":
        try:
            return LIGHT if app.styleHints().colorScheme().name.lower() == "light" else DARK
        except Exception:
            return DARK
    return DARK

def _normalize_legacy_page_styles(app: QApplication) -> None:
    """Remove old local light styles that override the application theme."""
    for widget in app.allWidgets():
        local=widget.styleSheet() or ""
        if not local: continue
        light_markers=("background:white","background: white","background-color:white","background-color: white","color:#1F3864","color: #1F3864","color:#555","color: #555","color:#333","color: #333","color:#777","color: #777","#C9D2DE","#D8C58A")
        if any(marker in local for marker in light_markers):
            if widget.__class__.__name__ == "QPushButton" and "#C9A227" in local:
                widget.setStyleSheet("")
            else:
                widget.setStyleSheet("")

def apply_theme(app: QApplication, theme: str | None = None) -> None:
    """Apply the selected application-wide theme."""
    selected=(theme or current_theme()).lower()
    if selected not in {"dark","light","auto"}: selected="dark"
    c=_colors_for(app,selected)
    palette=QPalette()
    palette.setColor(QPalette.Window,QColor(c["BG"]))
    palette.setColor(QPalette.WindowText,QColor(c["TEXT"]))
    palette.setColor(QPalette.Base,QColor(c["BASE"]))
    palette.setColor(QPalette.AlternateBase,QColor(c["SURFACE"]))
    palette.setColor(QPalette.Text,QColor(c["TEXT"]))
    palette.setColor(QPalette.Button,QColor(c["SURFACE_2"]))
    palette.setColor(QPalette.ButtonText,QColor(c["TEXT"]))
    palette.setColor(QPalette.Highlight,QColor(c["BLUE"]))
    palette.setColor(QPalette.HighlightedText,QColor("#FFFFFF"))
    palette.setColor(QPalette.PlaceholderText,QColor(c["MUTED"]))
    app.setPalette(palette)
    app.setStyleSheet(f"""
    * {{ font-family:'Segoe UI','Arial'; font-size:10pt; }}
    QMainWindow,QWidget {{ background:{c['BG']}; color:{c['TEXT']}; }}
    QFrame,QGroupBox {{ border:1px solid {c['BORDER']}; border-radius:8px; background:{c['SURFACE']}; }}
    QGroupBox {{ margin-top:12px; padding:16px 10px 10px 10px; font-weight:700; color:{c['TEXT']}; }}
    QGroupBox::title {{ subcontrol-origin:margin; left:12px; padding:0 6px; color:{c['TEXT']}; background:{c['SURFACE']}; }}
    QLabel {{ color:{c['TEXT']}; background:transparent; }}
    QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {{ background:{c['BASE']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; border-radius:6px; padding:7px 9px; min-height:20px; }}
    QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {{ border:1px solid {c['BLUE']}; }}
    QComboBox::drop-down {{ border:0; width:26px; }}
    QComboBox QAbstractItemView {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; selection-background-color:{c['BLUE']}; selection-color:#FFFFFF; }}
    QPushButton {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; border-radius:6px; padding:8px 14px; font-weight:600; min-height:18px; }}
    QPushButton:hover {{ background:{c['BLUE_HOVER']}; border-color:{c['BLUE_HOVER']}; color:#FFFFFF; }}
    QPushButton:pressed {{ background:{c['BLUE']}; color:#FFFFFF; }}
    QCheckBox,QRadioButton {{ color:{c['TEXT']}; spacing:8px; font-weight:500; }}
    QCheckBox:checked,QRadioButton:checked {{ color:{c['TEXT']}; font-weight:700; }}
    QCheckBox::indicator,QRadioButton::indicator {{ width:17px; height:17px; }}
    QCheckBox::indicator:unchecked,QRadioButton::indicator:unchecked {{ border:2px solid {c['MUTED']}; background:{c['SURFACE_2']}; border-radius:4px; }}
    QCheckBox::indicator:hover,QRadioButton::indicator:hover {{ border:2px solid {c['BLUE_HOVER']}; }}
    QCheckBox::indicator:checked {{ border:2px solid {c['BLUE']}; background:{c['BLUE']}; border-radius:4px; }}
    QRadioButton::indicator:checked {{ border:2px solid {c['BLUE']}; background:{c['BLUE']}; border-radius:9px; }}
    QGroupBox:checked {{ border:1px solid {c['BLUE']}; }}
    QGroupBox:unchecked {{ border:1px solid {c['BORDER']}; color:{c['MUTED']}; }}
    QGroupBox::indicator {{ width:16px; height:16px; }}
    QGroupBox::indicator:unchecked {{ border:2px solid {c['MUTED']}; background:{c['SURFACE_2']}; border-radius:8px; }}
    QGroupBox::indicator:checked {{ border:2px solid {c['BLUE']}; background:{c['BLUE']}; border-radius:8px; }}
    #cadPage QComboBox:hover,#cadPage QLineEdit:hover {{ border:1px solid {c['BLUE_HOVER']}; }}
    #cadPage QPushButton:focus {{ border:2px solid {c['BLUE_HOVER']}; }}
    QProgressBar {{ background:{c['BASE']}; border:1px solid {c['BORDER']}; border-radius:5px; text-align:center; color:{c['TEXT']}; min-height:12px; }}
    QProgressBar::chunk {{ background:{c['BLUE']}; border-radius:4px; }}
    QTableWidget,QTreeWidget,QListWidget {{ background:{c['BASE']}; alternate-background-color:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; gridline-color:{c['BORDER']}; selection-background-color:{c['BLUE']}; selection-color:#FFFFFF; }}
    QHeaderView::section {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:0; border-right:1px solid {c['BORDER']}; border-bottom:1px solid {c['BORDER']}; padding:8px; font-weight:700; }}
    QScrollBar:vertical {{ background:{c['BG']}; width:10px; margin:0; }}
    QScrollBar::handle:vertical {{ background:#304A64; border-radius:5px; min-height:30px; }}
    QScrollBar::handle:vertical:hover {{ background:{c['BLUE']}; }}
    QScrollBar:horizontal {{ background:{c['BG']}; height:10px; }}
    QScrollBar::handle:horizontal {{ background:#304A64; border-radius:5px; min-width:30px; }}
    QStatusBar {{ background:{'#08111B' if selected!='light' else '#E6EDF5'}; color:{c['MUTED']}; border-top:1px solid {c['BORDER']}; }}
    #sidebar {{ background:{'#09131F' if selected!='light' else '#E7EEF6'}; border:0; border-right:1px solid {c['BORDER']}; padding:8px; outline:0; }}
    #sidebar::item {{ color:{c['MUTED']}; padding:12px 14px; margin:2px 0; border-radius:6px; }}
    #sidebar::item:hover {{ background:{'#14283D' if selected!='light' else '#D8E6F5'}; color:{c['TEXT']}; }}
    #sidebar::item:selected {{ background:{c['BLUE']}; color:#FFFFFF; font-weight:700; }}
    #workspaceBanner {{ background:{'#10243A' if selected!='light' else '#E1EBF5'}; color:{c['TEXT']}; padding:8px 14px; border-bottom:1px solid {c['BORDER']}; }}
    QMessageBox {{ background:{c['SURFACE']}; color:{c['TEXT']}; }}
    """)
    QTimer.singleShot(0,lambda:_normalize_legacy_page_styles(app))
    QTimer.singleShot(500,lambda:_normalize_legacy_page_styles(app))
