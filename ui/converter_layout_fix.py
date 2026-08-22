"""Page-local geometry fix for the CRS Converter screen.

This module intentionally touches only ConverterPage widget geometry.  It does
not change CRS logic, parsers, CAD handling, translations, or other pages.
"""
from __future__ import annotations

from PySide6.QtWidgets import QSizePolicy


def apply_converter_page_layout(window) -> None:
    """Keep the CRS page visually complete on the minimum supported window.

    The existing page uses fixed-height child widgets.  The previous values
    consumed too much vertical space, so the Export Converted Points footer
    could be clipped by the window.  We keep the same structure and only
    reduce the fixed geometry enough to reserve a visible footer and table.
    """
    page = getattr(window, "pages", {}).get("converter")
    if page is None:
        return

    # Page-local controls only.
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

    # Equal CRS panels: large enough for the picker, but compact enough to
    # leave room for results and the export footer at 1100x700 minimum size.
    for picker in (
        getattr(page, "source_picker", None),
        getattr(page, "target_picker", None),
    ):
        if picker is not None:
            picker.setFixedHeight(174)
            picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    if hasattr(page, "convert_btn"):
        page.convert_btn.setFixedSize(120, 34)
    if hasattr(page, "progress"):
        page.progress.setFixedHeight(7)

    if hasattr(page, "conversionSummary"):
        page.conversionSummary.setFixedHeight(44)

    # The current implementation names this group box through its title.
    export_box = None
    for box in page.findChildren(type(page.source_picker)):
        # Do not touch CRSPicker instances.
        pass
    from PySide6.QtWidgets import QGroupBox
    for box in page.findChildren(QGroupBox):
        if box.title() == "Export Converted Points" or box.property("mhTitleKey") == "Export Converted Points":
            export_box = box
            break
    if export_box is not None:
        export_box.setFixedHeight(60)
        layout = export_box.layout()
        if layout is not None:
            layout.setContentsMargins(6, 6, 6, 5)
            layout.setSpacing(5)
        for button in export_box.findChildren(type(page.convert_btn)):
            button.setFixedHeight(32)

    table = getattr(page, "results_table", None)
    if table is not None:
        table.setMinimumHeight(45)
        table.verticalHeader().setDefaultSectionSize(26)
        table.verticalHeader().setMinimumSectionSize(26)
