"""CRS engine tests for the global PROJ-backed CRS catalog."""
import pytest

pyproj = pytest.importorskip("pyproj")

from core.crs.engine import CRSEngine  # noqa: E402
from core.models import PointResult  # noqa: E402


@pytest.fixture()
def engine():
    return CRSEngine()


def test_wgs84_to_ain_el_abd_mandatory_case(engine):
    x, y, z = engine.transform_point(
        "EPSG:4326", "EPSG:20438", 46.84550218, 24.77373641
    )
    assert 200000 < x < 800000
    assert 2000000 < y < 3500000


def test_round_trip_wgs84_to_ain_el_abd_and_back(engine):
    lon, lat = 46.84550218, 24.77373641
    x, y, _ = engine.transform_point("EPSG:4326", "EPSG:20438", lon, lat)
    lon2, lat2, _ = engine.transform_point("EPSG:20438", "EPSG:4326", x, y)
    assert lon2 == pytest.approx(lon, abs=1e-6)
    assert lat2 == pytest.approx(lat, abs=1e-6)


def test_utm_zone_37_to_38(engine):
    x, y, _ = engine.transform_point("EPSG:32637", "EPSG:32638", 300000, 2700000)
    assert x is not None and y is not None


def test_identity_transform_is_near_no_op(engine):
    x, y, _ = engine.transform_point("EPSG:4326", "EPSG:4326", 46.8, 24.7)
    assert x == pytest.approx(46.8)
    assert y == pytest.approx(24.7)


def test_search_finds_ain_el_abd_by_name(engine):
    results = engine.search("Ain el Abd")
    assert any(r.epsg == "EPSG:20438" for r in results)


def test_search_finds_epsg_code(engine):
    results = engine.search("4326")
    assert any(r.epsg == "EPSG:4326" for r in results)


def test_search_supports_non_epsg_authorities(engine):
    results = engine.search("ESRI:102003")
    assert any(r.epsg == "ESRI:102003" for r in results)


def test_global_catalog_contains_multiple_authorities(engine):
    catalog = engine.catalog()
    authorities = {r.auth_name for r in catalog}
    assert "EPSG" in authorities
    assert len(catalog) > 5000
    assert len(authorities) >= 2


def test_custom_authority_identifier_resolves(engine):
    crs = engine._resolve_crs("ESRI:102003")
    assert crs.name


def test_invalid_crs_raises_clear_error(engine):
    from pyproj.exceptions import CRSError
    with pytest.raises(CRSError):
        engine.get_transformer("NOT_A_REAL_CRS", "EPSG:4326")


def test_batch_transform_bad_point_does_not_abort_others(engine):
    points = [
        PointResult("P1", 46.8, 24.7, None),
        PointResult("P2", None, None, None),
        PointResult("P3", 46.9, 24.8, None),
    ]
    results = engine.transform_points("EPSG:4326", "EPSG:20438", points)
    assert len(results) == 3
    assert results[0].status == "SUCCESS"
    assert results[1].status == "FAILED"
    assert results[2].status == "SUCCESS"
