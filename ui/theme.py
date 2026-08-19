"""MH - Coordinate professional theme system."""
from __future__ import annotations
from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QSplitter
from PySide6.QtCore import QTimer, QSettings, QObject, QEvent, Qt

DARK = {"BG":"#0B1420","SURFACE":"#111E2D","SURFACE_2":"#16263A","BORDER":"#2A4058","TEXT":"#E8EEF5","MUTED":"#9BAFC3","BLUE":"#1976D2","BLUE_HOVER":"#2587E8","GOLD":"#C9A227","SUCCESS":"#35D07F","DANGER":"#F05B5B","BASE":"#0E1926"}
LIGHT = {"BG":"#F4F7FB","SURFACE":"#FFFFFF","SURFACE_2":"#EAF0F7","BORDER":"#C8D4E2","TEXT":"#172B45","MUTED":"#5F7186","BLUE":"#1769D1","BLUE_HOVER":"#2B7DE0","GOLD":"#B38300","SUCCESS":"#158A52","DANGER":"#C83D3D","BASE":"#FFFFFF"}
_SETTINGS = QSettings("Mahmoud Hemida", "MH GeoSuite Pro")


def current_theme() -> str:
    value=str(_SETTINGS.value("theme", "dark") or "dark").lower()
    return value if value in {"dark","light","auto"} else "dark"


def preferred_font() -> QFont:
    families = QFontDatabase.families()
    for name in ("Tajawal", "Noto Sans Arabic", "Noto Sans", "Segoe UI"):
        if name in families:
            font = QFont(name, 10)
            font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            return font
    return QFont("Arial", 10)


def _colors_for(app: QApplication, theme: str) -> dict[str,str]:
    if theme == "light": return LIGHT
    if theme == "auto":
        try: return LIGHT if app.styleHints().colorScheme().name.lower() == "light" else DARK
        except Exception: return DARK
    return DARK


def _normalize_legacy_page_styles(app: QApplication) -> None:
    for widget in app.allWidgets():
        local=widget.styleSheet() or ""
        if not local: continue
        markers=("background:white","background: white","background-color:white","background-color: white","color:#1F3864","color: #1F3864","color:#555","color: #555","color:#333","color: #333","color:#777","color: #777","#C9D2DE","#D8C58A")
        if any(marker in local for marker in markers): widget.setStyleSheet("")


