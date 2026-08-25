"""highlight_ids encoding from coverage.py (fixed matching-id list)."""

from __future__ import annotations


def encode_highlight_ids(prefix: str, master_ids: list[str], matched_ids: set[str]) -> list[str]:
    missing = [hid for hid in master_ids if hid not in matched_ids]
    total = len(master_ids)
    if not missing:
        return [f"{prefix}*"]
    if total and len(missing) < total / 2:
        return [f"-{hid}" for hid in missing]
    return [hid for hid in master_ids if hid in matched_ids]
