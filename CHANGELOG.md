# Changelog

All notable changes to this repo are listed here. The Lambda is a pure function: S3 in → `result.json` out. It does not write record JSON, touch Solr, or import the Flask metadata manager.

## Unreleased

### Added

- Lambda handler stub ([#2](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/2)): reads the manager invoke payload, derives the job folder from `s3_key`, writes `result.json` next to the upload as `ok: false` / `error_code: not_implemented`. No fake success geometry.
- Geo path ([#6](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/6)): `upload_kind: geo` reads GeoJSON or a shapefile zip, reprojects to EPSG:4326, simplifies, and writes WKT, `ENVELOPE(W,E,N,S)`, and centroid (`lat,lon`). `highlight_ids` and `spatial_coverage` are `[]` plus warnings (no HEROP join, no place-name matching). KML / GeoPackage / file gdb are rejected.
- CSV ID join ([#7](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/7), [#9](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/9)): `upload_kind: csv` against 2010 or 2018 US Census shapefiles under `oeps/`. Prefers `FIPS`, then `geo_id_column` / `HEROP_ID` / `GEOID`; zfill; `prefix + FIPS == HEROP_ID`. `spatial_level` is `bg` (not `blockgroup`). **2018** `highlight_ids` uses the coverage.py include / minus / `*` rules. **2010** returns geometry from 2010 units and `highlight_ids` `[]` (discovery tiles are 2018-only). Zero matches or mixed GEOID lengths fail. Partial matches succeed with diagnostics. `spatial_coverage` is unique **state names** from matched HEROP IDs (plus `United States` / `Contiguous US` when coverage is national / CONUS), not from place-name matching. Geometry is the simplified dissolve of **matched** units.
- Example invoke payloads under `examples/`.
- Unit tests (`pytest`); handler uses an injectable S3 client so tests do not need AWS.
- GitHub Actions workflow ([#16](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/16)) runs `pytest` on Python 3.10 and 3.12 for pushes and PRs to `dev` / `main`.
- Lambda **container image** ([#10](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/10)): `Dockerfile` (`linux/amd64`, Python 3.12) and [`docs/deploy.md`](docs/deploy.md) for ECR + `herop-sdohplace-spatial`. Handler wipes `sdoh-*` temp dirs after each run (full `/tmp` on Lambda).

### Changed

- Uploads bucket name is **`herop-sdohplace-upload`** (singular), matching the bucket Pengyin created ([#3](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/3)).

### Confirmed

- S3 job-folder keys ([#4](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/4)): `uploads/{record_id}/{timestamp}/{filename}` and `result.json` in the same folder. One Generate click = one directory; multiple jobs can exist at once.
- v1 product defaults (Pengyin, Aug 2026; [#19](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/19), also [#5](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/5)): state-name `spatial_coverage` (no Census Place); 2010 geometry + empty `highlight_ids`; one Generate = one level; raster = envelope only; test OEPS via search.sdohplace.org; manager **warns** if `match_rate` < 0.9 (no hard refuse). Refine Sept/Oct.
- Marynia (Aug 2026 Slack): geo uploads use the file’s boundaries (no HEROP join); CSV-only joins the specified **US Census** vintage/level (`oeps/` on S3; OEPS is a test dataset). Vintage pmtiles / temporal slider / multi-color Show coverage are Discovery, not this Lambda. 2010 `highlight_ids` stay `[]` until non-2018 tiles exist.

### AWS (not code)

- Execution role `herop-sdohplace-spatial-role` (Lambda trust, scoped S3 including ListBucket on the bucket ARN, CloudWatch logs). `AWSLambdaExecute` removed. Function `herop-sdohplace-spatial` is live in `us-east-2`.
- EC2 role `SDOHPlaceManagerRole` (solr1) has `lambda:InvokeFunction` on `herop-sdohplace-spatial` ([#11](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/11)).

## 0.0.1 — 2026-08-20

### Added

- Repo docs: [`docs/pipeline-contract.md`](docs/pipeline-contract.md) (Lambda ↔ manager interface) and [`docs/handoff-context.md`](docs/handoff-context.md) (Alaska / place-name bug, HEROP_ID, what not to build).
- Parent tracker [#1](https://github.com/healthyregions/SDOHPlace-SpatialPipeline/issues/1).
