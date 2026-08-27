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

from sdohplace_spatial.aardvark import centroid_lat_lon, envelope
from sdohplace_spatial.errors import PipelineError
from sdohplace_spatial.outline import GEOJSON_SUFFIXES, MAX_WKT_CHARS, outline_from_gdf
HIGHLIGHT_WARNING = (
    "highlight_ids is empty for geo uploads in this version; "
    "HEROP spatial join is not implemented yet"
)
COVERAGE_WARNING = (
    "spatial_coverage is empty for geo uploads in this version; "
    "state names come from CSV ID join, not from the file geometry"
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
        geom = outline_from_gdf(gdf, allow_missing_crs=suffix in GEOJSON_SUFFIXES)
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
