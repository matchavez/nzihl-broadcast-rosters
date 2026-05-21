"""Player-name corrections to apply on top of scraped NZIHL data.

NZIHL stores some names in the wrong case or shortened. The registry
below records explicit corrections; `normalize_name` applies them and
also title-cases names that arrived all-lowercase.
"""
from __future__ import annotations

# (team_id, jersey_number) -> (override_last, override_first | None)
# `override_first=None` means leave first name alone (just fix the surname).
SURNAME_OVERRIDES: dict[tuple[int, str], tuple[str, str | None]] = {
    # Canterbury Red Devils #7 — NZIHL has him as "Henare", real name is Te Rangi Henare.
    (675633, "7"): ("Te Rangi Henare", None),
}


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
