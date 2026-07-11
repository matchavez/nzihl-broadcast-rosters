"""Emit a machine-readable stats.json snapshot for the whole NZIHL registry.

The nightly roster pipeline already scrapes stats_1team.cfm (skaters +
goalies) and personnel.cfm (coaches) to build the roster PDFs, but only for
the teams playing in the current PDF window. This module reuses the exact
same parsers (scraper.scrape_team / parse_coaches) to scrape EVERY team in
the registry, every run, and writes a single stats.json a downstream
consumer (the Player Lower Thirds control page) can fetch season stats
from for any team, regardless of whether that team happens to be in the
current roster-PDF window.

Best-effort per team: a single team's scrape failing (network hiccup,
page reshape) must not take down the whole export — that team is simply
omitted from this run's stats.json (its previous committed values stay on
disk until the next successful run overwrites them).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from .teams import TEAMS, Team
from .scraper import (
    scrape_team,
    fetch_personnel_html,
    parse_coaches,
)


def _skater_dict(row) -> dict:
    return {
        "number": row.jersey,
        "first": row.first,
        "last": row.last,
        "position": row.position,
        "flag": row.flag,
        "gp": row.gp,
        "g": row.g,
        "a": row.a,
        "pts": row.g + row.a,
        "pim": row.pim,
    }


def _goalie_dict(row) -> dict:
    return {
        "number": row.jersey,
        "first": row.first,
        "last": row.last,
        "flag": row.flag,
        "gp": row.gp,
        "min": row.mp,
        "ga": row.ga,
        "gaa": row.gaa,
        "sv_pct": row.sv_pct,
        "so": row.so,
        "w": row.w,
        "l": row.l,
    }


def _coach_dict(row) -> dict:
    return {"title": row.title, "first": row.first, "last": row.last}


def scrape_team_stats(team: Team, client_id: int, league_id: int) -> dict:
    """Scrape one team's skaters/goalies/coaches into stats.json's per-team shape."""
    skaters, goalies = scrape_team(team.team_id)
    try:
        coaches = parse_coaches(fetch_personnel_html(team.team_id, client_id, league_id))
    except Exception:
        coaches = []
    return {
        "team_id": team.team_id,
        "display_name": team.display_name,
        "skaters": [_skater_dict(r) for r in skaters],
        "goalies": [_goalie_dict(r) for r in goalies],
        "coaches": [_coach_dict(r) for r in coaches],
    }


def scrape_all_teams_stats(client_id: int = 7131, league_id: int = 35499) -> dict[str, dict]:
    """Scrape every registered team. Best-effort per team — a failure for one
    team logs and is skipped rather than aborting the whole export."""
    out: dict[str, dict] = {}
    for team in TEAMS.values():
        try:
            out[team.short_code] = scrape_team_stats(team, client_id, league_id)
        except Exception as exc:  # noqa: BLE001 — best-effort, one team can't sink the run
            print(f"    ! stats.json: {team.short_code} scrape failed: {exc}")
    return out


def write_stats_json(
    out_path: Path,
    league_key: str,
    client_id: int = 7131,
    league_id: int = 35499,
    teams_stats: dict[str, dict] | None = None,
) -> dict:
    """Scrape (unless `teams_stats` is pre-supplied, e.g. by a test) and write
    stats.json. Returns the written payload dict."""
    if teams_stats is None:
        teams_stats = scrape_all_teams_stats(client_id, league_id)
    payload = {
        "generated_at": date.today().isoformat(),
        "league": league_key,
        "teams": teams_stats,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload
