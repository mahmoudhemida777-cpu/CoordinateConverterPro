import zipfile

import pytest

from core.parsers.kml_parser import parse_kml_bytes, parse_kml_file, parse_kmz_file

SAMPLE_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <Placemark>
    <name>Riyadh Tower</name>
    <Point><coordinates>46.84550218,24.77373641,650.5</coordinates></Point>
  </Placemark>
  <Placemark>
    <name>Corner A</name>
    <MultiGeometry>
      <Point><coordinates>46.85,24.78,0</coordinates></Point>
    </MultiGeometry>
  </Placemark>
  <Placemark>
    <name>No Geometry Here</name>
  </Placemark>
</Document>
</kml>
"""


def test_parse_kml_bytes_extracts_points():
    points = parse_kml_bytes(SAMPLE_KML)
    assert len(points) == 2
    assert points[0].name == "Riyadh Tower"
    assert points[0].src_x == pytest.approx(46.84550218)
    assert points[0].src_y == pytest.approx(24.77373641)
    assert points[0].src_z == pytest.approx(650.5)


def test_multigeometry_point_extracted():
    points = parse_kml_bytes(SAMPLE_KML)
    assert points[1].name == "Corner A"
    assert points[1].src_x == pytest.approx(46.85)


def test_placemark_without_geometry_is_skipped_not_crashed():
    points = parse_kml_bytes(SAMPLE_KML)
    names = [p.name for p in points]
    assert "No Geometry Here" not in names


def test_parse_kml_file(tmp_path):
    path = tmp_path / "test.kml"
    path.write_bytes(SAMPLE_KML)
    points = parse_kml_file(str(path))
    assert len(points) == 2


def test_kmz_auto_extraction(tmp_path):
    kmz_path = tmp_path / "test.kmz"
    with zipfile.ZipFile(kmz_path, "w") as z:
        z.writestr("doc.kml", SAMPLE_KML)
    points = parse_kmz_file(str(kmz_path))
    assert len(points) == 2
    assert points[0].name == "Riyadh Tower"


def test_kmz_with_no_kml_raises_clear_error(tmp_path):
    kmz_path = tmp_path / "empty.kmz"
    with zipfile.ZipFile(kmz_path, "w") as z:
        z.writestr("readme.txt", "not a kml")
    with pytest.raises(ValueError, match="No .kml file"):
        parse_kmz_file(str(kmz_path))
