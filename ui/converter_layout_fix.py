"""Page-local geometry for the CRS Converter screen.

This module intentionally changes only ConverterPage geometry. CRS logic,
parsers, CAD handling, exports, translations, and other pages are untouched.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QLayout,
    QWidget,
)


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


def _wrap_page_in_scroll_area(page: QWidget) -> bool:
    """Make the complete ConverterPage navigable on short/non-maximized windows."""
    if page.property("mh_converter_scroll_fixed"):
        return False

    root = page.layout()
    if root is None:
        return False

    content = QWidget()
    content.setObjectName("converterPageScrollableContent")
    content.setMinimumWidth(1080)
    content_layout = page.layout().__class__(content)
    content_layout.setContentsMargins(10, 5, 10, 7)
    content_layout.setSpacing(5)
    content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

    while root.count():
        item = root.takeAt(0)
        if item.widget() is not None:
            content_layout.addWidget(item.widget())
        elif item.layout() is not None:
            content_layout.addLayout(item.layout())
        elif item.spacerItem() is not None:
            content_layout.addItem(item)

    outer = QScrollArea(page)
    outer.setObjectName("converterPageOuterScroll")
    outer.setWidgetResizable(True)
    outer.setFrameShape(QScrollArea.Shape.NoFrame)
    outer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    outer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    outer.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    outer.setWidget(content)

    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(outer)
    page.setProperty("mh_converter_scroll_fixed", True)
    content.adjustSize()
    content.updateGeometry()
    outer.updateGeometry()
    return True


def apply_converter_page_layout(window) -> None:
    """Apply a responsive CRS Converter layout without changing behavior."""
    page = getattr(window, "pages", {}).get("converter")
    if page is None:
        return

    # Keep the entire converter usable on short windows, exactly like the CAD
    # page: the controls remain at their designed sizes and the user scrolls
    # instead of Qt clipping Export or the lower CRS controls.
    _wrap_page_in_scroll_area(page)

    root = page.layout()
    if root is not None:
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

    # The actual content layout is now owned by the scroll area's widget.
    scroll = page.findChild(QScrollArea, "converterPageOuterScroll")
    content_root = scroll.widget().layout() if scroll is not None and scroll.widget() is not None else None
    if content_root is None:
        return

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
    # caused the Source/Target lists to overlap and gives each picker the full
    # usable width. The picker widgets and all CRS logic remain untouched.
    source_picker = getattr(page, "source_picker", None)
    target_picker = getattr(page, "target_picker", None)
    if source_picker is not None and target_picker is not None:
        crs_layout = _find_layout_containing(content_root, source_picker)
        target_layout = _find_layout_containing(content_root, target_picker)
        if crs_layout is not None and crs_layout is target_layout:
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
    # five export buttons. Keep the complete group visible without clipping;
    # on short windows the outer scroll area handles the remaining height.
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
