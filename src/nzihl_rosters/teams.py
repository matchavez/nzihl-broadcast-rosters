"""NZIHL team registry.

Maps the NZIHL `teamID` and the team name as it appears in the
schedule page (`schedules.cfm`) to the metadata we need to render
a roster (colours, display name, home venue).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Team:
    team_id: int                 # NZIHL esportsdesk teamID
    display_name: str            # full broadcast name
    schedule_name: str           # how the team appears in the schedule page (uppercase)
    primary_hex: str             # team header band colour
    accent_hex: str              # secondary colour (used for IM flag etc.)
    title_hex: str               # team-name text colour drawn on the band
    home_venue: str              # short venue label for the footer
    short_code: str              # 3-letter code (CRD/BSW/...)


# ---- Registry (NZIHL men's, 2026) --------------------------------
TEAMS: dict[str, Team] = {
    "RED DEVILS": Team(
        team_id=675633,
        display_name="Canterbury Red Devils",
        schedule_name="RED DEVILS",
        primary_hex="#DC0000",
        accent_hex="#000000",
        title_hex="#FFFFFF",      # white on red
        home_venue="Alpine Ice Sports Centre, Christchurch",
        short_code="CRD",
    ),
    "SWARM": Team(
        team_id=674109,
        display_name="Botany Swarm",
        schedule_name="SWARM",
        primary_hex="#782738",
        accent_hex="#F7AF28",
        title_hex="#F7AF28",      # honey on maroon
        home_venue="Paradice Botany Downs, Auckland",
        short_code="BSW",
    ),
    "ADMIRALS": Team(
        team_id=674110,
        display_name="Pure NZ Admirals",
        schedule_name="ADMIRALS",
        primary_hex="#081D48",
        accent_hex="#F7BE11",
        title_hex="#F7BE11",      # gold on navy
        home_venue="Avondale Skate & Sport, Auckland",
        short_code="WAA",
    ),
    "THUNDER": Team(
        team_id=675634,
        display_name="Dunedin Thunder",
        schedule_name="THUNDER",
        primary_hex="#025B3D",
        accent_hex="#FDAD19",
        title_hex="#FDAD19",      # amber on forest
        home_venue="Dunedin Ice Stadium",
        short_code="DUN",
    ),
    "STAMPEDE": Team(
        team_id=675635,
        display_name="SkyCity Stampede",
        schedule_name="STAMPEDE",
        primary_hex="#FAC805",
        accent_hex="#1D3056",
        title_hex="#1D3056",      # navy on yellow — primary is too light for white
        home_venue="Queenstown Ice Arena",
        short_code="SCS",
    ),
}


def by_schedule_name(name: str) -> Team | None:
    """Lookup a team by the uppercase name used in the schedule page."""
    return TEAMS.get(name.strip().upper())


def by_team_id(team_id: int) -> Team | None:
    for team in TEAMS.values():
        if team.team_id == team_id:
            return team
    return None
