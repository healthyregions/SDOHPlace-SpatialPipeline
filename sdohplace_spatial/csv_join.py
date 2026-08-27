"""CSV ID join against US Census vintage shapefiles under oeps/. No Flask import."""

from __future__ import annotations

import io
from typing import Any

import geopandas as gpd
import pandas as pd

from sdohplace_spatial.aardvark import centroid_lat_lon, envelope
from sdohplace_spatial.errors import PipelineError
from sdohplace_spatial.highlight import encode_highlight_ids
from sdohplace_spatial.ids import geoids_from_series, pick_id_column, reject_mixed_levels
from sdohplace_spatial.levels import (
    LEVELS,
    SUPPORTED_BOUNDARY_YEARS,
    normalize_spatial_level,
    shapefile_url,
)
from sdohplace_spatial.outline import outline_from_gdf

COVERAGE_WARNING = (
    "spatial_coverage is empty pending product grain (state names); "
    "not derived from place-name matching"
)
HIGHLIGHT_2010_WARNING = (
    "highlight_ids is empty because discovery tiles are 2018-only; "
    "2010 geometry is still returned for map search"
)
UNMATCHED_SAMPLE = 10


def load_oeps(spatial_level: str, year: int) -> gpd.GeoDataFrame:
    url = shapefile_url(spatial_level, year)
    try:
        gdf = gpd.read_file(url)
    except Exception as exc:
        raise PipelineError(
            "unreadable_file",
            f"Could not read {year} {spatial_level} boundaries from oeps/: {exc}",
        ) from exc
    if "HEROP_ID" not in gdf.columns:
        raise PipelineError(
            "unreadable_file",
            f"{year} {spatial_level} shapefile has no HEROP_ID column.",
        )
    gdf = gdf.copy()
    gdf["HEROP_ID"] = gdf["HEROP_ID"].astype(str)
    return gdf


def load_oeps_2018(spatial_level: str) -> gpd.GeoDataFrame:
    return load_oeps(spatial_level, 2018)


def derive_csv(
    file_bytes: bytes,
    event: dict[str, Any],
    master_gdf: gpd.GeoDataFrame | None = None,
) -> dict[str, Any]:
    year = event.get("boundary_year", 2018)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = 2018
    if year not in SUPPORTED_BOUNDARY_YEARS:
        raise PipelineError(
            "unsupported_vintage",
            f"CSV join supports boundary_year 2010 or 2018, not {year}.",
        )

    spatial_level = normalize_spatial_level(event.get("spatial_level"))
    spec = LEVELS[spatial_level]
    prefix = spec["prefix"]
    id_length = spec["id_length"]

    try:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
    except Exception as exc:
        raise PipelineError("unreadable_file", f"Could not read CSV: {exc}") from exc
    if df.empty:
        raise PipelineError("no_matching_ids", "CSV has no data rows.")

    column = pick_id_column(list(df.columns), event.get("geo_id_column"))
    reject_mixed_levels(df[column].tolist(), spatial_level)
    df = df.copy()
    df["_geoid"] = geoids_from_series(df[column], id_length)
    df["_hid"] = prefix + df["_geoid"]
    df.loc[df["_geoid"] == "", "_hid"] = ""

    master = master_gdf if master_gdf is not None else load_oeps(spatial_level, year)
    master = master.copy()
    master["HEROP_ID"] = master["HEROP_ID"].astype(str)
    master_ids = master["HEROP_ID"].tolist()
    master_set = set(master_ids)

    row_ok = df["_hid"].isin(master_set)
    matched_count = int(row_ok.sum())
    unmatched_count = int((~row_ok).sum())
    rows_in = int(len(df))
    unmatched_sample = df.loc[~row_ok, column].astype(str).head(UNMATCHED_SAMPLE).tolist()

    if matched_count == 0:
        raise PipelineError(
            "no_matching_ids",
            f"None of the {rows_in} values in column '{column}' matched {spatial_level} boundaries for {year}.",
        )

    matched_ids = set(df.loc[row_ok, "_hid"])
    matched_gdf = master[master["HEROP_ID"].isin(matched_ids)]
    geom = outline_from_gdf(matched_gdf)
    wkt = geom.wkt
    minx, miny, maxx, maxy = geom.bounds
    c = geom.centroid

    warnings = [COVERAGE_WARNING]
    if year == 2018:
        highlight_ids = encode_highlight_ids(prefix, master_ids, matched_ids)
    else:
        highlight_ids = []
        warnings.append(HIGHLIGHT_2010_WARNING)
    if unmatched_count:
        warnings.append(
            f"{unmatched_count} IDs did not match the {year} {spatial_level} boundary vintage"
        )

    return {
        "ok": True,
        "geometry": wkt,
        "bounding_box": envelope(minx, maxx, maxy, miny),
        "centroid": centroid_lat_lon(c.x, c.y),
        "spatial_coverage": [],
        "highlight_ids": highlight_ids,
        "diagnostics": {
            "rows_in": rows_in,
            "matched": matched_count,
            "unmatched": unmatched_count,
            "unmatched_sample": unmatched_sample,
            "match_rate": matched_count / rows_in,
            "boundary_year_used": year,
            "warnings": warnings,
        },
    }
