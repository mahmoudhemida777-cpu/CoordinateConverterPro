"""
DXF exporter — AutoCAD / Civil 3D compatible.

NOTE ON TESTING: this module depends on `ezdxf`, which is not installable
in the offline sandbox this project was authored in (no network access).
It follows ezdxf's documented public API exactly (ezdxf.new / modelspace /
add_layer / add_point / add_text) and mirrors patterns from ezdxf's own
tutorials, but has NOT been executed locally. The GitHub Actions workflow
installs ezdxf from PyPI on the Windows runner and the pytest suite
(tests/test_dxf_exporter.py) exercises this module there as part of the
real build pipeline — treat that CI run as the first real execution.
"""
from __future__ import annotations

from enum import Enum
from typing import List

import ezdxf

from core.models import PointResult


class LabelMode(str, Enum):
    NUMBER = "Point Number"
    NAME = "Point Name"
    COORDS = "E,N"
    NUMBER_AND_NAME = "Point Number + Name"


def export_dxf(
    points: List[PointResult],
    out_path: str,
    label_mode: LabelMode = LabelMode.NAME,
    text_height: float = 1.0,
    use_target_coords: bool = True,
) -> str:
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    doc.layers.add(name="POINTS", color=1)   # red
    doc.layers.add(name="LABELS", color=3)   # green

    for i, p in enumerate(points, start=1):
        x = p.tgt_x if use_target_coords else p.src_x
        y = p.tgt_y if use_target_coords else p.src_y
        if x is None or y is None:
            continue  # skip failed/incomplete points, never abort the export

        msp.add_point((x, y), dxfattribs={"layer": "POINTS"})

        if label_mode == LabelMode.NUMBER:
            label = str(i)
        elif label_mode == LabelMode.NAME:
            label = p.name
        elif label_mode == LabelMode.COORDS:
            label = f"{x:.3f},{y:.3f}"
        else:  # NUMBER_AND_NAME
            label = f"{i} - {p.name}"

        msp.add_text(
            label,
            dxfattribs={"layer": "LABELS", "height": text_height, "insert": (x, y)},
        )

    doc.saveas(out_path)
    return out_path
