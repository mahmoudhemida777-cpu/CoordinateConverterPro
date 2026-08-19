"""Reliable Windows batch file discovery and execution."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

SUPPORTED_EXTENSIONS = {".kmz", ".kml", ".csv", ".xlsx", ".txt"}
CAD_EXTENSIONS = {".dxf", ".dwg"}
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


def find_batch_files(folder: str, include_cad: bool = False) -> List[Path]:
    """Discover survey files recursively; optionally include CAD files for workspace discovery."""
    root = Path(folder).expanduser()
    if not root.exists() or not root.is_dir():
        return []

    allowed = SUPPORTED_EXTENSIONS | CAD_EXTENSIONS if include_cad else SUPPORTED_EXTENSIONS
    found: List[Path] = []
    try:
        for current, dirs, files in os.walk(root, topdown=True, onerror=lambda _e: None):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "venv", ".venv"}]
            for filename in files:
                path = Path(current) / filename
                lower_name = filename.casefold()
                if lower_name.startswith("~$"):
                    continue
                if lower_name.endswith(OUTPUT_SUFFIX.casefold()):
                    continue
                if path.suffix.casefold() in allowed:
                    try:
                        found.append(path.resolve())
                    except OSError:
                        found.append(path.absolute())
    except (OSError, PermissionError):
        pass

    unique = {str(p).casefold(): p for p in found}
    return sorted(unique.values(), key=lambda p: str(p).casefold())


def run_batch(
    folder: str,
    process_one: Callable[[Path], FileResult],
    progress_cb: Optional[Callable[[int, int, Path], None]] = None,
) -> BatchReport:
    """Process every discovered batch-compatible file; CAD files are not included by default."""
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
