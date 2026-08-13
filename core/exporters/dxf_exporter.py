"""DXF exporter for AutoCAD / Civil 3D compatible point drawings."""
from __future__ import annotations

from enum import Enum
from typing import List

import ezdxf

from core.models import PointResult


class LabelMode(str, Enum):
    NUMBER = "Point Number"
    NAME = "Point Name"
    COORDS = "E,N"
    NUMBER_AND_NAME = "Point Number + Name"


def export_dxf(
    points: List[PointResult],
    out_path: str,
    label_mode: LabelMode = LabelMode.NAME,
    text_height: float = 1.0,
    use_target_coords: bool = True,
) -> str:
    """Write survey points as real DXF POINT entities plus labels.

    Target X/Y are written as Easting/Northing and target Z as elevation.
    Failed or incomplete points are skipped rather than breaking the export.
    """
    doc = ezdxf.new("R2013", setup=True)
    msp = doc.modelspace()
    doc.layers.add(name="POINTS", color=1)
    doc.layers.add(name="LABELS", color=3)

    for i, p in enumerate(points, start=1):
        x = p.tgt_x if use_target_coords else p.src_x
        y = p.tgt_y if use_target_coords else p.src_y
        z = p.tgt_z if use_target_coords else p.src_z
        if x is None or y is None:
            continue
        z = 0.0 if z is None else z

        msp.add_point((float(x), float(y), float(z)), dxfattribs={"layer": "POINTS"})

        if label_mode == LabelMode.NUMBER:
            label = str(i)
        elif label_mode == LabelMode.NAME:
            label = p.name
        elif label_mode == LabelMode.COORDS:
            label = f"{float(x):.3f},{float(y):.3f}"
        else:
            label = f"{i} - {p.name}"

        text = msp.add_text(
            label,
            dxfattribs={"layer": "LABELS", "height": float(text_height)},
        )
        text.dxf.insert = (float(x), float(y), float(z))

    doc.saveas(out_path)
    return out_path
