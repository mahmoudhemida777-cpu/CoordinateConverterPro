"""Robust survey TXT/ASCII coordinate parser with automatic column detection."""
from __future__ import annotations
import csv
import re
from core.models import PointResult


def sniff_columns(path: str) -> list[str]:
    return ["Point Number", "Easting", "Northing", "Elevation", "Description"]


def _norm(v: object) -> str:
    return "".join(ch for ch in str(v).strip().lower() if ch.isalnum())


def _num(v: object) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace("\u00a0", "")
    if not s:
        return None
    # Accept decimal comma when it is not being used as the field delimiter.
    if "," in s and "." not in s and s.count(",") == 1:
        s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _split(line: str) -> list[str]:
    line = line.strip()
    if not line:
        return []
    # Prefer explicit delimiters. For comma-delimited files use csv so quoted text works.
    if "," in line:
        try:
            return [x.strip() for x in next(csv.reader([line], delimiter=","))]
        except Exception:
            pass
    if ";" in line:
        return [x.strip() for x in line.split(";")]
    if "|" in line:
        return [x.strip() for x in line.split("|")]
    if "\t" in line:
        return [x.strip() for x in line.split("\t")]
    return [x.strip() for x in re.split(r"\s+", line) if x.strip()]


def _header_like(parts: list[str]) -> bool:
    keys = [_norm(p) for p in parts]
    aliases = (
        "easting", "east", "x", "xcoord", "xcoordinate", "longitude", "lon",
        "northing", "north", "y", "ycoord", "ycoordinate", "latitude", "lat",
        "elevation", "elev", "height", "z", "zcoord", "zcoordinate",
        "point", "pointnumber", "pointno", "pointid", "name", "id", "number"
    )
    return any(k in aliases or any(a in k for a in aliases if len(a) >= 4) for k in keys)


def _find_col(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    ns = [_norm(h) for h in headers]
    aa = [_norm(a) for a in aliases]
    for a in aa:
        if a in ns:
            return ns.index(a)
    for i, h in enumerate(ns):
        if any(a in h for a in aa):
            return i
    return None


def _numeric_columns(data: list[list[str]]) -> list[int]:
    if not data:
        return []
    width = max(len(r) for r in data)
    result = []
    sample = data[:50]
    for c in range(width):
        vals = [r[c] for r in sample if len(r) > c and str(r[c]).strip()]
        if vals and sum(_num(v) is not None for v in vals) >= max(1, int(len(vals) * 0.75)):
            result.append(c)
    return result


def parse_txt(path: str) -> list[PointResult]:
    """Read common survey ASCII/TXT layouts without asking the user for mapping.

    Supports headers or no headers, arbitrary X/Y/Z/point order, and comma,
    semicolon, pipe, tab, or whitespace-separated data. If headers are vague,
    numeric-column analysis is used as a fallback.
    """
    rows: list[tuple[int, list[str]]] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith(("#", "//")):
                continue
            parts = _split(line)
            if parts:
                rows.append((line_no, parts))
    if not rows:
        return []

    first = rows[0][1]
    has_header = _header_like(first) and not all(_num(x) is not None for x in first)
    headers = first if has_header else []
    data_rows = rows[1:] if has_header else rows
    data = [p for _, p in data_rows]
    if not data:
        return []

    if has_header:
        x_idx = _find_col(headers, ("easting", "east", "x", "xcoord", "xcoordinate", "longitude", "lon"))
        y_idx = _find_col(headers, ("northing", "north", "y", "ycoord", "ycoordinate", "latitude", "lat"))
        z_idx = _find_col(headers, ("elevation", "elev", "height", "z", "zcoord", "zcoordinate"))
        n_idx = _find_col(headers, ("pointnumber", "pointno", "pointid", "point", "name", "id", "number"))
        if x_idx is None or y_idx is None:
            nums = _numeric_columns(data)
            if len(nums) >= 2:
                x_idx, y_idx = nums[0], nums[1]
                z_idx = nums[2] if len(nums) >= 3 else None
    else:
        # Common headerless forms: E N Z, Point E N Z, or Point E N Z Description.
        first_data = data[0]
        nums = _numeric_columns(data)
        if len(first_data) >= 4 and _num(first_data[0]) is None and _num(first_data[1]) is not None and _num(first_data[2]) is not None:
            n_idx, x_idx, y_idx = 0, 1, 2
            z_idx = 3 if len(first_data) > 3 and _num(first_data[3]) is not None else None
        elif len(nums) >= 2:
            x_idx, y_idx = nums[0], nums[1]
            z_idx = nums[2] if len(nums) >= 3 else None
            n_idx = None
            if x_idx > 0 and all(len(r) > 0 and _num(r[0]) is None for r in data[:min(20, len(data))]):
                n_idx = 0
        else:
            raise ValueError("Could not automatically detect two numeric coordinate columns in TXT file")

    if x_idx is None or y_idx is None:
        raise ValueError("Could not automatically detect X/Easting and Y/Northing columns in TXT file")

    points: list[PointResult] = []
    for seq, (line_no, row) in enumerate(data_rows, 1):
        try:
            if len(row) <= max(x_idx, y_idx):
                raise ValueError
            x = _num(row[x_idx]); y = _num(row[y_idx])
            if x is None or y is None:
                raise ValueError
            z = _num(row[z_idx]) if z_idx is not None and len(row) > z_idx else None
            name = str(row[n_idx]).strip() if n_idx is not None and len(row) > n_idx and str(row[n_idx]).strip() else f"PT-{seq}"
            points.append(PointResult(name, x, y, z))
        except (ValueError, TypeError, IndexError):
            points.append(PointResult(f"PT-{seq}", None, None, None, status="FAILED", message=f"Invalid or missing X/Y at TXT line {line_no}"))
    if not any(p.src_x is not None and p.src_y is not None for p in points):
        raise ValueError("No valid coordinate points were detected in TXT file")
    return points
