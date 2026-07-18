"""
src/config/league_config.py

Central registry of supported leagues.

LEAGUES maps each league's code (used for folder/file naming
throughout data/raw, data/processed, data/logos, and outputs/) to its
display name (used on generated cards, e.g. "Premier League").

ACTIVE_LEAGUE is the league used by main.py, backtest.py, and
generate_cards.py when run with no arguments. Change this to switch
which league a plain `python main.py` targets.

Adding a new league:
    1. Add it to FOOTBALL_DATA_LEAGUE_CODES in src/data/update_data.py
    2. Add it here, to LEAGUES
    3. Make sure data/raw/{code}/ has raw season files, then run
       `python -m src.data.preprocess {code}` once
    4. (Optional) Add team colors to src/visualization/team_colors.py
       and logos to data/logos/{code}/
"""

from __future__ import annotations

import sys


LEAGUES: dict[str, str] = {
    "epl": "Premier League",
    "laliga": "La Liga",
    "bundesliga": "Bundesliga",
    "ligue_1": "Ligue 1",
    "serie_a": "Serie A",
}


# Matches per team in a full season - drives total_matches_per_team in
# main.py / generate_cards.py / backtest.py. Reflects each league's
# CURRENT team count: Bundesliga and Ligue 1 have 18 teams (34 games),
# the rest have 20 teams (38 games).
#
# Note: Ligue 1 had 20 teams (38 games) before the 2023_2024 season,
# when it dropped to 18. If you backtest Ligue 1 seasons before
# 2023_2024, those checkpoints need 38, not 34 - this single constant
# only reflects the current-season setup used by main.py and
# generate_cards.py.
MATCHES_PER_TEAM: dict[str, int] = {
    "epl": 38,
    "laliga": 38,
    "bundesliga": 34,
    "ligue_1": 34,
    "serie_a": 38,
}


ACTIVE_LEAGUE = "epl"


def get_matches_per_team(league_code: str) -> int:
    """
    Return the current full-season matches-per-team count for a
    league, e.g. "bundesliga" -> 34.
    """
    if league_code not in MATCHES_PER_TEAM:
        raise ValueError(
            f"No MATCHES_PER_TEAM entry for {league_code!r}. "
            f"Supported leagues: {list(MATCHES_PER_TEAM)}"
        )

    return MATCHES_PER_TEAM[league_code]


def get_league_display(league_code: str) -> str:
    """
    Return the human-readable display name for a league code, e.g.
    "laliga" -> "La Liga".
    """
    if league_code not in LEAGUES:
        raise ValueError(
            f"Unknown league code: {league_code!r}. "
            f"Supported leagues: {list(LEAGUES)}"
        )

    return LEAGUES[league_code]


def resolve_league(cli_args: list[str] | None = None) -> str:
    """
    Determine which league to run for: the first command-line
    argument if one was given, otherwise ACTIVE_LEAGUE.

    Used by main.py / backtest.py / generate_cards.py so that:
        python main.py            -> ACTIVE_LEAGUE
        python main.py laliga     -> "laliga"
    """
    args = sys.argv[1:] if cli_args is None else cli_args

    if args:
        league = args[0]

        if league not in LEAGUES:
            raise ValueError(
                f"Unknown league: {league!r}. "
                f"Supported leagues: {list(LEAGUES)}"
            )

        return league

    return ACTIVE_LEAGUE