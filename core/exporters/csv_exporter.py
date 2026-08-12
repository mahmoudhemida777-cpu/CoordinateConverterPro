"""CSV exporter."""
from __future__ import annotations

import csv
from typing import List

from core.models import PointResult


def export_csv(points: List[PointResult], out_path: str, precision: int = 3) -> str:
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["No.", "Point Name", "Source X", "Source Y", "Source Z",
                          "Target X", "Target Y", "Target Z", "Status"])
        for i, p in enumerate(points, start=1):
            fmt = lambda v: f"{v:.{precision}f}" if isinstance(v, (int, float)) else (v or "")
            writer.writerow([i, p.name, fmt(p.src_x), fmt(p.src_y), fmt(p.src_z),
                              fmt(p.tgt_x), fmt(p.tgt_y), fmt(p.tgt_z), p.status])
    return out_path
