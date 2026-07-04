"""Tests for box-score gameid resolution (no network)."""
from datetime import date

from nzihl_rosters import boxscores


SHELL = """
<a href="/leagues/stats_1team.cfm?clientID=7131&teamID=674109&leagueID=35499&printPage=0"><b>Botany Swarm</b></a>
<a href="/leagues/stats_1team.cfm?clientID=7131&teamID=674109&leagueID=35499&printPage=0"><b>BSW</b></a>
NZIHL June 27th, 2026 4:45PM Avondale, Auckland
<a href="/leagues/stats_1team.cfm?clientID=7131&teamID=674110&leagueID=35499&printPage=0"><b>Pure NZ Admirals</b></a>
<a href="/leagues/stats_1team.cfm?clientID=7131&teamID=674110&leagueID=35499&printPage=0"><b>WAA</b></a>
Game Number: 25
"""

SCHEDULE = """
[FINAL](https://www.nzihl.com/leagues/hockey_boxscores.cfm?clientid=7131&leagueid=35499&gameid=2519935)
[FINAL](https://www.nzihl.com/leagues/hockey_boxscores.cfm?clientid=7131&leagueid=35499&gameid=2519936)
SAT 27 JUN tickets only, no boxscore link yet
"""


def test_parse_shell_orders_away_then_home_and_reads_date():
    parsed = boxscores.parse_shell(SHELL)
    assert parsed == {"away_id": 674109, "home_id": 674110, "date": date(2026, 6, 27)}


def test_parse_shell_rejects_non_game_page():
    assert boxscores.parse_shell("<html>no teams here, June stuff</html>") is None


def test_last_final_gameid_picks_the_max():
    assert boxscores.last_final_gameid(SCHEDULE) == 2519936


def test_public_boxscore_url_shape():
    url = boxscores.public_boxscore_url(2519937)
    assert "hockey_boxscores.cfm" in url and "gameid=2519937" in url
    assert "clientid=7131" in url and "leagueid=35499" in url


def test_prune_and_merge_drops_entries_older_than_keep_days():
    today = date(2026, 7, 2)
    existing = [
        {"date": "2026-06-24", "datetime": "2026-06-24T16:45:00+12:00",
         "away": "SkyCity Stampede", "home": "Botany Swarm"},
    ]
    merged = boxscores.prune_and_merge(existing, [], keep_days=3, today=today)
    assert merged == []  # well past the 3-day keep window


def test_prune_and_merge_keeps_recently_played_entries():
    today = date(2026, 7, 2)
    existing = [
        {"date": "2026-06-30", "datetime": "2026-06-30T16:45:00+12:00",
         "away": "SkyCity Stampede", "home": "Botany Swarm"},
    ]
    merged = boxscores.prune_and_merge(existing, [], keep_days=3, today=today)
    assert len(merged) == 1  # only 2 days old, still within the keep window


def test_prune_and_merge_new_games_replace_old_duplicate_and_sort():
    today = date(2026, 7, 2)
    existing = [
        {"date": "2026-07-04", "datetime": "2026-07-04T16:45:00+12:00",
         "away": "SkyCity Stampede", "home": "Botany Swarm", "gameid": None},
    ]
    new = [
        {"date": "2026-07-04", "datetime": "2026-07-04T16:45:00+12:00",
         "away": "SkyCity Stampede", "home": "Botany Swarm", "gameid": 2519941},
        {"date": "2026-07-05", "datetime": "2026-07-05T16:45:00+12:00",
         "away": "SkyCity Stampede", "home": "Botany Swarm", "gameid": 2519942},
    ]
    merged = boxscores.prune_and_merge(existing, new, keep_days=3, today=today)
    assert len(merged) == 2
    assert merged[0]["gameid"] == 2519941  # replaced, not duplicated
    assert merged[1]["date"] == "2026-07-05"


def test_resolve_marks_in_core_window_true_without_core_keys():
    """Back-compat: callers that don't pass core_keys (e.g. existing tests,
    single-window callers) get every game marked in_core_window=True."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from nzihl_rosters.schedule import Game
    from nzihl_rosters.teams import TEAMS

    swarm = TEAMS["SWARM"]
    admirals = TEAMS["ADMIRALS"]
    g = Game(datetime(2026, 7, 10, 16, 45, tzinfo=ZoneInfo("Pacific/Auckland")),
              away=swarm, home=admirals, is_final=False)
    out = boxscores.resolve([g], SCHEDULE)
    assert out[0]["in_core_window"] is True


def test_resolve_marks_in_core_window_false_when_outside_core_keys():
    """Games outside the narrower PDF window (not in core_keys) are still
    included in the manifest but flagged in_core_window=False, so pages that
    want the old narrow behaviour (the portal) can filter them back out while
    hockeyrosters shows them as 'coming soon'."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from nzihl_rosters.schedule import Game
    from nzihl_rosters.teams import TEAMS

    swarm = TEAMS["SWARM"]
    admirals = TEAMS["ADMIRALS"]
    near = Game(datetime(2026, 7, 6, 16, 45, tzinfo=ZoneInfo("Pacific/Auckland")),
                away=swarm, home=admirals, is_final=False)
    far = Game(datetime(2026, 7, 14, 16, 45, tzinfo=ZoneInfo("Pacific/Auckland")),
               away=admirals, home=swarm, is_final=False)
    core_keys = {(near.away.team_id, near.home.team_id, near.start_local)}
    out = boxscores.resolve([near, far], SCHEDULE, core_keys=core_keys)
    by_date = {o["date"]: o["in_core_window"] for o in out}
    assert by_date["2026-07-06"] is True
    assert by_date["2026-07-14"] is False
