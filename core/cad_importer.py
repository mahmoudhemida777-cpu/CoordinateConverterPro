from __future__ import annotations
from pathlib import Path
from core.models import PointResult


def _p(name, xyz):
    return PointResult(name, float(xyz[0]), float(xyz[1]), float(xyz[2] if len(xyz) > 2 else 0.0))


def _extract(doc):
    msp = doc.modelspace()
    out = []
    n = 1
    for e in msp.query("POINT"):
        out.append(_p(f"POINT-{n}", e.dxf.location)); n += 1
    for e in msp.query("LWPOLYLINE"):
        elev = float(getattr(e.dxf, "elevation", 0.0) or 0.0)
        for v in e.get_points("xy"):
            out.append(_p(f"POLY-{n}", (v[0], v[1], elev))); n += 1
    for e in msp.query("POLYLINE"):
        for v in e.vertices:
            out.append(_p(f"POLY-{n}", v.dxf.location)); n += 1
    if not out:
        for e in msp.query("INSERT"):
            ins = getattr(e.dxf, "insert", None)
            if ins is not None:
                out.append(_p(f"BLOCK-{n}", ins)); n += 1
    unique=[]; seen=set()
    for p in out:
        key=(round(p.src_x,9),round(p.src_y,9),round(p.src_z or 0.0,9))
        if key not in seen:
            seen.add(key); unique.append(p)
    return unique


def extract_cad_points(path: str | Path):
    path=Path(path)
    if path.suffix.casefold() == ".dxf":
        import ezdxf
        doc=ezdxf.readfile(str(path))
    elif path.suffix.casefold() == ".dwg":
        try:
            from ezdxf.addons import odafc
            doc=odafc.readfile(str(path))
        except Exception as exc:
            raise RuntimeError("DWG يحتاج ODA File Converter. يمكن فتح الملف بعد تثبيت ODA File Converter أو تصديره إلى DXF.") from exc
    else:
        raise ValueError(f"Unsupported CAD file type: {path.suffix}")
    points=_extract(doc)
    if not points:
        raise RuntimeError("لم يتم العثور على نقاط أو رؤوس Polyline داخل Model Space.")
    return points
