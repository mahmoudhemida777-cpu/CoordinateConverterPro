"""Page-local geometry fix for the CRS Converter screen."""
from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QSizePolicy


def apply_converter_page_layout(window) -> None:
    """Fit only the CRS Converter page without changing its functionality."""
    page = getattr(window, "pages", {}).get("converter")
    if page is None:
        return

    root = page.layout()
    if root is not None:
        root.setContentsMargins(10, 5, 10, 7)
        root.setSpacing(4)

    if hasattr(page, "workspace_bar"):
        page.workspace_bar.setMaximumHeight(34)
    if hasattr(page, "choose_btn"):
        page.choose_btn.setFixedSize(130, 34)
    if hasattr(page, "file_label"):
        page.file_label.setMinimumHeight(34)

    # Equal CRS panels. 174 px leaves a reserved area for the table and the
    # export footer even at the application's 1100x700 minimum size.
    for picker in (getattr(page, "source_picker", None), getattr(page, "target_picker", None)):
        if picker is not None:
            picker.setFixedHeight(174)
            picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    if hasattr(page, "convert_btn"):
        page.convert_btn.setFixedSize(120, 34)
    if hasattr(page, "progress"):
        page.progress.setFixedHeight(7)

    summary = page.findChild(QGroupBox, "conversionSummary")
    if summary is not None:
        summary.setFixedHeight(44)
        layout = summary.layout()
        if layout is not None:
            layout.setContentsMargins(8, 3, 8, 3)
            layout.setSpacing(6)

    export_box = None
    for box in page.findChildren(QGroupBox):
        if box.property("mhTitleKey") == "Export Converted Points" or box.title() == "Export Converted Points":
            export_box = box
            break

    if export_box is not None:
        export_box.setFixedHeight(60)
        layout = export_box.layout()
        if layout is not None:
            layout.setContentsMargins(6, 6, 6, 5)
            layout.setSpacing(5)
        for button in export_box.findChildren(QPushButton):
            button.setFixedHeight(32)

    table = getattr(page, "results_table", None)
    if table is not None:
        table.setMinimumHeight(45)
        table.verticalHeader().setDefaultSectionSize(26)
        table.verticalHeader().setMinimumSectionSize(26)
