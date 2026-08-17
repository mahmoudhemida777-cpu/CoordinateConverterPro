from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QGroupBox, QCheckBox, QComboBox, QRadioButton, QHeaderView, QSizePolicy,
    QScrollArea, QAbstractItemView, QFrame
)

from core.crs.engine import CRSEngine
from core.models import PointResult
from core.parsers import csv_parser, xlsx_parser, kml_parser, txt_parser
from core.exporters.dxf_exporter import export_dxf, LabelMode
from core.point_ordering import order_points
from ui.widgets.crs_picker import CRSPicker
from ui.widgets.workspace_bar import WorkspaceFileBar
from ui.pages.settings_page import current_precision

COORDINATE_FILTER = (
    "Coordinate files (*.kmz *.kml *.csv *.xlsx *.txt);;"
    "KMZ/KML (*.kmz *.kml);;CSV (*.csv);;Excel (*.xlsx);;"
    "Survey TXT (*.txt);;All files (*.*)"
)


def _section(box: QGroupBox, number: str, title: str) -> None:
    box.setTitle(f"{number}  {title}")
    box.setCheckable(False)
    box.setFlat(False)


class CadPage(QWidget):
    """Responsive CAD/Civil 3D page with an explicit Preview commit.

    Parsing, axis and ordering edits are staged first. PREVIEW applies the
    current selections to the table, so the user can verify the exact result
    before conversion/export. The source file is never mutated in place.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("cadPage")
        self.engine = CRSEngine()
        self.source_points: list[PointResult] = []
        self.result_points: list[PointResult] = []
        self.current_file: str | None = None
        self.workspace_folder: str | None = None
        self._detected_columns: list[str] = []
        self._axis_swapped = False
        self._preview_dirty = False

        page_scroll = QScrollArea(self)
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setObjectName("cadPageScroll")

        content = QWidget()
        content.setObjectName("cadPageContent")
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 12, 18, 18)
        root.setSpacing(9)
        page_scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page_scroll)

        title_row = QHBoxLayout()
        title = QLabel("Civil / CAD Converter")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.reset_btn = QPushButton("RESET")
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.clicked.connect(self._reset_page)
        title_row.addWidget(self.reset_btn)
        root.addLayout(title_row)

        sub = QLabel(
            "Convert survey points to CAD (DXF) or Civil 3D (CSV) — "
            "Smart Parsing, Axis Control and independent Grid/Zigzag ordering."
        )
        sub.setWordWrap(True)
        sub.setObjectName("pageSubtitle")
        root.addWidget(sub)

        self.workspace_bar = WorkspaceFileBar()
        self.workspace_bar.file_selected.connect(self._load_path)
        root.addWidget(self.workspace_bar)

        file_row = QHBoxLayout()
        self.file_status = QLabel("No coordinate file loaded")
        self.file_status.setWordWrap(True)
        file_row.addWidget(self.file_status, 1)
        choose = QPushButton("Open / Change File")
        choose.clicked.connect(self._choose_file)
        file_row.addWidget(choose)
        root.addLayout(file_row)

        self.direct_mode = QCheckBox(
            "DIRECT CAD EXPORT — use loaded coordinates exactly as they are (NO CRS conversion)"
        )
        self.direct_mode.stateChanged.connect(self._mode_changed)
        root.addWidget(self.direct_mode)

        parsing = QGroupBox()
        _section(parsing, "1", "FILE PARSING OPTIONS")
        pg = QGridLayout(parsing)
        pg.setContentsMargins(14, 24, 14, 12)
        pg.setHorizontalSpacing(14)
        pg.setVerticalSpacing(9)

        self.parsing_engine = QComboBox()
        self.parsing_engine.addItems(["Smart (Recommended)", "Manual / Select Columns"])
        self.parsing_engine.currentIndexChanged.connect(self._mark_preview_dirty)
        self.detected_format = QComboBox()
        self.detected_format.setEnabled(False)
        pg.addWidget(QLabel("Parsing Engine"), 0, 0)
        pg.addWidget(self.parsing_engine, 0, 1)
        pg.addWidget(QLabel("Detected Format"), 0, 2)
        pg.addWidget(self.detected_format, 0, 3)

        self.x_column = QComboBox()
        self.y_column = QComboBox()
        self.z_column = QComboBox()
        self.name_column = QComboBox()
        for combo in (self.x_column, self.y_column, self.z_column, self.name_column):
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            combo.currentIndexChanged.connect(self._mark_preview_dirty)

        pg.addWidget(QLabel("Easting / X"), 1, 0)
        pg.addWidget(self.x_column, 1, 1)
        pg.addWidget(QLabel("Northing / Y"), 1, 2)
        pg.addWidget(self.y_column, 1, 3)
        pg.addWidget(QLabel("Elevation / Z (optional)"), 2, 0)
        pg.addWidget(self.z_column, 2, 1)
        pg.addWidget(QLabel("Point Code / Name (optional)"), 2, 2)
        pg.addWidget(self.name_column, 2, 3)
        pg.setColumnStretch(1, 1)
        pg.setColumnStretch(3, 1)

        parsing_hint = QLabel(
            "Choose the correct columns above, then click PREVIEW to apply the changes to the table."
        )
        parsing_hint.setObjectName("infoLabel")
        parsing_hint.setWordWrap(True)
        pg.addWidget(parsing_hint, 3, 0, 1, 3)
        self.preview_btn = QPushButton("◉  PREVIEW")
        self.preview_btn.setObjectName("primaryButton")
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.clicked.connect(self._preview_clicked)
        pg.addWidget(self.preview_btn, 3, 3)
        root.addWidget(parsing)

        axis = QGroupBox()
        _section(axis, "2", "AXIS ORDER — IMPORTANT")
        af = QVBoxLayout(axis)
        af.setContentsMargins(14, 24, 14, 12)
        self.axis_xy = QRadioButton("Easting (X) → Northing (Y)  |  Standard (Recommended)")
        self.axis_yx = QRadioButton("Northing (Y) → Easting (X)  |  SWAP")
        self.axis_xy.setChecked(True)
        self.axis_xy.toggled.connect(self._mark_preview_dirty)
        self.axis_yx.toggled.connect(self._mark_preview_dirty)
        af.addWidget(self.axis_xy)
        af.addWidget(self.axis_yx)
        axis_hint = QLabel(
            "The selected axis order is applied to the PREVIEW table when you click PREVIEW."
        )
        axis_hint.setObjectName("infoLabel")
        axis_hint.setWordWrap(True)
        af.addWidget(axis_hint)
        root.addWidget(axis)

        ordering = QGroupBox()
        _section(ordering, "3", "GRID / ZIGZAG POINT NUMBERING")
        og = QGridLayout(ordering)
        og.setContentsMargins(14, 24, 14, 12)
        og.setHorizontalSpacing(14)
        og.setVerticalSpacing(9)

        self.ordering_mode = QComboBox()
        self.ordering_mode.addItem("Zigzag (Start West)", "GRID_ZIGZAG_WEST")
        self.ordering_mode.addItem("Zigzag (Start East)", "GRID_ZIGZAG_EAST")
        self.ordering_mode.addItem("Keep Source Order", "SOURCE")
        self.ordering_mode.currentIndexChanged.connect(self._mark_preview_dirty)
        og.addWidget(QLabel("Ordering Method"), 0, 0)
        og.addWidget(self.ordering_mode, 0, 1)

        self.group_by_name = QCheckBox("Group by Point Code / Name")
        self.group_by_name.setChecked(True)
        self.group_by_name.toggled.connect(self._mark_preview_dirty)
        og.addWidget(self.group_by_name, 0, 2)

        self.auto_grid = QCheckBox("Auto Detect Grid")
        self.auto_grid.setChecked(True)
        self.auto_grid.toggled.connect(self._mark_preview_dirty)
        og.addWidget(self.auto_grid, 0, 3)

        self.tolerance_combo = QComboBox()
        self.tolerance_combo.addItems(["Auto", "0.01", "0.05", "0.10", "0.25", "0.50", "1.00"])
        self.tolerance_combo.currentIndexChanged.connect(self._mark_preview_dirty)
        og.addWidget(QLabel("Row tolerance (m)"), 1, 0)
        og.addWidget(self.tolerance_combo, 1, 1)

        self.reverse_rows = QCheckBox("Reverse Each Row")
        self.reverse_rows.toggled.connect(self._mark_preview_dirty)
        og.addWidget(self.reverse_rows, 1, 2)
        og.setColumnStretch(1, 1)
        og.setColumnStretch(3, 1)
        root.addWidget(ordering)

        crs = QGroupBox("COORDINATE REFERENCE SYSTEM")
        cg = QVBoxLayout(crs)
        cg.setContentsMargins(14, 24, 14, 12)
        source_row = QHBoxLayout()
        self.source_picker = CRSPicker(self.engine, "SOURCE CRS")
        self.target_picker = CRSPicker(self.engine, "TARGET CRS")
        source_row.addWidget(self.source_picker, 1)
        source_row.addWidget(self.target_picker, 1)
        cg.addLayout(source_row)
        crs_hint = QLabel(
            "CRS conversion is performed only by CONVERT & PREPARE. "
            "PREVIEW shows parsing/axis/ordering changes before conversion."
        )
        crs_hint.setObjectName("infoLabel")
        crs_hint.setWordWrap(True)
        cg.addWidget(crs_hint)
        root.addWidget(crs)

        preview_box = QGroupBox()
        _section(preview_box, "4", "POINTS PREVIEW TABLE")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(10, 24, 10, 10)

        preview_header = QHBoxLayout()
        self.preview_state = QLabel("Preview is up to date")
        self.preview_state.setObjectName("previewState")
        preview_header.addWidget(self.preview_state, 1)
        preview_header.addWidget(QLabel("Total Points:"))
        self.total_preview = QLabel("0")
        preview_header.addWidget(self.total_preview)
        preview_header.addSpacing(12)
        preview_header.addWidget(QLabel("Displayed:"))
        self.displayed_preview = QLabel("0")
        preview_header.addWidget(self.displayed_preview)
        preview_header.addSpacing(12)
        preview_header.addWidget(QLabel("Invalid:"))
        self.invalid_preview = QLabel("0")
        preview_header.addWidget(self.invalid_preview)
        preview_header.addSpacing(8)
        self.preview_again_btn = QPushButton("↻  PREVIEW")
        self.preview_again_btn.setObjectName("primaryButton")
        self.preview_again_btn.clicked.connect(self._preview_clicked)
        preview_header.addWidget(self.preview_again_btn)
        preview_layout.addLayout(preview_header)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("cadPointsTable")
        self.table.setHorizontalHeaderLabels(
            ["#", "Point Code / Name", "Easting / X", "Northing / Y", "Elevation / Z", "Status"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setMinimumHeight(300)
        preview_layout.addWidget(self.table, 1)
        root.addWidget(preview_box, 1)

        action_row = QHBoxLayout()
        self.convert_btn = QPushButton("CONVERT & PREPARE FOR CAD / CIVIL 3D")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.clicked.connect(self._convert)
        action_row.addWidget(self.convert_btn, 2)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        action_row.addWidget(self.progress, 1)
        root.addLayout(action_row)

        summary = QHBoxLayout()
        self.total = QLabel("Total: 0")
        self.success = QLabel("Success: 0")
        self.failed = QLabel("Failed: 0")
        summary.addWidget(self.total)
        summary.addWidget(self.success)
        summary.addWidget(self.failed)
        summary.addStretch()
        root.addLayout(summary)

        export_row = QHBoxLayout()
        dxf = QPushButton("EXPORT DXF")
        civil = QPushButton("EXPORT CIVIL 3D CSV")
        dxf.clicked.connect(self._export_dxf)
        civil.clicked.connect(self._export_civil3d_csv)
        export_row.addWidget(dxf, 1)
        export_row.addWidget(civil, 1)
        root.addLayout(export_row)

    # ---------- Workspace integration ----------
    def set_workspace_folder(self, folder: str) -> None:
        self.workspace_folder = folder
        self.workspace_bar.set_folder(folder, self.current_file)

    def load_active_file(self, path: str) -> None:
        if path and Path(path).is_file():
            self._load_path(path)

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Coordinate File", self.workspace_folder or "", COORDINATE_FILTER
        )
        if path:
            self._load_path(path)

    def _load_batch_converted_xlsx(self, path: str) -> bool:
        try:
            points = xlsx_parser.parse_xlsx_auto(path)
            if not points:
                return False
            self.current_file = path
            self.workspace_folder = str(Path(path).parent)
            self.source_points = points
            self.result_points = [
                PointResult(p.name, p.src_x, p.src_y, p.src_z, p.src_x, p.src_y, p.src_z,
                            status=p.status, message="Loaded from batch conversion")
                for p in points
            ]
            self.direct_mode.setChecked(True)
            self._populate_parsing_options(path, ".xlsx")
            self._render_points(self._ordered_results(self.result_points))
            self._set_preview_clean("Batch result loaded")
            self.file_status.setText(f"Batch result loaded: {Path(path).name} — {len(points)} points")
            return True
        except Exception as exc:
            self.file_status.setText(f"Batch result could not be loaded: {exc}")
            return False

    # ---------- Parsing ----------
    def _load_path(self, path: str) -> None:
        try:
            path_obj = Path(path)
            suffix = path_obj.suffix.casefold()
            if suffix not in {".csv", ".xlsx", ".txt", ".kml", ".kmz"}:
                raise ValueError(f"Unsupported coordinate file type: {suffix}")
            self.current_file = str(path_obj)
            self.workspace_folder = str(path_obj.parent)
            self.workspace_bar.set_folder(self.workspace_folder, self.current_file)
            self._populate_parsing_options(self.current_file, suffix)
            points = self._parse_smart()
            if not points:
                raise ValueError("No coordinate points were detected in the selected file.")
            self.source_points = points
            self.result_points = []
            self.progress.setValue(0)
            self._render_points(self._ordered_results(self.source_points))
            self._set_preview_clean("Loaded source data")
            self.file_status.setText(f"Loaded: {path_obj.name} — {len(points)} points detected")
        except Exception as exc:
            self.source_points = []
            self.result_points = []
            self._render_points([])
            self.file_status.setText(f"Load failed: {exc}")
            QMessageBox.critical(self, "Coordinate File Error", str(exc))

    def _parse_smart(self):
        suffix = Path(self.current_file).suffix.casefold()
        if suffix == ".csv":
            return csv_parser.parse_csv_auto(self.current_file)
        if suffix == ".xlsx":
            return xlsx_parser.parse_xlsx_auto(self.current_file)
        if suffix == ".txt":
            return txt_parser.parse_txt(self.current_file)
        if suffix in {".kml", ".kmz"}:
            return kml_parser.parse_kml_or_kmz(self.current_file)
        return []

    def _populate_parsing_options(self, path: str, suffix: str) -> None:
        self._detected_columns = []
        for combo in (self.x_column, self.y_column, self.z_column, self.name_column):
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
        self.detected_format.clear()
        self.detected_format.addItem({
            ".csv": "CSV (Comma delimited)",
            ".xlsx": "Excel Workbook",
            ".txt": "Survey TXT",
            ".kml": "KML / WGS 84",
            ".kmz": "KMZ / WGS 84",
        }.get(suffix, suffix))
        if suffix == ".csv":
            self._detected_columns = list(csv_parser.sniff_columns(path))
        elif suffix == ".xlsx":
            self._detected_columns = list(xlsx_parser.sniff_columns(path))
        elif suffix == ".txt":
            self._detected_columns = list(txt_parser.sniff_columns(path))
        else:
            self.source_picker.set_selected("EPSG:4326", "WGS 84 — Geographic 2D (Longitude / Latitude)")
            return
        for combo in (self.x_column, self.y_column, self.z_column, self.name_column):
            combo.blockSignals(True)
            combo.addItems(self._detected_columns)
            combo.blockSignals(False)
        self.z_column.insertItem(0, "<none>")
        self.name_column.insertItem(0, "<none>")
        xi = self._pick_column(self._detected_columns, ("easting", "east", "x", "longitude", "lon"))
        yi = self._pick_column(self._detected_columns, ("northing", "north", "y", "latitude", "lat"))
        zi = self._pick_column(self._detected_columns, ("elevation", "elev", "height", "z"))
        ni = self._pick_column(self._detected_columns, (
            "point number", "point_number", "pointno", "pointid", "pointcode", "code", "point", "name", "id", "number"
        ))
        if xi >= 0: self.x_column.setCurrentIndex(xi)
        if yi >= 0: self.y_column.setCurrentIndex(yi)
        if zi >= 0: self.z_column.setCurrentIndex(zi + 1)
        if ni >= 0: self.name_column.setCurrentIndex(ni + 1)

    @staticmethod
    def _pick_column(columns, names) -> int:
        normalized = [str(c).strip().lower().replace("_", " ") for c in columns]
        for name in names:
            key = str(name).strip().lower().replace("_", " ")
            if key in normalized:
                return normalized.index(key)
        for i, key in enumerate(normalized):
            if any(str(name).lower().replace("_", " ") in key for name in names):
                return i
        return -1

    def _reparse_current(self) -> None:
        self._mark_preview_dirty()

    def _apply_manual_mapping(self):
        suffix = Path(self.current_file).suffix.casefold()
        name = self.name_column.currentText()
        z = self.z_column.currentText()
        mapping_name = None if name in {"", "<none>"} else name
        mapping_z = None if z in {"", "<none>"} else z
        if suffix == ".csv":
            return csv_parser.parse_csv(self.current_file, csv_parser.ColumnMapping(
                mapping_name, self.x_column.currentText(), self.y_column.currentText(), mapping_z
            ))
        if suffix == ".xlsx":
            return xlsx_parser.parse_xlsx(self.current_file, xlsx_parser.ColumnMapping(
                mapping_name, self.x_column.currentText(), self.y_column.currentText(), mapping_z
            ))
        return self._parse_smart()

    # ---------- Preview ----------
    def _mark_preview_dirty(self, *_args) -> None:
        if not self.source_points:
            return
        self._preview_dirty = True
        self.result_points = []
        self.preview_state.setText("Changes pending — click PREVIEW to update the table")
        self.preview_state.setObjectName("warningLabel")
        self.preview_state.style().unpolish(self.preview_state)
        self.preview_state.style().polish(self.preview_state)

    def _set_preview_clean(self, message: str = "Preview is up to date") -> None:
        self._preview_dirty = False
        self.preview_state.setText(message)
        self.preview_state.setObjectName("previewState")
        self.preview_state.style().unpolish(self.preview_state)
        self.preview_state.style().polish(self.preview_state)

    def _preview_clicked(self) -> None:
        try:
            points = self._preview_source_points()
            if not points:
                QMessageBox.warning(self, "No Data", "Load a coordinate file before using PREVIEW.")
                return
            points = self._apply_axis(points)
            ordered = self._ordered_results(points)
            self._render_points(ordered)
            self._set_preview_clean(f"Preview updated — {len(ordered)} point(s)")
            self.file_status.setText(
                f"Preview updated from current parsing/axis/order settings — {len(ordered)} points"
            )
        except Exception as exc:
            self._preview_dirty = True
            self.preview_state.setText("Preview failed — fix the selected options and try again")
            QMessageBox.critical(self, "Preview Error", str(exc))

    def _preview_source_points(self) -> list[PointResult]:
        if not self.current_file or not Path(self.current_file).is_file():
            return list(self.source_points)
        if self.parsing_engine.currentIndex() == 1:
            points = self._apply_manual_mapping()
        else:
            points = self._parse_smart()
        if not points:
            raise ValueError("The selected parsing settings produced no coordinate points.")
        self.source_points = list(points)
        return list(points)

    def _mode_changed(self) -> None:
        self._mark_preview_dirty()

    def _apply_axis(self, points: list[PointResult]) -> list[PointResult]:
        if not self.axis_yx.isChecked():
            self._axis_swapped = False
            return [
                PointResult(p.name, p.src_x, p.src_y, p.src_z, p.tgt_x, p.tgt_y, p.tgt_z,
                            status=p.status, message=p.message)
                for p in points
            ]
        self._axis_swapped = True
        return [
            PointResult(p.name, p.src_y, p.src_x, p.src_z,
                        p.tgt_y, p.tgt_x, p.tgt_z,
                        status=p.status, message=p.message)
            for p in points
        ]

    def _convert(self) -> None:
        if not self.source_points:
            QMessageBox.warning(self, "No Input", "Load a coordinate file before conversion.")
            return
        try:
            points = self._preview_source_points()
            points = self._apply_axis(points)
            self.total.setText(f"Total: {len(points)}")
            self.progress.setValue(10)
            if self.direct_mode.isChecked():
                self.result_points = [
                    PointResult(p.name, p.src_x, p.src_y, p.src_z,
                                p.src_x, p.src_y, p.src_z,
                                status="SUCCESS" if p.src_x is not None and p.src_y is not None else "FAILED",
                                message="DIRECT — no CRS conversion")
                    for p in points
                ]
            else:
                source = self.source_picker.selected_epsg()
                target = self.target_picker.selected_epsg()
                if not source or not target:
                    raise ValueError("Select both Source CRS and Target CRS before conversion.")
                self.result_points = self.engine.transform_points(source, target, points, operation="auto")
            self.progress.setValue(90)
            self._render_points(self._ordered_results(self.result_points))
            ok = sum(p.status == "SUCCESS" for p in self.result_points)
            bad = len(self.result_points) - ok
            self.success.setText(f"Success: {ok}")
            self.failed.setText(f"Failed: {bad}")
            self.progress.setValue(100)
            self._set_preview_clean("Preview reflects converted result")
            self.file_status.setText(
                f"Conversion completed with {bad} failed point(s)" if bad
                else f"Conversion completed successfully — {ok} point(s)"
            )
        except Exception as exc:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Conversion Error", str(exc))
            self.file_status.setText(f"Conversion failed: {exc}")

    def _ordering_tolerance(self) -> float | None:
        value = self.tolerance_combo.currentText()
        return None if value == "Auto" else float(value)

    def _ordered_results(self, points=None):
        points = list(points if points is not None else (self.result_points or self.source_points))
        mode = self.ordering_mode.currentData() or "SOURCE"
        return order_points(
            points,
            mode=mode,
            tolerance=self._ordering_tolerance() if self.auto_grid.isChecked() else None,
            reverse=self.reverse_rows.isChecked(),
            group_by_name=self.group_by_name.isChecked(),
        )

    def _render_points(self, ordered) -> None:
        self.table.setRowCount(0)
        precision = current_precision()
        invalid = 0
        for item in ordered:
            p = item.point
            row = self.table.rowCount()
            self.table.insertRow(row)
            x = p.tgt_x if p.tgt_x is not None else p.src_x
            y = p.tgt_y if p.tgt_y is not None else p.src_y
            z = p.tgt_z if p.tgt_z is not None else p.src_z
            status = p.status or "PENDING"
            if status == "FAILED":
                invalid += 1
            values = [
                str(item.number), str(p.name or ""),
                "" if x is None else f"{float(x):.{precision}f}",
                "" if y is None else f"{float(y):.{precision}f}",
                "" if z is None else f"{float(z):.{precision}f}",
                status,
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        count = len(ordered)
        self.total.setText(f"Total: {count}")
        ok = sum(p.point.status == "SUCCESS" for p in ordered)
        bad = sum(p.point.status == "FAILED" for p in ordered)
        self.success.setText(f"Success: {ok}")
        self.failed.setText(f"Failed: {bad}")
        self.total_preview.setText(str(count))
        self.displayed_preview.setText(str(self.table.rowCount()))
        self.invalid_preview.setText(str(max(invalid, bad)))

    def _populate(self) -> None:
        self._render_points(self._ordered_results(self.result_points or self.source_points))

    # ---------- Export ----------
    def _export_dxf(self) -> None:
        if self._preview_dirty:
            QMessageBox.warning(self, "Preview Required", "Apply your changes with PREVIEW before exporting.")
            return
        points = self.result_points or self.source_points
        if not points:
            QMessageBox.warning(self, "No Data", "Load and prepare coordinate points first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export DXF", self.workspace_folder or "", "DXF (*.dxf)")
        if not path:
            return
        try:
            export_dxf(
                points,
                path,
                label_mode=LabelMode.NUMBER_AND_NAME if self.write_code.isChecked() else LabelMode.NUMBER,
                use_target_coords=not self.direct_mode.isChecked() and bool(self.result_points),
                order_mode=self.ordering_mode.currentData() or "SOURCE",
                tolerance=self._ordering_tolerance() if self.auto_grid.isChecked() else None,
                group_by_name=self.group_by_name.isChecked(),
            )
            self.file_status.setText(f"DXF exported: {Path(path).name}")
            QMessageBox.information(self, "DXF Export", f"DXF created successfully:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "DXF Export Error", str(exc))

    def _export_civil3d_csv(self) -> None:
        if self._preview_dirty:
            QMessageBox.warning(self, "Preview Required", "Apply your changes with PREVIEW before exporting.")
            return
        points = self.result_points or self.source_points
        if not points:
            QMessageBox.warning(self, "No Data", "Load and prepare coordinate points first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Civil 3D CSV", self.workspace_folder or "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            ordered = self._ordered_results(points)
            precision = current_precision()
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Point Number", "Point Code", "Easting", "Northing", "Elevation", "Status", "Message"])
                for item in ordered:
                    p = item.point
                    x = p.tgt_x if p.tgt_x is not None else p.src_x
                    y = p.tgt_y if p.tgt_y is not None else p.src_y
                    z = p.tgt_z if p.tgt_z is not None else p.src_z
                    writer.writerow([
                        item.number, p.name or "",
                        "" if x is None else f"{float(x):.{precision}f}",
                        "" if y is None else f"{float(y):.{precision}f}",
                        "" if z is None else f"{float(z):.{precision}f}",
                        p.status, p.message,
                    ])
            self.file_status.setText(f"Civil 3D CSV exported: {Path(path).name}")
            QMessageBox.information(self, "Civil 3D Export", f"CSV created successfully:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Civil 3D Export Error", str(exc))

    # ---------- Reset ----------
    def _reset_page(self) -> None:
        self.source_points = []
        self.result_points = []
        self.current_file = None
        self._axis_swapped = False
        self._preview_dirty = False
        self.direct_mode.blockSignals(True)
        self.direct_mode.setChecked(False)
        self.direct_mode.blockSignals(False)
        self.progress.setValue(0)
        self.file_status.setText("No coordinate file loaded")
        self.detected_format.clear()
        for combo in (self.x_column, self.y_column, self.z_column, self.name_column):
            combo.clear()
        self._render_points([])
        self._set_preview_clean()
