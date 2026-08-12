"""
KML / KMZ parser.

KMZ handling is fully automatic: the user only picks a .kmz file, and this
module transparently extracts the internal .kml, parses it, and returns
points. No manual "unzip first" step is exposed to the user.

Supports: Point, MultiGeometry (containing Points), Placemark name/altitude.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import List

from lxml import etree

from core.models import PointResult

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def _extract_kml_from_kmz(path: str) -> bytes:
    with zipfile.ZipFile(path, "r") as z:
        kml_names = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not kml_names:
            raise ValueError("No .kml file found inside the KMZ archive.")
        # Prefer doc.kml at root if present, else first .kml found
        preferred = [n for n in kml_names if Path(n).name.lower() == "doc.kml"]
        target = preferred[0] if preferred else kml_names[0]
        return z.read(target)


def _parse_coordinates_text(text: str) -> List[tuple]:
    """A <coordinates> element can contain one or many 'lon,lat[,alt]'
    tuples separated by whitespace (used by LineString/Polygon too, but we
    only care about Point geometries here)."""
    coords = []
    for token in text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            lon = float(parts[0])
            lat = float(parts[1])
            alt = float(parts[2]) if len(parts) >= 3 and parts[2] != "" else None
            coords.append((lon, lat, alt))
    return coords


def parse_kml_bytes(data: bytes) -> List[PointResult]:
    root = etree.fromstring(data)
    points: List[PointResult] = []

    for placemark in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        name_el = placemark.find("kml:name", KML_NS)
        name = name_el.text.strip() if name_el is not None and name_el.text else None

        # Direct Point
        point_els = placemark.findall(".//kml:Point/kml:coordinates", KML_NS)
        # Points nested inside MultiGeometry are also matched by the XPath above
        # since it searches any descendant Point.
        if not point_els:
            continue

        for idx, coord_el in enumerate(point_els):
            if coord_el.text is None:
                continue
            coords = _parse_coordinates_text(coord_el.text)
            for j, (lon, lat, alt) in enumerate(coords):
                label = name or f"PT-{len(points) + 1}"
                if len(point_els) > 1 or len(coords) > 1:
                    label = f"{label}-{idx + 1}" if len(point_els) > 1 else f"{label}"
                points.append(PointResult(label, lon, lat, alt))
    return points


def parse_kml_file(path: str) -> List[PointResult]:
    with open(path, "rb") as f:
        return parse_kml_bytes(f.read())


def parse_kmz_file(path: str) -> List[PointResult]:
    kml_bytes = _extract_kml_from_kmz(path)
    return parse_kml_bytes(kml_bytes)


def parse_kml_or_kmz(path: str) -> List[PointResult]:
    suffix = Path(path).suffix.lower()
    if suffix == ".kmz":
        return parse_kmz_file(path)
    if suffix == ".kml":
        return parse_kml_file(path)
    raise ValueError(f"Unsupported extension for KML/KMZ parser: {suffix}")
