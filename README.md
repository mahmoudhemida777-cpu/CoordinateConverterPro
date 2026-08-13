# MH GeoSuite Pro v1.1.0

Professional Surveying & Geospatial Engineering Suite by Mahmoud Hemida.

## Current status

The current `main` branch contains the real PySide6 desktop application with functional pages and connected workflows. The application is not intended to present placeholder pages as working features.

### Functional modules

- **Dashboard** — scans a project folder, lists supported coordinate files, selects an Active File, and propagates that file to Import, CRS Converter, Batch, Map and Civil/CAD.
- **Import** — KMZ/KML/CSV/XLSX/XLS loading with column mapping for tabular files.
- **CRS Converter** — source-to-target CRS transformation through PROJ/pyproj, validation, result table and XLSX/CSV/DXF/Civil 3D exports.
- **Survey Tools** — COGO distance, horizontal distance, azimuth, coordinate deltas and polygon area.
- **Civil / CAD** — loads raw coordinate files or Batch `_converted.xlsx` results; Batch results are treated as final target coordinates and are not converted a second time; exports DXF and Civil 3D PENZD CSV.
- **Batch Converter** — folder/file/Active File processing using the same CRS engine as single-file conversion; records each successful/warning operation in History and propagates successful converted workbooks to Civil/CAD.
- **Map** — offline point preview for CSV/XLSX/KML/KMZ.
- **History** — persistent conversion log with automatic refresh and clear/refresh controls.
- **Settings** — Arabic/English selection and persistent decimal precision from 0–6; precision is applied to displayed conversion results and tabular exports.
- **About** — application/version and PROJ engine information.

## CRS support

CRS selection is powered by PROJ/pyproj and supports authority identifiers beyond EPSG where available. Ain el Abd 1970 / UTM Zone 38N (`EPSG:20438`) is supported, with Hayford 1909 / International 1924 aliases exposed for easier discovery.

## File workflows

### Single conversion

`Dashboard → Active File → CRS Converter → Source CRS → Target CRS → Convert → Export`

### Batch conversion

`Dashboard → Active File or Choose Folder/Files → Batch → Source CRS → Target CRS → Convert`

Successful Batch workbooks are emitted as `<name>_converted.xlsx` with `Target X/Y/Z` and `Project Info`. When that result reaches Civil/CAD, the target coordinates are loaded directly and the application reports **Already Converted** instead of asking for another CRS transformation.

### CAD / Civil 3D

- DXF point entities with labels.
- Civil 3D PENZD CSV: Point, Easting, Northing, Elevation, Description.
- Target coordinates are used for converted results.

## Testing

The repository includes automated tests for the CRS engine, parsers, exporters, validation, batch processing and UI page integration. GitHub Actions runs the test suite and the Windows build/smoke-test workflow configured by the repository.

A successful CI run validates the automated checks; it should not be described as a substitute for a human acceptance test of every button in a production Windows environment.

## Version

`MH GeoSuite Pro v1.1.0`

Developed by **Mahmoud Hemida**.
