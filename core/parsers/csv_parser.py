"""CSV parser with user-configurable column mapping."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List, Optional

from core.models import PointResult


@dataclass
class ColumnMapping:
    name_col: Optional[str]
    x_col: str  # Easting / Longitude
    y_col: str  # Northing / Latitude
    z_col: Optional[str] = None


def sniff_columns(path: str, encoding: str = "utf-8-sig") -> List[str]:
    """Return the header row so the UI can present a column-mapping dialog."""
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.reader(f)
        header = next(reader)
    return [h.strip() for h in header]


def parse_csv(path: str, mapping: ColumnMapping, encoding: str = "utf-8-sig") -> List[PointResult]:
    points: List[PointResult] = []
    with open(path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            name = row.get(mapping.name_col, "").strip() if mapping.name_col else f"PT-{i}"
            try:
                x = float(row[mapping.x_col])
                y = float(row[mapping.y_col])
            except (KeyError, ValueError, TypeError):
                points.append(PointResult(name or f"PT-{i}", None, None, None,
                                           status="FAILED", message="Invalid or missing X/Y"))
                continue
            z = None
            if mapping.z_col:
                raw_z = row.get(mapping.z_col)
                try:
                    z = float(raw_z) if raw_z not in (None, "") else None
                except ValueError:
                    z = None
            points.append(PointResult(name or f"PT-{i}", x, y, z))
    return points
