"""Plain-text survey point exporter."""
from __future__ import annotations

from typing import List

from core.models import PointResult


def export_txt(points: List[PointResult], out_path: str, precision: int = 3) -> str:
    precision = max(0, min(6, int(precision)))
    with open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("Point Number\tEasting\tNorthing\tElevation\tDescription\n")
        for i, p in enumerate(points, start=1):
            if p.tgt_x is None or p.tgt_y is None:
                continue
            z = p.tgt_z if p.tgt_z is not None else 0.0
            name = (p.name or "").replace("\t", " ").replace("\r", " ").replace("\n", " ")
            f.write(
                f"{i}\t{p.tgt_x:.{precision}f}\t{p.tgt_y:.{precision}f}\t{z:.{precision}f}\t{name}\n"
            )
    return out_path
