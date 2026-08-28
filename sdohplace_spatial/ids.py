"""Normalize FIPS / GEOID / HEROP_ID. Do not import the Flask manager."""

from __future__ import annotations

from sdohplace_spatial.errors import PipelineError
from sdohplace_spatial.levels import CENSUS_LENGTHS, LEVELS

ID_CANDIDATES = ("FIPS", "HEROP_ID", "GEOID", "geoid", "GEO_ID")


def extract_geoid(raw: object) -> str:
    text = str(raw).strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
    if "." in text:
        text = text.split(".", 1)[0]
    upper = text.upper()
    if "US" in upper:
        text = text[upper.index("US") + 2 :]
    return text.strip()


def herop_prefix_of(raw: object) -> str | None:
    text = str(raw).strip().upper()
    if "US" not in text:
        return None
    idx = text.index("US")
    if idx < 3:
        return None
    return text[idx - 3 : idx + 2]


def pick_id_column(columns: list[str], geo_id_column: str | None) -> str:
    if "FIPS" in columns:
        return "FIPS"
    if geo_id_column and geo_id_column in columns:
        return geo_id_column
    for name in ID_CANDIDATES:
        if name in columns:
            return name
    raise PipelineError(
        "no_id_column",
        "No FIPS / GEOID / HEROP_ID column found. Pass geo_id_column if the field has another name.",
    )


def geoids_from_series(values, id_length: int) -> list[str]:
    # Excel/pandas may have stripped leading zeros (06037 → 6037). Pad back
    # before prefix + FIPS == HEROP_ID. Join key stays a string, never int.
    return [extract_geoid(v).zfill(id_length) if extract_geoid(v) else "" for v in values]


def reject_mixed_levels(raw_values, spatial_level: str) -> None:
    spec = LEVELS[spatial_level]
    expected = spec["id_length"]
    expected_prefix = spec["prefix"]
    other_lengths = CENSUS_LENGTHS - {expected}
    prefixes = set()
    for raw in raw_values:
        prefix = herop_prefix_of(raw)
        if prefix:
            prefixes.add(prefix)
        geoid = extract_geoid(raw)
        if not geoid:
            continue
        length = len(geoid)
        if length in other_lengths:
            raise PipelineError(
                "mixed_spatial_level",
                f"CSV has GEOID length {length} which is not {spatial_level} ({expected} digits).",
            )
    if prefixes and prefixes != {expected_prefix}:
        raise PipelineError(
            "mixed_spatial_level",
            f"CSV HEROP_ID prefixes {sorted(prefixes)} do not match {spatial_level} ({expected_prefix}).",
        )
