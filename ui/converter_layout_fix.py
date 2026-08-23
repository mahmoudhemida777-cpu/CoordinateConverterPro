"""Page-local geometry for the CRS Converter screen.

This module intentionally changes only ConverterPage geometry. CRS logic,
parsers, CAD handling, exports, translations, and other pages are untouched.
"""
from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QPushButton, QSizePolicy


def apply_converter_page_layout(window) -> None:
    """Apply a responsive CRS Converter layout without changing behavior."""
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

    # CRS pickers: keep both columns identical and large enough for the
    # search field + visible result list. Do not force them to grow beyond
    # the available page height.
    for picker in (
        getattr(page, "source_picker", None),
        getattr(page, "target_picker", None),
    ):
        if picker is not None:
            picker.setMinimumHeight(211)
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

    # Results table is the only vertical stretch area on the Results page.
    table = getattr(page, "results_table", None)
    if table is not None:
        table.setMinimumHeight(85)
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        table.verticalHeader().setDefaultSectionSize(26)
        table.verticalHeader().setMinimumSectionSize(26)

    # IMPORTANT: Export Converted Points contains BOTH the information label
    # and the five export buttons. The old 62 px fixed height was too small
    # for its contents and caused the buttons to be clipped/hidden. Keep the
    # whole group visible; the Export page itself remains independent from
    # the Results page, so this does not steal height from the results table.
    export_box = None
    for box in page.findChildren(QGroupBox):
        if (
            box.property("mhTitleKey") == "Export Converted Points"
            or box.title() == "Export Converted Points"
        ):
            export_box = box
            break

    if export_box is not None:
        export_box.setMinimumHeight(138)
        export_box.setFixedHeight(138)
        export_box.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout = export_box.layout()
        if layout is not None:
            layout.setContentsMargins(12, 12, 12, 10)
            layout.setSpacing(8)
        for button in export_box.findChildren(QPushButton):
            button.setFixedHeight(42)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

    # Keep the three internal pages usable even when the host window is
    # resized. The application's MainWindow already enforces 1100x700 as the
    # minimum window size; no global/page changes are made here.
    page.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