class _CadResponsiveFilter(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize: self._apply(watched)
        return False
    @staticmethod
    def _apply(page) -> None:
        splitter = page.findChild(QSplitter)
        if splitter is None: return
        narrow = page.width() < 1400
        wanted = Qt.Orientation.Vertical if narrow else Qt.Orientation.Horizontal
        if splitter.orientation() != wanted:
            splitter.setOrientation(wanted); splitter.setSizes([610, 430] if narrow else [540, 760])
        elif narrow:
            sizes=splitter.sizes()
            if len(sizes)==2 and (sizes[0] < 500 or sizes[1] < 280): splitter.setSizes([610, 430])


def _install_cad_responsive_layout(app: QApplication) -> None:
    for widget in app.allWidgets():
        if widget.objectName() != "cadPage": continue
        if widget.property("mhCadResponsiveInstalled"):
            _CadResponsiveFilter._apply(widget); continue
        filt=_CadResponsiveFilter(widget); widget.installEventFilter(filt)
        widget.setProperty("mhCadResponsiveInstalled", True); widget.setProperty("mhCadResponsiveFilter", filt)
        _CadResponsiveFilter._apply(widget)


def apply_theme(app: QApplication, theme: str | None = None) -> None:
    selected=(theme or current_theme()).lower()
    if selected not in {"dark","light","auto"}: selected="dark"
    c=_colors_for(app,selected)
    app.setFont(preferred_font())
    palette=QPalette()
    for role,key in ((QPalette.Window,"BG"),(QPalette.WindowText,"TEXT"),(QPalette.Base,"BASE"),(QPalette.AlternateBase,"SURFACE"),(QPalette.Text,"TEXT"),(QPalette.Button,"SURFACE_2"),(QPalette.ButtonText,"TEXT"),(QPalette.Highlight,"BLUE"),(QPalette.PlaceholderText,"MUTED")):
        palette.setColor(role,QColor(c[key]))
    palette.setColor(QPalette.HighlightedText,QColor("#FFFFFF")); app.setPalette(palette)
    app.setStyleSheet(f"""
    * {{ font-family:'Tajawal','Noto Sans Arabic','Noto Sans','Segoe UI','Arial'; font-size:10.5pt; }}
    QMainWindow,QWidget {{ background:{c['BG']}; color:{c['TEXT']}; }}
    QFrame {{ background:transparent; border:0; }}
    QGroupBox {{ margin-top:16px; padding:22px 12px 12px 12px; border:1px solid {c['BORDER']}; border-radius:9px; background:{c['SURFACE']}; font-weight:700; color:{c['TEXT']}; }}
    QGroupBox::title {{ subcontrol-origin:margin; left:12px; top:3px; padding:2px 8px; color:{c['TEXT']}; background:{c['SURFACE']}; }}
    QLabel {{ color:{c['TEXT']}; background:transparent; }}
    #pageTitle {{ font-size:18pt; font-weight:800; color:{c['TEXT']}; }}
    #pageSubtitle {{ color:{c['MUTED']}; font-size:10pt; }}
    QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox {{ background:{c['BASE']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; border-radius:7px; padding:7px 10px; min-height:24px; selection-background-color:{c['BLUE']}; selection-color:#FFFFFF; }}
    QLineEdit:focus,QTextEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {{ border:2px solid {c['BLUE']}; }}
    QComboBox QAbstractItemView {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; selection-background-color:{c['BLUE']}; selection-color:#FFFFFF; padding:4px; }}
    QComboBox QAbstractItemView::item {{ padding:8px 10px; min-height:26px; }}
    QComboBox::drop-down {{ border:0; width:30px; }}
    QPushButton {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; border-radius:7px; padding:8px 14px; font-weight:600; min-height:28px; min-width:100px; }}
    QPushButton:hover {{ background:{c['BLUE_HOVER']}; border-color:{c['BLUE_HOVER']}; color:#FFFFFF; }}
    QPushButton:pressed,QPushButton:checked {{ background:{c['BLUE']}; color:#FFFFFF; }}
    QCheckBox,QRadioButton {{ color:{c['TEXT']}; spacing:7px; font-weight:500; min-height:28px; }}
    QCheckBox::indicator,QRadioButton::indicator {{ width:18px; height:18px; }}
    QTableWidget,QTreeWidget,QListWidget {{ background:{c['BASE']}; alternate-background-color:{c['SURFACE_2']}; color:{c['TEXT']}; border:1px solid {c['BORDER']}; gridline-color:{c['BORDER']}; selection-background-color:{c['BLUE']}; selection-color:#FFFFFF; }}
    QHeaderView::section {{ background:{c['SURFACE_2']}; color:{c['TEXT']}; border:0; border-right:1px solid {c['BORDER']}; border-bottom:1px solid {c['BORDER']}; padding:8px; font-weight:700; }}
    QSplitter::handle {{ background:{c['BORDER']}; }}
    QScrollBar:vertical {{ background:{c['BG']}; width:10px; }} QScrollBar::handle:vertical {{ background:#304A64; border-radius:5px; min-height:30px; }}
    QScrollBar:horizontal {{ background:{c['BG']}; height:10px; }} QScrollBar::handle:horizontal {{ background:#304A64; border-radius:5px; min-width:30px; }}
    QProgressBar {{ background:{c['BASE']}; border:1px solid {c['BORDER']}; border-radius:5px; text-align:center; color:{c['TEXT']}; min-height:14px; }} QProgressBar::chunk {{ background:{c['BLUE']}; border-radius:4px; }}
    QStatusBar {{ background:{'#08111B' if selected!='light' else '#E6EDF5'}; color:{c['MUTED']}; border-top:1px solid {c['BORDER']}; }}
    #sidebar {{ background:{'#09131F' if selected!='light' else '#E7EEF6'}; border:0; border-right:1px solid {c['BORDER']}; padding:8px; outline:0; }}
    #sidebar::item {{ color:{c['MUTED']}; padding:10px 12px; margin:2px 0; border-radius:7px; min-height:45px; }}
    #sidebar::item:hover {{ background:{'#14283D' if selected!='light' else '#D8E6F5'}; color:{c['TEXT']}; }}
    #sidebar::item:selected {{ background:{c['BLUE']}; color:#FFFFFF; font-weight:700; border-left:3px solid {c['GOLD']}; padding-left:9px; }}
    #workspaceBanner {{ background:{'#10243A' if selected!='light' else '#E1EBF5'}; color:{c['TEXT']}; padding:8px 14px; border-bottom:1px solid {c['BORDER']}; }}
    #cadPage QComboBox,#cadPage QLineEdit {{ min-width:105px; }}
    """)
    QTimer.singleShot(0,lambda:_normalize_legacy_page_styles(app))
    QTimer.singleShot(0,lambda:_install_cad_responsive_layout(app))
    QTimer.singleShot(300,lambda:_install_cad_responsive_layout(app))
    QTimer.singleShot(700,lambda:_install_cad_responsive_layout(app))
