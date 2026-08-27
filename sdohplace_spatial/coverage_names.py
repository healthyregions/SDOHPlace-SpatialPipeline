"""spatial_coverage from matched HEROP units (IDs), not from place-name strings."""

from __future__ import annotations

from typing import Any, Iterable

from sdohplace_spatial.states import (
    CONUS_FIPS,
    NATIONAL_FIPS,
    STATE_FP_LOOKUP,
    state_fips_from_herop_id,
)

ZCTA_STATE_COLUMNS = ("STATEFP", "STATE_FIPS", "STATEFP10", "STATEFP20")


def _fips_from_zcta_master(matched_gdf: Any) -> set[str]:
    if matched_gdf is None:
        return set()
    for col in ZCTA_STATE_COLUMNS:
        if col in matched_gdf.columns:
            values = matched_gdf[col].dropna().astype(str).str.zfill(2)
            return {v for v in values if v in STATE_FP_LOOKUP}
    return set()


def spatial_coverage_from_matches(
    matched_ids: Iterable[str],
    spatial_level: str,
    matched_gdf: Any = None,
) -> list[str]:
    fips: set[str] = set()
    for hid in matched_ids:
        fp = state_fips_from_herop_id(str(hid), spatial_level)
        if fp:
            fips.add(fp)
    if spatial_level == "zcta":
        fips |= _fips_from_zcta_master(matched_gdf)

    names = sorted({STATE_FP_LOOKUP[f] for f in fips if f in STATE_FP_LOOKUP})
    if not names:
        return []
    if NATIONAL_FIPS <= fips:
        names.append("United States")
    elif CONUS_FIPS <= fips:
        names.append("Contiguous US")
    return names
