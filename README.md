# nzihl-broadcast-rosters

Auto-generated single-page roster PDFs for the NZIHL broadcast booth. Pulls
live rosters and the upcoming schedule from esportsdesk (`admin.esportsdesk.com`,
the no-cache origin), applies a few name corrections the league hasn't fixed yet,
and renders one PDF per upcoming series.

Runs daily on GitHub Actions; PDFs land as a release artifact attached
to the run, and a `boxscores.json` gameid manifest is committed back to the repo.

## What it produces

For each upcoming series within the next 4 days, one A4 portrait PDF:

- Two columns, away team on the left, home team on the right.
- Centred team-name header in the team primary colour.
- A compact `HC <name>   AC <name>, <name>` coaching-staff line under each
  team's header band, scraped from `personnel.cfm` (same platform as the
  roster stats). No line is drawn if a team has no Head/Assistant Coach
  listed — the lookup is best-effort and never fails the whole PDF.
- Goalie cards across the top (GP > 0 only) with `GP / GAA / SV%`.
- Skaters sorted by jersey #, with `POS  G  A` columns.
- Top-3 scorers per team (by G+A) get a pale honey row highlight.
- Players who haven't dressed yet — including goalies — fall into a dimmed
  "NOT YET PLAYED THIS SEASON" group at the bottom of each column.

`boxscores.json` separately lists games up to **11 days** out (no PDF yet),
so the `hockeyrosters` page can show them further ahead as "coming soon."

## Project layout

```
src/nzihl_rosters/
  teams.py         # registry: team_id, display name, colours, home venue
  overrides.py     # explicit name overrides + title-casing
  scraper.py       # parses stats_1team.cfm + personnel.cfm into Skater/Goalie/CoachRow lists
  schedule.py      # parses schedules.cfm into a list of upcoming Games
  boxscores.py     # gameid resolution + boxscores.json manifest writer
  layout.py        # the single-page PDF builder
  cli.py           # CLI: schedule → filter window → group → render
.github/workflows/build-rosters.yml   # daily cron (17:30 UTC), publishes release
boxscores.json     # committed gameid manifest (self-prunes entries >3 days old)
tests/             # unit tests against hand-crafted HTML fixtures
```

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

# What would run today?
python -m nzihl_rosters --within-days 4 --dry-run

# Actually render the PDFs into ./output/, plus the boxscores.json manifest
# (11-day lookahead by default, independent of --within-days)
python -m nzihl_rosters --within-days 4 --manifest-within-days 11 --output ./output
```

## Automation

The workflow runs daily at **17:30 UTC** (roughly 05:30 NZST / 06:30 NZDT —
timed to land before 7am NZ time despite GitHub Actions' scheduling delay).
Any games within the next 4 days get their roster PDFs attached to a release
named `rosters-<run number>`.

Trigger a run manually any time:

```bash
gh workflow run "Build rosters"
```

## Adding a player-name override

Edit `src/nzihl_rosters/overrides.py`:

```python
SURNAME_OVERRIDES = {
    # (team_id, jersey_number): (correct_surname, correct_first_or_None)
}
```

The override is keyed by `(team_id, jersey)` so it survives even if NZIHL
records the wrong name. Pure lowercase names (e.g. `harry louw`) are
auto-title-cased by `normalize_name`, so you only need explicit entries
for names that need a *non-trivial* correction.

## Adding / updating a team

Edit `src/nzihl_rosters/teams.py`. The colours come from the
**2026 NZIHL/NZWIHL Style Guide** in the `nzihl-broadcast-assets` repo.

## Testing

```bash
PYTHONPATH=src python -m pytest tests/
```

The fixture-based tests don't hit the network — they verify the parser
against hand-crafted HTML snippets that mirror the real structure. The
CI workflow also runs the live fetch as part of every build, so any
upstream HTML drift will surface as a workflow failure.

## Known gotchas

- **Round labels** are derived from the calendar week from 8 May 2026.
  If the season schedule changes, refresh `_round_label` in `cli.py`.
- **NZWIHL is a separate repo, not an extension of this one.** The women's
  league is built by [matchavez/nzwihl-broadcast-rosters](https://github.com/matchavez/nzwihl-broadcast-rosters) —
  its own package, own team registry, own workflow. This repo's registry only
  ever covers the 5 NZIHL men's franchises currently wired up; that's expected,
  not a to-do.
- **Player flags `A` (alternate captain) and `C` (captain)** are rendered
  in the team's primary colour like other text flags. NZIHL only tags
  one alternate per game; if multiple should be shown, edit the source.
