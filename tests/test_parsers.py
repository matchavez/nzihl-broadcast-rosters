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


def test_skaters_parse_correctly_with_extra_columns():
    """Regression test: a stats_1team.cfm revision that inserts a BY (birth
    year) column — and appends P/G, +/-, PPG, etc. — must not shift GP/G/A
    off by one. Columns are located by header label, not a fixed offset."""
    html = (FIXTURES / "team_redDevils_v2cols.html").read_text()
    skaters = parse_skaters(html, team_id=675633)
    by_num = {s.jersey: s for s in skaters}

    g = by_num["88"]
    assert g.gp == 12 and g.g == 20 and g.a == 11
    assert g.position == "F"
    assert g.plus_minus == "13"

    brown = by_num["8"]
    assert brown.gp == 12 and brown.g == 1 and brown.a == 4
    assert brown.plus_minus == "-7"
    assert brown.flag == "C"

    henare = by_num["7"]
    assert henare.plus_minus == "E"


def test_skaters_plus_minus_blank_when_column_absent():
    """The original (no BY, no +/-) layout must still parse cleanly, with
    plus_minus defaulting to blank rather than erroring or misreading PTS."""
    html = (FIXTURES / "team_redDevils_min.html").read_text()
    skaters = parse_skaters(html, team_id=675633)
    assert all(s.plus_minus == "" for s in skaters)


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


def test_goalies_parse_correctly_with_extra_by_column():
    """Regression test: a stats_1team.cfm revision that inserts a BY (birth
    year) column between "#" and "GP" in the GOALIE STATISTICS table must
    not zero out GP (which previously made every goalie fall through to the
    bench as "hasn't played", even when GP/MP were real)."""
    html = (FIXTURES / "team_redDevils_v2cols.html").read_text()
    goalies = parse_goalies(html, team_id=675633)
    assert len(goalies) == 1
    fanning = goalies[0]
    assert fanning.jersey == "52"
    assert fanning.first == "Niall"
    assert fanning.last == "FANNING"
    assert fanning.gp == 1, f"expected gp=1, got {fanning.gp!r} (BY column likely misread as GP)"
    assert fanning.mp == 61
    assert fanning.gaa == "3.93"
    assert fanning.sv_pct == ".920"


def test_goalies_parse_correctly_with_broken_tooltip_header():
    """Regression test: the live GOALIE STATISTICS table wraps header labels
    in `<span title="...">` tooltips, and the GAA tooltip's title attribute
    embeds a literal `<br />` (e.g. "Goals Against Average<br />(based on a
    60 minute game)"). A naive tag-stripping regex treats that embedded `<`/`>`
    as a real tag boundary, garbling the cleaned "GAA" label so the header
    lookup misses it and silently falls back to the wrong column (GA's index).
    Confirmed against SkyCity Stampede's real GP=5 goalies Joel Gerard and
    Aston Brookes, whose GAA (3.19 / 3.39) was being misread as their GA
    (16 / 17) before this fix."""
    html = (FIXTURES / "team_stampede_broken_tooltip.html").read_text()
    goalies = parse_goalies(html, team_id=675635)
    by_num = {g.jersey: g for g in goalies}

    gerard = by_num["35"]
    assert gerard.gp == 5 and gerard.mp == 301
    assert gerard.gaa == "3.19", f"expected gaa=3.19, got {gerard.gaa!r} (GAA tooltip likely misparsed as GA)"
    assert gerard.sv_pct == ".905"

    brookes = by_num["39"]
    assert brookes.gp == 5 and brookes.mp == 301
    assert brookes.gaa == "3.39", f"expected gaa=3.39, got {brookes.gaa!r}"
    assert brookes.sv_pct == ".909"


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
