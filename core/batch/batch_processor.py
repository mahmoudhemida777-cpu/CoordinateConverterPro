"""Batch conversion: process every supported file in a folder.

A single bad file never stops the batch; each file's outcome is recorded
in the returned BatchReport.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

SUPPORTED_EXTENSIONS = {".kmz", ".kml", ".csv", ".xlsx"}


@dataclass
class FileResult:
    path: str
    status: str  # SUCCESS | FAILED | WARNING
    points_total: int = 0
    points_success: int = 0
    points_failed: int = 0
    message: str = ""


@dataclass
class BatchReport:
    results: List[FileResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.status == "SUCCESS")

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == "FAILED")

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == "WARNING")


def find_batch_files(folder: str) -> List[Path]:
    p = Path(folder)
    return sorted(
        f for f in p.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def run_batch(
    folder: str,
    process_one: Callable[[Path], FileResult],
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
) -> BatchReport:
    """`process_one` is injected by the caller (UI layer) so this module
    stays decoupled from the CRS engine / exporters, and is unit-testable
    with a fake `process_one`."""
    files = find_batch_files(folder)
    report = BatchReport()
    total = len(files)
    for i, f in enumerate(files, start=1):
        if progress_cb:
            progress_cb(i, total, f)
        try:
            result = process_one(f)
        except Exception as exc:  # noqa: BLE001
            result = FileResult(str(f), "FAILED", message=str(exc))
        report.results.append(result)
    return report
