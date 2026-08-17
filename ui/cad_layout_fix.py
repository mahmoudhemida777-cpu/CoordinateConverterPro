from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
)


def apply_cad_page_layout(window: QWidget) -> bool:
    """Make the CAD page fully navigable on small/non-maximized windows.

    The CAD page already owns its functional controls. This helper only fixes
    presentation: it moves the existing page layout into an outer scroll area,
    gives the options pane enough width for its labels/combos, and keeps the
    preview/export area accessible without changing conversion logic.
    """
    cad = window.findChild(QWidget, "cadPage")
    if cad is None or cad.property("mh_layout_fixed"):
        return False

    root = cad.layout()
    if root is None:
        return False

    content = QWidget()
    content.setObjectName("cadPageScrollableContent")
    content.setMinimumWidth(1080)
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(18, 12, 18, 14)
    content_layout.setSpacing(7)
    content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

    # Move the already-created widgets/layouts into the scrollable content
    # widget. No CAD controls or signal connections are recreated.
    while root.count():
        item = root.takeAt(0)
        if item.widget() is not None:
            content_layout.addWidget(item.widget())
        elif item.layout() is not None:
            content_layout.addLayout(item.layout())
        elif item.spacerItem() is not None:
            content_layout.addItem(item)

    outer = QScrollArea(cad)
    outer.setObjectName("cadPageOuterScroll")
    outer.setWidgetResizable(True)
    outer.setFrameShape(QScrollArea.Shape.NoFrame)
    outer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    outer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    outer.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    outer.setWidget(content)

    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(outer)

    # The page currently has an inner scroll area for the options pane. Keep it
    # as a safety net, but make the pane wide enough that every selector and
    # label is readable at normal desktop sizes.
    scroll_areas = [s for s in cad.findChildren(QScrollArea) if s is not outer]
    if scroll_areas:
        options_scroll = scroll_areas[0]
        options_scroll.setMinimumWidth(470)
        options_scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        left_content = options_scroll.widget()
        if left_content is not None:
            left_content.setMinimumWidth(450)

            parsing = left_content.findChild(QGroupBox)
            if parsing is not None and "FILE & PARSING OPTIONS" in parsing.title():
                parsing.setMinimumWidth(450)

    # Give the two-pane splitter a deliberate desktop baseline: options remain
    # usable while the preview receives the larger share of available width.
    for layout in content.findChildren(QHBoxLayout):
        if layout.count() >= 2:
            first = layout.itemAt(0).widget()
            second = layout.itemAt(1).widget()
            if isinstance(first, QScrollArea) and second is not None:
                layout.setStretch(0, 0)
                layout.setStretch(1, 1)
                break

    # Prevent the preview table from collapsing below a usable width.
    table = cad.findChild(QWidget, "cadPointsTable")
    if table is not None:
        table.setMinimumWidth(560)

    cad.setProperty("mh_layout_fixed", True)
    content.adjustSize()
    content.updateGeometry()
    outer.updateGeometry()
    return True
