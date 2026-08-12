"""Reliable batch file discovery and execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

# Supported formats currently implemented by the Batch Converter.
SUPPORTED_EXTENSIONS = {".kmz", ".kml", ".csv", ".xlsx"}
OUTPUT_SUFFIX = "_converted.xlsx"


@dataclass
class FileResult:
    path: str
    status: str
    points_total: int = 0
    points_success: int = 0
    points_failed: int = 0
    message: str = ""


@dataclass
class BatchReport:
    results: List[FileResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(r.status == "SUCCESS" for r in self.results)

    @property
    def failed_count(self) -> int:
        return sum(r.status == "FAILED" for r in self.results)

    @property
    def warning_count(self) -> int:
        return sum(r.status == "WARNING" for r in self.results)


def find_batch_files(folder: str) -> List[Path]:
    """Recursively find implemented coordinate files, case-insensitively."""
    root = Path(folder).expanduser()
    if not root.exists() or not root.is_dir():
        return []

    found: List[Path] = []
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith("~$"):
                continue
            if path.name.lower().endswith(OUTPUT_SUFFIX):
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(path.resolve())
    except (OSError, PermissionError):
        pass

    return sorted(found, key=lambda p: str(p).lower())


def run_batch(
    folder: str,
    process_one: Callable[[Path], FileResult],
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
) -> BatchReport:
    """Process every discovered file; a failure never stops the batch."""
    files = find_batch_files(folder)
    report = BatchReport()
    total = len(files)

    for i, file_path in enumerate(files, start=1):
        if progress_cb:
            progress_cb(i, total, file_path)
        try:
            result = process_one(file_path)
        except Exception as exc:
            result = FileResult(str(file_path), "FAILED", message=str(exc))
        report.results.append(result)

    return report
