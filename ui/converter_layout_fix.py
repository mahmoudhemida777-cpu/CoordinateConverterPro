"""Page-local geometry for the CRS Converter screen.

This module intentionally changes only ConverterPage geometry. CRS logic,
parsers, CAD handling, exports, translations, and other pages are untouched.
"""
from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QSizePolicy


def apply_converter_page_layout(window) -> None:
    """Apply the stable CRS Converter layout without changing behavior."""
    page = getattr(window, "pages", {}).get("converter")
    if page is None:
        return

    root = page.layout()
    if root is not None:
        root.setContentsMargins(10, 5, 10, 7)
        root.setSpacing(5)

    # Project-file row.
    if hasattr(page, "workspace_bar"):
        page.workspace_bar.setFixedHeight(34)
        page.workspace_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
    if hasattr(page, "choose_btn"):
        page.choose_btn.setFixedSize(130, 34)
    if hasattr(page, "file_label"):
        page.file_label.setFixedHeight(34)

    # CRSPicker's internal controls require about 211 px. Anything smaller
    # clips the list/selected label and creates the overlap seen previously.
    for picker in (
        getattr(page, "source_picker", None),
        getattr(page, "target_picker", None),
    ):
        if picker is not None:
            picker.setFixedHeight(211)
            picker.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

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

    # Results table is the only vertical stretch area. The export footer is
    # fixed so it remains completely visible and never overlays the table.
    table = getattr(page, "results_table", None)
    if table is not None:
        table.setMinimumHeight(85)
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        table.verticalHeader().setDefaultSectionSize(26)
        table.verticalHeader().setMinimumSectionSize(26)

    export_box = None
    for box in page.findChildren(QGroupBox):
        if (
            box.property("mhTitleKey") == "Export Converted Points"
            or box.title() == "Export Converted Points"
        ):
            export_box = box
            break

    if export_box is not None:
        export_box.setFixedHeight(62)
        export_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout = export_box.layout()
        if layout is not None:
            layout.setContentsMargins(8, 7, 8, 6)
            layout.setSpacing(7)
        for button in export_box.findChildren(QPushButton):
            button.setFixedHeight(34)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
