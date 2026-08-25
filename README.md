# SDOHPlace-SpatialPipeline

AWS Lambda pipeline that derives spatial metadata (geometry, bbox, centroid, coverage, highlight IDs) for [SDOH Place](https://github.com/healthyregions/SDOHPlace-MetadataManager).

The manager calls this function and writes the result onto a metadata record. This repo does **not** save records or index Solr.

Read these **before coding** (a new Cursor window will not have the old chat):

1. [docs/pipeline-contract.md](docs/pipeline-contract.md) — input/output, S3, async, open questions
2. [docs/handoff-context.md](docs/handoff-context.md) — Alaska bug, HEROP_ID, GitHub/Slack decisions, folders

Development branch: `dev`.

## Status

Skeleton handler only. It reads the manager invoke payload, derives the job folder from `s3_key`, and writes a stub `result.json` (`ok: false`, `error_code: not_implemented`). It does **not** derive geometry — a fake success outline would recreate the Alaska bug.

```
uploads/{record_id}/{timestamp}/{filename}
uploads/{record_id}/{timestamp}/result.json
```

Handler: `sdohplace_spatial.handler.lambda_handler`. Bucket env: `UPLOADS_BUCKET` (default `herop-sdohplace-upload`). Example payload: [`examples/invoke-payload.json`](examples/invoke-payload.json).

`upload_kind: geo` reads a GeoJSON or shapefile zip from S3, reprojects to EPSG:4326, simplifies, and writes WKT / bbox / centroid. `highlight_ids` is `[]` (no HEROP join yet).

`upload_kind: csv` joins 2018 HEROP `oeps/` boundaries by FIPS / GEOID / `HEROP_ID` and writes `highlight_ids` plus a simplified dissolve of matched units. `spatial_coverage` is still empty pending product grain.

```
pip install -r requirements-dev.txt
pytest
```
