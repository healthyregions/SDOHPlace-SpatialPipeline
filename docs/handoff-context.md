# Handoff context (do not lose)

This file is the rest of the Aug 2026 working session that is **not** already in [pipeline-contract.md](pipeline-contract.md). Read **both** files before writing code. That contract file is the interface; this file is why it looks that way, what was already said on GitHub/Slack, and Cursor-folder notes.

Issue: https://github.com/healthyregions/SDOHPlace-MetadataManager/issues/87  
Author of the issue: Pengyin Shan (`@pengyin-shan`). The separate-Lambda-repo idea is hers.  
Pipeline owner: Yong Wook Kim (`@ywkim312`).  
Product: Marynia Kolak (`@Makosak`). Data re-upload: Mallikarjun / GRA.

---

## Cursor / folders (read this first)

| | Path |
| --- | --- |
| Metadata Manager (old Cursor window / this chat lived here) | `C:\workspace-healthyregions\SDOHPlace-MetadataManager` |
| This pipeline repo | `C:\workspace-healthyregions\SDOHPlace-SpatialPipeline` |
| GitHub | https://github.com/healthyregions/SDOHPlace-SpatialPipeline |
| Branch | `dev` (also exists `main`, same initial commit then docs on `dev`) |
| Clone remote | `git@github.com:healthyregions/SDOHPlace-SpatialPipeline.git` |

A Cursor chat is tied to the **open folder**. Opening SpatialPipeline in a new window starts a **new** chat that cannot see the Metadata Manager thread. These two markdown files are the handoff.

Do **not** put Lambda code inside `SDOHPlace-MetadataManager` (not even `manager/`). One new repo only — not a second “shared library” repo in v1.

Yong **cannot create** repositories under `healthyregions` (GitHub org UI showed View as: Public, no New button). Pengyin created this repo. Ask her if another org repo is needed.

License: GPL-3.0 (same as Metadata Manager). Visibility: public.

---

## Why the pipeline exists

Geometry in the manager is **not** derived from data today. `Schema.make_record_data_from_form_data` in `manager/registry.py` looks at `spatial_coverage` strings, lowercased, in this **first-match** order, and only if `geometry` is empty:

1. `"united states"` → `full-us-simplified.geojson`
2. `"contiguous us"` → `contiguous-us-simplified.geojson`
3. `"alaska"` → `alaska-simplified.geojson`
4. `"hawaii"` → `hawaii-simplified.geojson`

An alphabetical US state list hits **Alaska** and stops. That is the defect. Do **not** “fix” it by smarter place-name matching. Coverage must come from **actual geometry / IDs**. Do **not** backfill geometry from place names as a stopgap. Do **not** hand-type HEROP_IDs. Existing records get corrected by running **source files through this pipeline**. Retire the `registry.py` place-name block **last**, after the replacement is proven (issue STEP 5).

Cherry-pick from production (issue §1):

| Record | Title | Claimed coverage | Stored geometry |
| --- | --- | --- | --- |
| `herop-rsulgs` | DOSE-SYS | 47 states | Alaska only |
| `herop-ddydvt` | Housing + Transportation Index | 51 states | Alaska only |

H+T’s `spatial_coverage` in the manager JSON is already a **51-state name list** (that is the grain we proposed for v1). Its `highlight_ids` is currently `["150US*"]` (block groups). Geometry is the Alaska polygon. `bounding_box` / `centroid` are `"None"`.

Issue Solr snapshot (`blacklight-core-prod`) at write-up time:

- 193 documents total
- 72 visible (`gbl_suppressed_b:false`); 121 suppressed (per-year children, correctly hidden)
- 33 visible with no coverage IDs → no Show coverage
- 0 of 193 have `dcat_bbox` or `dcat_centroid`
- 11 visible with no geometry → invisible to map search

Acceptance for this pipeline (issue §4.1): given DOSE-SYS, OEPS Data Package 2018, and County Health Rankings source files, return geometry covering the states the record actually claims — **47 for DOSE-SYS, not Alaska only**.

---

## Two different map features (do not conflate)

