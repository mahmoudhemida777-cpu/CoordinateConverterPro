from __future__ import annotations

from pathlib import Path
from types import MethodType

from PySide6.QtWidgets import QFileDialog, QMessageBox

from core.cad_importer import extract_cad_points
from ui.i18n import tr


def apply_cad_import_fix(cad) -> None:
    """Patch the existing CadPage without replacing its established UI/workflow."""
    if cad.property("mh_cad_import_fixed"):
        return

    original_load = cad._load_path

    def load_path(self, path: str) -> None:
        suffix = Path(path).suffix.casefold()
        if suffix not in {".dxf", ".dwg"}:
            return original_load(path)
        try:
            points = list(extract_cad_points(path) or [])
            if not points:
                raise ValueError(tr("No coordinate points were detected in the selected file."))
            self.current_file = str(Path(path).resolve())
            self.workspace_folder = str(Path(path).resolve().parent)
            self.workspace_bar.set_folder(self.workspace_folder, self.current_file)
            self.source_points = points
            self.result_points = []
            self.direct_mode.setChecked(True)
            self.detected_format.clear()
            self.detected_format.addItem(suffix.upper().lstrip("."))
            self.file_status.setText(f"{tr('Loaded CAD file')}: {Path(path).name} — {len(points)} {tr('points loaded')}")
            self._render_points(self._ordered_results(points))
            self._set_preview_clean(tr("Loaded CAD source data"))
        except Exception as exc:
            self.source_points = []
            self.result_points = []
            self._render_points([])
            self.file_status.setText(f"{tr('Load failed')}: {exc}")
            QMessageBox.critical(self, tr("Coordinate File Error"), str(exc))

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Choose File"),
            self.workspace_folder or "",
            "Supported coordinate/CAD (*.dxf *.dwg *.kmz *.kml *.csv *.xlsx *.txt);;"
            "CAD (*.dxf *.dwg);;Coordinate (*.kmz *.kml *.csv *.xlsx *.txt);;All files (*.*)",
        )
        if path:
            self._load_path(path)

    cad._load_path = MethodType(load_path, cad)
    cad._choose_file = MethodType(choose_file, cad)
    cad.setProperty("mh_cad_import_fixed", True)
