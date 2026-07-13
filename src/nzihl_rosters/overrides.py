"""Player-name corrections to apply on top of scraped NZIHL data.

NZIHL stores some names in the wrong case or shortened. The registry
below records explicit corrections; `normalize_name` applies them and
also title-cases names that arrived all-lowercase.

SINGLE SOURCE OF TRUTH (2026-07-13): the constants below are only the
FALLBACK snapshot. `load_remote_overrides()` fetches the real canonical
data from nzihl-broadcast-assets/assets/name-overrides.json and replaces
them in place; called once near the top of cli.main(). If that fetch
fails, these hardcoded values keep scraping working exactly as before --
a name-overrides.json outage should never break a scheduled scrape.
"""
from __future__ import annotations

# (team_id, jersey_number) -> (override_last, override_first | None)
# `override_first=None` means leave first name alone (just fix the surname).
SURNAME_OVERRIDES: dict[tuple[int, str], tuple[str, str | None]] = {
    # No active overrides. Add entries here as NZIHL name issues are flagged.
}

# Two-word surnames to keep whole when scraper.py's _split_first_last would
# otherwise naively split at the last space. Referenced there via the
# `overrides` module object (NOT `from .overrides import MULTI_WORD_SURNAMES`)
# so a later load_remote_overrides() rebind is actually seen -- a bare import
# would keep pointing at the object that existed at import time.
MULTI_WORD_SURNAMES: set[str] = {"hayward jones", "de jonge"}


def _smart_title(text: str) -> str:
    """Title-case a name but preserve common particles and hyphenated parts.

    e.g. "kercso-magos" -> "Kercso-Magos", "MacDonald" stays "MacDonald".
    Only title-cases when the string is entirely lower or entirely upper.
    """
    if not text:
        return text
    is_all_lower = text == text.lower()
    is_all_upper = text == text.upper()
    if not (is_all_lower or is_all_upper):
        # mixed-case names (MacDonald, McKenzie, etc.) are already right
        return text

    def cap_part(part: str) -> str:
        if not part:
            return part
        return part[0].upper() + part[1:].lower()

    # split on hyphens then spaces, capitalising each part
    return " ".join(
        "-".join(cap_part(seg) for seg in word.split("-"))
        for word in text.split(" ")
    )


def normalize_name(first: str, last: str, team_id: int, jersey: str) -> tuple[str, str]:
    """Apply title-casing and per-player overrides.

    Returns (first_clean, last_clean).
    """
    first_clean = _smart_title(first.strip())
    last_clean = _smart_title(last.strip())

    override = SURNAME_OVERRIDES.get((team_id, jersey))
    if override:
        override_last, override_first = override
        last_clean = override_last
        if override_first is not None:
            first_clean = override_first

    return first_clean, last_clean


NAME_OVERRIDES_URL = (
    "https://raw.githubusercontent.com/matchavez/nzihl-broadcast-assets/"
    "main/assets/name-overrides.json"
)
_LEAGUE = "nzihl"


def load_remote_overrides(*, timeout: int = 10) -> bool:
    """Fetch the canonical name-overrides.json (single source of truth across
    every broadcast-asset repo -- see matchavez/hockey's
    nzihl_player_name_overrides memory) and replace this module's
    MULTI_WORD_SURNAMES / SURNAME_OVERRIDES in place.

    Call once near the top of cli.main(), before any scraping starts. On any
    failure this leaves the hardcoded fallback values above untouched and
    returns False -- a scheduled scrape must never hard-fail just because
    this one extra fetch didn't land.
    """
    global MULTI_WORD_SURNAMES, SURNAME_OVERRIDES
    import requests

    try:
        resp = requests.get(NAME_OVERRIDES_URL, timeout=timeout)
        resp.raise_for_status()
        cfg = resp.json()
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, see docstring
        print(f"warning: could not fetch name-overrides.json ({exc}); using built-in fallback")
        return False

    words = cfg.get("multi_word_surnames")
    if words:
        MULTI_WORD_SURNAMES = {str(w).lower() for w in words}

    team_jersey = cfg.get("team_jersey_overrides")
    if team_jersey is not None:
        merged: dict[tuple[int, str], tuple[str, str | None]] = {}
        for entry in team_jersey:
            if entry.get("league") != _LEAGUE:
                continue
            key = (int(entry["team_id"]), str(entry["jersey"]))
            merged[key] = (entry["last"], entry.get("first"))
        SURNAME_OVERRIDES = merged

    return True
