"""Survey point ordering utilities for sequential/grid exports."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List
from core.models import PointResult

@dataclass(frozen=True)
class OrderedPoint:
    point: PointResult
    number: int
    row: int = 0
    column: int = 0

def _xy(p: PointResult):
    return (p.tgt_x if p.tgt_x is not None else p.src_x,
            p.tgt_y if p.tgt_y is not None else p.src_y)

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

def order_points(points: Iterable[PointResult], mode: str="SOURCE", tolerance: float|None=None, reverse: bool=False) -> List[OrderedPoint]:
    """Order points for exports.

    GRID_ZIGZAG_WEST starts each first row from the westernmost (minimum X)
    point and alternates direction on each row. GRID_ZIGZAG_EAST starts from
    the easternmost (maximum X) point and alternates direction on each row.
    """
    pts=list(points); mode=mode.upper()
    if mode=="SOURCE":
        ordered=[(p,0,0) for p in pts]
    else:
        valid=[p for p in pts if _xy(p)[0] is not None and _xy(p)[1] is not None]
        invalid=[p for p in pts if _xy(p)[0] is None or _xy(p)[1] is None]
        if mode in {"X_ASC","EAST_WEST"}:
            ordered=[(p,0,0) for p in sorted(valid,key=lambda p:(_xy(p)[0],_xy(p)[1]))]
        elif mode in {"X_DESC","WEST_EAST"}:
            ordered=[(p,0,0) for p in sorted(valid,key=lambda p:(-_xy(p)[0],_xy(p)[1]))]
        elif mode=="Y_ASC":
            ordered=[(p,0,0) for p in sorted(valid,key=lambda p:(_xy(p)[1],_xy(p)[0]))]
        elif mode=="Y_DESC":
            ordered=[(p,0,0) for p in sorted(valid,key=lambda p:(-_xy(p)[1],_xy(p)[0]))]
        else:
            start_east = mode in {"GRID_ZIGZAG_EAST", "GRID_ZIGZAG_E"}
            groups=_cluster_axis([_xy(p)[1] for p in valid],tolerance)
            groups=sorted(groups,key=lambda g:sum(_xy(valid[i])[1] for i in g)/len(g),reverse=True)
            rows=[]
            for r,g in enumerate(groups,1):
                row=[valid[i] for i in g]
                # First row follows the requested start side; every next row reverses it.
                ascending_x = (not start_east) if r % 2 == 1 else start_east
                row.sort(key=lambda p:_xy(p)[0], reverse=not ascending_x)
                rows.extend((p,r,c) for c,p in enumerate(row,1))
            ordered=rows+[(p,0,0) for p in invalid]
    if reverse: ordered.reverse()
    return [OrderedPoint(p,n,r,c) for n,(p,r,c) in enumerate(ordered,1)]
