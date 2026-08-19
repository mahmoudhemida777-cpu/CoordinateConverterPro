"""CAD/KMZ point extraction for MH-Coordinate.

DXF is read directly with ezdxf. DWG is intentionally optional: ezdxf does not
read DWG natively, so when the ODA File Converter bridge is installed the
existing ezdxf ODA add-on can be used; otherwise a clear actionable error is
returned instead of silently producing incomplete coordinates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.models import PointResult


def _point(name: str, xyz) -> PointResult:
    values = list(xyz) + [0.0, 0.0, 0.0]
    return PointResult(name, float(values[0]), float(values[1]), float(values[2]))


def _dxf_points(path: str | Path) -> list[PointResult]:
    import ezdxf

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    result: list[PointResult] = []
    counter = 1

    for entity in msp.query("POINT"):
        result.append(_point(f"POINT-{counter}", entity.dxf.location))
        counter += 1

    for entity in msp.query("LWPOLYLINE"):
        layer = getattr(entity.dxf, "layer", "0")
        elevation = float(getattr(entity.dxf, "elevation", 0.0) or 0.0)
        for vertex in entity.get_points("xy"):
            result.append(_point(f"{layer}-PL-{counter}", (vertex[0], vertex[1], elevation)))
            counter += 1

    for entity in msp.query("POLYLINE"):
        layer = getattr(entity.dxf, "layer", "0")
        for vertex in entity.vertices:
            result.append(_point(f"{layer}-PL-{counter}", vertex.dxf.location))
            counter += 1

    return result


def _dwg_points(path: str | Path) -> list[PointResult]:
    try:
        from ezdxf.addons import odafc
    except Exception as exc:
        raise RuntimeError(
            "DWG requires the optional ODA File Converter bridge. "
            "Install/configure ODA File Converter, then retry the DWG file."
        ) from exc
    try:
        doc = odafc.readfile(str(path))
    except Exception as exc:
        raise RuntimeError(
            "The DWG could not be opened. Configure ODA File Converter "
            "for ezdxf ODA support, or export the drawing as DXF."
        ) from exc
    # ODA returns an ezdxf document; reuse the same entity extraction logic by
    # walking the modelspace without writing an intermediate file.
    msp = doc.modelspace()
    result: list[PointResult] = []
    counter = 1
    for entity in msp.query("POINT"):
        result.append(_point(f"POINT-{counter}", entity.dxf.location)); counter += 1
    for entity in msp.query("LWPOLYLINE"):
        layer = getattr(entity.dxf, "layer", "0")
        elevation = float(getattr(entity.dxf, "elevation", 0.0) or 0.0)
        for vertex in entity.get_points("xy"):
            result.append(_point(f"{layer}-PL-{counter}", (vertex[0], vertex[1], elevation))); counter += 1
    for entity in msp.query("POLYLINE"):
        layer = getattr(entity.dxf, "layer", "0")
        for vertex in entity.vertices:
            result.append(_point(f"{layer}-PL-{counter}", vertex.dxf.location)); counter += 1
    return result


def extract_cad_points(path: str | Path) -> list[PointResult]:
    """Extract POINT and polyline vertices from DXF/DWG or placemark points from KMZ/KML."""
    file_path = Path(path)
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
