# Changelog

All notable changes to this repo are listed here. The Lambda is a pure function: S3 in → `result.json` out. It does not write record JSON, touch Solr, or import the Flask metadata manager.

## Unreleased

### Added

- Lambda handler stub ([#2](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/2)): reads the manager invoke payload, derives the job folder from `s3_key`, writes `result.json` next to the upload as `ok: false` / `error_code: not_implemented`. No fake success geometry.
- Geo path ([#6](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/6)): `upload_kind: geo` reads GeoJSON or a shapefile zip, reprojects to EPSG:4326, simplifies, and writes WKT, `ENVELOPE(W,E,N,S)`, and centroid (`lat,lon`). `highlight_ids` and `spatial_coverage` are `[]` plus warnings (no HEROP join, no place-name matching). KML / GeoPackage / file gdb are rejected.
- CSV ID join ([#7](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/7)): `upload_kind: csv` against 2018 `oeps/` shapefiles. Prefers `FIPS`, then `geo_id_column` / `HEROP_ID` / `GEOID`; zfill; `prefix + FIPS == HEROP_ID`. `spatial_level` is `bg` (not `blockgroup`). `highlight_ids` uses the coverage.py include / minus / `*` rules. Zero matches or mixed GEOID lengths fail. Partial matches succeed with diagnostics. `spatial_coverage` stays `[]` pending Marynia. Geometry is the simplified dissolve of **matched** units. 2010 CSV is still `not_implemented` (#9).
- Example invoke payloads under `examples/`.
- Unit tests (`pytest`); handler uses an injectable S3 client so tests do not need AWS.
- GitHub Actions workflow ([#16](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/16)) runs `pytest` on Python 3.10 and 3.12 for pushes and PRs to `dev` / `main`.

### Changed

- Uploads bucket name is **`herop-sdohplace-upload`** (singular), matching the bucket Pengyin created ([#3](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/3)).

### Confirmed

- S3 job-folder keys ([#4](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/4)): `uploads/{record_id}/{timestamp}/{filename}` and `result.json` in the same folder. One Generate click = one directory; multiple jobs can exist at once.

### AWS (not code)

- Execution role `herop-sdohplace-spatial-role` (Lambda trust, scoped S3, CloudWatch logs). `AWSLambdaExecute` removed.
- EC2 `lambda:InvokeFunction` still waits until function `herop-sdohplace-spatial` exists ([#11](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/11)).

## 0.0.1 — 2026-08-20

### Added

- Repo docs: [`docs/pipeline-contract.md`](docs/pipeline-contract.md) (Lambda ↔ manager interface) and [`docs/handoff-context.md`](docs/handoff-context.md) (Alaska / place-name bug, HEROP_ID, what not to build).
- Parent tracker [#1](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/1).
