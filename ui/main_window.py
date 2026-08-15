"""Main application window: sidebar + stacked pages."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QListWidget,QListWidgetItem,QStackedWidget,QStyle
from ui.pages.dashboard_page import DashboardPage
from ui.pages.import_page import ImportPage
from ui.pages.converter_page import ConverterPage
from ui.pages.cad_page import CadPage
from ui.pages.batch_page import BatchPage
from ui.pages.survey_page import SurveyPage
from ui.pages.map_page import MapPage
from ui.pages.history_page import HistoryPage
from ui.pages.settings_page import SettingsPage
from ui.pages.about_page import AboutPage
from ui.i18n import tr

APP_NAME="MH GeoSuite Pro"; APP_TAGLINE="Professional Surveying & Geospatial Engineering Suite"
SIDEBAR_ITEMS=[("dashboard","Dashboard"),("import","Import"),("converter","CRS Converter"),("survey","Survey Tools"),("cad","Civil / CAD"),("batch","Batch Converter"),("map","Map"),("history","History"),("settings","Settings"),("about","About")]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_NAME); self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)); self.resize(1200,800); self.workspace_folder=None
        central=QWidget(); self.setCentralWidget(central); layout=QHBoxLayout(central); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.sidebar=QListWidget(); self.sidebar.setFixedWidth(200); self.sidebar.setObjectName("sidebar")
        for key,label in SIDEBAR_ITEMS:
            item=QListWidgetItem(tr(label)); item.setData(Qt.UserRole,key); self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        self.stack=QStackedWidget(); self.pages={"dashboard":DashboardPage(),"import":ImportPage(),"converter":ConverterPage(),"survey":SurveyPage(),"cad":CadPage(),"batch":BatchPage(),"map":MapPage(),"history":HistoryPage(),"settings":SettingsPage(),"about":AboutPage()}
        for key,_ in SIDEBAR_ITEMS: self.stack.addWidget(self.pages[key])
        self.pages["dashboard"].file_selected.connect(self._set_active_file)
        self.pages["dashboard"].folder_selected.connect(self._set_workspace_folder)
        self.pages["batch"].batch_completed.connect(self._on_batch_completed)
        layout.addWidget(self.sidebar); layout.addWidget(self.stack); self.sidebar.setCurrentRow(0); self.statusBar().showMessage(tr("Ready"))

    def _set_workspace_folder(self, folder: str):
        self.workspace_folder = folder
        for page in self.pages.values():
            setter = getattr(page, "set_workspace_folder", None)
            if callable(setter): setter(folder)
        self.statusBar().showMessage(f"Project Folder: {folder} — shared workspace")

    def _set_active_file(self,path:str):
        for key in ("import","converter","cad","batch","map"):
            loader=getattr(self.pages[key],"load_active_file",None)
            if callable(loader): loader(path)
        self.statusBar().showMessage(f"Active File: {path}")

    def _on_batch_completed(self,output_paths:list,target_crs:str,source_crs:str):
        if output_paths:
            cad=self.pages["cad"]
            loader=getattr(cad,"_load_batch_converted_xlsx",None)
            if callable(loader) and loader(output_paths[0]):
                self.statusBar().showMessage(f"Batch result ready for CAD/Civil 3D: {output_paths[0]}")

    def _on_sidebar_changed(self,row:int):
        key,_=SIDEBAR_ITEMS[row]; self.stack.setCurrentWidget(self.pages[key])
