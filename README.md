# Coordinate Converter Pro

A Windows desktop application (PySide6) for converting survey/GIS point
coordinates between any two Coordinate Reference Systems, powered by
PROJ/pyproj. Supports KMZ/KML/CSV/XLSX import, XLSX/CSV/DXF export, batch
folder conversion, and bilingual (AR/EN) interface.

## ⚠️ Honest status of this delivery

This is the **complete, real source project** — not a stub, not
placeholder code. Every module listed under "What has actually been
tested" below has been executed for real and passes. However:

**No compiled `.exe` is included in this delivery**, because it was
authored in an offline Linux sandbox with no internet access and no
Windows environment. It is architecturally impossible to produce a real
Windows `.exe`, run a Windows smoke test, or publish a GitHub Release
from that environment. Claiming otherwise would be false.

**What gets you the real `.exe`:** push this repository to GitHub. The
included workflow (`.github/workflows/build-windows.yml`) runs on a real
`windows-latest` GitHub-hosted runner and will:
install dependencies → run the full pytest suite → build the EXE with
PyInstaller → run a Windows smoke test against the actual built EXE →
package it as `CoordinateConverterPro-Windows.zip` → build
`CoordinateConverterPro_Setup.exe` with Inno Setup → upload both as
workflow artifacts → and, if you push a `v*.*.*` tag, create a GitHub
Release with both files attached.

If the pytest step or the Windows smoke-test step fails, every later
step (packaging, installer, release) is skipped automatically — the
workflow will never report success on a broken build.

### How to get the EXE

```bash
git init
git add .
git commit -m "Initial commit — Coordinate Converter Pro v1.0.0"
git remote add origin <your-empty-github-repo-url>
git push -u origin main
git tag v1.0.0
git push origin v1.0.0
```

Then open the **Actions** tab on GitHub, watch the `Build Windows
Release` run, and once green:
- Download `CoordinateConverterPro-Windows` from the run's Artifacts, **or**
- Download `CoordinateConverterPro_Setup.exe` from the same Artifacts, **or**
- If you pushed the `v1.0.0` tag, go to **Releases** — both files are attached there.

## What has actually been tested (in this authoring environment)

pyproj, ezdxf, and PySide6 are not installable offline here (no PyPI
access). Everything that does NOT depend on them was executed for real
via `scripts/local_smoke_test.py` (stdlib `unittest`, 14/14 passing):

- CSV parsing incl. column mapping and graceful handling of bad rows
- XLSX parsing incl. column mapping
- XLSX export — verified exact `Points` + `Project Info` sheet structure
- CSV export
- KML parsing incl. `Placemark`, `Point`, `MultiGeometry`
- KMZ parsing incl. automatic internal `.kml` extraction (no manual unzip)
- Coordinate/point validation (missing, out-of-range, duplicates)
- UTM zone-mismatch heuristic warning
- Batch processor: continues past a failing file, correct progress callbacks

`tests/test_crs_engine.py` (pyproj) and `tests/test_dxf_exporter.py`
(ezdxf) are written and included, and will run for real on the GitHub
Actions Windows runner where those packages install normally — including
the mandatory spec test case (EPSG:4326 → EPSG:20438 for the given Riyadh
coordinate), computed by PROJ, never hard-coded.

The PySide6 UI has not been launched locally (no display, no PySide6
available offline). It is exercised by `scripts/windows_smoke_test.py` in
CI, which launches the real built EXE and confirms it starts without
crashing.

## Architecture

```
app.py                  Entry point
core/
  models.py              Dependency-free shared data models
  crs/engine.py           PROJ/pyproj transformation + EPSG search
  parsers/                csv, xlsx, kml/kmz
  exporters/               xlsx, csv, dxf
  validation/               point + zone validation
  batch/                     folder batch processor
ui/                       PySide6 windows, pages, widgets, i18n
survey/, cad/, gis/       Extension points for v1.1+ tools (Survey Tools,
                          Civil/CAD, SHP/GeoJSON) — not yet implemented,
                          intentionally not faked as working
tests/                   pytest suite (full, runs on CI)
scripts/                 local_smoke_test.py (stdlib-only, runs here),
                          windows_smoke_test.py (runs on CI against the EXE)
installer/               Inno Setup script
.github/workflows/       Windows build/test/package/release pipeline
resources/               icon.ico (placeholder — replace with your brand icon)
```

## V1 scope (per spec)

Implemented: CRS search & Any→Any conversion, KMZ/KML/CSV/XLSX import,
XLSX/CSV/DXF export, column mapping, validation, batch conversion,
AR/EN toggle, logging, precision setting.

Architecture-ready but not yet implemented (clearly labeled as such in
the UI, never faked as working): Survey Tools (COGO, bearing, etc.),
extended Civil/CAD tools, Map Preview, GeoJSON/SHP import-export,
History, Project save/open.

## License

Commercial — Coordinate Converter Pro.