| | Map search | Show coverage |
| --- | --- | --- |
| What | Filter results as you pan/zoom | Redraw map with that dataset’s units |
| Driven by | `locn_geometry` via `Intersects(ENVELOPE(w,e,n,s))` | **`sdoh_highlight_ids_sm` only** |
| Discovery code | `SolrQueryBuilder.tsx` | `resultCard.tsx` |
| Breaks when | geometry missing/wrong | ID list empty → button greyed out |

`dcat_bbox` and `dcat_centroid` drive **neither** today (no hits in discovery `src/` or shipped JS). They are FAIR / Google Dataset Search / DCAT harvesters. Still return them in Aardvark format.

Pengyin’s original Lambda output was only four fields: `geometry`, `bounding_box`, `centroid`, `spatial_coverage`. Yong asked to add `highlight_ids` (Show coverage) and `diagnostics`. Pengyin adopted that JSON (see contract). Original prose mentioned a `derived` wrapper; **do not wrap**.

---

## HEROP_ID

Format: `<3-digit census summary level>US<GEOID/FIPS>`. Unique across levels; stays a string; GEOID is everything after `US` (or strip the first 5 characters).

| Level | Prefix | GEOID length | Example |
| --- | --- | --- | --- |
| State | `040US` | 2 | `040US17` Illinois |
| County | `050US` | 5 | `050US17019` Champaign County |
| Tract | `140US` | 11 | `140US17019005900` |
| Block group | `150US` | 12 | `150US170190059002` |
| ZCTA | `860US` | 5 | `860US61801` |

Org write-up: https://github.com/healthyregions/geodata and https://geodata.healthyregions.org

Schema wildcards for `highlight_ids`: `040US*`, `050US*`, `140US*`, `150US*`, `860US*`, or `050US17*` (all counties in Illinois), or a specific id like `040US17`. Minus filters: `coverage.py` uses `-{HEROP_ID}` when fewer than half of master units are missing.

`coverage.py` encoding (port this, do not invent a new scheme):

- 0 missing vs master shapefile → `["050US*"]` (prefix + `*`)
- missing &lt; half of master → list of `-{HEROP_ID}` for missing
- missing ≥ half → list of matching `HEROP_ID`s

CSV ID detection in `coverage.py`: prefer column `FIPS`, else `geo_id_column`. zfill to `id_length`. Then prefix + FIPS must equal `HEROP_ID`.

**Pitfall when porting:** `SpatialResolution` enum value `blockgroup` does not match map key `bg`. Calling `to_prefix()` for block groups would KeyError. Use `bg` in Lambda `spatial_level`. Manager maps `"Census Block Group"` → `bg`.

Flask already has `flask generate-highlight-ids` (`manager/commands.py`) wrapping `check_coverage`. The Lambda **replaces** that manual CLI for the Generate button.

---

## Uploads and who clicks Generate

Two upload paths, **one** Generate button (Pengyin):

1. **Curator** attaches a file in the manager → S3 → clicks Generate.
2. **Contributor** (discovery app) uploads directly to S3; manager only records that a file exists. File sits untouched until a curator reviewing that submission clicks Generate.

No compute on rejected submissions. Nothing written into a record before a human looks at it. `record_id` (like `herop-xxxxxx`) is assigned when the record/submission is created, **before** Generate.

Original issue S3 delete-after-use: **rejected**. Agreed: **keep-until-publish** (or lifecycle expiry). Re-run Generate must not require a re-upload if the object is still there.

Pengyin’s first key sketch (flat file):

```
uploads/{record_id}/{timestamp}-{filename}
e.g. uploads/herop-rsulgs/20260820T143022Z-dose_sys_counties.csv
```

Yong’s async tweak (job **folder**), confirmed by Pengyin Aug 2026 (and reconfirmed in Slack):

```
uploads/{record_id}/{timestamp}/{filename}
uploads/{record_id}/{timestamp}/result.json
```

One Generate click = one directory. Several jobs can exist at once (different `{timestamp}` folders). Not “only one job on the whole bucket.” Bucket she created: **`herop-sdohplace-upload`** (singular), `us-east-2`, no public access. Execution role: `herop-sdohplace-spatial-role`.

HEROP merge files live in **`oeps/`** on `herop-geodata` (2010 and 2018 shapefiles). Discovery **tiles** live under **`sdohplace/`** and are **2018 only** for all six levels; frontend hardcodes `<level>-2018.pmtiles`. Those two prefixes are easy to mix up.

---

