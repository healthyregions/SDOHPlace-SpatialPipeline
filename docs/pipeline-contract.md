# Lambda ↔ metadata-manager contract

Working agreement for this repo. Source: [SDOHPlace-MetadataManager#87](https://github.com/healthyregions/SDOHPlace-MetadataManager/issues/87) and follow-up comments (Aug 2026).

**Also read [handoff-context.md](handoff-context.md)** (why the pipeline exists, Alaska bug, HEROP_ID, what was already said on GitHub/Slack, Cursor folders). A new chat will not have the old Metadata Manager thread.

Update these files when Marynia answers or the interface changes. Do **not** start merge/dissolve implementation until §8 is resolved.

---

## 1. What this repo is

AWS Lambda that **derives spatial metadata** from an uploaded CSV or GeoJSON/shapefile.

It is a **pure function**: read S3 → derive fields → write `result.json` to S3. It does **not** write record JSON, touch Solr, or import the Flask metadata manager.

| Side | Repo | Owner |
| --- | --- | --- |
| Pipeline (this repo) | `healthyregions/SDOHPlace-SpatialPipeline` | Yong Wook Kim — Lambda end to end (repo, function, IAM, deploys) |
| Manager + frontend | `healthyregions/SDOHPlace-MetadataManager` | Pengyin Shan |
| Product decisions | — | Marynia (`@Makosak`) |

Publication to search.sdohplace.org stays a **human** `flask registry index`. A saved record is not a live record.

Work happens on branch `dev`.

---

## 2. Why async

The manager EC2 runs **gunicorn behind nginx** (no Docker in production). Defaults:

- gunicorn workers: **30s** (binding limit)
- nginx: **60s**

Do **not** raise gunicorn timeout. Invoke Lambda **asynchronously**. No API Gateway; manager uses **boto3 + IAM role**.

Flow:

1. Curator clicks **Generate geospatial metadata**.
2. Manager uploads the file to S3 (or the contributor already did).
3. Manager invokes Lambda with `InvocationType=Event` (does not wait for the payload).
4. Lambda writes `result.json` in the same job folder.
5. Manager **polls S3** for that object. No HTTP callback into nginx.

---

## 3. S3

| | |
| --- | --- |
| Uploads bucket | `herop-sdohplace-upload` |
| Region | `us-east-2` (same as `herop-geodata`) |
| Public access | none |
| IAM | execution role `herop-sdohplace-spatial-role` in place; EC2 `InvokeFunction` after the function exists |
| HEROP boundaries | `herop-geodata` prefix `oeps/` — vintages **2010** and **2018** |

**Keep-until-publish** (not delete-on-Lambda-return). Wipe Lambda `/tmp` after each run. Manager may delete the job folder after the curator publishes.

### Key pattern

```
uploads/{record_id}/{timestamp}/{filename}
uploads/{record_id}/{timestamp}/result.json
```

Example:

```
uploads/herop-rsulgs/20260820T143022Z/dose_sys_counties.csv
uploads/herop-rsulgs/20260820T143022Z/result.json
```

`timestamp` is UTC `YYYYMMDDTHHMMSSZ`. One Generate click = one job folder.

---

## 4. Input (manager → Lambda)

```json
{
  "record_id": "herop-rsulgs",
  "s3_key": "uploads/herop-rsulgs/20260820T143022Z/dose_sys_counties.csv",
  "upload_kind": "csv",
  "boundary_year": 2018,
  "spatial_level": "county",
  "geo_id_column": "GEOID"
}
```

| Field | Notes |
| --- | --- |
| `record_id` | Logging / correlation only. Lambda never writes the record. |
| `s3_key` | Object in `herop-sdohplace-upload`. Derive the job folder from this key; write `result.json` next to the file. |
| `upload_kind` | `csv` or `geo`. `geo` = zip (shapefile sidecars) or a single GeoJSON. |
| `boundary_year` | CSV path only. v1: `2010` or `2018`. |
| `spatial_level` | CSV path only. `state` \| `county` \| `tract` \| `bg` \| `zcta`. Manager maps schema labels (`"County"`, `"Census Tract"`, …) **before** invoke. |
| `geo_id_column` | CSV path only. Lambda auto-detects FIPS / GEOID / `HEROP_ID` / stripped leading zeros; ask the curator only if detection fails. |

Do **not** put the file bytes in the payload.

One Generate = **one** `spatial_level`. Mixed county+tract in one CSV → `ok: false`.

`boundary_year`, `spatial_level`, and `geo_id_column` are ignored for `upload_kind: "geo"`.

---

## 5. Output (Lambda → `result.json`)

Aardvark / OGM formats. Coordinate order is a trap: WKT is lon-lat; centroid is **lat,lon**.

| JSON field | Solr field | Format |
| --- | --- | --- |
| `geometry` | `locn_geometry` | WKT, EPSG:4326, **simplified** dissolve |
| `bounding_box` | `dcat_bbox` | `ENVELOPE(West,East,North,South)` |
| `centroid` | `dcat_centroid` | `latitude,longitude` (lat first) |
| `spatial_coverage` | `dct_spatial_sm` | list of place-name strings (grain: §8) |
| `highlight_ids` | `sdoh_highlight_ids_sm` | HEROP_IDs; drives **Show coverage** |

### Success

```json
{
  "ok": true,
  "geometry": "MULTIPOLYGON (((...)))",
  "bounding_box": "ENVELOPE(-124.848,-66.886,49.384,24.396)",
  "centroid": "39.833,-98.583",
  "spatial_coverage": ["Illinois", "Indiana"],
  "highlight_ids": ["050US*"],
  "diagnostics": {
    "rows_in": 3142,
    "matched": 3140,
    "unmatched": 2,
    "unmatched_sample": ["09110", "09120"],
    "match_rate": 0.999,
    "boundary_year_used": 2018,
    "warnings": ["2 IDs did not match the 2018 boundary vintage"]
  }
}
```

### Failure

```json
{
  "ok": false,
  "error_code": "no_matching_ids",
  "message": "None of the 3142 values in column 'GEOID' matched county boundaries for 2018."
}
```

`ok: false` only for:

- unreadable file
- no usable ID column
- **zero** matches
- empty geometry
- missing/unusable CRS (geo path)
- mixed spatial levels in one CSV
- payload/geometry too large after simplify

Partial matches → `ok: true` plus diagnostics. Vintage mismatch is a **warning**, not a crash.

Lambda does **not** refuse to write based on `match_rate` (except 0). If the curator should be blocked below a threshold, that is the **manager** (show diagnostics, confirm). Marynia sets the threshold (§8).

Overwrite on Generate: spatial fields + `highlight_ids` only. Non-spatial fields are never touched. Manager snapshots before write.

No `derived` wrapper. Field ids already match the manager.

---

## 6. Derivation rules (v1)

### CSV path

Port/extend ID-join logic from Metadata Manager `manager/coverage/coverage.py` (do not import that package).

1. Read CSV from S3.
2. Normalize IDs (zfill, FIPS vs `HEROP_ID`).
3. Join HEROP `oeps/` shapefile for `{spatial_level}-{boundary_year}`.
4. Dissolve matched units → **simplify** → WKT.
5. `bounding_box` / `centroid` from that outline.
6. `highlight_ids` from the ID join (same include / exclude / `050US*` idea as `coverage.py`) — **not** from a spatial intersection. **2018 only** for a non-empty list (see vintages).
7. `spatial_coverage` — pending Marynia; default assumption is unique **state names**, plus `United States` / `Contiguous US` when coverage is national / CONUS. **No Census Place intersect in v1** (slow, huge lists, poor Solr facets).

Existing `coverage.py` HEROP URLs (2018 examples):

```
https://herop-geodata.s3.us-east-2.amazonaws.com/oeps/county-2018-500k-shp.zip
```

Levels: `state` `040US` (id len 2), `county` `050US` (5), `tract` `140US` (11), `bg` `150US` (12), `zcta` `860US` (5). Full HEROP_ID table and `highlight_ids` include/exclude/`*` rules: [handoff-context.md](handoff-context.md).

When porting `coverage.py`: enum `blockgroup` ≠ map key `bg` (KeyError). Lambda `spatial_level` is `bg`. Prefer a `FIPS` column, else `geo_id_column`; zfill; then `prefix + FIPS == HEROP_ID`.

**Simplify is required.** Today’s ~18KB figure is a simplified US polygon. A raw county/tract dissolve can exceed the 6MB sync payload and hurt Solr. Even with async, keep WKT small. Test DOSE-SYS, County Health Rankings, and a tract-level national file before calling size “fine.”

**Time budget:** still time real files. Async avoids the 30s HTTP kill, but Lambda max is 15 minutes; tract-national dissolve can still fail. Plan a container image (geopandas/GDAL), not a zip.

### Geo path

Read zip shapefile or GeoJSON → reproject EPSG:4326 → simplify → same output fields. `highlight_ids` for geo uploads may need a spatial join onto 2018 HEROP units; if that is not ready, return `[]` + warning rather than inventing IDs.

### Vintages (pending Marynia on tiles)

Facts:

- Merge shapefiles (`oeps/`): **2010 and 2018**.
- Discovery app tiles: **2018 only** (`<level>-2018.pmtiles`). 2010 `highlight_ids` would paint a **blank** Show coverage map.

Proposed v1 (Pengyin agreed pending Marynia):

| `boundary_year` | geometry / coverage | `highlight_ids` |
| --- | --- | --- |
| 2018 | 2018 `oeps/` shapefiles | full ID-join list |
| 2010 | **2010** `oeps/` shapefiles | `[]` + warning that tiles are 2018-only |

This is **not** “2010 IDs drawn on 2018 boundaries.” Snapping 2010 data to 2018 geometry would be a different policy. No 2010→2018 crosswalk in v1. Adding 2010 pmtiles is Marynia’s call.

### Out of scope (v1)

- Raster (NLCD, 30m canopy) — envelope only, not this dissolve pipeline (confirm Marynia).
- Census Place intersect for `spatial_coverage`.
- Lambda importing the Flask app. Tiny shared package or duplicated bbox/centroid formatting with the same fixtures. Manager may recompute bbox/centroid if a curator hand-edits geometry.

---

## 7. AWS / IAM

Yong owns Lambda IAM + deploys. Pengyin created the uploads bucket **`herop-sdohplace-upload`** (`us-east-2`; name is singular, not `uploads`).

In place:

- Yong console user (`ywkim@illinois.edu`)
- Execution role `herop-sdohplace-spatial-role`: trust `lambda.amazonaws.com`; inline S3 GetObject on the bucket / PutObject on `*/result.json`; `AWSLambdaBasicExecutionRole` for logs (`AWSLambdaExecute` removed)
- `herop-geodata` public `GetObject` for `oeps/` (no extra IAM on the Lambda role for v1)

Still needed:

- **EC2 instance role:** `lambda:InvokeFunction` on `herop-sdohplace-spatial` — Pengyin will add this when the function exists (ping her)
- Confirm `iam:PassRole` on `herop-sdohplace-spatial-role` when creating the function

---

## 8. Open — wait for Marynia (`@Makosak`)

Do not implement merge/dissolve until these are decided (skeleton/docs are OK).

1. **`spatial_coverage` grain** — confirm state names + `United States` / `Contiguous US`; Census Places deferred.
2. **Vintage / tiles** — keep 2010 geometry + empty `highlight_ids`, or add 2010 pmtiles so Show coverage works for 2010.
3. **Multi-resolution records** — map shows all levels or only the finest? One Generate = one `spatial_level` regardless.
4. **Raster** — out of this pipeline, envelope only.
5. **Large test files** — 3–4 real files (DOSE-SYS, County Health Rankings, tract-national, awkward cases) to time-budget against.
6. **Manager write policy** — refuse to save below some `match_rate` even when Lambda returns `ok: true`?

Regular (not stress) tests: download via discovery app [search.sdohplace.org](https://search.sdohplace.org) **Go to Resource**. Box / OEPS copies TBD with Marynia.

---

## 9. Still needed from Pengyin

- Confirm job-folder key pattern vs `uploads/{record_id}/{timestamp}-{filename}` (folder form is for async poll).
- `lambda:InvokeFunction` on the EC2 role after the function exists.
- Shared bbox/centroid fixtures if the manager will recompute on hand-edit.

---

## 10. Implementation order (after §8)

1. Skeleton: handler reads input, writes a stub `result.json` (no geopandas yet).
2. S3 read + `upload_kind: geo` reproject/simplify (no HEROP join).
3. CSV ID join against 2018 `oeps/` (port `coverage.py`).
4. Dissolve + simplify → WKT, bbox, centroid, `highlight_ids`.
5. 2010 path per vintage policy.
6. Container image, IAM, async invoke smoke test from a dummy payload.
7. End-to-end on DOSE-SYS with the manager Generate button (Pengyin).

Acceptance from #87: DOSE-SYS geometry covers the states the record actually claims (47, not Alaska-only).
