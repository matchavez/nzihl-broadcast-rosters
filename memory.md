# memory.md — matchavez/nzihl-broadcast-rosters

Self-context for Claude. README.md is solid and human-facing (install/run instructions, schema) — was corrected 2026-07-11 (stale data-source claim, obsolete initial-scaffold section, stale cron reference, NZWIHL note repointed at the sibling repo). This file adds the automation state, gotchas, and cross-repo wiring README doesn't cover. Last refreshed: 2026-07-11 (coaching-staff line added).

## What this repo is
Daily GitHub Action that renders one A4 roster PDF per upcoming NZIHL series (goalies top, skaters by jersey #, top-3 scorers highlighted, "not yet played" group), pulling live data from esportsdesk, and publishes them as a GitHub Release. Sibling repo **nzwihl-broadcast-rosters** is the same pipeline for the women's league.

## Layout
`src/nzihl_rosters/{teams,overrides,scraper,schedule,layout,cli}.py`, `tests/` (fixture-driven unit tests), `.github/workflows/build-rosters.yml`, `boxscores.json` (committed gameid manifest, self-pruning >3 days past date).

## Automation
- Cron `30 17 * * *` UTC = 07:30ish NZT depending on DST. The workflow comment was fixed 2026-07-11 (used to say "19:00 UTC", now correctly says 17:30 UTC).
- Generates PDFs for games within **4 days** (`--within-days 4`) but the committed `boxscores.json` manifest looks **11 days** ahead (`--manifest-within-days 11`) so the hockeyrosters page can show "coming soon" further out than the PDF actually exists. These two windows are intentionally decoupled — don't "fix" one to match the other.
- Runs unit tests before generating; release is named `rosters-<run number>`.

## Coaching staff line (2026-07-11)
Roster PDFs now render a compact `HC <name>   AC <name>, <name>` strip under
each team's header band, above GOALIES. Source is `personnel.cfm` — same
esportsdesk platform/host as `stats_1team.cfm`, just a different endpoint
(`admin.esportsdesk.com/leagues/personnel.cfm?clientid=7131&leagueid=35499&teamid=<id>`).
It returns a simple Title/Name table (Team Staff, Physio, General Manager,
Head Coach, Assistant Coach ×N, Team Lead) — only Head Coach/Assistant Coach
rows are kept (`scraper.py`'s `CoachRow`/`parse_coaches`/`fetch_personnel_html`).
The Name cell holds first/last on separate lines within one `<td>` (a literal
newline, not a `<br>`) — worth remembering if this ever needs re-parsing.

Design went through one round of Mat's feedback: the first version was a
"COACHING STAFF" section header (matching GOALIES/SKATERS style) with two
stacked lines. Mat: "narrow this quite a bit... lose Coaching Staff, lead
each with HC and AC, and get it onto one line." Current version does that —
see `layout.py`'s `draw_team`, right after the header-band `cur_y` line —
and still auto-shrinks + ellipsis-truncates as a safety net, since the very
first side-by-side attempt (before that safety net existed) clipped off the
page edge on a team with long assistant-coach names.

Wiring: `cli.py`'s `build_series_pdf` calls a `_fetch_coaches()` helper
that's best-effort (`try/except -> []`) so a `personnel.cfm` hiccup can't
fail an otherwise-good roster PDF. `build_roster_pdf`'s `away_coaches`/
`home_coaches` kwargs default to `None` (→ no line drawn), so this is a
backward-compatible addition, not a breaking one.

Ported in lockstep to the NZWIHL sibling (commit 0af589a there) — same
`personnel.cfm` endpoint works with NZWIHL's `clientid=7132&leagueid=35501`.

## stats.json export (2026-07-12)
Added `src/nzihl_rosters/stats_export.py`, wired into `cli.py` as a best-effort
step (try/except, can't fail an otherwise-good roster run) right after the
boxscores manifest write. Emits `stats.json` at repo root:
`{"generated_at": "<date>", "league": "nzihl", "teams": {"<TLA>": {"skaters":[...],"goalies":[...],"coaches":[...]}}}`,
one entry per team scraped from `stats_1team.cfm` (skaters now also carry
`pim`; goalies carry `ga`/`so`/`w`/`l` -- all via header-label column lookup,
default 0 if the column's absent, same robustness pattern as the rest of
`scraper.py`). `build-rosters.yml` commits it alongside the boxscores
manifest, diffing on content (`jq -S 'del(.generated_at)'`) so an unchanged
day produces no commit.

**Why it exists:** feeds the new **Player Lower Thirds** control page
(`matchavez/hockey`'s `hockey/lowerthirds/` + `activity-banner/`) season
stat lines -- see Claude's `nzihl-player-lower-thirds` memory. This repo
and its NZWIHL sibling are the sole source of season totals for that
project; `nzihl-season-data` covers *completed game* history instead.

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
