"""Robust CAD coordinate extraction for MH - Coordinate.

DXF is read with ezdxf and, when the normal reader rejects a damaged drawing,
its recovery reader is attempted. Survey drawings commonly contain POINT,
LWPOLYLINE/POLYLINE vertices, Civil 3D block insertions, and 3DFACE vertices.
All coordinate-bearing entities are collected and exact duplicates are removed.
DWG remains supported through the optional ezdxf ODA File Converter bridge.
"""
from __future__ import annotations

from pathlib import Path

from core.models import PointResult


def _point(name: str, xyz) -> PointResult:
    values = list(xyz) + [0.0, 0.0, 0.0]
    return PointResult(name, float(values[0]), float(values[1]), float(values[2]))


def _extract_from_doc(doc) -> list[PointResult]:
    msp = doc.modelspace()
    result: list[PointResult] = []
    counter = 1

    # Native survey/CAD POINT entities.
    for entity in msp.query("POINT"):
        location = getattr(entity.dxf, "location", None)
        if location is not None:
            result.append(_point(f"POINT-{counter}", location))
            counter += 1

    # Lightweight polylines: every vertex is a coordinate point.
    for entity in msp.query("LWPOLYLINE"):
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        elevation = float(getattr(entity.dxf, "elevation", 0.0) or 0.0)
        try:
            vertices = entity.get_points("xy")
        except Exception:
            vertices = []
        for vertex in vertices:
            result.append(_point(f"{layer}-PL-{counter}", (vertex[0], vertex[1], elevation)))
            counter += 1

    # Classic 2D/3D POLYLINE vertices.
    for entity in msp.query("POLYLINE"):
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        try:
            vertices = entity.vertices
        except Exception:
            vertices = []
        for vertex in vertices:
            location = getattr(vertex.dxf, "location", None)
            if location is not None:
                result.append(_point(f"{layer}-PL-{counter}", location))
                counter += 1

    # Civil 3D/survey COGO points are frequently stored as INSERTs. Collect
    # them even when the drawing also contains polylines; duplicate coordinates
    # are removed below.
    for entity in msp.query("INSERT"):
        insertion = getattr(entity.dxf, "insert", None)
        if insertion is None:
            continue
        block = str(getattr(entity.dxf, "name", "BLOCK") or "BLOCK")
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        result.append(_point(f"{layer}-{block}-{counter}", insertion))
        counter += 1

    # 3DFACE vertices are also common in exported survey/CAD data.
    for entity in msp.query("3DFACE"):
        for attr in ("vtx0", "vtx1", "vtx2", "vtx3"):
            value = getattr(entity.dxf, attr, None)
            if value is not None:
                result.append(_point(f"FACE-{counter}", value))
                counter += 1

    # Remove exact coordinate duplicates caused by closed polylines, block
    # representations, or 3DFACE shared corners.
    unique: list[PointResult] = []
    seen: set[tuple[float, float, float]] = set()
    for point in result:
        key = (
            round(float(point.src_x), 9),
            round(float(point.src_y), 9),
            round(float(point.src_z or 0.0), 9),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique


def _dxf_points(path: str | Path) -> list[PointResult]:
    import ezdxf

    doc = None
    first_error = None
    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:
        first_error = exc

    # Recovery mode handles otherwise valid DXF files with damaged sections,
    # duplicate handles, or minor structural errors without hiding the failure.
    if doc is None:
        try:
            from ezdxf import recover
            doc, auditor = recover.readfile(str(path))
            if auditor.has_errors:
                # Keep the recovered document: coordinate extraction can still
                # be valid even when the drawing has non-coordinate audit errors.
                pass
        except Exception as recover_error:
            raise RuntimeError(
                "The DXF file could not be read or recovered. Verify that it is a valid DXF drawing and is not locked/corrupted."
            ) from recover_error

    points = _extract_from_doc(doc)
    if not points:
        detail = ""
        if first_error is not None:
            detail = f" Original reader error: {first_error}"
        raise RuntimeError(
            "The DXF drawing was recognized, but no coordinate-bearing POINT, polyline vertex, block insertion, or 3DFACE vertex was found in model space."
            + detail
        )
    return points


def _dwg_points(path: str | Path) -> list[PointResult]:
    try:
        from ezdxf.addons import odafc
    except Exception as exc:
        raise RuntimeError(
            "DWG requires the optional ODA File Converter bridge. Install/configure ODA File Converter, then retry the DWG file."
        ) from exc
    try:
        doc = odafc.readfile(str(path))
    except Exception as exc:
        raise RuntimeError(
            "The DWG could not be opened. Configure ODA File Converter for ezdxf ODA support, or export the drawing as DXF."
        ) from exc
    points = _extract_from_doc(doc)
    if not points:
        raise RuntimeError("The DWG was opened, but no coordinate-bearing CAD entities were found in model space.")
    return points


def extract_cad_points(path: str | Path) -> list[PointResult]:
    """Extract coordinate points from DXF/DWG or placemark points from KMZ/KML."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(str(file_path))
    suffix = file_path.suffix.casefold()
    if suffix == ".dxf":
        return _dxf_points(file_path)
    if suffix == ".dwg":
        return _dwg_points(file_path)
    if suffix in {".kmz", ".kml"}:
        from core.parsers import kml_parser
        points = kml_parser.parse_kmz_file(str(file_path)) if suffix == ".kmz" else kml_parser.parse_kml_file(str(file_path))
        return list(points or [])
    raise ValueError(f"Unsupported CAD file type: {suffix}")
