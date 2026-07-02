"""Tests for expand_to_series: a series found in the lookahead window should
pull in the rest of its games even when they fall outside the window.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from nzihl_rosters.schedule import Game, expand_to_series, group_into_series
from nzihl_rosters.teams import TEAMS

NZ_TZ = ZoneInfo("Pacific/Auckland")

RED_DEVILS = TEAMS["RED DEVILS"]
SWARM = TEAMS["SWARM"]
ADMIRALS = TEAMS["ADMIRALS"]
THUNDER = TEAMS["THUNDER"]


def _dt(y, m, d, h=19, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=NZ_TZ)


def test_sunday_game_pulled_in_when_saturday_is_in_window():
    # Weekend series: Sat 4 Jul (in window) + Sun 5 Jul (outside a naive
    # 4-day window from a Wednesday sweep).
    sat = Game(_dt(2026, 7, 4, 19, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    sun = Game(_dt(2026, 7, 5, 15, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    all_games = [sat, sun]

    window_games = [sat]  # only Saturday inside the raw cutoff
    expanded = expand_to_series(window_games, all_games)

    assert len(expanded) == 2
    assert sat in expanded and sun in expanded
    assert expanded == sorted(expanded, key=lambda g: g.start_local)


def test_unrelated_series_not_pulled_in():
    sat = Game(_dt(2026, 7, 4, 19, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    sun = Game(_dt(2026, 7, 5, 15, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    # A different matchup entirely, also upcoming but not in the window and
    # not part of the same series — must NOT be pulled in.
    other = Game(_dt(2026, 7, 6, 18, 0), away=ADMIRALS, home=THUNDER, is_final=False)
    all_games = [sat, sun, other]

    window_games = [sat]
    expanded = expand_to_series(window_games, all_games)

    assert other not in expanded
    assert len(expanded) == 2


def test_rematch_more_than_3_days_later_not_pulled_in():
    # Same two teams, but the next meeting is weeks away — group_into_series
    # already treats that as a separate series, and expand_to_series must
    # respect that boundary.
    sat = Game(_dt(2026, 7, 4, 19, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    later = Game(_dt(2026, 7, 18, 19, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    all_games = [sat, later]

    window_games = [sat]
    expanded = expand_to_series(window_games, all_games)

    assert later not in expanded
    assert expanded == [sat]


def test_final_games_excluded_from_expansion():
    # Saturday already played (final) by the time of a later run; only the
    # still-upcoming Sunday game should surface via its own window match.
    sat = Game(_dt(2026, 7, 4, 19, 0), away=SWARM, home=RED_DEVILS, is_final=True,
               away_score=3, home_score=2)
    sun = Game(_dt(2026, 7, 5, 15, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    all_games = [sat, sun]

    window_games = [sun]
    expanded = expand_to_series(window_games, all_games)

    assert expanded == [sun]


def test_empty_window_returns_empty():
    assert expand_to_series([], [Game(_dt(2026, 7, 4), away=SWARM, home=RED_DEVILS, is_final=False)]) == []


def test_expanded_games_still_group_into_one_series_for_pdf():
    sat = Game(_dt(2026, 7, 4, 19, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    sun = Game(_dt(2026, 7, 5, 15, 0), away=SWARM, home=RED_DEVILS, is_final=False)
    expanded = expand_to_series([sat], [sat, sun])
    series = group_into_series(expanded)
    assert len(series) == 1
    assert series[0] == [sat, sun]
