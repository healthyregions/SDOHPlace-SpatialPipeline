"""upload_kind=geo: zip shapefile or GeoJSON → EPSG:4326 → simplify.

No HEROP join. highlight_ids is [] plus a warning. No GeoPackage / gdb / KML.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from typing import Any

import geopandas as gpd
from shapely.geometry import GeometryCollection
from shapely.ops import unary_union

from sdohplace_spatial.aardvark import centroid_lat_lon, envelope
from sdohplace_spatial.errors import PipelineError

SIMPLIFY_TOLERANCES = (0.001, 0.01, 0.05, 0.1)
MAX_WKT_CHARS = 500_000
GEOJSON_SUFFIXES = (".geojson", ".json")
HIGHLIGHT_WARNING = (
    "highlight_ids is empty for geo uploads in this version; "
    "HEROP spatial join is not implemented yet"
)
COVERAGE_WARNING = (
    "spatial_coverage is empty pending product grain (state names); "
    "not derived from place-name matching"
)


def _suffix(s3_key: str) -> str:
    return os.path.splitext(s3_key.lower())[1]


def derive_geo(file_bytes: bytes, s3_key: str) -> dict[str, Any]:
    suffix = _suffix(s3_key)
    if suffix in (".kml", ".kmz", ".gpkg", ".gdb"):
        raise PipelineError(
            "unreadable_file",
            f"v1 geo path does not support '{suffix}'. Use a shapefile zip or GeoJSON.",
        )
    if suffix not in GEOJSON_SUFFIXES and suffix != ".zip":
        raise PipelineError(
            "unreadable_file",
            f"Cannot read '{suffix}' as geo. Expected .geojson, .json, or .zip (shapefile).",
        )

    tmp = tempfile.mkdtemp(prefix="sdoh-geo-")
    try:
        gdf = _read_geodataframe(file_bytes, suffix, tmp)
        geom = _to_simplified_4326(gdf, suffix)
        wkt = geom.wkt
        if len(wkt) > MAX_WKT_CHARS:
            raise PipelineError(
                "too_large",
                f"Simplified WKT is still {len(wkt)} characters (limit {MAX_WKT_CHARS}).",
            )
        minx, miny, maxx, maxy = geom.bounds
        c = geom.centroid
        return {
            "ok": True,
            "geometry": wkt,
            "bounding_box": envelope(minx, maxx, maxy, miny),
            "centroid": centroid_lat_lon(c.x, c.y),
            "spatial_coverage": [],
            "highlight_ids": [],
            "diagnostics": {
                "rows_in": int(len(gdf)),
                "matched": int(len(gdf)),
                "unmatched": 0,
                "unmatched_sample": [],
                "match_rate": 1.0,
                "warnings": [HIGHLIGHT_WARNING, COVERAGE_WARNING],
            },
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _read_geodataframe(file_bytes: bytes, suffix: str, tmp: str) -> gpd.GeoDataFrame:
    try:
        if suffix in GEOJSON_SUFFIXES:
            path = os.path.join(tmp, "upload.geojson")
            with open(path, "wb") as handle:
                handle.write(file_bytes)
            return gpd.read_file(path)
        _assert_shapefile_zip(file_bytes)
        path = os.path.join(tmp, "upload.zip")
        with open(path, "wb") as handle:
            handle.write(file_bytes)
        return gpd.read_file(path)
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError("unreadable_file", f"Could not read geo upload: {exc}") from exc


def _assert_shapefile_zip(file_bytes: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
            names = [name.lower() for name in zf.namelist()]
    except zipfile.BadZipFile as exc:
        raise PipelineError("unreadable_file", "Upload is not a valid zip.") from exc
    if not any(name.endswith(".shp") for name in names):
        raise PipelineError(
            "unreadable_file",
            "Zip does not contain a .shp shapefile (sidecars required).",
        )


def _to_simplified_4326(gdf: gpd.GeoDataFrame, suffix: str):
    if gdf.empty or gdf.geometry.isna().all():
        raise PipelineError("empty_geometry", "Geo upload has no usable geometries.")
    if gdf.crs is None:
        if suffix in GEOJSON_SUFFIXES:
            gdf = gdf.set_crs(4326)
        else:
            raise PipelineError(
                "unsupported_crs",
                "Shapefile is missing a CRS. Assign a CRS and re-upload.",
            )
    try:
        gdf = gdf.to_crs(4326)
    except Exception as exc:
        raise PipelineError("unsupported_crs", f"Could not reproject to EPSG:4326: {exc}") from exc

    merged = unary_union(list(gdf.geometry.dropna()))
    if merged is None or merged.is_empty:
        raise PipelineError("empty_geometry", "Dissolve produced empty geometry.")
    if isinstance(merged, GeometryCollection):
        merged = unary_union([part for part in merged.geoms if not part.is_empty])
        if merged.is_empty:
            raise PipelineError("empty_geometry", "Dissolve produced empty geometry.")

    simplified = None
    for tolerance in SIMPLIFY_TOLERANCES:
        candidate = merged.simplify(tolerance, preserve_topology=True)
        if candidate.is_empty:
            continue
        simplified = candidate
        if len(candidate.wkt) <= MAX_WKT_CHARS:
            return candidate
    if simplified is None or simplified.is_empty:
        raise PipelineError("empty_geometry", "Simplify produced empty geometry.")
    return simplified
