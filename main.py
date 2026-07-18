from pathlib import Path
import pandas as pd

from src.data.update_data import update_current_league_data
from src.data.preprocess import preprocess_league

from src.live.live_forecast import run_live_forecast
from src.live.season_state import build_actual_table_so_far

from src.config.season_config import (
    get_forecast_season_context,
    print_forecast_context,
)
from src.config.league_config import resolve_league, get_matches_per_team


BASE_DIR = Path(__file__).resolve().parent

UPDATE_DATA = True
PREPROCESS_DATA = True

# Set to a "YYYY-MM-DD" string to override the auto-detected forecast
# date - e.g. to forecast as the season looked on a past date. Leave
# as None to use today's date via get_forecast_season_context.
# Should match generate_cards.py's AS_OF_DATE_OVERRIDE so the tables
# and cards line up.
#
# Example: AS_OF_DATE_OVERRIDE = "2025-12-31"
AS_OF_DATE_OVERRIDE = None #"2025-12-31"

N_SIMULATIONS = 10000
SEED = 42


def main(league: str | None = None):

    league = league or resolve_league()

    data_path = (
        BASE_DIR
        / "data"
        / "processed"
        / league
        / f"{league}_matches_clean.csv"
    )

    output_dir = (
        BASE_DIR
        / "outputs"
        / "tables"
        / league
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    matches = pd.read_csv(data_path)

    season, as_of_date = (
        get_forecast_season_context(matches)
    )

    print_forecast_context(
        season=season,
        as_of_date=as_of_date,
    )

    # --------------------------------------------------
    # Update raw data and rebuild processed dataset
    # --------------------------------------------------
    if UPDATE_DATA:
        try:
            update_current_league_data(
                league=league,
                season=season,
            )
        except Exception as exc:
            print(
                f"\nWarning: could not update raw data for "
                f"{league} ({exc!r}). "
                f"Continuing with existing data."
            )

    if PREPROCESS_DATA:
        preprocess_league(
            league=league,
        )

        matches = pd.read_csv(data_path)

        season, as_of_date = (
            get_forecast_season_context(matches)
        )

        print_forecast_context(
            season=season,
            as_of_date=as_of_date,
        )

    if AS_OF_DATE_OVERRIDE is not None:
        as_of_date = AS_OF_DATE_OVERRIDE
        print(f"(Using AS_OF_DATE_OVERRIDE = {as_of_date})")

    # --------------------------------------------------
    # Current season diagnostics
    # --------------------------------------------------
    played_table = build_actual_table_so_far(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
    )

    if not played_table.empty:

        played_table["PPG"] = (
            played_table["Points"]
            / played_table["Played"]
        )

        print("\nCurrent-season PPG table")

        print(
            played_table[
                [
                    "Team",
                    "Played",
                    "Points",
                    "PPG",
                    "GF",
                    "GA",
                    "GD",
                ]
            ]
        )

    # --------------------------------------------------
    # Run forecast
    # --------------------------------------------------
    actual_table, forecast, strength_table = (
        run_live_forecast(
            matches=matches,
            season=season,
            as_of_date=as_of_date,
            n_recent_seasons=5,
            season_decay=0.50,
            total_matches_per_team=get_matches_per_team(league),
            promoted_weight_multiplier=0.60,
            n_simulations=N_SIMULATIONS,
            seed=SEED,
        )
    )

    # --------------------------------------------------
    # Save outputs
    # --------------------------------------------------
    actual_path = (
        output_dir
        / f"{league}_{season}_actual_table_as_of_{as_of_date}.csv"
    )

    forecast_path = (
        output_dir
        / f"{league}_{season}_live_forecast_as_of_{as_of_date}.csv"
    )

    strength_path = (
        output_dir
        / f"{league}_{season}_live_strength_as_of_{as_of_date}.csv"
    )

    actual_table.to_csv(
        actual_path,
        index=False,
    )

    forecast.to_csv(
        forecast_path,
        index=False,
    )

    strength_table.to_csv(
        strength_path,
        index=False,
    )

    # --------------------------------------------------
    # Output tables
    # --------------------------------------------------
    print("\nActual table so far")
    print(actual_table)

    print("\nLive forecast for remaining season")
    print(forecast)

    print("\nLive strength table")

    strength_cols = [
        "Team",
        "PreseasonEloStrength",
        "EloStrength",
        "LiveEloChange",
        "StrengthOfSchedule",
        "SOSAdjustment",
        "PPGStrength",
        "GDStrength",
        "OverallStrength",
    ]

    available_cols = [
        col
        for col in strength_cols
        if col in strength_table.columns
    ]

    print(
        strength_table[
            available_cols
        ]
    )

    # --------------------------------------------------
    # Saved files
    # --------------------------------------------------
    print("\nSaved:")

    print(actual_path)
    print(forecast_path)
    print(strength_path)


if __name__ == "__main__":
    main()