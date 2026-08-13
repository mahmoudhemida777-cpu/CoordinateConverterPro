from __future__ import annotations

import csv
import re
from pathlib import Path
from core.models import PointResult


def sniff_columns(path: str) -> list[str]:
    """Return logical columns for the Survey TXT importer."""
    return ["Point Number", "Easting", "Northing", "Elevation", "Description"]


def _split(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    # Support common survey TXT delimiters: comma, pipe, semicolon, tab,
    # or arbitrary whitespace. Keep descriptions containing spaces intact
    # when a comma/pipe/tab delimiter is present.
    if any(d in line for d in (",", "|", ";", "\t")):
        return [x.strip() for x in next(csv.reader([line], delimiter=","))] if "," in line else [x.strip() for x in re.split(r"[|;\t]", line)]
    return line.split()


def parse_txt(path: str) -> list[PointResult]:
    points: list[PointResult] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = _split(line)
            if parts and parts[0].lower() in {"point", "point number", "point_number", "name"}:
                continue
            if len(parts) < 3:
                raise ValueError(f"Invalid TXT row at line {line_no}: expected Point, Easting, Northing")
            try:
                name = parts[0]
                x = float(parts[1]); y = float(parts[2])
                z = float(parts[3]) if len(parts) >= 4 and parts[3] != "" else None
            except ValueError as exc:
                raise ValueError(f"Invalid numeric value at TXT line {line_no}") from exc
            points.append(PointResult(name, x, y, z))
    return points