## Async (why, and what changed)

Issue first draft was **synchronous** invoke, no API, no token, no callback. Production manager: gunicorn **30s** (binding), nginx **60s**, not Docker, start/stop scripts, Dockerfile unused. Lambda 15 minutes is **not** the UI limit.

Agreed: **async**. Do not raise gunicorn. `InvocationType=Event`. Write `result.json`. Manager polls S3. **No callback URL** into nginx. No API Gateway. Auth = IAM on EC2 + Lambda roles.

6MB sync payload is no longer the return path, but **WKT size still matters** (Solr `locn_geometry`, result.json, manager form). Today’s ~18KB is the **simplified** whole-US polygon already in the manager, not a raw dissolve. Always simplify. Plan a **Lambda container image** (geopandas/GDAL), not a zip. Lambda `/tmp` is ephemeral; delete local copies. Max runtime 15 minutes still applies.

---

## Frontend constraint (Pengyin’s manager/discovery work, not this repo)

`dynamicMap.tsx` currently takes the **first** highlight ID’s 3-character prefix and draws **one** tile layer. A list like `["050US*","140US*"]` shows counties and **drops tracts**. That is why OEPS Data Package highlights only counties.

Pengyin demoed multi-color Show coverage (county orange, tract purple, etc.) against a **manually edited** OEPS `highlight_ids`. Marynia likes the concept; keep it on a **Discovery branch** (alpha, colorblind contrast, temporal slider). Do not treat that demo as a reason for Lambda to emit mixed-level IDs from one CSV. Lambda still: **one** `spatial_level` per Generate. Until the branch ships, mixed-level `highlight_ids` will not all render.

---

## Manager-side work (Pengyin; do not duplicate here)

- Generate button on record + submission-with-file
- boto3 async invoke + poll `result.json` + failures/timeouts
- Mandatory pre-write **snapshot** + one-command rollback
- List of “changed, not yet published”
- Recompute bbox/centroid at persist if curator **hand-edits** geometry after Lambda
- S3 presigned URLs for contributors; staff upload; keep-until-publish + lifecycle
- Retire `registry.py` place-name geometry **last**
- Shared bbox/centroid Aardvark formatting — Lambda must **not** `import manager`. Tiny shared package later, or duplicate ~20 lines with the same fixtures
- Discovery contribution form: file + boundary year + spatial level + geo-id column
- Convert #87 bullets into separate GitHub issues **after** the interface (and Marynia) settle — she offered to assign them; Yong asked to wait

Issue STEP 3 e2e: one record (DOSE-SYS) → Generate → snapshot → save → confirm **not** yet in Solr → curator review → index → verify on discovery.

Ownership she stated: Yong = Lambda **end to end on AWS** (repo, function, IAM, deploys). Pengyin = metadata manager + frontend. EC2 still needs a policy she/ops attach: S3 upload/poll/delete + `lambda:InvokeFunction`.

---

## What was already posted (so we do not contradict it)

Yong’s #87 comment: §3 answers (Lambda does CSV merge; partial match + diagnostics; extra input clarifications; add `highlight_ids` + `diagnostics`) and concerns **A–G** (geometry size, gunicorn/async, skip CDP intersect, keep-until-publish, no Flask import, one spatial_level, HEROP vintages).

Pengyin agreed: simplify + test real files; keep-until-publish; no Flask import; boto3+IAM no API Gateway; error shape; async after checking gunicorn 30s.

She asked Marynia: spatial_coverage grain; vintage/2010 pmtiles; multi-resolution map (all levels vs finest); raster out of scope; 3–4 large files; should the **manager** refuse to write below a match_rate even if `ok: true`.

Vintage correction Yong sent: 2010 data → **2010** `oeps/` shapefiles for geometry/coverage; empty `highlight_ids` because tiles are 2018. **Not** 2010 IDs on 2018 boundaries. She had assumed the latter; we corrected it. She will let Marynia decide 2010 pmtiles.

