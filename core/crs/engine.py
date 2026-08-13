"""
CRS Engine — Coordinate Converter Pro
======================================
Wraps pyproj/PROJ to perform Any-CRS -> Any-CRS transformations, and to
search the EPSG database bundled with pyproj/PROJ for CRS discovery.

IMPORTANT: This module performs NO manual/hard-coded coordinate math.
Every transformation is computed by PROJ via pyproj.Transformer.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from core.models import CRSInfo, PointResult

import pyproj
from pyproj import CRS, Transformer
from pyproj.database import query_crs_info
from pyproj.exceptions import CRSError


class CRSEngine:
    """Any CRS -> Any CRS transformation engine backed by PROJ."""

    # Common engineering/survey aliases that should resolve even when the
    # user searches in Arabic or uses a common spelling variant.
    _CRS_ALIASES = {
        "عين العبد": "20438",
        "عين العبد 38": "20438",
        "عين العبد 1970": "20438",
        "عين العبد 1970 38": "20438",
        "ain al abd": "20438",
        "ain al abd 38": "20438",
        "ain el abd 38": "20438",
        "ain el abd 1970": "20438",
        "ain el abd 1970 38": "20438",
        "ain el abd / utm zone 38n": "20438",
        "ain el abd utm zone 38n": "20438",
        "ain el abd utm 38n": "20438",
    }

    def __init__(self) -> None:
        self._transformer_cache: dict[tuple[str, str], Transformer] = {}

    def search(self, query: str, limit: int = 50) -> List[CRSInfo]:
        """Search the bundled EPSG/PROJ database by name, EPSG code, or alias."""
        query_norm = query.strip()
        results: List[CRSInfo] = []
        alias_key = " ".join(query_norm.lower().split())

        # Explicit aliases for Ain el Abd / UTM zone 38N (EPSG:20438).
        if alias_key in self._CRS_ALIASES:
            try:
                crs = CRS.from_epsg(int(self._CRS_ALIASES[alias_key]))
                results.append(CRSInfo("EPSG", "20438", crs.name, "PROJECTED_CRS"))
            except CRSError:
                pass

        code_candidate = query_norm.upper().replace("EPSG:", "").strip()
        if code_candidate.isdigit():
            try:
                crs = CRS.from_epsg(int(code_candidate))
                results.append(CRSInfo("EPSG", code_candidate, crs.name, crs.type_name))
            except CRSError:
                pass

        # Name-based search across common CRS categories.
        for auth in ("EPSG",):
            for crs_type in (
                "GEOGRAPHIC_2D_CRS",
                "PROJECTED_CRS",
                "GEOGRAPHIC_3D_CRS",
                "COMPOUND_CRS",
            ):
                try:
                    for entry in query_crs_info(auth_name=auth, pj_types=[crs_type]):
                        if query_norm.lower() in entry.name.lower() or code_candidate == entry.code:
                            results.append(CRSInfo(entry.auth_name, entry.code, entry.name, crs_type))
                            if len(results) >= limit:
                                return self._dedupe(results)
                except Exception:
                    continue
        return self._dedupe(results)

    @staticmethod
    def _dedupe(items: List[CRSInfo]) -> List[CRSInfo]:
        seen = set()
        out = []
        for it in items:
            key = (it.auth_name, it.code)
            if key not in seen:
                seen.add(key)
                out.append(it)
        return out

    def get_crs_details(self, epsg_or_code: str) -> dict:
        crs = self._resolve_crs(epsg_or_code)
        datum = crs.datum
        ellipsoid = datum.ellipsoid if datum else None
        axis_units = crs.axis_info[0].unit_name if crs.axis_info else "unknown"
        return {
            "name": crs.name,
            "epsg": f"EPSG:{crs.to_epsg()}" if crs.to_epsg() else str(crs.srs),
            "datum": datum.name if datum else "N/A",
            "ellipsoid": ellipsoid.name if ellipsoid else "N/A",
            "projection": crs.coordinate_operation.method_name if crs.coordinate_operation else "Geographic (no projection)",
            "units": axis_units,
            "is_projected": crs.is_projected,
            "is_geographic": crs.is_geographic,
        }

    def _resolve_crs(self, identifier: str) -> CRS:
        ident = identifier.strip()
        try:
            if ident.upper().startswith("EPSG:"):
                return CRS.from_epsg(int(ident.split(":", 1)[1]))
            if ident.isdigit():
                return CRS.from_epsg(int(ident))
            return CRS.from_user_input(ident)
        except Exception as exc:
            raise CRSError(f"Could not resolve CRS '{identifier}': {exc}") from exc

    def get_transformer(self, source: str, target: str) -> Transformer:
        key = (source, target)
        if key not in self._transformer_cache:
            src_crs = self._resolve_crs(source)
            tgt_crs = self._resolve_crs(target)
            self._transformer_cache[key] = Transformer.from_crs(src_crs, tgt_crs, always_xy=True)
        return self._transformer_cache[key]

    def transform_point(
        self,
        source: str,
        target: str,
        x: float,
        y: float,
        z: Optional[float] = None,
    ) -> Tuple[float, float, Optional[float]]:
        transformer = self.get_transformer(source, target)
        if z is not None:
            tx, ty, tz = transformer.transform(x, y, z)
            return tx, ty, tz
        tx, ty = transformer.transform(x, y)
        return tx, ty, None

    def transform_points(
        self,
        source: str,
        target: str,
        points: Sequence[PointResult],
    ) -> List[PointResult]:
        out: List[PointResult] = []
        for p in points:
            if p.src_x is None or p.src_y is None:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message="Missing source coordinates"))
                continue
            try:
                tx, ty, tz = self.transform_point(source, target, p.src_x, p.src_y, p.src_z)
                status = "SUCCESS"
                message = ""
                if tx != tx or ty != ty:
                    status, message = "FAILED", "Transformation returned NaN (point likely outside CRS domain)"
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, tx, ty, tz, status, message))
            except Exception as exc:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message=str(exc)))
        return out

    def proj_version(self) -> str:
        return pyproj.proj_version_str
