"""Page-local geometry for the CRS Converter screen.

This module intentionally changes only ConverterPage geometry. CRS logic,
parsers, CAD handling, exports, translations, and other pages are untouched.
"""
from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QGroupBox, QPushButton, QSizePolicy


def _find_layout_containing(root_layout, widget):
    """Return the nested layout that directly contains *widget*."""
    if root_layout is None:
        return None
    for index in range(root_layout.count()):
        item = root_layout.itemAt(index)
        if item is None:
            continue
        if item.widget() is widget:
            return root_layout
        child = item.layout()
        if child is not None:
            found = _find_layout_containing(child, widget)
            if found is not None:
                return found
    return None


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

    # CRS pickers intentionally stack vertically, matching the CAD page's
    # section-oriented layout. This eliminates the horizontal squeeze that
    # caused the Source/Target lists to overlap and makes each picker full
    # width. We change only the direction of their existing layout; the
    # picker widgets and all CRS logic remain untouched.
    source_picker = getattr(page, "source_picker", None)
    target_picker = getattr(page, "target_picker", None)
    if source_picker is not None and target_picker is not None:
        crs_layout = _find_layout_containing(root, source_picker)
        if crs_layout is not None and crs_layout is _find_layout_containing(root, target_picker):
            if isinstance(crs_layout, QBoxLayout):
                crs_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            crs_layout.setSpacing(10)
            for picker in (source_picker, target_picker):
                picker.setMinimumHeight(225)
                picker.setMaximumHeight(16777215)
                picker.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
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

    # Export Converted Points contains BOTH the information label and the
    # five export buttons. Keep the complete group visible.
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

    page.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
