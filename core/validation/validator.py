"""Point-set validation: missing coords, invalid ranges, duplicates.

Design principle: validation NEVER aborts a batch. Every issue is recorded
against the specific point and returned in a report; the caller decides
whether to proceed, skip, or halt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core.models import PointResult


@dataclass
class ValidationIssue:
    point_name: str
    severity: str  # "ERROR" | "WARNING"
    message: str


@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    def add(self, point_name: str, severity: str, message: str) -> None:
        self.issues.append(ValidationIssue(point_name, severity, message))


def validate_points(
    points: List[PointResult],
    source_is_geographic: bool = True,
) -> ValidationReport:
    report = ValidationReport()
    seen_names: dict[str, int] = {}
    seen_coords: dict[tuple, list] = {}

    for p in points:
        # Missing coordinates
        if p.src_x is None or p.src_y is None:
            report.add(p.name, "ERROR", "Missing source coordinates")
            continue

        # Invalid coordinate ranges (only meaningful for geographic CRS)
        if source_is_geographic:
            if not (-180.0 <= p.src_x <= 180.0):
                report.add(p.name, "ERROR", f"Longitude out of range: {p.src_x}")
            if not (-90.0 <= p.src_y <= 90.0):
                report.add(p.name, "ERROR", f"Latitude out of range: {p.src_y}")

        # Duplicate point names
        seen_names[p.name] = seen_names.get(p.name, 0) + 1

        # Duplicate coordinates (rounded to 6 decimals to catch near-identical)
        coord_key = (round(p.src_x, 6), round(p.src_y, 6))
        seen_coords.setdefault(coord_key, []).append(p.name)

    for name, count in seen_names.items():
        if count > 1:
            report.add(name, "WARNING", f"Duplicate point name appears {count} times")

    for coord, names in seen_coords.items():
        if len(names) > 1:
            report.add(
                ", ".join(names), "WARNING",
                f"Duplicate coordinates {coord} shared by {len(names)} points",
            )

    return report


def validate_zone_consistency(source_crs_name: str, target_crs_name: str) -> List[str]:
    """Lightweight heuristic check for an obviously mismatched UTM zone
    conversion (e.g. converting between two different UTM zones directly
    without going through a geographic CRS first) — flags for user review,
    never blocks."""
    warnings: List[str] = []
    src_upper = source_crs_name.upper()
    tgt_upper = target_crs_name.upper()
    if "UTM" in src_upper and "UTM" in tgt_upper:
        import re
        src_zone = re.search(r"ZONE\s*(\d+)", src_upper)
        tgt_zone = re.search(r"ZONE\s*(\d+)", tgt_upper)
        if src_zone and tgt_zone and src_zone.group(1) != tgt_zone.group(1):
            warnings.append(
                f"Converting across different UTM zones ({src_zone.group(1)} -> "
                f"{tgt_zone.group(1)}). Verify this is intentional."
            )
    return warnings
