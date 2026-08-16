"""DXF exporter for AutoCAD / Civil 3D compatible point drawings."""
from __future__ import annotations
from enum import Enum
from typing import List
import ezdxf
from core.models import PointResult
from core.point_ordering import order_points

class LabelMode(str, Enum):
    NUMBER="Point Number"
    NAME="Point Name"
    COORDS="E,N"
    NUMBER_AND_NAME="Point Number + Name"

def export_dxf(points: List[PointResult], out_path: str, label_mode: LabelMode=LabelMode.NUMBER_AND_NAME, text_height: float=1.0, use_target_coords: bool=True, order_mode: str="GRID_ZIGZAG_WEST", tolerance: float|None=None, reverse: bool=False, group_by_name: bool=False) -> str:
    """Write survey points as DXF POINT entities and coordinate-based labels."""
    doc=ezdxf.new("R2013",setup=True); msp=doc.modelspace()
    if "POINTS" not in doc.layers: doc.layers.add(name="POINTS",color=1)
    if "LABELS" not in doc.layers: doc.layers.add(name="LABELS",color=3)
    ordered=order_points(points,mode=order_mode,tolerance=tolerance,reverse=reverse,group_by_name=group_by_name)
    for item in ordered:
        i,p=item.number,item.point; x=p.tgt_x if use_target_coords else p.src_x; y=p.tgt_y if use_target_coords else p.src_y; z=p.tgt_z if use_target_coords else p.src_z
        if x is None or y is None: continue
        z=0.0 if z is None else z; msp.add_point((float(x),float(y),float(z)),dxfattribs={"layer":"POINTS"})
        name=str(p.name or "").strip()
        if label_mode==LabelMode.NUMBER: label=str(i)
        elif label_mode==LabelMode.NAME: label=name or str(i)
        elif label_mode==LabelMode.COORDS: label=f"{float(x):.3f},{float(y):.3f}"
        else: label=f"{i} - {name}" if name else str(i)
        text=msp.add_text(label,dxfattribs={"layer":"LABELS","height":float(text_height)}); text.dxf.insert=(float(x),float(y),float(z))
    doc.saveas(out_path); return out_path
