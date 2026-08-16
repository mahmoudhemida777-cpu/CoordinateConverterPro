"""MH GeoSuite Pro professional dark UI theme."""
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

BG = "#0B1420"
SURFACE = "#111E2D"
SURFACE_2 = "#16263A"
BORDER = "#2A4058"
TEXT = "#E8EEF5"
MUTED = "#9BAFC3"
BLUE = "#1976D2"
BLUE_HOVER = "#2587E8"
GOLD = "#C9A227"
SUCCESS = "#35D07F"
DANGER = "#F05B5B"


def apply_theme(app: QApplication) -> None:
    """Apply the application-wide professional dark theme."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor("#0E1926"))
    palette.setColor(QPalette.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(SURFACE_2))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(BLUE))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.PlaceholderText, QColor(MUTED))
    app.setPalette(palette)
    app.setStyleSheet(f"""
    * {{ font-family: 'Segoe UI', 'Arial'; font-size: 10pt; }}
    QMainWindow, QWidget {{ background: {BG}; color: {TEXT}; }}
    QFrame, QGroupBox {{ border: 1px solid {BORDER}; border-radius: 8px; background: {SURFACE}; }}
    QGroupBox {{ margin-top: 12px; padding: 16px 10px 10px 10px; font-weight: 700; color: {TEXT}; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {TEXT}; background: {SURFACE}; }}
    QLabel {{ color: {TEXT}; background: transparent; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: #0E1926; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 9px; min-height: 20px; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {BLUE}; }}
    QComboBox::drop-down {{ border: 0; width: 26px; }}
    QComboBox QAbstractItemView {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER}; selection-background-color: {BLUE}; }}
    QPushButton {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px 14px; font-weight: 600; min-height: 18px; }}
    QPushButton:hover {{ background: {BLUE_HOVER}; border-color: {BLUE_HOVER}; }}
    QPushButton:pressed {{ background: {BLUE}; }}
    QCheckBox, QRadioButton {{ color: {TEXT}; spacing: 8px; }}
    QProgressBar {{ background: #0E1926; border: 1px solid {BORDER}; border-radius: 5px; text-align: center; color: {TEXT}; min-height: 12px; }}
    QProgressBar::chunk {{ background: {BLUE}; border-radius: 4px; }}
    QTableWidget, QTreeWidget, QListWidget {{ background: #0E1926; alternate-background-color: #122132; color: {TEXT}; border: 1px solid {BORDER}; gridline-color: #20364D; selection-background-color: #1B5FA8; selection-color: #FFFFFF; }}
    QHeaderView::section {{ background: #162B43; color: {TEXT}; border: 0; border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; padding: 8px; font-weight: 700; }}
    QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: #304A64; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {BLUE}; }}
    QScrollBar:horizontal {{ background: {BG}; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: #304A64; border-radius: 5px; min-width: 30px; }}
    QStatusBar {{ background: #08111B; color: {MUTED}; border-top: 1px solid {BORDER}; }}
    #sidebar {{ background: #09131F; border: 0; border-right: 1px solid {BORDER}; padding: 8px; outline: 0; }}
    #sidebar::item {{ color: {MUTED}; padding: 12px 14px; margin: 2px 0; border-radius: 6px; }}
    #sidebar::item:hover {{ background: #14283D; color: {TEXT}; }}
    #sidebar::item:selected {{ background: {BLUE}; color: #FFFFFF; font-weight: 700; }}
    #workspaceBanner {{ background: #10243A; color: {TEXT}; padding: 8px 14px; border-bottom: 1px solid {BORDER}; }}
    QMessageBox {{ background: {SURFACE}; }}
    """)
