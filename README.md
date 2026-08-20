# SDOHPlace-SpatialPipeline

AWS Lambda pipeline that derives spatial metadata (geometry, bbox, centroid, coverage, highlight IDs) for [SDOH Place](https://github.com/healthyregions/SDOHPlace-MetadataManager).

The manager calls this function and writes the result onto a metadata record. This repo does **not** save records or index Solr.

Read these **before coding** (a new Cursor window will not have the old chat):

1. [docs/pipeline-contract.md](docs/pipeline-contract.md) — input/output, S3, async, open questions
2. [docs/handoff-context.md](docs/handoff-context.md) — Alaska bug, HEROP_ID, GitHub/Slack decisions, folders

Development branch: `dev`.
