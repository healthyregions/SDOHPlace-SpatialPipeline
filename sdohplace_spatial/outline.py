"""Dissolve + simplify to EPSG:4326. Shared by geo uploads and CSV ID-join."""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import GeometryCollection
from shapely.ops import unary_union

from sdohplace_spatial.errors import PipelineError

SIMPLIFY_TOLERANCES = (0.001, 0.01, 0.05, 0.1)
MAX_WKT_CHARS = 500_000
GEOJSON_SUFFIXES = (".geojson", ".json")


def outline_from_gdf(gdf: gpd.GeoDataFrame, *, allow_missing_crs: bool = False):
    if gdf.empty or gdf.geometry.isna().all():
        raise PipelineError("empty_geometry", "No usable geometries to dissolve.")
    if gdf.crs is None:
        if allow_missing_crs:
            gdf = gdf.set_crs(4326)
        else:
            raise PipelineError(
                "unsupported_crs",
                "Geometry is missing a CRS. Assign a CRS and re-upload.",
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
    if len(simplified.wkt) > MAX_WKT_CHARS:
        raise PipelineError(
            "too_large",
            f"Simplified WKT is still {len(simplified.wkt)} characters (limit {MAX_WKT_CHARS}).",
        )
    return simplified
