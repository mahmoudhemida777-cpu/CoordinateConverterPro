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
    """
    Find all supported coordinate files inside the selected folder.

    Supports:
    KMZ, KML, CSV, XLSX

    Searches recursively through subfolders.
    """
    root = Path(folder)

    if not root.exists() or not root.is_dir():
        return []

    files = []

    for f in root.rglob("*"):
        if not f.is_file():
            continue

        suffix = f.suffix.strip().lower()

        if suffix in SUPPORTED_EXTENSIONS:
            files.append(f)

    return sorted(files, key=lambda p: str(p).lower())
def run_batch(
    folder: str,
    process_one: Callable[[Path], FileResult],
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
) -> BatchReport:
    """
    Process every supported file in a folder.

    A failure in one file does not stop the remaining files.
    """

    files = find_batch_files(folder)

    report = BatchReport()
    total = len(files)

    for i, file_path in enumerate(files, start=1):

        if progress_cb:
            progress_cb(i, total, file_path)

        try:
            result = process_one(file_path)

        except Exception as exc:
            result = FileResult(
                str(file_path),
                "FAILED",
                message=str(exc),
            )

        report.results.append(result)

    return report
