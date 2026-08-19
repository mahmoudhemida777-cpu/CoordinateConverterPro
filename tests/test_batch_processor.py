from pathlib import Path

import pytest

from core.batch.batch_processor import find_batch_files, run_batch, FileResult


@pytest.fixture()
def sample_folder(tmp_path):
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "b.xlsx").write_text("x")
    (tmp_path / "c.kmz").write_text("x")
    (tmp_path / "d.txt").write_text("x")
    (tmp_path / "e.kml").write_text("x")
    return str(tmp_path)


def test_find_batch_files_only_supported_extensions(sample_folder):
    files = find_batch_files(sample_folder)
    names = sorted(f.name for f in files)
    assert names == ["a.csv", "b.xlsx", "c.kmz", "d.txt", "e.kml"]


def test_find_batch_files_can_include_cad_for_workspace_discovery(sample_folder):
    root = Path(sample_folder)
    (root / "survey.dxf").write_text("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n")
    (root / "drawing.dwg").write_bytes(b"DWG")
    files = find_batch_files(sample_folder, include_cad=True)
    names = sorted(f.name for f in files)
    assert "survey.dxf" in names
    assert "drawing.dwg" in names


def test_run_batch_continues_after_a_failure(sample_folder):
    def process(path: Path) -> FileResult:
        if path.name == "b.xlsx":
            raise RuntimeError("simulated failure")
        return FileResult(str(path), "SUCCESS", points_total=1, points_success=1)

    report = run_batch(sample_folder, process)
    assert report.success_count == 4
    assert report.failed_count == 1
    assert len(report.results) == 5


def test_progress_callback_invoked_for_each_file(sample_folder):
    calls = []
    report = run_batch(
        sample_folder,
        lambda p: FileResult(str(p), "SUCCESS"),
        lambda i, total, p: calls.append((i, total)),
    )
    assert len(calls) == 5
    assert calls[-1] == (5, 5)
