"""CAD/KMZ point extraction for MH - Coordinate.

DXF is read directly with ezdxf. Survey drawings often store points as POINT
entities, polyline vertices, or INSERT/block insertion points, so the importer
uses a layered extraction strategy and reports a useful error when a drawing
contains no coordinate-bearing entities. DWG remains supported through the
optional ezdxf ODA File Converter bridge.
"""
from __future__ import annotations

from pathlib import Path

from core.models import PointResult


def _point(name: str, xyz) -> PointResult:
    values = list(xyz) + [0.0, 0.0, 0.0]
    return PointResult(name, float(values[0]), float(values[1]), float(values[2]))


def _entity_name(entity, fallback: str) -> str:
    layer = str(getattr(entity.dxf, "layer", "0") or "0")
    if entity.dxftype() == "INSERT":
        block = str(getattr(entity.dxf, "name", "BLOCK") or "BLOCK")
        # Prefer a useful block/point identifier while keeping names unique.
        return f"{block}-{fallback}"
    return f"{layer}-{fallback}"


def _extract_from_doc(doc) -> list[PointResult]:
    msp = doc.modelspace()
    result: list[PointResult] = []
    counter = 1

    # Native survey POINT entities.
    for entity in msp.query("POINT"):
        result.append(_point(f"POINT-{counter}", entity.dxf.location))
        counter += 1

    # Lightweight and classic polylines: every vertex is a coordinate point.
    for entity in msp.query("LWPOLYLINE"):
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        elevation = float(getattr(entity.dxf, "elevation", 0.0) or 0.0)
        for vertex in entity.get_points("xy"):
            result.append(_point(f"{layer}-PL-{counter}", (vertex[0], vertex[1], elevation)))
            counter += 1

    for entity in msp.query("POLYLINE"):
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        for vertex in entity.vertices:
            result.append(_point(f"{layer}-PL-{counter}", vertex.dxf.location))
            counter += 1

    # Many Civil 3D/survey exports represent COGO points as blocks. Only use
    # INSERTs as a fallback when no POINT/polyline coordinates were found, so
    # ordinary drawings do not suddenly receive duplicate block coordinates.
    if not result:
        for entity in msp.query("INSERT"):
            insertion = getattr(entity.dxf, "insert", None)
            if insertion is None:
                continue
            result.append(_point(_entity_name(entity, f"INS-{counter}"), insertion))
            counter += 1

    # 3DFACE is another common way to carry survey vertices in exported CAD.
    if not result:
        for entity in msp.query("3DFACE"):
            for attr in ("vtx0", "vtx1", "vtx2", "vtx3"):
                value = getattr(entity.dxf, attr, None)
                if value is not None:
                    result.append(_point(f"FACE-{counter}", value))
                    counter += 1

    # Remove exact duplicate coordinates introduced by closed polylines/faces.
    unique: list[PointResult] = []
    seen: set[tuple[float, float, float]] = set()
    for point in result:
        key = (round(float(point.src_x), 9), round(float(point.src_y), 9), round(float(point.src_z or 0.0), 9))
        if key in seen:
            continue
        seen.add(key)
        unique.append(point)
    return unique


def _dxf_points(path: str | Path) -> list[PointResult]:
    import ezdxf

    try:
        doc = ezdxf.readfile(str(path))
    except Exception as exc:
        raise RuntimeError(
            "The DXF file could not be read. Verify that it is a valid DXF drawing and is not locked/corrupted."
        ) from exc
    points = _extract_from_doc(doc)
    if not points:
        raise RuntimeError(
            "The DXF drawing was recognized, but no POINT/polyline/block coordinates were found in model space."
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
