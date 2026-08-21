"""Tests for fetch_schedule_html()'s retry-on-empty-response behaviour.

Regression coverage for the 2026-08-22 incident: a manual off-schedule run
got back a 200 OK merged schedule page with zero day-header and zero
inline-date matches (esportsdesk's playoff bracket page appears to be
hand-edited after each game and can be served mid-edit), so the pipeline
silently reported "no upcoming games" instead of retrying.
"""
from __future__ import annotations

from nzihl_rosters import schedule


def test_fetch_schedule_html_retries_when_response_has_no_game_markup(monkeypatch):
    empty_page = "<html><body>nothing here</body></html>"
    real_page = "<h5><strong>Sat 22 Aug, 2026</strong></h5>"
    calls = {"n": 0}

    def fake_fetch(url, *, timeout=30):
        calls["n"] += 1
        # First round (default page + 3 explicit month pages) comes back
        # empty; the second round returns real content.
        return empty_page if calls["n"] <= 4 else real_page

    sleeps = []
    monkeypatch.setattr(schedule, "fetch", fake_fetch)
    monkeypatch.setattr(schedule.time, "sleep", lambda s: sleeps.append(s))

    html = schedule.fetch_schedule_html()

    assert "Sat 22 Aug, 2026" in html
    assert sleeps == [schedule.FETCH_RETRY_DELAY_SECONDS]
    assert calls["n"] == 8  # two full rounds of 4 fetches each


def test_fetch_schedule_html_gives_up_after_max_attempts_without_crashing(monkeypatch):
    empty_page = "<html><body>nothing here</body></html>"

    monkeypatch.setattr(schedule, "fetch", lambda url, **kw: empty_page)
    monkeypatch.setattr(schedule.time, "sleep", lambda s: None)

    html = schedule.fetch_schedule_html()

    # Never raises — still returns the (empty) merged pages so the normal
    # "no upcoming games" reporting path in cli.py handles it gracefully.
    assert html.count("nothing here") == 4


def test_fetch_schedule_html_does_not_retry_when_first_response_has_content(monkeypatch):
    real_page = "<h5><strong>Sat 22 Aug, 2026</strong></h5>"
    calls = {"n": 0}

    def fake_fetch(url, *, timeout=30):
        calls["n"] += 1
        return real_page

    monkeypatch.setattr(schedule, "fetch", fake_fetch)
    monkeypatch.setattr(schedule.time, "sleep", lambda s: (_ for _ in ()).throw(
        AssertionError("should not sleep when the first response already has content")))

    schedule.fetch_schedule_html()
    assert calls["n"] == 4  # exactly one round, no retry


def test_looks_empty_true_for_blank_html():
    assert schedule._looks_empty("<html><body>nothing</body></html>")


def test_looks_empty_false_when_day_header_present():
    assert not schedule._looks_empty("<h5><strong>Sat 22 Aug, 2026</strong></h5>")


def test_looks_empty_false_when_inline_date_present():
    assert not schedule._looks_empty("Aug. 22, 2026 @ 7:00 PM")
