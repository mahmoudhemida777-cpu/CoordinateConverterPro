import csv
import os

import pytest

from core.parsers.csv_parser import sniff_columns, parse_csv, ColumnMapping


@pytest.fixture()
def sample_csv(tmp_path):
    path = tmp_path / "points.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Point Name", "Easting", "Northing", "Elevation"])
        w.writerow(["P1", "46.84550218", "24.77373641", "650.5"])
        w.writerow(["P2", "46.85", "24.78", ""])
        w.writerow(["P3", "", "24.79", "10"])  # missing X -> should fail gracefully
    return str(path)


def test_sniff_columns(sample_csv):
    assert sniff_columns(sample_csv) == ["Point Name", "Easting", "Northing", "Elevation"]


def test_parse_valid_rows(sample_csv):
    mapping = ColumnMapping(name_col="Point Name", x_col="Easting", y_col="Northing", z_col="Elevation")
    points = parse_csv(sample_csv, mapping)
    assert len(points) == 3
    assert points[0].name == "P1"
    assert points[0].src_x == pytest.approx(46.84550218)
    assert points[0].src_y == pytest.approx(24.77373641)
    assert points[0].src_z == pytest.approx(650.5)


def test_missing_x_does_not_crash_batch(sample_csv):
    mapping = ColumnMapping(name_col="Point Name", x_col="Easting", y_col="Northing", z_col="Elevation")
    points = parse_csv(sample_csv, mapping)
    p3 = points[2]
    assert p3.status == "FAILED"
    assert p3.src_x is None


def test_missing_z_is_none_not_error(sample_csv):
    mapping = ColumnMapping(name_col="Point Name", x_col="Easting", y_col="Northing", z_col="Elevation")
    points = parse_csv(sample_csv, mapping)
    p2 = points[1]
    assert p2.src_z is None
    assert p2.status == "PENDING"


def test_no_name_column_auto_generates_names(tmp_path):
    path = tmp_path / "noname.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["X", "Y"])
        w.writerow(["46.8", "24.7"])
    mapping = ColumnMapping(name_col=None, x_col="X", y_col="Y")
    points = parse_csv(str(path), mapping)
    assert points[0].name == "PT-1"
