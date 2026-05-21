# nzihl-broadcast-rosters

Auto-generated single-page roster PDFs for the NZIHL broadcast booth. Pulls
live rosters and the upcoming schedule from `nzihl.com`, applies a few
name corrections the league hasn't fixed yet (e.g. **Te Rangi Henare**),
and renders one PDF per upcoming series.

Runs daily on GitHub Actions; PDFs land as a release artifact attached
to the run.

## What it produces

For each upcoming series within the next 4 days, one A4 portrait PDF:

- Two columns, away team on the left, home team on the right.
- Centred team-name header in the team primary colour.
- Goalie cards across the top (GP > 0 only) with `GP / GAA / SV%`.
- Skaters sorted by jersey #, with `POS  G  A` columns.
- Top-3 scorers per team (by G+A) get a pale honey row highlight.
- Players who haven't dressed yet — including goalies — fall into a dimmed
  "NOT YET PLAYED THIS SEASON" group at the bottom of each column.

## Project layout

```
src/nzihl_rosters/
  teams.py         # registry: team_id, display name, colours, home venue
  overrides.py     # explicit name overrides (Te Rangi Henare) + title-casing
  scraper.py       # parses stats_1team.cfm into Skater/GoalieRow lists
  schedule.py      # parses schedules.cfm into a list of upcoming Games
  layout.py        # the single-page PDF builder
  cli.py           # CLI: schedule → filter window → group → render
.github/workflows/build-rosters.yml   # daily cron, publishes release
tests/             # unit tests against hand-crafted HTML fixtures
```

## Quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

# What would run today?
python -m nzihl_rosters --within-days 4 --dry-run

# Actually render the PDFs into ./output/
python -m nzihl_rosters --within-days 4 --output ./output
```

## Push to GitHub

The code is ready; create the repo and push:

```bash
cd /path/to/nzihl-broadcast-rosters

# 1. Create the GitHub repo (one of)
gh repo create matchavez/nzihl-broadcast-rosters --public --source=. --remote=origin --push
# …or via the web UI, then:
# git init && git remote add origin git@github.com:matchavez/nzihl-broadcast-rosters.git

# 2. Commit and push
git add .
git commit -m "Initial scaffold: NZIHL roster auto-builder"
git branch -M main
git push -u origin main
```

That's it — once the default branch lands, the workflow's daily cron
will fire at 19:00 UTC (07:00 NZ) and any games within the next 4 days
will have their roster PDFs attached to a release named
`rosters-<run number>`.

You can also trigger it manually any time:

```bash
gh workflow run "Build rosters"
```

## Adding a player-name override

Edit `src/nzihl_rosters/overrides.py`:

```python
SURNAME_OVERRIDES = {
    (675633, "7"): ("Te Rangi Henare", None),
    # (team_id, jersey_number): (correct_surname, correct_first_or_None)
}
```

The override is keyed by `(team_id, jersey)` so it survives even if NZIHL
records the wrong name. Pure lowercase names (e.g. `harry louw`) are
auto-title-cased by `normalize_name`, so you only need explicit entries
for names that need a *non-trivial* correction.

## Adding / updating a team

Edit `src/nzihl_rosters/teams.py`. The colours come from the
**2026 NZIHL/NZWIHL Style Guide** in the assets repo. NZWIHL teams will
need a parallel registry once we extend to the women's side.

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
- **NZWIHL not yet supported.** The team registry currently lists only
  the five NZIHL men's franchises.
- **Player flags `A` (alternate captain) and `C` (captain)** are rendered
  in the team's primary colour like other text flags. NZIHL only tags
  one alternate per game; if multiple should be shown, edit the source.
