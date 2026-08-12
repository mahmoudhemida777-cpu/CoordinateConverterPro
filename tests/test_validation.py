from core.models import PointResult
from core.validation.validator import validate_points, validate_zone_consistency


def test_missing_coordinates_flagged_as_error():
    pts = [PointResult("P1", None, None, None)]
    report = validate_points(pts)
    assert len(report.errors) == 1
    assert "Missing" in report.errors[0].message


def test_out_of_range_longitude_flagged():
    pts = [PointResult("P1", 200.0, 24.0, None)]
    report = validate_points(pts)
    assert any("Longitude" in e.message for e in report.errors)


def test_out_of_range_latitude_flagged():
    pts = [PointResult("P1", 46.0, 95.0, None)]
    report = validate_points(pts)
    assert any("Latitude" in e.message for e in report.errors)


def test_duplicate_names_flagged_as_warning():
    pts = [PointResult("P1", 1.0, 1.0, None), PointResult("P1", 2.0, 2.0, None)]
    report = validate_points(pts)
    assert any("Duplicate point name" in w.message for w in report.warnings)


def test_duplicate_coordinates_flagged_as_warning():
    pts = [PointResult("P1", 1.0, 1.0, None), PointResult("P2", 1.0, 1.0, None)]
    report = validate_points(pts)
    assert any("Duplicate coordinates" in w.message for w in report.warnings)


def test_valid_points_produce_no_errors():
    pts = [PointResult("P1", 46.84, 24.77, 650.0)]
    report = validate_points(pts)
    assert report.errors == []


def test_a_single_bad_point_does_not_block_others():
    pts = [
        PointResult("P1", None, None, None),
        PointResult("P2", 46.0, 24.0, None),
    ]
    report = validate_points(pts)
    # P1 is flagged, but validation still evaluated P2 without raising
    assert len(report.errors) == 1


def test_utm_zone_mismatch_warns():
    warnings = validate_zone_consistency("WGS 84 / UTM Zone 37N", "WGS 84 / UTM Zone 38N")
    assert len(warnings) == 1


def test_utm_same_zone_no_warning():
    warnings = validate_zone_consistency("WGS 84 / UTM Zone 38N", "WGS 84 / UTM Zone 38N")
    assert warnings == []
