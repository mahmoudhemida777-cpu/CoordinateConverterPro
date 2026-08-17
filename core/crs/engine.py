"""Global CRS engine backed by PROJ/pyproj plus the project-local Amanah grid."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import pyproj
from pyproj import CRS, Transformer
from pyproj.database import get_authorities, query_crs_info
from pyproj.exceptions import CRSError
from pyproj.transformer import TransformerGroup

from core.models import CRSInfo, PointResult


class _AmanahLocalTransformer:
    """2D similarity adjustment fitted to the supplied Amanah control points."""

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
    def inverse_transform(cls, x: float, y: float) -> tuple[float, float]:
        det = cls._Q00 * cls._Q11 - cls._Q01 * cls._Q10
        dx, dy = x - cls._TX, y - cls._TY
        return (
            (cls._Q11 * dx - cls._Q10 * dy) / det,
            (-cls._Q01 * dx + cls._Q00 * dy) / det,
        )

    def __init__(self, use_inverse: bool = False, identity: bool = False) -> None:
        self.use_inverse = use_inverse
        self.identity = identity

    def transform(self, x: float, y: float, z: Optional[float] = None):
        if self.identity:
            tx, ty = x, y
        elif self.use_inverse:
            tx, ty = self.inverse_transform(x, y)
        else:
            tx, ty = self.forward(x, y)
        return (tx, ty, z) if z is not None else (tx, ty)


class _ComposedTransformer:
    def __init__(self, first, second) -> None:
        self.first, self.second = first, second

    def transform(self, x: float, y: float, z: Optional[float] = None):
        if z is None:
            a, b = self.first.transform(x, y)
            return self.second.transform(a, b)
        first_result = self.first.transform(x, y, z)
        if len(first_result) == 3:
            a, b, c = first_result
        else:
            a, b = first_result
            c = z
        try:
            return self.second.transform(a, b, c)
        except TypeError:
            return (*self.second.transform(a, b), c)


class CRSEngine:
    """CRS search and coordinate transformation service.

    All standard authorities are delegated to the installed PROJ database.
    The only project-specific identifier is the Amanah Riyadh local grid,
    which is explicitly separated from EPSG:20438 (Ain el Abd 1970 / UTM 38N).
    """

    AMANAH_RIYADH = "AMANAH-RYD-LOCAL-38N"
    AMANAH_NAME = "Amanah Riyadh Local Grid 38N"
    AMANAH_BASE = "EPSG:20438"

    _CRS_ALIASES = {
        "عين العبد": "EPSG:20438",
        "عين العبد 38": "EPSG:20438",
        "عين العبد 1970": "EPSG:20438",
        "عين العبد 1970 38": "EPSG:20438",
        "ain al abd": "EPSG:20438",
        "ain al abd 38": "EPSG:20438",
        "ain el abd": "EPSG:20438",
        "ain el abd 38": "EPSG:20438",
        "ain el abd 1970": "EPSG:20438",
        "ain el abd 1970 38": "EPSG:20438",
        "ain el abd / utm zone 38n": "EPSG:20438",
        "ain el abd utm zone 38n": "EPSG:20438",
        "ain el abd utm 38n": "EPSG:20438",
        "hayford 1909": "EPSG:20438",
        "hayford 1909 ain el abd": "EPSG:20438",
        "hayford 1909 ain al abd": "EPSG:20438",
        "international 1924": "EPSG:20438",
        "international 1924 ain el abd": "EPSG:20438",
        "international 1924 ain al abd": "EPSG:20438",
        "ain el abd 1970 hayford 1909": "EPSG:20438",
        "ain el abd 1970 international 1924": "EPSG:20438",
        "amanah riyadh": AMANAH_RIYADH,
        "amanah riyadh local grid": AMANAH_RIYADH,
        "amanah riyadh local grid 38n": AMANAH_RIYADH,
        "amanah riyadh 38n": AMANAH_RIYADH,
        "مرجع الأمانة": AMANAH_RIYADH,
        "مرجع امانة الرياض": AMANAH_RIYADH,
        "مرجع الأمانة المحلي": AMANAH_RIYADH,
        "مرجع أمانة الرياض المحلي": AMANAH_RIYADH,
    }

    _SEARCH_TYPES = (
        "GEOGRAPHIC_2D_CRS", "PROJECTED_CRS", "GEOGRAPHIC_3D_CRS",
        "GEOCENTRIC_CRS", "VERTICAL_CRS", "COMPOUND_CRS", "BOUND_CRS",
        "DERIVED_PROJECTED_CRS", "DERIVED_GEOGRAPHIC_2D_CRS",
        "DERIVED_GEOGRAPHIC_3D_CRS",
    )

    def __init__(self) -> None:
        self._transformer_cache: dict[tuple[str, str, str], object] = {}
        self._catalog_cache: Optional[List[CRSInfo]] = None
        self._operation_cache: dict[tuple[str, str], List[dict]] = {}

    @property
    def authorities(self) -> List[str]:
        return list(get_authorities())

    @staticmethod
    def _norm(value: str) -> str:
        return " ".join(str(value).strip().lower().split())

    @staticmethod
    def _split_authority_code(identifier: str) -> tuple[str, str]:
        auth, code = identifier.split(":", 1)
        return auth.upper(), code.strip()

    @staticmethod
    def _dedupe(items: List[CRSInfo]) -> List[CRSInfo]:
        seen = set()
        out = []
        for item in items:
            key = (item.auth_name.upper(), item.code)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def catalog(self, include_deprecated: bool = False) -> List[CRSInfo]:
        if self._catalog_cache is not None and not include_deprecated:
            return list(self._catalog_cache)
        results: List[CRSInfo] = []
        for authority in get_authorities():
            for crs_type in self._SEARCH_TYPES:
                try:
                    rows = query_crs_info(
                        auth_name=authority,
                        pj_types=[crs_type],
                        allow_deprecated=include_deprecated,
                    )
                    results.extend(CRSInfo(r.auth_name, r.code, r.name, crs_type) for r in rows)
                except Exception:
                    continue
        results = self._dedupe(results)
        if not include_deprecated:
            self._catalog_cache = results
        return list(results)

    def search(self, query: str, limit: int = 50) -> List[CRSInfo]:
        text = str(query or "").strip()
        if not text:
            return self.catalog()[:limit]
        key = self._norm(text)
        results: List[CRSInfo] = []

        alias = self._CRS_ALIASES.get(key)
        if alias == self.AMANAH_RIYADH:
            results.append(CRSInfo("MHLOCAL", self.AMANAH_RIYADH, self.AMANAH_NAME, "PROJECTED_CRS"))
        elif alias:
            try:
                crs = CRS.from_user_input(alias)
                auth, code = self._split_authority_code(alias)
                results.append(CRSInfo(auth, code, crs.name, crs.type_name))
            except CRSError:
                pass

        # Explicit authority identifiers are resolved directly, including
        # non-EPSG authorities such as ESRI, IGNF, CRS and custom authorities
        # supported by the installed PROJ database.
        if ":" in text:
            try:
                auth, code = self._split_authority_code(text)
                crs = CRS.from_user_input(f"{auth}:{code}")
                results.append(CRSInfo(auth, code, crs.name, crs.type_name))
                return self._dedupe(results)[:limit]
            except CRSError:
                pass

        if text.isdigit():
            for authority in get_authorities():
                for crs_type in self._SEARCH_TYPES:
                    try:
                        rows = query_crs_info(
                            auth_name=authority,
                            pj_types=[crs_type],
                            allow_deprecated=False,
                        )
                        for row in rows:
                            if row.code == text:
                                results.append(CRSInfo(row.auth_name, row.code, row.name, crs_type))
                    except Exception:
                        continue
            return self._dedupe(results)[:limit]

        if "amanah" in key or "الأمانة" in key or "امانة" in key:
            results.append(CRSInfo("MHLOCAL", self.AMANAH_RIYADH, self.AMANAH_NAME, "PROJECTED_CRS"))

        # Name/authority/identifier keyword search is deliberately backed by
        # the complete PROJ catalog rather than a hard-coded EPSG list.
        for item in self.catalog():
            haystack = f"{item.auth_name}:{item.code} {item.name}".lower()
            if key in haystack:
                results.append(item)
                if len(results) >= limit:
                    break
        return self._dedupe(results)[:limit]

    def _resolve_crs(self, identifier: str) -> CRS:
        original = str(identifier).strip()
        alias = self._CRS_ALIASES.get(self._norm(original))
        ident = alias or original
        if ident.upper() == self.AMANAH_RIYADH:
            raise CRSError(
                f"'{self.AMANAH_RIYADH}' is a project-local CRS; use the engine transformation API."
            )
        try:
            return CRS.from_user_input(ident)
        except Exception as exc:
            raise CRSError(f"Could not resolve CRS '{original}': {exc}") from exc

    @classmethod
    def _is_amanah(cls, identifier: str) -> bool:
        key = cls._norm(identifier)
        return cls._CRS_ALIASES.get(key, str(identifier).strip().upper()) == cls.AMANAH_RIYADH

    def get_crs_details(self, identifier: str) -> dict:
        if self._is_amanah(identifier):
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
        crs = self._resolve_crs(identifier)
        datum = crs.datum
        ellipsoid = datum.ellipsoid if datum else None
        units = crs.axis_info[0].unit_name if crs.axis_info else "unknown"
        return {
            "name": crs.name,
            "epsg": f"{crs.to_authority()[0]}:{crs.to_authority()[1]}" if crs.to_authority() else str(crs.srs),
            "datum": datum.name if datum else "N/A",
            "ellipsoid": ellipsoid.name if ellipsoid else "N/A",
            "projection": crs.coordinate_operation.method_name if crs.coordinate_operation else "Geographic (no projection)",
            "units": units,
            "is_projected": crs.is_projected,
            "is_geographic": crs.is_geographic,
        }

    def validate_point_domain(self, identifier: str, x: float, y: float) -> tuple[bool, str]:
        if self._is_amanah(identifier):
            return self.validate_point_domain(self.AMANAH_BASE, x, y)
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            return False, "Coordinate is not numeric."
        if x != x or y != y:
            return False, "Coordinate contains NaN."
        try:
            crs = self._resolve_crs(identifier)
            if crs.is_geographic:
                lon, lat = x, y
            else:
                inv = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
                lon, lat = inv.transform(x, y)
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                return False, f"Coordinate resolves outside Earth bounds ({lon:.6f}, {lat:.6f})."
            area = crs.area_of_use
            if area and not (area.west <= lon <= area.east and area.south <= lat <= area.north):
                return False, f"Coordinate is outside the selected CRS area of use ({lon:.6f}, {lat:.6f})."
        except Exception as exc:
            return False, f"Could not validate coordinate for CRS: {exc}"
        return True, ""

    def _custom_transformer(self, source: str, target: str):
        src_local = self._is_amanah(source)
        tgt_local = self._is_amanah(target)
        if src_local and tgt_local:
            # Critical invariant: local CRS -> itself is identity, not a second
            # application of the fitted similarity transform.
            return _AmanahLocalTransformer(identity=True)
        if src_local:
            base_to_target = Transformer.from_crs(
                self._resolve_crs(self.AMANAH_BASE), self._resolve_crs(target), always_xy=True
            )
            return _ComposedTransformer(_AmanahLocalTransformer(use_inverse=True), base_to_target)
        source_to_base = Transformer.from_crs(
            self._resolve_crs(source), self._resolve_crs(self.AMANAH_BASE), always_xy=True
        )
        return _ComposedTransformer(source_to_base, _AmanahLocalTransformer())

    def get_operations(self, source: str, target: str) -> List[dict]:
        key = (source, target)
        if key in self._operation_cache:
            return list(self._operation_cache[key])
        src_local = self._is_amanah(source)
        tgt_local = self._is_amanah(target)
        if src_local or tgt_local:
            if src_local and tgt_local:
                operations = [{
                    "id": 0,
                    "name": "Identity",
                    "description": "Amanah Riyadh Local Grid 38N → itself (no transformation)",
                    "accuracy": 0.0,
                }]
            else:
                direction = (
                    "Amanah Riyadh Local Grid 38N → Ain el Abd 1970 / UTM 38N"
                    if src_local else
                    "Ain el Abd 1970 / UTM 38N → Amanah Riyadh Local Grid 38N"
                )
                operations = [{
                    "id": 0,
                    "name": "Amanah Riyadh Local Grid 38N",
                    "description": f"{direction} (5-control-point 2D similarity fit)",
                    "accuracy": 0.003,
                }]
            self._operation_cache[key] = operations
            return list(operations)

        group = TransformerGroup(
            self._resolve_crs(source), self._resolve_crs(target),
            always_xy=True, allow_ballpark=False
        )
        operations = [
            {
                "id": idx,
                "name": transformer.name,
                "description": transformer.description,
                "accuracy": transformer.accuracy,
            }
            for idx, transformer in enumerate(group.transformers)
        ]
        self._operation_cache[key] = operations
        return list(operations)

    def get_transformer(self, source: str, target: str, operation: str = "auto"):
        key = (source, target, operation)
        if key in self._transformer_cache:
            return self._transformer_cache[key]
        if self._is_amanah(source) or self._is_amanah(target):
            if operation not in ("auto", "0"):
                raise CRSError(f"Unknown Amanah local transformation operation '{operation}'.")
            transformer = self._custom_transformer(source, target)
        else:
            group = TransformerGroup(
                self._resolve_crs(source), self._resolve_crs(target),
                always_xy=True, allow_ballpark=False
            )
            transformers = list(group.transformers)
            if not transformers:
                raise CRSError(f"No non-ballpark transformation available from {source} to {target}.")
            if operation == "auto":
                transformer = transformers[0]
            else:
                try:
                    transformer = transformers[int(operation)]
                except (ValueError, IndexError) as exc:
                    raise CRSError(f"Unknown transformation operation '{operation}'.") from exc
        self._transformer_cache[key] = transformer
        return transformer

    def get_selected_operation(self, source: str, target: str, operation: str = "auto") -> dict:
        operations = self.get_operations(source, target)
        if not operations:
            return {"id": None, "name": "N/A", "description": "No operation", "accuracy": None}
        if operation == "auto":
            return operations[0]
        try:
            return operations[int(operation)]
        except (ValueError, IndexError) as exc:
            raise CRSError(f"Unknown transformation operation '{operation}'.") from exc

    def transform_point(
        self, source: str, target: str, x: float, y: float,
        z: Optional[float] = None, operation: str = "auto"
    ) -> Tuple[float, float, Optional[float]]:
        transformer = self.get_transformer(source, target, operation)
        if z is not None:
            result = transformer.transform(x, y, z)
            if len(result) == 3:
                tx, ty, tz = result
            else:
                tx, ty = result
                tz = z
            return tx, ty, tz
        tx, ty = transformer.transform(x, y)
        return tx, ty, None

    def transform_points(
        self, source: str, target: str, points: Sequence[PointResult], operation: str = "auto"
    ) -> List[PointResult]:
        out: List[PointResult] = []
        for point in points:
            if point.src_x is None or point.src_y is None:
                out.append(PointResult(
                    point.name, point.src_x, point.src_y, point.src_z,
                    status="FAILED", message="Missing source coordinates"
                ))
                continue
            valid, reason = self.validate_point_domain(source, point.src_x, point.src_y)
            if not valid:
                out.append(PointResult(
                    point.name, point.src_x, point.src_y, point.src_z,
                    status="FAILED", message=f"Source CRS/coordinate mismatch: {reason}"
                ))
                continue
            try:
                tx, ty, tz = self.transform_point(
                    source, target, point.src_x, point.src_y, point.src_z, operation
                )
                if any(v != v for v in (tx, ty)):
                    raise ValueError("Transformation returned NaN (point likely outside CRS domain)")
                target_valid, target_reason = self.validate_point_domain(target, tx, ty)
                if not target_valid:
                    raise ValueError(f"Target CRS validation failed: {target_reason}")
                out.append(PointResult(
                    point.name, point.src_x, point.src_y, point.src_z,
                    tx, ty, tz, "SUCCESS", ""
                ))
            except Exception as exc:
                out.append(PointResult(
                    point.name, point.src_x, point.src_y, point.src_z,
                    status="FAILED", message=str(exc)
                ))
        return out

    def proj_version(self) -> str:
        return pyproj.proj_version_str
