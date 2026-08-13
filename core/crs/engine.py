"""Global CRS engine backed by PROJ plus the project-specific Amanah Riyadh local grid."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from core.models import CRSInfo, PointResult
import pyproj
from pyproj import CRS, Transformer
from pyproj.database import get_authorities, query_crs_info
from pyproj.exceptions import CRSError
from pyproj.transformer import TransformerGroup


class _AmanahLocalTransformer:
    """2D similarity transform fitted to the five supplied Amanah control points.

    Base CRS: Ain el Abd 1970 / UTM zone 38N (EPSG:20438).
    Target: Amanah Riyadh Local Grid 38N (project/local CRS, no EPSG code).
    """
    # B = t + A @ Q for row-vector coordinates [E, N].
    _Q00 = 1.0000009853195706
    _Q01 = 0.0000003768526400
    _Q10 = -0.0000003768526410
    _Q11 = 1.0000009853195706
    _TX = 3.16010054
    _TY = -1.01024623

    @classmethod
    def forward(cls, x: float, y: float) -> tuple[float, float]:
        return (
            cls._TX + cls._Q00 * x + cls._Q10 * y,
            cls._TY + cls._Q01 * x + cls._Q11 * y,
        )

    @classmethod
    def inverse(cls, x: float, y: float) -> tuple[float, float]:
        det = cls._Q00 * cls._Q11 - cls._Q01 * cls._Q10
        dx = x - cls._TX
        dy = y - cls._TY
        return (
            (cls._Q11 * dx - cls._Q10 * dy) / det,
            (-cls._Q01 * dx + cls._Q00 * dy) / det,
        )

    def __init__(self, inverse: bool = False) -> None:
        self.inverse = inverse

    def transform(self, x: float, y: float, z: Optional[float] = None):
        if self.inverse:
            tx, ty = self.inverse(x, y)
        else:
            tx, ty = self.forward(x, y)
        return (tx, ty, z) if z is not None else (tx, ty)


class _ComposedTransformer:
    def __init__(self, first, second) -> None:
        self.first = first
        self.second = second

    def transform(self, x: float, y: float, z: Optional[float] = None):
        if z is None:
            a, b = self.first.transform(x, y)
            return self.second.transform(a, b)
        a, b, c = self.first.transform(x, y, z)
        try:
            return self.second.transform(a, b, c)
        except TypeError:
            return (*self.second.transform(a, b), c)


class CRSEngine:
    AMANAH_RIYADH = "AMANAH-RYD-LOCAL-38N"
    AMANAH_NAME = "Amanah Riyadh Local Grid 38N"
    AMANAH_BASE = "EPSG:20438"

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
        "amanah riyadh": AMANAH_RIYADH, "amanah riyadh local grid": AMANAH_RIYADH,
        "amanah riyadh local grid 38n": AMANAH_RIYADH, "amanah riyadh 38n": AMANAH_RIYADH,
        "مرجع الأمانة": AMANAH_RIYADH, "مرجع امانة الرياض": AMANAH_RIYADH,
        "مرجع الأمانة المحلي": AMANAH_RIYADH, "مرجع أمانة الرياض المحلي": AMANAH_RIYADH,
    }
    _SEARCH_TYPES = (
        "GEOGRAPHIC_2D_CRS", "PROJECTED_CRS", "GEOGRAPHIC_3D_CRS", "GEOCENTRIC_CRS",
        "VERTICAL_CRS", "COMPOUND_CRS", "BOUND_CRS", "DERIVED_PROJECTED_CRS",
        "DERIVED_GEOGRAPHIC_2D_CRS", "DERIVED_GEOGRAPHIC_3D_CRS",
    )

    def __init__(self) -> None:
        self._transformer_cache: dict[tuple[str, str, str], object] = {}
        self._catalog_cache: Optional[List[CRSInfo]] = None
        self._operation_cache: dict[tuple[str, str], List[dict]] = {}

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
        if alias == self.AMANAH_RIYADH:
            results.append(CRSInfo("MHLOCAL", "AMANAH-RYD-LOCAL-38N", self.AMANAH_NAME, "PROJECTED_CRS"))
        elif alias:
            try:
                crs = CRS.from_user_input(alias)
                auth, code = self._split_authority_code(alias)
                results.append(CRSInfo(auth, code, crs.name, crs.type_name))
            except Exception:
                pass
        authority_code = query_norm.upper()
        if ":" in authority_code and authority_code != self.AMANAH_RIYADH:
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
        if "amanah" in needle or "الأمانة" in needle or "امانة" in needle:
            results.append(CRSInfo("MHLOCAL", "AMANAH-RYD-LOCAL-38N", self.AMANAH_NAME, "PROJECTED_CRS"))
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
        if ident.upper() == self.AMANAH_RIYADH:
            raise CRSError(f"'{self.AMANAH_RIYADH}' is a project-local CRS; use the engine transformation API.")
        try:
            return CRS.from_user_input(ident)
        except Exception as exc:
            raise CRSError(f"Could not resolve CRS '{identifier}': {exc}") from exc

    @classmethod
    def _is_amanah(cls, identifier: str) -> bool:
        key = " ".join(identifier.strip().lower().split())
        return cls._CRS_ALIASES.get(key, identifier.strip().upper()) == cls.AMANAH_RIYADH

    def get_crs_details(self, epsg_or_code: str) -> dict:
        if self._is_amanah(epsg_or_code):
            return {
                "name": self.AMANAH_NAME,
                "epsg": self.AMANAH_RIYADH,
                "datum": "Ain el Abd 1970 + project local adjustment",
                "ellipsoid": "International 1924 (Hayford 1909)",
                "projection": "UTM Zone 38N + fitted 2D similarity adjustment",
                "units": "metre",
                "is_projected": True,
                "is_geographic": False,
            }
        crs = self._resolve_crs(epsg_or_code)
        datum = crs.datum; ellipsoid = datum.ellipsoid if datum else None
        axis_units = crs.axis_info[0].unit_name if crs.axis_info else "unknown"
        return {"name": crs.name, "epsg": f"EPSG:{crs.to_epsg()}" if crs.to_epsg() else str(crs.srs),
                "datum": datum.name if datum else "N/A", "ellipsoid": ellipsoid.name if ellipsoid else "N/A",
                "projection": crs.coordinate_operation.method_name if crs.coordinate_operation else "Geographic (no projection)",
                "units": axis_units, "is_projected": crs.is_projected, "is_geographic": crs.is_geographic}

    def validate_point_domain(self, crs_identifier: str, x: float, y: float) -> tuple[bool, str]:
        if self._is_amanah(crs_identifier):
            return self.validate_point_domain(self.AMANAH_BASE, x, y)
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

    def _custom_transformer(self, source: str, target: str):
        src_a = self._is_amanah(source); tgt_a = self._is_amanah(target)
        if src_a and tgt_a:
            return _AmanahLocalTransformer(False)
        if src_a:
            base_to_target = Transformer.from_crs(self._resolve_crs(self.AMANAH_BASE), self._resolve_crs(target), always_xy=True)
            return _ComposedTransformer(_AmanahLocalTransformer(True), base_to_target)
        target_base = Transformer.from_crs(self._resolve_crs(source), self._resolve_crs(self.AMANAH_BASE), always_xy=True)
        if tgt_a:
            return _ComposedTransformer(target_base, _AmanahLocalTransformer(False))
        raise CRSError("Internal custom CRS routing error")

    def get_operations(self, source: str, target: str) -> List[dict]:
        key = (source, target)
        if key in self._operation_cache:
            return list(self._operation_cache[key])
        if self._is_amanah(source) or self._is_amanah(target):
            operations = [{
                "id": 0,
                "name": "Amanah Riyadh Local Grid 38N",
                "description": "Ain el Abd 1970 / UTM 38N → Amanah Riyadh Local Grid 38N (5-control-point 2D similarity fit)",
                "accuracy": 0.003,
            }]
            self._operation_cache[key] = operations
            return list(operations)
        group = TransformerGroup(self._resolve_crs(source), self._resolve_crs(target), always_xy=True, allow_ballpark=False)
        operations = []
        for idx, transformer in enumerate(group.transformers):
            operations.append({"id": idx, "name": transformer.name, "description": transformer.description, "accuracy": transformer.accuracy})
        self._operation_cache[key] = operations
        return list(operations)

    def get_transformer(self, source: str, target: str, operation: str = "auto"):
        key = (source, target, operation)
        if key not in self._transformer_cache:
            if self._is_amanah(source) or self._is_amanah(target):
                if operation not in ("auto", "0"):
                    raise CRSError(f"Unknown Amanah local transformation operation '{operation}'.")
                self._transformer_cache[key] = self._custom_transformer(source, target)
            else:
                group = TransformerGroup(self._resolve_crs(source), self._resolve_crs(target), always_xy=True, allow_ballpark=False)
                transformers = list(group.transformers)
                if not transformers:
                    raise CRSError(f"No non-ballpark transformation available from {source} to {target}.")
                if operation == "auto":
                    selected = transformers[0]
                else:
                    try:
                        selected = transformers[int(operation)]
                    except (ValueError, IndexError):
                        raise CRSError(f"Unknown transformation operation '{operation}'.")
                self._transformer_cache[key] = selected
        return self._transformer_cache[key]

    def get_selected_operation(self, source: str, target: str, operation: str = "auto") -> dict:
        operations = self.get_operations(source, target)
        if not operations:
            return {"id": None, "name": "N/A", "description": "No operation", "accuracy": None}
        if operation == "auto":
            return operations[0]
        try:
            return operations[int(operation)]
        except (ValueError, IndexError):
            raise CRSError(f"Unknown transformation operation '{operation}'.")

    def transform_point(self, source: str, target: str, x: float, y: float, z: Optional[float] = None, operation: str = "auto") -> Tuple[float, float, Optional[float]]:
        transformer = self.get_transformer(source, target, operation)
        if z is not None:
            tx, ty, tz = transformer.transform(x, y, z); return tx, ty, tz
        result = transformer.transform(x, y)
        return result[0], result[1], None

    def transform_points(self, source: str, target: str, points: Sequence[PointResult], operation: str = "auto") -> List[PointResult]:
        out: List[PointResult] = []
        for p in points:
            if p.src_x is None or p.src_y is None:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message="Missing source coordinates")); continue
            valid, reason = self.validate_point_domain(source, p.src_x, p.src_y)
            if not valid:
                out.append(PointResult(p.name, p.src_x, p.src_y, p.src_z, status="FAILED", message=f"Source CRS/coordinate mismatch: {reason}")); continue
            try:
                tx, ty, tz = self.transform_point(source, target, p.src_x, p.src_y, p.src_z, operation)
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
