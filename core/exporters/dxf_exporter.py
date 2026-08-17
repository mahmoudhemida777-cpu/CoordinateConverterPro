"""DXF exporter for AutoCAD / Civil 3D compatible point drawings."""
from __future__ import annotations

import re
from enum import Enum
from typing import List

import ezdxf

from core.models import PointResult
from core.point_ordering import order_points


class LabelMode(str, Enum):
    NUMBER = "Point Number"
    NAME = "Point Name"
    COORDS = "E,N"
    NUMBER_AND_NAME = "Point Number + Name"


# AutoCAD ACI colors. The sequence is deliberately stable so the same code
# receives the same color during one export, while different codes remain
# visually distinct.
CODE_ACI_COLORS = [1, 3, 4, 5, 6, 30, 40, 50, 70, 80, 120, 140, 160, 180, 200]


def _safe_layer_suffix(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "UNNAMED").strip())
    return text[:80] or "UNNAMED"


def export_dxf(
    points: List[PointResult],
    out_path: str,
    label_mode: LabelMode = LabelMode.NUMBER_AND_NAME,
    text_height: float = 1.0,
    use_target_coords: bool = True,
    order_mode: str = "GRID_ZIGZAG_WEST",
    tolerance: float | None = None,
    reverse: bool = False,
    group_by_name: bool = False,
) -> str:
    """Write survey points as DXF entities, color-coded by point code.

    ``order_mode="SOURCE"`` is the explicit no-zigzag mode. When grouping is
    enabled, every code gets its own point and label layer and therefore its
    own AutoCAD color. No entity from one code is placed on another code's
    layer.
    """
    doc = ezdxf.new("R2013", setup=True)
    msp = doc.modelspace()

    if "POINTS" not in doc.layers:
        doc.layers.add(name="POINTS", color=7)
    if "LABELS" not in doc.layers:
        doc.layers.add(name="LABELS", color=7)

    ordered = order_points(
        points,
        mode=order_mode,
        tolerance=tolerance,
        reverse=reverse,
        group_by_name=group_by_name,
    )

    code_to_aci: dict[str, int] = {}

    def code_color(code: object) -> int:
        key = str(code or "UNNAMED")
        if key not in code_to_aci:
            code_to_aci[key] = CODE_ACI_COLORS[len(code_to_aci) % len(CODE_ACI_COLORS)]
        return code_to_aci[key]

    def ensure_code_layers(code: object) -> tuple[str, str, int]:
        suffix = _safe_layer_suffix(code)
        aci = code_color(code)
        point_layer = f"PT_{suffix}"
        label_layer = f"LBL_{suffix}"
        if point_layer not in doc.layers:
            doc.layers.add(name=point_layer, color=aci)
        if label_layer not in doc.layers:
            doc.layers.add(name=label_layer, color=aci)
        return point_layer, label_layer, aci

    for item in ordered:
        i, p = item.number, item.point
        x = p.tgt_x if use_target_coords else p.src_x
        y = p.tgt_y if use_target_coords else p.src_y
        z = p.tgt_z if use_target_coords else p.src_z
        if x is None or y is None:
            continue
        z = 0.0 if z is None else z

        point_layer, label_layer, aci = ensure_code_layers(item.group)
        msp.add_point(
            (float(x), float(y), float(z)),
            dxfattribs={"layer": point_layer, "color": aci},
        )

        name = str(p.name or "").strip()
        if label_mode == LabelMode.NUMBER:
            label = str(i)
        elif label_mode == LabelMode.NAME:
            label = name or str(i)
        elif label_mode == LabelMode.COORDS:
            label = f"{float(x):.3f},{float(y):.3f}"
        else:
            label = f"{i} - {name}" if name else str(i)

        text = msp.add_text(
            label,
            dxfattribs={"layer": label_layer, "height": float(text_height), "color": aci},
        )
        text.dxf.insert = (float(x), float(y), float(z))

    # Store the code/color mapping as DXF metadata where supported by ezdxf;
    # this makes the exported drawing self-describing without affecting CAD
    # geometry.
    try:
        doc.header["$MH_CODE_COLORS"] = ";".join(
            f"{key}={value}" for key, value in code_to_aci.items()
        )
    except Exception:
        pass

    doc.saveas(out_path)
    return out_path
