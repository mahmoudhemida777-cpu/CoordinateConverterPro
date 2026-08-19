"""Main application window: sidebar + stacked pages."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget, QStyle, QApplication, QAbstractButton, QGroupBox, QComboBox
from ui.pages.dashboard_page import DashboardPage
from ui.pages.import_page import ImportPage
from ui.pages.converter_page import ConverterPage
from ui.pages.survey_page import SurveyPage
from ui.pages.cad_page import CadPage
from ui.pages.batch_page import BatchPage
from ui.pages.map_page import MapPage
from ui.pages.history_page import HistoryPage
from ui.pages.settings_page import SettingsPage
from ui.pages.about_page import AboutPage
from ui.i18n import tr, set_language, register_language_listener, current_language
from ui.theme import apply_theme, preferred_font

APP_NAME="MH - Coordinate"
APP_TAGLINE="Professional Surveying & Geospatial Engineering Suite"
SIDEBAR_ITEMS=[
    ("dashboard","Dashboard",QStyle.StandardPixmap.SP_ComputerIcon),("import","Import",QStyle.StandardPixmap.SP_DialogOpenButton),
    ("converter","CRS Converter",QStyle.StandardPixmap.SP_BrowserReload),("survey","Survey Tools",QStyle.StandardPixmap.SP_FileDialogDetailedView),
    ("cad","Civil / CAD",QStyle.StandardPixmap.SP_DesktopIcon),("batch","Batch Converter",QStyle.StandardPixmap.SP_DialogApplyButton),
    ("map","Map",QStyle.StandardPixmap.SP_FileDialogContentsView),("history","History",QStyle.StandardPixmap.SP_FileDialogListView),
    ("settings","Settings",QStyle.StandardPixmap.SP_FileDialogDetailedView),("about","About",QStyle.StandardPixmap.SP_MessageBoxInformation),
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); app=QApplication.instance()
        if app is not None:
            saved=str(QSettings("Mahmoud Hemida", "MH GeoSuite Pro").value("language", "en") or "en")
            set_language(saved); apply_theme(app); app.setFont(preferred_font()); self._set_app_direction()
        self.setWindowTitle(APP_NAME); self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)); self.resize(1440,900); self.setMinimumSize(1100,700); self.workspace_folder=None
        central=QWidget();self.setCentralWidget(central);layout=QHBoxLayout(central);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.sidebar=QListWidget();self.sidebar.setFixedWidth(238);self.sidebar.setObjectName("sidebar");self.sidebar.setIconSize(QSize(20,20));self.sidebar.setSpacing(2);self.sidebar.setUniformItemSizes(True)
        for key,label,pix in SIDEBAR_ITEMS:
            item=QListWidgetItem(self.style().standardIcon(pix),tr(label));item.setData(Qt.ItemDataRole.UserRole,key);item.setData(Qt.ItemDataRole.UserRole+1,label);item.setSizeHint(QSize(214,45));self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        right=QWidget();right_layout=QVBoxLayout(right);right_layout.setContentsMargins(0,0,0,0);right_layout.setSpacing(0)
        self.workspace_banner=QLabel("PROJECT WORKSPACE: Not selected — choose a folder once from Dashboard");self.workspace_banner.setObjectName("workspaceBanner");right_layout.addWidget(self.workspace_banner)
        self.stack=QStackedWidget();self.pages={"dashboard":DashboardPage(),"import":ImportPage(),"converter":ConverterPage(),"survey":SurveyPage(),"cad":CadPage(),"batch":BatchPage(),"map":MapPage(),"history":HistoryPage(),"settings":SettingsPage(),"about":AboutPage()}
        for key,_,_ in SIDEBAR_ITEMS:self.stack.addWidget(self.pages[key])
        self.pages["dashboard"].file_selected.connect(self._set_active_file);self.pages["dashboard"].folder_selected.connect(self._set_workspace_folder);self.pages["batch"].batch_completed.connect(self._on_batch_completed);self.pages["history"].file_reloaded.connect(self._reload_history_file)
        right_layout.addWidget(self.stack);layout.addWidget(self.sidebar);layout.addWidget(right);self.sidebar.setCurrentRow(0);self.statusBar().showMessage(tr("Ready"));register_language_listener(self._on_language_changed)

    def _set_app_direction(self):
        app=QApplication.instance()
        if app is not None:app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if current_language()=="ar" else Qt.LayoutDirection.LeftToRight)

    def _on_language_changed(self,language:str)->None:
        self._set_app_direction()
        for row,(_,english,_) in enumerate(SIDEBAR_ITEMS):
            if row<self.sidebar.count():self.sidebar.item(row).setText(tr(english))
        for widget in self.findChildren((QAbstractButton,QLabel,QGroupBox)):
            key=widget.property("mhTextKey")
            if key:widget.setText(tr(str(key)))
        for combo in self.findChildren(QComboBox):
            for index in range(combo.count()):
                key=combo.itemData(index,Qt.ItemDataRole.UserRole+1)
                if key:combo.setItemText(index,tr(str(key)))

    def _set_workspace_folder(self,folder:str):
        self.workspace_folder=folder;self.workspace_banner.setText(f"PROJECT WORKSPACE: {folder}  |  Shared across all pages")
        for page in self.pages.values():
            setter=getattr(page,"set_workspace_folder",None)
            if callable(setter):setter(folder)
        self.statusBar().showMessage(f"Project Folder: {folder} — shared workspace")

    def _set_active_file(self,path:str):
        for key in ("import","converter","cad","batch","map"):
            loader=getattr(self.pages[key],"load_active_file",None)
            if callable(loader):loader(path)
        self.statusBar().showMessage(f"Active File: {path}")

    def _reload_history_file(self,path:str):
        self._set_active_file(path);self.sidebar.setCurrentRow(2);self.statusBar().showMessage(f"History file loaded: {path} — ready for further editing/conversion")

    def _on_batch_completed(self,output_paths:list,target_crs:str,source_crs:str):
        if output_paths:
            cad=self.pages["cad"];loader=getattr(cad,"_load_batch_converted_xlsx",None)
            if callable(loader) and loader(output_paths[0]):self.statusBar().showMessage(f"Batch result ready for CAD/Civil 3D: {output_paths[0]}")

    def _on_sidebar_changed(self,row:int):
        if 0<=row<len(SIDEBAR_ITEMS):self.stack.setCurrentWidget(self.pages[SIDEBAR_ITEMS[row][0]])
