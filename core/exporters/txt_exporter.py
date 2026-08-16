"""Plain-text survey point exporter with coordinate-based ordering."""
from __future__ import annotations
from typing import List
from core.models import PointResult
from core.point_ordering import order_points


def export_txt(points: List[PointResult], out_path: str, precision: int = 3,
               order_mode: str = "GRID_ZIGZAG", tolerance: float | None = None,
               reverse: bool = False) -> str:
    precision = max(0, min(6, int(precision)))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("Point Number\tEasting\tNorthing\tElevation\tDescription\n")
        for item in order_points(points, mode=order_mode, tolerance=tolerance, reverse=reverse):
            p = item.point
            if p.tgt_x is None or p.tgt_y is None:
                continue
            z = p.tgt_z if p.tgt_z is not None else 0.0
            name = (p.name or "").replace("\t", " ").replace("\r", " ").replace("\n", " ")
            f.write(f"{item.number}\t{p.tgt_x:.{precision}f}\t{p.tgt_y:.{precision}f}\t{z:.{precision}f}\t{name}\n")
    return out_path
