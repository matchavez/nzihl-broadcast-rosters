"""Parser tests against hand-crafted HTML fixtures that mirror the
structure of the live NZIHL pages. The real fetch is exercised in CI.
"""
from __future__ import annotations

from pathlib import Path

from nzihl_rosters.scraper import parse_skaters, parse_goalies
from nzihl_rosters.schedule import parse_schedule
from nzihl_rosters.teams import TEAMS

FIXTURES = Path(__file__).parent / "fixtures"


def test_skaters_parse_correctly():
    html = (FIXTURES / "team_redDevils_min.html").read_text()
    skaters = parse_skaters(html, team_id=675633)
    by_num = {s.jersey: s for s in skaters}

    # Gagnon: import, top scorer
    g = by_num["88"]
    assert g.first == "Alex"
    assert g.last == "GAGNON"
    assert g.gp == 4 and g.g == 5 and g.a == 3
    assert g.flag == "IM"
    assert g.position == "F"

    # Jersey 7: no override — surname is "Henare" as NZIHL lists it
    henare = by_num["7"]
    assert henare.last == "HENARE", f"got {henare.last!r}"
    assert henare.first == "Garth"

    # Lowercase auto-title-casing: "harry louw" → "Harry" / "LOUW"
    louw = by_num["81"]
    assert louw.first == "Harry"
    assert louw.last == "LOUW"

    # RO flag preserved
    barton = by_num["4"]
    assert barton.flag == "RO"
    assert barton.gp == 0


def test_goalies_parse_correctly():
    html = (FIXTURES / "team_redDevils_min.html").read_text()
    goalies = parse_goalies(html, team_id=675633)
    assert len(goalies) == 1
    fanning = goalies[0]
    assert fanning.jersey == "52"
    assert fanning.first == "Niall"
    assert fanning.last == "FANNING"
    assert fanning.gp == 1
    assert fanning.gaa == "3.93"
    assert fanning.sv_pct == ".920"


def test_schedule_parses_upcoming_only():
    html = (FIXTURES / "schedule_min.html").read_text()
    games = parse_schedule(html)
    # 4 game blocks: 1 final + 3 upcoming
    assert len(games) == 4, f"expected 4 games, got {len(games)}"
    finals = [g for g in games if g.is_final]
    upcoming = [g for g in games if not g.is_final]
    assert len(finals) == 1
    assert len(upcoming) == 3

    # First upcoming is Admirals @ Thunder on Fri 22 May 19:00
    first = upcoming[0]
    assert first.away.short_code == "WAA"
    assert first.home.short_code == "DUN"
    assert first.start_local.strftime("%Y-%m-%d %H:%M") == "2026-05-22 19:00"

    # Saturday weekend pair: Swarm @ Red Devils 17:10, then Admirals @ Thunder 18:30
    assert upcoming[1].away.short_code == "BSW"
    assert upcoming[1].home.short_code == "CRD"
    assert upcoming[1].start_local.strftime("%H:%M") == "17:10"
    assert upcoming[2].away.short_code == "WAA"
    assert upcoming[2].home.short_code == "DUN"
    assert upcoming[2].start_local.strftime("%H:%M") == "18:30"

    # Final game has the year embedded in the page (not inferred)
    fin = finals[0]
    assert fin.start_local.year == 2026
    assert fin.away.short_code == "CRD"
    assert fin.home.short_code == "SCS"
