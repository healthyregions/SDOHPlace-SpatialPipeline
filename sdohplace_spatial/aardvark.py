"""Aardvark / OGM string formats. WKT is lon-lat; centroid is lat,lon."""

from __future__ import annotations


def envelope(west: float, east: float, north: float, south: float) -> str:
    return f"ENVELOPE({_coord(west)},{_coord(east)},{_coord(north)},{_coord(south)})"


def centroid_lat_lon(longitude: float, latitude: float) -> str:
    return f"{_coord(latitude)},{_coord(longitude)}"


def _coord(value: float) -> str:
    return f"{float(value):.6f}"
