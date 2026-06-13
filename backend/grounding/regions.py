"""Country-based Ansar user pool prefilter (analogous to jurisdiction.py for legal chunks)."""

from __future__ import annotations

# Seed user UUID suffix ranges per region (from ansar_users.json clusters)
REGION_USER_RANGES: dict[str, tuple[int, int]] = {
    "FIN": (1, 20),
    "GBR": (21, 25),
    "EU": (26, 30),
    "BGD": (31, 37),
    "LBN": (38, 44),
    "SDN": (45, 50),
}

# Primary region per crisis country + optional diaspora regions
COUNTRY_REGIONS: dict[str, list[str]] = {
    "FIN": ["FIN", "EU"],
    "GBR": ["GBR", "EU"],
    "BGD": ["BGD"],
    "LBN": ["LBN"],
    "SDN": ["SDN"],
}

MIN_POOL_SIZE = 5


def _user_id_for_index(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


def user_ids_for_country(country_iso: str | None) -> list[str] | None:
    """Return ordered list of candidate user UUIDs for a crisis country.

    Returns None when no region mapping exists (caller should load all users).
    """
    if not country_iso:
        return None

    regions = COUNTRY_REGIONS.get(country_iso.upper())
    if not regions:
        return None

    ids: list[str] = []
    seen: set[str] = set()
    for region in regions:
        start, end = REGION_USER_RANGES[region]
        for i in range(start, end + 1):
            uid = _user_id_for_index(i)
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
    return ids
