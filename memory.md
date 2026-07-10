# memory.md — matchavez/nzihl-broadcast-rosters

Self-context for Claude. README.md is solid and human-facing (install/run instructions, schema). This file adds the automation state, gotchas, and cross-repo wiring README doesn't cover. Last refreshed: 2026-07-11.

## What this repo is
Daily GitHub Action that renders one A4 roster PDF per upcoming NZIHL series (goalies top, skaters by jersey #, top-3 scorers highlighted, "not yet played" group), pulling live data from esportsdesk, and publishes them as a GitHub Release. Sibling repo **nzwihl-broadcast-rosters** is the same pipeline for the women's league.

## Layout
`src/nzihl_rosters/{teams,overrides,scraper,schedule,layout,cli}.py`, `tests/` (fixture-driven unit tests), `.github/workflows/build-rosters.yml`, `boxscores.json` (committed gameid manifest, self-pruning >3 days past date).

## Automation
- Cron `30 17 * * *` UTC = 07:30ish NZT depending on DST — **the workflow file's own inline comment still says "19:00 UTC = 07:00 NZST/08:00 NZDT", which is stale** (cron was moved 19:00→17:30 UTC on 2026-07-04 to land before 7am NZT despite GitHub Actions scheduling delay). Trust the actual `cron:` value, not the comment, if they ever disagree again.
- Generates PDFs for games within **4 days** (`--within-days 4`) but the committed `boxscores.json` manifest looks **11 days** ahead (`--manifest-within-days 11`) so the hockeyrosters page can show "coming soon" further out than the PDF actually exists. These two windows are intentionally decoupled — don't "fix" one to match the other.
- Runs unit tests before generating; release is named `rosters-<run number>`.

## Known gotchas fixed here (useful if similar bugs resurface)
- **Month-boundary bug (2026-07-08):** gameid resolution for `last_final_gameid` silently returned null for *all* games whenever the league's last Final fell in the prior calendar month. Ported the fix pre-emptively from nzwihl-broadcast-rosters after it hit NZWIHL/Inferno.
- **Goalie GAA misread (2026-07-02):** a quote-unaware tag stripper broke on a tooltip's embedded `<br />`, causing GAA to be misread as GA. Debug this class of bug via a temp GH Actions artifact dump, not `web_fetch` (esportsdesk pages don't render meaningfully via plain fetch tooling).
- **Short codes:** Pure NZ Admirals' legacy `WAA` code was retired in favor of `ADM` (2026-07-10) to match the Style Guide TLA — if you see `WAA` anywhere it's stale.
- Player names are scraped lowercase; `overrides.py` title-cases via `normalize_name` and only needs explicit `SURNAME_OVERRIDES` entries for non-trivial corrections (keyed by `(team_id, jersey)` so it survives even if the league's own records are wrong). No active overrides as of last check (Henare override was removed 2026-06-16).

## Related repos
- **matchavez/nzwihl-broadcast-rosters** — same codebase pattern, separate repo, keep fixes in sync between the two (this repo currently leads on fixes, then ports to the sibling).
- **matchavez/hockeyrosters** — consumes `boxscores.json`/release PDFs to render the talent-facing download page.
- **matchavez/nzihl-season-data** — separate, longer-horizon warehouse of *completed* box scores (this repo only cares about *upcoming* games).

## Sync note
Keep this file and README.md in sync with every meaningful change. If they drift, flag it to Mat and get approval before publishing the sync rather than doing it silently.
