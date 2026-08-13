"""CSV parser with automatic survey-coordinate format detection."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List, Optional

from core.models import PointResult


@dataclass
class ColumnMapping:
    name_col: Optional[str]
    x_col: str
    y_col: str
    z_col: Optional[str] = None


def _is_number(value: str) -> bool:
    try:
        float(value.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _read_rows(path: str, encoding: str = "utf-8-sig") -> list[list[str]]:
    with open(path, newline="", encoding=encoding, errors="replace") as f:
        return [[cell.strip() for cell in row] for row in csv.reader(f) if any(cell.strip() for cell in row)]


def _header_like(row: list[str]) -> bool:
    if len(row) < 2:
        return False
    text = " ".join(x.lower() for x in row)
    return any(k in text for k in ("easting", "northing", "longitude", "latitude", "elev", "point", "name", "x", "y", "z")) and not all(_is_number(x) for x in row[:3])


def sniff_columns(path: str, encoding: str = "utf-8-sig") -> List[str]:
    """Return real headers when present; otherwise provide safe generated headers."""
    rows = _read_rows(path, encoding)
    if not rows:
        return ["Point", "Easting", "Northing", "Elevation"]
    first = rows[0]
    if _header_like(first):
        return first
    if len(first) >= 4 and not _is_number(first[0]) and _is_number(first[1]) and _is_number(first[2]):
        return ["Point", "Easting", "Northing", "Elevation"][:len(first)]
    return ["Easting", "Northing", "Elevation"][:len(first)]


def parse_csv(path: str, mapping: ColumnMapping, encoding: str = "utf-8-sig") -> List[PointResult]:
    points: List[PointResult] = []
    with open(path, newline="", encoding=encoding, errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            name = row.get(mapping.name_col, "").strip() if mapping.name_col else f"PT-{i}"
            try:
                x = float(row[mapping.x_col])
                y = float(row[mapping.y_col])
            except (KeyError, ValueError, TypeError):
                points.append(PointResult(name or f"PT-{i}", None, None, None, status="FAILED", message="Invalid or missing X/Y"))
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


def parse_csv_auto(path: str, encoding: str = "utf-8-sig") -> List[PointResult]:
    """Import survey CSV automatically, with or without a header/point column."""
    rows = _read_rows(path, encoding)
    if not rows:
        return []

    has_header = _header_like(rows[0])
    data = rows[1:] if has_header else rows
    headers = rows[0] if has_header else None
    if not data:
        return []

    def col_index(names: tuple[str, ...], default: int | None = None) -> int | None:
        if not headers:
            return default
        lowered = [h.strip().lower() for h in headers]
        for name in names:
            if name in lowered:
                return lowered.index(name)
        for i, h in enumerate(lowered):
            if any(name in h for name in names):
                return i
        return default

    x_idx = col_index(("easting", "east", "longitude", "lon", "x"), 0)
    y_idx = col_index(("northing", "north", "latitude", "lat", "y"), 1)
    z_idx = col_index(("elevation", "elev", "height", "z"), 2)
    name_idx = col_index(("point number", "point_number", "point", "name", "id"), None)

    # Headerless 4-column survey data is normally Point,E,N,Z.
    if not has_header and len(data[0]) >= 4 and not _is_number(data[0][0]) and _is_number(data[0][1]) and _is_number(data[0][2]):
        name_idx, x_idx, y_idx, z_idx = 0, 1, 2, 3

    points: List[PointResult] = []
    for i, row in enumerate(data, start=1):
        try:
            if x_idx is None or y_idx is None or len(row) <= max(x_idx, y_idx):
                raise ValueError
            x = float(row[x_idx]); y = float(row[y_idx])
            z = float(row[z_idx]) if z_idx is not None and len(row) > z_idx and row[z_idx] != "" else None
        except (ValueError, TypeError):
            points.append(PointResult(f"PT-{i}", None, None, None, status="FAILED", message="Invalid or missing X/Y"))
            continue
        name = row[name_idx].strip() if name_idx is not None and len(row) > name_idx and row[name_idx].strip() else f"PT-{i}"
        points.append(PointResult(name, x, y, z))
    return points
