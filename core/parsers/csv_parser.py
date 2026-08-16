"""Robust survey coordinate parser for CSV/TXT-like delimited files."""
from __future__ import annotations
import csv
from dataclasses import dataclass
from typing import List, Optional
from core.models import PointResult
@dataclass
class ColumnMapping:
    name_col: Optional[str]; x_col: str; y_col: str; z_col: Optional[str] = None
def _is_number(value: str) -> bool:
    try: float(str(value).strip()); return True
    except (ValueError,TypeError): return False
def _read_rows(path:str,encoding:str="utf-8-sig"):
    with open(path,"r",encoding=encoding,errors="replace",newline="") as f:
        sample=f.read(8192);f.seek(0)
        try:dialect=csv.Sniffer().sniff(sample,delimiters=",;\t|")
        except csv.Error:dialect=csv.excel
        return [[str(c).strip() for c in row] for row in csv.reader(f,dialect) if any(str(c).strip() for c in row)]
def _norm(s):return "".join(c for c in str(s).strip().lower() if c.isalnum())
def _header_like(row):
    if len(row)<2:return False
    keys=[_norm(x) for x in row];aliases={"easting","east","x","xcoord","xcoordinate","northing","north","y","ycoord","ycoordinate","longitude","lon","latitude","lat","elevation","elev","height","z","zcoord","zcoordinate","point","pointnumber","pointid","name","id"}
    return any(k in aliases or any(a in k for a in ("easting","northing","longitude","latitude","elevation","pointnumber")) for k in keys) and not all(_is_number(x) for x in row[:min(3,len(row))])
def sniff_columns(path,encoding="utf-8-sig"):
    rows=_read_rows(path,encoding)
    if not rows:return ["Point","Easting","Northing","Elevation"]
    return rows[0] if _header_like(rows[0]) else [f"Column {i+1}" for i in range(len(rows[0]))]
def _find_col(headers,aliases,fallback=None):
    ns=[_norm(h) for h in headers];al=[_norm(a) for a in aliases]
    for a in al:
        if a in ns:return ns.index(a)
    for i,h in enumerate(ns):
        if any(a in h for a in al):return i
    return fallback
def parse_csv(path,mapping,encoding="utf-8-sig"):
    # If the UI inferred the same/invalid X and Y header, bypass mapping and use data-driven inference.
    if not mapping.x_col or not mapping.y_col or mapping.x_col==mapping.y_col:return parse_csv_auto(path,encoding)
    rows=_read_rows(path,encoding)
    if not rows:return []
    headers=rows[0];data=rows[1:] if _header_like(headers) else rows
    if not _header_like(headers):
        def pos(col):
            try:return int(str(col).split()[-1])-1
            except Exception:return None
        xi,yi,zi,ni=pos(mapping.x_col),pos(mapping.y_col),pos(mapping.z_col) if mapping.z_col else None,pos(mapping.name_col) if mapping.name_col else None;points=[]
        for i,row in enumerate(data,1):
            try:x=float(row[xi]);y=float(row[yi]);z=float(row[zi]) if zi is not None and len(row)>zi and str(row[zi]).strip() else None
            except (TypeError,ValueError,IndexError):points.append(PointResult(f"PT-{i}",None,None,None,status="FAILED",message="Invalid or missing X/Y"));continue
            name=str(row[ni]).strip() if ni is not None and len(row)>ni and str(row[ni]).strip() else f"PT-{i}";points.append(PointResult(name,x,y,z))
        return points
    idx={h:i for i,h in enumerate(headers)};points=[]
    for i,row in enumerate(data,1):
        def val(col):return row[idx[col]].strip() if col in idx and idx[col]<len(row) else ""
        name=val(mapping.name_col) if mapping.name_col else f"PT-{i}"
        try:x=float(val(mapping.x_col));y=float(val(mapping.y_col))
        except (ValueError,TypeError):points.append(PointResult(name or f"PT-{i}",None,None,None,status="FAILED",message="Invalid or missing X/Y"));continue
        z=None
        if mapping.z_col:
            try:z=float(val(mapping.z_col)) if val(mapping.z_col) else None
            except ValueError:pass
        points.append(PointResult(name or f"PT-{i}",x,y,z))
    return points
def parse_csv_auto(path,encoding="utf-8-sig"):
    rows=_read_rows(path,encoding)
    if not rows:return []
    headers=rows[0];has_header=_header_like(headers);data=rows[1:] if has_header else rows
    if not data:return []
    xidx=_find_col(headers,("easting","east","x","x_coord","xcoordinate","longitude","lon"),0 if not has_header else None);yidx=_find_col(headers,("northing","north","y","y_coord","ycoordinate","latitude","lat"),1 if not has_header else None);zidx=_find_col(headers,("elevation","elev","height","z","z_coord","zcoordinate"),2 if not has_header else None);nidx=_find_col(headers,("pointnumber","point_no","pointid","point","name","id","number"))
    if not has_header and len(data[0])>=4 and not _is_number(data[0][0]) and _is_number(data[0][1]) and _is_number(data[0][2]):nidx,xidx,yidx,zidx=0,1,2,3
    if has_header and (xidx is None or yidx is None or xidx==yidx):
        width=max(len(r) for r in data);numeric=[]
        for c in range(width):
            vals=[r[c] for r in data[:30] if len(r)>c and str(r[c]).strip()]
            if vals and sum(_is_number(v) for v in vals)>=max(1,int(len(vals)*0.8)):numeric.append(c)
        if len(numeric)>=2:xidx,yidx=numeric[:2];zidx=numeric[2] if len(numeric)>=3 else None
    points=[]
    for i,row in enumerate(data,1):
        try:
            if xidx is None or yidx is None or len(row)<=max(xidx,yidx):raise ValueError
            x=float(row[xidx]);y=float(row[yidx]);z=float(row[zidx]) if zidx is not None and len(row)>zidx and str(row[zidx]).strip() else None
        except (ValueError,TypeError):points.append(PointResult(f"PT-{i}",None,None,None,status="FAILED",message="Invalid or missing X/Y"));continue
        name=str(row[nidx]).strip() if nidx is not None and len(row)>nidx and str(row[nidx]).strip() else f"PT-{i}";points.append(PointResult(name,x,y,z))
    return points
