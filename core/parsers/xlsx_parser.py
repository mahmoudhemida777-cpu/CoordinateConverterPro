"""XLSX parser with user-configurable column mapping (mirrors csv_parser)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import openpyxl

from core.models import PointResult


@dataclass
class ColumnMapping:
    name_col: Optional[str]
    x_col: str
    y_col: str
    z_col: Optional[str] = None


def sniff_columns(path: str, sheet: Optional[str] = None) -> List[str]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    header = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    wb.close()
    return header


def parse_xlsx(path: str, mapping: ColumnMapping, sheet: Optional[str] = None) -> List[PointResult]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    wb.close()
    if not rows:
        return []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(header)}

    points: List[PointResult] = []
    for i, row in enumerate(rows[1:], start=1):
        name = None
        if mapping.name_col and mapping.name_col in idx:
            raw = row[idx[mapping.name_col]]
            name = str(raw).strip() if raw is not None else None
        try:
            x = float(row[idx[mapping.x_col]])
            y = float(row[idx[mapping.y_col]])
        except (KeyError, TypeError, ValueError, IndexError):
            points.append(PointResult(name or f"PT-{i}", None, None, None,
                                       status="FAILED", message="Invalid or missing X/Y"))
            continue
        z = None
        if mapping.z_col and mapping.z_col in idx:
            raw_z = row[idx[mapping.z_col]]
            try:
                z = float(raw_z) if raw_z is not None else None
            except (ValueError, TypeError):
                z = None
        points.append(PointResult(name or f"PT-{i}", x, y, z))
    return points