Testing she suggested meanwhile: [search.sdohplace.org](https://search.sdohplace.org) **Go to Resource**. Box / OEPS existence to confirm with Marynia.

Related sibling repos (not this pipeline): `sdohplace-data-discovery`, `sdohplace-intake-api`, `SDOHPlace-MetadataManager`, `geodata`.

---

## Slack follow-ups (do not rewrite Lambda v1 from these)

**S3 keys (Pengyin reconfirm).** Folder form `uploads/{record_id}/{timestamp}/{filename}` + sibling `result.json` is what the manager will poll. One job = one directory; several jobs can exist at once. PutObject on the uploads bucket is already granted.

**Discovery multi-scale colors (Pengyin + Marynia).** Frontend-only. Pengyin keeps the branch until this pipeline has processed existing data. Marynia: more testing (line alpha, colorblind, temporal slider / Big Ten portal). Lambda still one `spatial_level` per Generate.

**Vintage tiles vs this Lambda.** Discovery currently pins 2018 pmtiles; the time slider does not swap boundaries. Marynia: 2018 is not accurate for most data; new vintage pmtiles (and later slider assets) are the product direction. Pengyin: a vintage metadata field is needed because `highlight_id` cannot tell 2010 from 2018 — **v2 / Discovery**. This repo still returns 2010 geometry from 2010 shapefiles and empty `highlight_ids` until those tiles exist.

**Pengyin v1/v2 table (Aug 2026).** She asked to align, then said Yong’s BYO / result.json / no-v2-now reading was what she needed. V2 pmtiles stay a future record, not current work. One leftover sentence in her Show coverage row still says Lambda may emit `highlight_ids` for “geographic data matching 2018 units”; v1 geo path does **not** do that join. CSV `boundary_year=2018` is the 2018 highlight_ids case.

**Census vintage, not “OEPS vintage” (Marynia).** CSV join is to **US Census** vintages in [healthyregions/geodata](https://github.com/healthyregions/geodata) (the same files OEPS uses). `oeps/` is only the S3 prefix. OEPS is an example dataset for testing.

**Bring-your-own boundaries (Marynia).** Preferred path: curator/contributor supplies Census or custom polygons (`upload_kind: geo`); Lambda uses that geometry. Merge to the Census vintage library **only** when the file is CSV-only, with explicit `boundary_year` + `spatial_level`. RAs re-gathering assets this semester = more Generate inputs, not a new pipeline. Map search comes from `locn_geometry`. Show coverage for custom polygons is still a Discovery gap (HEROP `highlight_ids` + 2018 tiles). Do not join geo uploads onto HEROP just to fill `highlight_ids`.

---

## v1 out of scope (tiny but easy to accidentally build)

- GeoPackage / file gdb / KML (geo path is zip shapefile or GeoJSON only)
- 2010→2018 ID crosswalk
- Spatial-joining geo uploads onto HEROP units so custom polygons get `highlight_ids`
- Publishing pmtiles (geodata / Discovery; Marynia wants vintage tiles, not this repo)
- Census Place (CDP) intersect for `dct_spatial_sm`
- Raster dissolve (NLCD, 30m canopy) — envelope only if in scope at all
- Mixed spatial levels in one CSV
- Importing the Flask app into Lambda
- Writing Solr or record JSON from Lambda
- Raising gunicorn timeout instead of async
- Place-name → geometry
- A second GitHub repo for “shared spatial module” in v1

---

## Suggested error_code strings

Not a frozen enum, but use these so manager and Lambda match:

| `error_code` | When |
| --- | --- |
| `not_implemented` | Stub handler only; derivation not built yet. Manager can still poll `result.json`. |
| `unreadable_file` | Cannot read CSV/zip/GeoJSON |
| `no_id_column` | No FIPS / GEOID / HEROP_ID / named column |
| `no_matching_ids` | Zero IDs matched the chosen vintage/level |
| `empty_geometry` | Dissolve produced nothing |
| `mixed_spatial_level` | More than one level in one CSV |
| `unsupported_crs` | Geo path missing/unusable CRS |
| `too_large` | WKT/result still too big after simplify |
| `unsupported_vintage` | If Marynia says reject 2010 instead of empty highlight_ids |

---

## Do not treat these as frozen

v1 defaults are in [pipeline-contract.md](pipeline-contract.md) §8 (Pengyin Aug 2026, plus Marynia BYO-boundaries / vintage-tile notes). Marynia asked to prototype now and refine in September/October with Mallikarjun (edge cases / full dataset runs) and a GRA (research + later v2). Census Place and vintage pmtiles stay outside this Lambda.
