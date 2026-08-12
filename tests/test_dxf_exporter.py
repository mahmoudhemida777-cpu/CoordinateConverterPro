"""DXF exporter tests — require ezdxf, unavailable offline. Skipped
locally, run for real on the GitHub Actions Windows runner."""
import pytest

ezdxf = pytest.importorskip("ezdxf")

from core.exporters.dxf_exporter import export_dxf, LabelMode  # noqa: E402
from core.models import PointResult  # noqa: E402


def test_export_dxf_creates_file(tmp_path):
    out = tmp_path / "points.dxf"
    pts = [PointResult("P1", 46.8, 24.7, 650, 500000.1, 2740123.4, 650.0, "SUCCESS")]
    export_dxf(pts, str(out))
    assert out.exists()


def test_export_dxf_has_points_and_labels_layers(tmp_path):
    out = tmp_path / "points.dxf"
    pts = [PointResult("P1", 46.8, 24.7, 650, 500000.1, 2740123.4, 650.0, "SUCCESS")]
    export_dxf(pts, str(out))
    doc = ezdxf.readfile(str(out))
    layer_names = {layer.dxf.name for layer in doc.layers}
    assert "POINTS" in layer_names
    assert "LABELS" in layer_names


def test_export_dxf_skips_failed_points_without_crashing(tmp_path):
    out = tmp_path / "points.dxf"
    pts = [
        PointResult("P1", 46.8, 24.7, None, 500000.1, 2740123.4, None, "SUCCESS"),
        PointResult("P2", None, None, None, status="FAILED"),
    ]
    export_dxf(pts, str(out))  # must not raise
    doc = ezdxf.readfile(str(out))
    msp = doc.modelspace()
    points = list(msp.query("POINT"))
    assert len(points) == 1  # only the successful point


def test_export_dxf_label_mode_number(tmp_path):
    out = tmp_path / "points.dxf"
    pts = [PointResult("PointA", 1, 1, None, 100.0, 200.0, None, "SUCCESS")]
    export_dxf(pts, str(out), label_mode=LabelMode.NUMBER)
    doc = ezdxf.readfile(str(out))
    texts = [t.dxf.text for t in doc.modelspace().query("TEXT")]
    assert texts == ["1"]
