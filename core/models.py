"""Shared lightweight data models used across parsers, exporters, validation,
the CRS engine, and the UI. Deliberately dependency-free (stdlib only) so
that parsers/exporters/validation can be unit-tested without requiring
pyproj/PySide6 to be installed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PointResult:
    name: str
    src_x: Optional[float]
    src_y: Optional[float]
    src_z: Optional[float]
    tgt_x: Optional[float] = None
    tgt_y: Optional[float] = None
    tgt_z: Optional[float] = None
    status: str = "PENDING"  # SUCCESS | FAILED | WARNING
    message: str = ""


@dataclass
class CRSInfo:
    auth_name: str
    code: str
    name: str
    crs_type: str

    @property
    def epsg(self) -> str:
        return f"{self.auth_name}:{self.code}"
