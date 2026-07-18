from __future__ import annotations

from datetime import datetime
import pandas as pd


SEASON_START_MONTH = 8   # August
SEASON_END_MONTH = 5     # May


def season_start_year_from_label(
    season: str,
) -> int:
    return int(season.split("_")[0])


def season_end_year_from_label(
    season: str,
) -> int:
    return int(season.split("_")[1])


def get_available_seasons(
    matches: pd.DataFrame,
) -> list[str]:
    seasons = (
        matches["Season"]
        .dropna()
        .unique()
        .tolist()
    )

    seasons.sort()

    return seasons


def determine_current_football_year(
    today: datetime | None = None,
) -> int:
    if today is None:
        today = datetime.today()

    if today.month >= SEASON_START_MONTH:
        return today.year

    return today.year - 1


def season_exists(
    matches: pd.DataFrame,
    season: str,
) -> bool:
    return season in set(matches["Season"].unique())


def get_current_season(
    matches: pd.DataFrame,
    today: datetime | None = None,
) -> str:
    football_year = determine_current_football_year(
        today=today
    )

    season = (
        f"{football_year}_{football_year + 1}"
    )

    if season_exists(matches, season):
        return season

    seasons = get_available_seasons(matches)

    if len(seasons) == 0:
        raise ValueError(
            "No seasons found in dataset."
        )

    return seasons[-1]


def get_default_as_of_date(
    season: str,
    today: datetime | None = None,
) -> str:
    if today is None:
        today = datetime.today()

    season_start = season_start_year_from_label(
        season
    )

    season_end = season_end_year_from_label(
        season
    )

    season_start_date = datetime(
        season_start,
        8,
        1,
    )

    season_end_date = datetime(
        season_end,
        5,
        31,
    )

    if today < season_start_date:
        return season_start_date.strftime(
            "%Y-%m-%d"
        )

    if today > season_end_date:
        return season_end_date.strftime(
            "%Y-%m-%d"
        )

    return today.strftime("%Y-%m-%d")


def get_forecast_season_context(
    matches: pd.DataFrame,
    today: datetime | None = None,
) -> tuple[str, str]:
    season = get_current_season(
        matches=matches,
        today=today,
    )

    as_of_date = get_default_as_of_date(
        season=season,
        today=today,
    )

    return season, as_of_date


def print_forecast_context(
    season: str,
    as_of_date: str,
) -> None:
    print("\nForecast Context")
    print("-" * 40)
    print(f"Season: {season}")
    print(f"As of date: {as_of_date}")