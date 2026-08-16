"""Survey point ordering utilities for sequential/grid exports."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List
from collections import OrderedDict
from core.models import PointResult

@dataclass(frozen=True)
class OrderedPoint:
    point: PointResult
    number: int
    row: int = 0
    column: int = 0
    group: str = ""

def _xy(p: PointResult):
    return (p.tgt_x if p.tgt_x is not None else p.src_x,
            p.tgt_y if p.tgt_y is not None else p.src_y)

def _point_group(p: PointResult) -> str:
    """Return a stable grouping key from survey point code/name."""
    value = str(p.name or "").strip()
    return value if value else "<NO CODE>"

def _cluster_axis(values: List[float], tolerance: float | None = None) -> List[List[int]]:
    if not values: return []
    order=sorted(range(len(values)), key=lambda i: values[i])
    if tolerance is None:
        diffs=[values[order[i+1]]-values[order[i]] for i in range(len(order)-1)]
        positive=[d for d in diffs if d>1e-9]
        tolerance=(sorted(positive)[len(positive)//2]*0.25) if positive else 1e-6
    groups=[[order[0]]]; centers=[values[order[0]]]
    for idx in order[1:]:
        if abs(values[idx]-centers[-1])<=tolerance:
            groups[-1].append(idx); centers[-1]=sum(values[i] for i in groups[-1])/len(groups[-1])
        else:
            groups.append([idx]); centers.append(values[idx])
    return groups

def _order_grid(points: List[PointResult], start_east: bool, tolerance: float | None) -> list[tuple[PointResult,int,int]]:
    """Order one point-code group as an independent geographic zigzag."""
    if not points:
        return []
    valid=[p for p in points if _xy(p)[0] is not None and _xy(p)[1] is not None]
    invalid=[p for p in points if _xy(p)[0] is None or _xy(p)[1] is None]
    groups=_cluster_axis([_xy(p)[1] for p in valid],tolerance)
    groups=sorted(groups,key=lambda g:sum(_xy(valid[i])[1] for i in g)/len(g),reverse=True)
    rows=[]
    for r,g in enumerate(groups,1):
        row=[valid[i] for i in g]
        ascending_x=(not start_east) if r % 2 == 1 else start_east
        row.sort(key=lambda p:_xy(p)[0], reverse=not ascending_x)
        rows.extend((p,r,c) for c,p in enumerate(row,1))
    rows.extend((p,0,0) for p in invalid)
    return rows

def order_points(
    points: Iterable[PointResult],
    mode: str="SOURCE",
    tolerance: float|None=None,
    reverse: bool=False,
    group_by_name: bool=False,
) -> List[OrderedPoint]:
    """Order points for exports.

    GRID_ZIGZAG_WEST starts each independent row from minimum X and alternates.
    GRID_ZIGZAG_EAST starts each independent row from maximum X and alternates.
    When group_by_name=True, every distinct point code/name is ordered as its
    own grid; groups never influence each other's row clustering or direction.
    Numbering remains globally unique for CAD/Civil 3D compatibility.
    """
    pts=list(points); mode=mode.upper()
    if mode=="SOURCE":
        ordered=[(p,0,0,_point_group(p)) for p in pts]
    else:
        valid=[p for p in pts if _xy(p)[0] is not None and _xy(p)[1] is not None]
        invalid=[p for p in pts if _xy(p)[0] is None or _xy(p)[1] is None]
        if mode in {"X_ASC","EAST_WEST"}:
            base=sorted(valid,key=lambda p:(_xy(p)[0],_xy(p)[1])); ordered=[(p,0,0,_point_group(p)) for p in base]
        elif mode in {"X_DESC","WEST_EAST"}:
            base=sorted(valid,key=lambda p:(-_xy(p)[0],_xy(p)[1])); ordered=[(p,0,0,_point_group(p)) for p in base]
        elif mode=="Y_ASC":
            base=sorted(valid,key=lambda p:(_xy(p)[1],_xy(p)[0])); ordered=[(p,0,0,_point_group(p)) for p in base]
        elif mode=="Y_DESC":
            base=sorted(valid,key=lambda p:(-_xy(p)[1],_xy(p)[0])); ordered=[(p,0,0,_point_group(p)) for p in base]
        else:
            start_east=mode in {"GRID_ZIGZAG_EAST","GRID_ZIGZAG_E"}
            if group_by_name:
                grouped: OrderedDict[str,list[PointResult]]=OrderedDict()
                for p in pts:
                    grouped.setdefault(_point_group(p),[]).append(p)
                ordered=[]
                for key,group in grouped.items():
                    ordered.extend((p,r,c,key) for p,r,c in _order_grid(group,start_east,tolerance))
            else:
                for p,r,c in _order_grid(valid,start_east,tolerance):
                    ordered.append((p,r,c,_point_group(p)))
                ordered.extend((p,0,0,_point_group(p)) for p in invalid)
    if reverse: ordered.reverse()
    return [OrderedPoint(p,n,r,c,g) for n,(p,r,c,g) in enumerate(ordered,1)]
