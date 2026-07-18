from __future__ import annotations

import pandas as pd


def get_season_matches(
    matches: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    season_df = matches[matches["Season"] == season].copy()
    season_df["Date"] = pd.to_datetime(season_df["Date"], errors="coerce")
    return season_df.sort_values("Date").reset_index(drop=True)


def split_played_and_remaining(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    season_df = get_season_matches(matches, season)

    cutoff = pd.to_datetime(as_of_date)

    played = season_df[
        (season_df["Date"] <= cutoff)
        & season_df["FTHG"].notna()
        & season_df["FTAG"].notna()
    ].copy()

    remaining = season_df[
        season_df["Date"] > cutoff
    ].copy()

    return played.reset_index(drop=True), remaining.reset_index(drop=True)


def build_actual_table_so_far(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
):
    from src.simulation.league_table import build_league_table

    played, _ = split_played_and_remaining(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
    )

    return build_league_table(played)


def get_remaining_fixtures(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
) -> pd.DataFrame:
    _, remaining = split_played_and_remaining(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
    )

    return remaining[
        ["Date", "Season", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
    ].reset_index(drop=True)