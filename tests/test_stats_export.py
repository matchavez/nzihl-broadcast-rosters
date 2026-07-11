"""Tests for stats.json export (no network — fixture-driven)."""
import json
from pathlib import Path

from nzihl_rosters.scraper import parse_skaters, parse_goalies, parse_coaches
from nzihl_rosters import stats_export

FIXTURES = Path(__file__).parent / "fixtures"


def test_skater_dict_shape_and_pts_derivation():
    html = (FIXTURES / "team_redDevils_v2cols.html").read_text()
    skaters = parse_skaters(html, team_id=675633)
    d = stats_export._skater_dict(skaters[0])
    assert set(d) == {"number", "first", "last", "position", "flag", "gp", "g", "a", "pts", "pim"}
    assert d["pts"] == d["g"] + d["a"]


def test_goalie_dict_shape():
    html = (FIXTURES / "team_redDevils_v2cols.html").read_text()
    goalies = parse_goalies(html, team_id=675633)
    d = stats_export._goalie_dict(goalies[0])
    assert set(d) == {"number", "first", "last", "flag", "gp", "min", "ga", "gaa", "sv_pct", "so", "w", "l"}


def test_write_stats_json_shape(tmp_path):
    """write_stats_json with a pre-supplied teams_stats dict (bypassing the
    network scrape) — verifies the top-level payload shape a consumer
    (the Player Lower Thirds phone page) depends on."""
    fake_teams = {"CRD": {"team_id": 675633, "display_name": "Canterbury Red Devils",
                           "skaters": [], "goalies": [], "coaches": []}}
    out = tmp_path / "stats.json"
    payload = stats_export.write_stats_json(out, league_key="nzihl", teams_stats=fake_teams)
    assert payload["league"] == "nzihl"
    assert "generated_at" in payload
    assert payload["teams"] == fake_teams
    on_disk = json.loads(out.read_text())
    assert on_disk == payload


def test_scrape_all_teams_stats_skips_a_failing_team(monkeypatch):
    """One team's scrape_team_stats raising must not abort the whole export
    — best-effort, matches boxscores.py's philosophy elsewhere in this repo."""
    from nzihl_rosters.teams import TEAMS

    def fake_scrape_team_stats(team, client_id, league_id):
        if team.short_code == "CRD":
            raise RuntimeError("simulated network failure")
        return {"team_id": team.team_id, "display_name": team.display_name,
                "skaters": [], "goalies": [], "coaches": []}

    monkeypatch.setattr(stats_export, "scrape_team_stats", fake_scrape_team_stats)
    out = stats_export.scrape_all_teams_stats()
    assert "CRD" not in out
    assert len(out) == len(TEAMS) - 1
