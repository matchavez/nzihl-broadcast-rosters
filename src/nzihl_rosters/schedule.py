"""Parse the NZIHL schedule page into a list of upcoming games.

The real `schedules.cfm` page is organised as:

  <h5><strong>Fri 22 May, 2026</strong></h5>
  <table>
    <tr>
      <td>[Final](...) </td>             ← only present when game has been played
      or
      <td>7:00 PM</td>                    ← only present for upcoming games
      ...
      <td><a href="...stats_1team.cfm?...teamID=674110...">Pure NZ Admirals</a></td>
      ...
      <td><a href="...stats_1team.cfm?...teamID=675634...">Dunedin Thunder</a></td>
      ...
    </tr>
    ...
  </table>
  <h5><strong>Sat 23 May, 2026</strong></h5>
  ...

We parse by extracting the **teamID** from `stats_1team.cfm` links — that's
a rock-solid signal even if NZIHL change the display name later. Game
status (played vs upcoming) comes from whether the row contains a
`hockey_boxscores.cfm` link (= a `[Final]` link).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .http import fetch
from .teams import Team, by_team_id


SCHEDULE_URL = "https://admin.esportsdesk.com/leagues/schedules.cfm"
NZ_TZ = ZoneInfo("Pacific/Auckland")


@dataclass
class Game:
    start_local: datetime
    away: Team
    home: Team
    is_final: bool
    away_score: int | None = None
    home_score: int | None = None

    @property
    def venue(self) -> str:
        return self.home.home_venue

    @property
    def matchup_slug(self) -> str:
        return f"{self.home.short_code}-vs-{self.away.short_code}"


def fetch_schedule_html(client_id: int = 7131, league_id: int = 35499) -> str:
    """Merge the default page with explicit current+next-2-month pages.

    2026-07-28 fix: the default un-parameterized page is scoped to roughly the
    site's current server month and does NOT include games starting after
    month-end -- confirmed missing the entire August playoff bracket (semis
    Aug 7-8, grand final Aug 21-24) while scraped in late July, even though
    those games were well within both the PDF and manifest lookahead windows.
    Concatenating in the explicit-month page (see fetch_schedule_html_for_month,
    confirmed reliable 2026-07-08) for this month and the next two closes that
    gap without touching any window-day math. parse_schedule() dedupes the
    resulting overlap.
    """
    params = {"clientid": client_id, "leagueid": league_id}
    url = f"{SCHEDULE_URL}?{urlencode(params)}"
    pages = []
    try:
        p = fetch(url)
        print(f"DEBUG fetch default page: len={len(p)}")
        pages.append(p)
    except Exception as exc:
        print(f"DEBUG fetch default page RAISED: {exc!r}")
        raise
    now = datetime.now(NZ_TZ)
    print(f"DEBUG now={now.isoformat()}")
    for offset in (0, 1, 2):
        m = now.month + offset
        y = now.year
        while m > 12:
            m -= 12
            y += 1
        try:
            p = fetch_schedule_html_for_month(client_id, league_id, month_id=m, year_id=y)
            print(f"DEBUG fetch month={m} year={y}: len={len(p)}")
            pages.append(p)
        except Exception as exc:
            print(f"DEBUG fetch month={m} year={y} RAISED: {exc!r}")
            raise
    return "\n".join(pages)


def fetch_schedule_html_for_month(client_id: int = 7131, league_id: int = 35499, *,
                                   month_id: int, year_id: int) -> str:
    """Explicit calendar month/year variant of the schedule table (printPage=1,
    schedType=main -- confirmed 2026-07-08 to accept monthID/yearID and return that
    month's Final results incl. boxscore links). fetch_schedule_html() above returns
    the full homepage-style page, which embeds a marketing widget covering the whole
    season PLUS a month-scoped widget -- this fetch is the reliable, explicitly-scoped
    fallback used when neither happens to contain a Final game in the needed month
    (see boxscores._last_final_gameid_lookback)."""
    params = {"clientid": client_id, "leagueid": league_id, "schedType": "main",
              "printPage": 1, "monthID": month_id, "yearID": year_id}
    url = f"{SCHEDULE_URL}?{urlencode(params)}"
    return fetch(url)


# ---------- regexes -------------------------------------------------

# `<h5> ... Fri 22 May, 2026 ... </h5>` — capture day, month name, year.
_DAY_HEADER_RE = re.compile(
    r"<h5[^>]*>\s*(?:<strong>\s*)?"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(\d{1,2})\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+"
    r"(\d{4})",
    re.IGNORECASE,
)

_TR_RE = re.compile(r"<tr[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
_TD_RE = re.compile(r"<td[^>]*>([\s\S]*?)</td>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")

# Links to stats_1team.cfm carry the teamID — the most reliable team signal.
_TEAM_LINK_RE = re.compile(r'stats_1team\.cfm\?[^"\'<>]*teamID=(\d+)', re.IGNORECASE)

# Boxscore link → game has been played.
_BOXSCORE_RE = re.compile(r"hockey_boxscores\.cfm", re.IGNORECASE)

# A row with a time field starts with "7:00 PM" (or "10:30 AM").
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(AM|PM)\b", re.IGNORECASE)

# Integers in row text — used to recover scores from finals.
_INT_RE = re.compile(r"\b(\d{1,3})\b")

# "Aug. 7, 2026 @ 7:00 PM" — full inline date+time, as used by the explicit
# monthID/yearID page (schedule.py's default fetch instead relies on <h5> day
# headers; the two admin.esportsdesk.com templates aren't the same). Confirmed
# 2026-07-28: the August playoff bracket page uses this inline format with NO
# <h5> day headers at all, so the header-block parser below finds zero rows on
# it unless we also handle this layout.
_INLINE_DATE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+"
    r"(\d{1,2}),\s+(\d{4})\s*@\s*(\d{1,2}):(\d{2})\s*(AM|PM)",
    re.IGNORECASE,
)

_MONTHS = {m.lower(): i+1 for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
)}


def _strip_tags(s: str) -> str:
    # Replace tags with a space rather than nothing — otherwise adjacent
    # cell contents merge (`<td>7:00 PM</td><td>tickets</td>` -> `7:00 PMtickets`).
    return unescape(_TAG_RE.sub(" ", s)).strip()


def _row_team_ids(row_html: str) -> list[int]:
    """Return jersey-order team IDs from a row, deduplicated.

    Each game row has two distinct teams; each team is usually linked twice
    (once by full name, once by 3-letter code), so we dedupe while preserving
    first-seen order.
    """
    seen: list[int] = []
    for m in _TEAM_LINK_RE.finditer(row_html):
        tid = int(m.group(1))
        if tid not in seen:
            seen.append(tid)
    return seen


def _row_time(row_html: str) -> tuple[int, int] | None:
    """Return (hour24, minute) if the row contains a time string, else None."""
    m = _TIME_RE.search(_strip_tags(row_html))
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    ampm = m.group(3).upper()
    if ampm == "PM" and hour != 12:
        hour += 12
    if ampm == "AM" and hour == 12:
        hour = 0
    return hour, minute


def parse_schedule(html: str, *, year_hint: int | None = None) -> list[Game]:
    """Parse the schedule page. `year_hint` is ignored — the page itself
    carries the year in its day headers."""
    games: list[Game] = []

    headers = list(_DAY_HEADER_RE.finditer(html))
    print(f"DEBUG parse_schedule: {len(headers)} <h5> day headers found, html len={len(html)}")
    for i, h in enumerate(headers):
        day = int(h.group(1))
        month = _MONTHS[h.group(2).lower()]
        year = int(h.group(3))
        day_date = datetime(year, month, day, tzinfo=NZ_TZ)

        # everything from this header to the next header is this day's table block
        block_start = h.end()
        block_end = headers[i+1].start() if i+1 < len(headers) else len(html)
        block = html[block_start:block_end]

        for tr_match in _TR_RE.finditer(block):
            row_html = tr_match.group(1)
            team_ids = _row_team_ids(row_html)
            if len(team_ids) < 2:
                continue   # not a game row — likely a header or filter row
            away = by_team_id(team_ids[0])
            home = by_team_id(team_ids[1])
            if not (away and home):
                continue

            is_final = bool(_BOXSCORE_RE.search(row_html))
            time_match = _row_time(row_html)
            if is_final:
                # Played game — the time isn't shown in this row layout; use noon as
                # a stable placeholder. Caller cares about the date, not the time,
                # for played games.
                start_local = day_date.replace(hour=12, minute=0)
                # Recover scores: two integers in stripped row text.
                stripped = _strip_tags(row_html)
                nums = [int(n) for n in _INT_RE.findall(stripped)]
                # nums often contains the two scores; first two are usually them.
                away_score = nums[0] if len(nums) >= 1 else None
                home_score = nums[1] if len(nums) >= 2 else None
                games.append(Game(start_local, away, home, True, away_score, home_score))
            elif time_match:
                hour, minute = time_match
                start_local = day_date.replace(hour=hour, minute=minute)
                games.append(Game(start_local, away, home, False))
            # rows without time and without a boxscore link are skipped

    print(f"DEBUG parse_schedule: {len(games)} rows extracted after header-block pass")

    # Second pass: rows carrying their own inline "Mon. D, YYYY @ H:MM AM/PM"
    # date (the explicit-month/playoff-page template, no <h5> day headers) --
    # scan the whole document regardless of the header-block pass above. Rows
    # from the default full-season-page template never contain this inline
    # pattern (their date only lives in the enclosing <h5>), so this can't
    # double-count anything the first pass already found; the caller-facing
    # dedupe below is belt-and-suspenders.
    for tr_match in _TR_RE.finditer(html):
        row_html = tr_match.group(1)
        team_ids = _row_team_ids(row_html)
        if len(team_ids) < 2:
            continue
        away = by_team_id(team_ids[0])
        home = by_team_id(team_ids[1])
        if not (away and home):
            continue
        stripped = _strip_tags(row_html)
        date_m = _INLINE_DATE_RE.search(stripped)
        if not date_m:
            continue
        month = _MONTHS[date_m.group(1).lower()]
        day = int(date_m.group(2))
        year = int(date_m.group(3))
        hour = int(date_m.group(4))
        minute = int(date_m.group(5))
        ampm = date_m.group(6).upper()
        if ampm == "PM" and hour != 12:
            hour += 12
        if ampm == "AM" and hour == 12:
            hour = 0
        is_final = bool(_BOXSCORE_RE.search(row_html))
        if is_final:
            start_local = datetime(year, month, day, 12, 0, tzinfo=NZ_TZ)
            nums = [int(n) for n in _INT_RE.findall(stripped)]
            away_score = nums[0] if len(nums) >= 1 else None
            home_score = nums[1] if len(nums) >= 2 else None
            games.append(Game(start_local, away, home, True, away_score, home_score))
        else:
            start_local = datetime(year, month, day, hour, minute, tzinfo=NZ_TZ)
            games.append(Game(start_local, away, home, False))

    # Dedupe: fetch_schedule_html() now concatenates several overlapping page
    # fetches (default + explicit current/next months), so the same game can
    # appear more than once. Keep first occurrence, keyed on the fields that
    # identify a single real-world game.
    seen: set[tuple[int, int, datetime, bool]] = set()
    deduped: list[Game] = []
    for g in games:
        key = (g.away.team_id, g.home.team_id, g.start_local, g.is_final)
        if key not in seen:
            seen.add(key)
            deduped.append(g)
    print(f"DEBUG parse_schedule: {len(games)} total rows before dedup, {len(deduped)} after dedup")
    return deduped


def upcoming_within(days: int, html: str | None = None) -> list[Game]:
    if html is None:
        html = fetch_schedule_html()
    games = parse_schedule(html)
    now = datetime.now(NZ_TZ)
    # End-of-day cutoff: "within N days" means THROUGH the Nth day out. The old
    # timestamp cutoff (now + N days, evaluated at the ~08:50am NZT run) silently
    # dropped boundary-day EVENING games — e.g. a Jul 18 17:10 game vanished from a
    # Jul 7 run's 11-day manifest while a Jul 18 sibling of an in-window Jul 17 game
    # survived via expand_to_series, making the hockeyrosters page look randomly
    # wrong (caught 2026-07-08). Same math also made in_core_window trickle a
    # weekend in one day at a time on the portal.
    cutoff = (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)
    return [g for g in games if (not g.is_final) and now <= g.start_local <= cutoff]


def _game_key(g: Game) -> tuple[int, int, datetime]:
    return (g.away.team_id, g.home.team_id, g.start_local)


def expand_to_series(window_games: list[Game], all_games: list[Game]) -> list[Game]:
    """Pull in every other upcoming game that belongs to the same series as a
    game already found inside the lookahead window — even if that other game
    falls outside the window.

    NZIHL teams often play the same opponent twice in a weekend (e.g. Sat +
    Sun). If the window cutoff lands between the two games (a Wednesday sweep
    with a 4-day window catches Saturday but not Sunday), the second game
    would otherwise be missed until a later run. "Same series" reuses
    `group_into_series`'s rule: consecutive games between the same two teams
    no more than 3 days apart.
    """
    if not window_games:
        return []

    upcoming_all = [g for g in all_games if not g.is_final]
    all_series = group_into_series(upcoming_all)

    window_keys = {_game_key(g) for g in window_games}

    seen: set[tuple[int, int, datetime]] = set()
    out: list[Game] = []
    for series in all_series:
        if not any(_game_key(g) in window_keys for g in series):
            continue
        for g in series:
            key = _game_key(g)
            if key not in seen:
                seen.add(key)
                out.append(g)

    out.sort(key=lambda g: g.start_local)
    return out


def group_into_series(games: list[Game]) -> list[list[Game]]:
    """Group games between the same two teams into a series.

    Multiple matchups can overlap on the same weekend; we group per-matchup,
    then split any matchup whose consecutive games are more than 3 days apart
    into separate series.
    """
    by_key: dict[tuple[int, int], list[list[Game]]] = {}
    for g in sorted(games, key=lambda x: x.start_local):
        key = tuple(sorted([g.away.team_id, g.home.team_id]))
        groups = by_key.setdefault(key, [])
        if groups and (g.start_local - groups[-1][-1].start_local) <= timedelta(days=3):
            groups[-1].append(g)
        else:
            groups.append([g])
    out: list[list[Game]] = []
    for groups in by_key.values():
        out.extend(groups)
    out.sort(key=lambda s: s[0].start_local)
    return out
