from __future__ import annotations

import csv
import re
from core.models import PointResult


def sniff_columns(path: str) -> list[str]:
    """Return logical columns for Survey TXT files."""
    return ["Point Number", "Easting", "Northing", "Elevation", "Description"]


def _split(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    if any(d in line for d in (",", "|", ";", "\t")):
        return [x.strip() for x in next(csv.reader([line], delimiter=","))] if "," in line else [x.strip() for x in re.split(r"[|;\t]", line)]
    return line.split()


def _is_number(value: str) -> bool:
    try:
        float(value.strip())
        return True
    except (ValueError, AttributeError):
        return False


def _is_header(parts: list[str]) -> bool:
    if not parts:
        return False
    text = " ".join(p.lower() for p in parts)
    return any(k in text for k in ("easting", "northing", "longitude", "latitude", "elev", "point number", "point_number"))


def parse_txt(path: str) -> list[PointResult]:
    """Import common survey TXT layouts automatically.

    Supported examples:
      E,N,Z
      Point,E,N,Z
      E N Z
      Point E N Z
    Headers are optional and common delimiters are accepted.
    """
    points: list[PointResult] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        rows: list[tuple[int, list[str]]] = []
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = _split(line)
            if parts:
                rows.append((line_no, parts))

    for line_no, parts in rows:
        if _is_header(parts):
            continue
        if len(parts) < 3:
            raise ValueError(f"Invalid TXT row at line {line_no}: expected E,N[,Z] or Point,E,N[,Z]")

        # Headerless Point,E,N,Z: first field is text and next two are numeric.
        if len(parts) >= 4 and not _is_number(parts[0]) and _is_number(parts[1]) and _is_number(parts[2]):
            name = parts[0] or f"PT-{len(points)+1}"
            x_idx, y_idx, z_idx = 1, 2, 3
        # Headerless E,N,Z: first three fields are numeric; generate point name.
        elif _is_number(parts[0]) and _is_number(parts[1]):
            name = f"PT-{len(points)+1}"
            x_idx, y_idx, z_idx = 0, 1, 2
        else:
            raise ValueError(f"Invalid numeric coordinates at TXT line {line_no}")

        try:
            x = float(parts[x_idx]); y = float(parts[y_idx])
            z = float(parts[z_idx]) if len(parts) > z_idx and parts[z_idx] != "" else None
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid numeric value at TXT line {line_no}") from exc
        points.append(PointResult(name, x, y, z))
    return points
