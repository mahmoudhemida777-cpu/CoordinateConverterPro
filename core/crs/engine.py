"""Global CRS engine backed by PROJ with coordinate-domain validation."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from core.models import CRSInfo, PointResult
import pyproj
from pyproj import CRS, Transformer
from pyproj.database import get_authorities, query_crs_info
from pyproj.exceptions import CRSError


class CRSEngine:
    _CRS_ALIASES = {
        "عين العبد": "EPSG:20438", "عين العبد 38": "EPSG:20438", "عين العبد 1970": "EPSG:20438",
        "عين العبد 1970 38": "EPSG:20438", "ain al abd": "EPSG:20438", "ain al abd 38": "EPSG:20438",
        "ain el abd": "EPSG:20438", "ain el abd 38": "EPSG:20438", "ain el abd 1970": "EPSG:20438",
        "ain el abd 1970 38": "EPSG:20438", "ain el abd / utm zone 38n": "EPSG:20438",
        "ain el abd utm zone 38n": "EPSG:20438", "ain el abd utm 38n": "EPSG:20438",
        "hayford 1909": "EPSG:20438", "hayford 1909 ain el abd": "EPSG:20438",
        "hayford 1909 ain al abd": "EPSG:20438", "international 1924": "EPSG:20438",
        "international 1924 ain el abd": "EPSG:20438", "international 1924 ain al abd": "EPSG:20438",
        "ain el abd 1970 hayford 1909": "EPSG:20438", "ain el abd 1970 international 1924": "EPSG:20438",
    }
    _SEARCH_TYPES = (
        "GEOGRAPHIC_2D_CRS", "PROJECTED_CRS", "GEOGRAPHIC_3D_CRS", "GEOCENTRIC_CRS",
        "VERTICAL_CRS", "COMPOUND_CRS", "BOUND_CRS", "DERIVED_PROJECTED_CRS",
        "DERIVED_GEOGRAPHIC_2D_CRS", "DERIVED_GEOGRAPHIC_3D_CRS",
    )

    def __init__(self) -> None:
        self._transformer_cache: dict[tuple[str, str], Transformer] = {}
        self._catalog_cache: Optional[List[CRSInfo]] = None

    @property
    def authorities(self) -> List[str]:
        return list(get_authorities())

    def catalog(self, include_deprecated: bool = False) -> List[CRSInfo]:
        if self._catalog_cache is not None and not include_deprecated:
            return list(self._catalog_cache)
        results: List[CRSInfo] = []
        for auth in get_authorities():
            for crs_type in self._SEARCH_TYPES:
                try:
                    for entry in query_crs_info(auth_name=auth, pj_types=[crs_type], allow_deprecated=include_deprecated):
                        results.append(CRSInfo(entry.auth_name, entry.code, entry.name, crs_type))
                except Exception:
                    continue
        results = self._dedupe(results)
        if not include_deprecated:
            self._catalog_cache = results
        return list(results)

    def search(self, query: str, limit: int = 50) -> List[CRSInfo]:
        query_norm = query.strip()
        if not query_norm:
            return self.catalog()[:limit]
        key = " ".join(query_norm.lower().split())
        results: List[CRSInfo] = []
        alias = self._CRS_ALIASES.get(key)
        if alias:
            try:
                crs = CRS.from_user_input(alias)
                auth, code = self._split_authority_code(alias)
                results.append(CRSInfo(auth, code, crs.name, crs.type_name))
            except Exception:
                pass
        authority_code = query_norm.upper()
        if ":" in authority_code:
            auth, code = authority_code.split(":", 1)
            try:
                crs = CRS.from_user_input(f"{auth}:{code}")
                results.append(CRSInfo(auth, code, crs.name, crs.type_name))
            except Exception:
                pass
        elif query_norm.isdigit():
            for item in self.catalog():
                if item.code == query_norm:
                    results.append(item)
                    if len(results) >= limit:
                        return self._dedupe(results)[:limit]
        needle = key
        for item in self.catalog():
            if needle in item.name.lower() or needle in item.epsg.lower():
                results.append(item)
                if len(results) >= limit:
                    return self._dedupe(results)[:limit]
        return self._dedupe(results)[:limit]

    @staticmethod
    def _split_authority_code(identifier: str) -> tuple[str, str]:
        auth, code = identifier.split(":", 1)
        return auth.upper(), code

    @staticmethod
    def _dedupe(items: List[CRSInfo]) -> List[CRSInfo]:
        seen = set(); out = []
        for it in items:
            key = (it.auth_name.upper(), it.code)
            if key not in seen:
                seen.add(key); out.append(it)
        return out

    def _resolve_crs(self, identifier: str) -> CRS:
        ident = identifier.strip()
        alias = self._CRS_ALIASES.get(" ".join(ident.lower().split()))
        if alias:
            ident = alias
        try:
            return CRS.from_user_input(ident)
        except Exception as exc:
            raise CRSError(f"Could not resolve CRS '{identifier}': {exc}") from exc

    def get_crs_details(self, epsg_or_code: str) -> dict:
        crs = self._resolve_crs(epsg_or_code)
        datum = crs.datum; ellipsoid = datum.ellipsoid if datum else None
        axis_units = crs.axis_info[0].unit_name if crs.axis_info else "unknown"
        return {"name": crs.name, "epsg": f"EPSG:{crs.to_epsg()}" if crs.to_epsg() else str(crs.srs),
                "datum": datum.name if datum else "N/A", "ellipsoid": ellipsoid.name if ellipsoid else "N/A",
                "projection": crs.coordinate_operation.method_name if crs.coordinate_operation else "Geographic (no projection)",
                "units": axis_units, "is_projected": crs.is_projected, "is_geographic": crs.is_geographic}

    def validate_point_domain(self, crs_identifier: str, x: float, y: float) -> tuple[bool, str]:
        """Check that a coordinate is plausible for the selected CRS area of use."""
        crs = self._resolve_crs(crs_identifier)
        if not (float(x) == float(x) and float(y) == float(y)):
            return False, "Coordinate contains NaN."
        try:
            if crs.is_geographic:
                lon, lat = float(x), float(y)
            else:
                inv = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
                lon, lat = inv.transform(float(x), float(y))
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                return False, f"Coordinate resolves outside Earth bounds ({lon:.6f}, {lat:.6f})."
            area = crs.area_of_use
            if area and not (area.west <= lon <= area.east and area.south <= lat <= area.north):
                return False, f"Coordinate is outside the selected CRS area of use ({lon:.6f}, {lat:.6f})."
        except Exception as exc:
            return False, f"Could not validate coordinate for CRS: {exc}"
        return True, ""

    def get_transformer(self, source: str, target: str) -> Transformer:
        key = (source, target)
        if key not in self._transformer_cache:
            self._transformer_cache[key] = Transformer.from_crs(self._resolve_crs(source), self._resolve_crs(target), always_xy=True)
        return self._transformer_cache[key]

    def transform_point(self, source: str, target: str, x: float, y: float, z: Optional[float] = None) -> Tuple[float, float, Optional[float]]:
        transformer = self.get_transformer(source, target)
        if z is not None:
            tx, ty, tz = transformer.transform(x, y, z); return tx, ty, tz
        tx, ty = transformer.transform(x, y); return tx, ty, None

    def transform_points(self, source: str, target: str, points: Sequence[PointResult]) -> List[PointResult]:
        out: List[PointResult] = []
        for p in points:
            if p.src_x is None or p.src_y is None:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message="Missing source coordinates")); continue
            valid, reason = self.validate_point_domain(source, p.src_x, p.src_y)
            if not valid:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message=f"Source CRS/coordinate mismatch: {reason}")); continue
            try:
                tx, ty, tz = self.transform_point(source, target, p.src_x, p.src_y, p.src_z)
                if any(v != v for v in (tx, ty)):
                    raise ValueError("Transformation returned NaN (point likely outside CRS domain)")
                target_valid, target_reason = self.validate_point_domain(target, tx, ty)
                if not target_valid:
                    raise ValueError(f"Target CRS validation failed: {target_reason}")
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, tx, ty, tz, "SUCCESS", ""))
            except Exception as exc:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message=str(exc)))
        return out

    def proj_version(self) -> str:
        return pyproj.proj_version_str
