# SDOHPlace-SpatialPipeline

AWS Lambda pipeline that derives spatial metadata (geometry, bbox, centroid, coverage, highlight IDs) for [SDOH Place](https://github.com/healthyregions/SDOHPlace-MetadataManager).

The manager calls this function and writes the result onto a metadata record. This repo does **not** save records or index Solr.

**Contract and process:** [docs/pipeline-contract.md](docs/pipeline-contract.md)

Development branch: `dev`.
