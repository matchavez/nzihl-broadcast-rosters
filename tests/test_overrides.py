from __future__ import annotations

from nzihl_rosters import overrides
from nzihl_rosters.scraper import _split_first_last


def test_hayward_jones_and_de_jonge_split_whole():
    assert _split_first_last("Nash Hayward Jones") == ("Nash", "Hayward Jones")
    assert _split_first_last("Flynn Hayward Jones") == ("Flynn", "Hayward Jones")
    assert _split_first_last("Benjamin De Jonge") == ("Benjamin", "De Jonge")


def test_hyphenated_and_generic_regression():
    assert _split_first_last("Joel Keogh-Cope") == ("Joel", "Keogh-Cope")
    assert _split_first_last("Eli Seo Jun Paek") == ("Eli Seo Jun", "Paek")


def test_load_remote_overrides_success_updates_module_state(monkeypatch):
    fallback_multi = set(overrides.MULTI_WORD_SURNAMES)
    fallback_so = dict(overrides.SURNAME_OVERRIDES)

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "multi_word_surnames": ["hayward jones", "de jonge", "van berg"],
                "team_jersey_overrides": [
                    # nzwihl entry -- must be filtered out, this repo is nzihl-only
                    {"league": "nzwihl", "team_id": 675637, "jersey": "3",
                     "first": "Reagyn", "last": "Shattock"},
                ],
            }

    def fake_get(url, timeout=None):
        assert "name-overrides.json" in url
        return FakeResp()

    monkeypatch.setattr("requests.get", fake_get)
    try:
        assert overrides.load_remote_overrides() is True
        assert overrides.MULTI_WORD_SURNAMES == {"hayward jones", "de jonge", "van berg"}
        # nzwihl-only entry correctly excluded from this (nzihl) repo's table
        assert overrides.SURNAME_OVERRIDES == {}
        assert _split_first_last("Nash Hayward Jones") == ("Nash", "Hayward Jones")
        assert _split_first_last("A Van Berg") == ("A", "Van Berg")
    finally:
        overrides.MULTI_WORD_SURNAMES = fallback_multi
        overrides.SURNAME_OVERRIDES = fallback_so


def test_load_remote_overrides_failure_keeps_fallback(monkeypatch):
    fallback_multi = set(overrides.MULTI_WORD_SURNAMES)
    fallback_so = dict(overrides.SURNAME_OVERRIDES)

    def fake_get(url, timeout=None):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr("requests.get", fake_get)
    assert overrides.load_remote_overrides() is False
    # module state untouched -- a scheduled scrape must never regress just
    # because this one extra fetch failed
    assert overrides.MULTI_WORD_SURNAMES == fallback_multi
    assert overrides.SURNAME_OVERRIDES == fallback_so
