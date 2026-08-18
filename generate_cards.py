"""
generate_cards.py

Generates social-media-ready forecast cards:

  1. Season forecast card - league table with per-position
     probabilities, plus a Title Race highlight section.
  2. Matchday overview card - all fixtures for the next matchday,
     each with a Home/Draw/Away outcome bar.
  3. Match detail cards - one per fixture in the next matchday, with
     predicted scoreline, expected goals, and outcome probabilities.

Every fixture card generated is also written to the predictions
archive at data/predictions/{league}/{season}.csv, so the prediction
survives the run that made it and can later be scored against the
actual result by generate_results.py.

This script reuses the same lower-level functions as
src.live.live_forecast.run_live_forecast, but calls them directly so
that it also has access to:
  - sim_results (needed for per-position probabilities)
  - remaining_predictions (needed for the matchday cards)

Run after main.py (or independently, if
data/processed/{league}/{league}_matches_clean.csv is already up to
date):

    python generate_cards.py
"""

from pathlib import Path
import pandas as pd

from src.live.live_forecast import (
    prepare_live_remaining_predictions,
    run_live_monte_carlo_simulation,
)
from src.live.season_state import build_actual_table_so_far
from src.live.matchday import get_next_matchday_fixtures, matchday_label

from src.simulation.monte_carlo import (
    summarize_simulations,
    format_forecast_table,
    add_position_probability_column,
    get_title_probabilities,
)

from src.visualization.card import CardGenerator

from src.data.predictions_archive import append_predictions

from src.config.season_config import (
    get_forecast_season_context,
    print_forecast_context,
)
from src.config.league_config import (
    resolve_league,
    get_league_display,
    get_matches_per_team,
)


BASE_DIR = Path(__file__).resolve().parent


# Set to a "YYYY-MM-DD" string to override the auto-detected forecast
# date - useful for generating cards as they would have looked at an
# earlier point in the season (e.g. mid-season, before the title race
# is decided). Leave as None to use the current date via
# get_forecast_season_context, same as main.py.
#
# Example: AS_OF_DATE_OVERRIDE = None  # "2025-12-31"
AS_OF_DATE_OVERRIDE = None  # "2025-12-31"

# Should match the parameters used in main.py's run_live_forecast call,
# so the cards reflect the same forecast that main.py produced.
N_RECENT_SEASONS = 5
SEASON_DECAY = 0.50
PROMOTED_WEIGHT_MULTIPLIER = 0.60
N_SIMULATIONS = 10000
SEED = 42


def season_label(season: str) -> str:
    """
    Convert "2025_2026" -> "2025/26" for display.
    """
    start, end = season.split("_")
    return f"{start}/{end[2:]}"


def card_date_label(as_of_date: str) -> str:
    """
    Convert "2025-12-31" -> "31-12-2025" for use in output folder
    names, e.g. outputs/cards/epl/epl_31-12-2025/.
    """
    year, month, day = as_of_date.split("-")
    return f"{day}-{month}-{year}"


def build_table_df(forecast: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the output of format_forecast_table (+ Probability column
    from add_position_probability_column) into the column layout
    expected by CardGenerator.create_season_forecast_card:
        Position, Team, Points, GD, Probability, Top 4 %, Relegation %
    """
    table_df = forecast.rename(
        columns={
            "Rank": "Position",
            "Expected Points": "Points",
            "Expected GD": "GD",
        }
    )

    table_df["Points"] = table_df["Points"].round().astype(int)
    table_df["GD"] = table_df["GD"].round().astype(int)

    return table_df[
        ["Position", "Team", "Points", "GD", "Probability", "Top 4 %", "Relegation %"]
    ]


def main(league: str | None = None):
    league_code = league or resolve_league()
    league_display = get_league_display(league_code)

    data_path = (
        BASE_DIR
        / "data"
        / "processed"
        / league_code
        / f"{league_code}_matches_clean.csv"
    )

    # outputs/cards/{league}/ - the per-date subfolder for this run
    # is created below once as_of_date is known.
    cards_base_dir = (
        BASE_DIR
        / "outputs"
        / "cards"
        / league_code
    )

    logos_dir = (
        BASE_DIR
        / "data"
        / "logos"
        / league_code
    )

    matches = pd.read_csv(data_path)

    season, as_of_date = get_forecast_season_context(matches)

    if AS_OF_DATE_OVERRIDE is not None:
        as_of_date = AS_OF_DATE_OVERRIDE
        print(f"(Using AS_OF_DATE_OVERRIDE = {as_of_date})")

    print_forecast_context(season=season, as_of_date=as_of_date)

    display_season = season_label(season)

    # --------------------------------------------------
    # Prepare strength table, remaining fixtures, played matches
    # --------------------------------------------------
    played, remaining_predictions, strength_table = (
        prepare_live_remaining_predictions(
            matches=matches,
            season=season,
            as_of_date=as_of_date,
            n_recent_seasons=N_RECENT_SEASONS,
            season_decay=SEASON_DECAY,
            total_matches_per_team=get_matches_per_team(league_code),
            promoted_weight_multiplier=PROMOTED_WEIGHT_MULTIPLIER,
        )
    )

    # outputs/cards/{league}/{league}_{DD-MM-YYYY}/ for this run
    cards_dir = (
        cards_base_dir
        / f"{league_code}_{card_date_label(as_of_date)}"
    )

    gen = CardGenerator(
        output_dir=str(cards_dir),
        logos_dir=str(logos_dir),
    )

    # --------------------------------------------------
    # Season forecast card
    # --------------------------------------------------
    if remaining_predictions.empty:
        # Season is already complete - table is final, every team's
        # forecast position is its actual position with certainty.
        actual_table = build_actual_table_so_far(
            matches=matches, season=season, as_of_date=as_of_date,
        )

        table_df = actual_table[["Position", "Team", "Points", "GD"]].copy()
        table_df["Probability"] = 100.0
        table_df["Top 4 %"] = table_df["Position"].apply(lambda p: 100.0 if p <= 4 else 0.0)
        table_df["Relegation %"] = table_df["Position"].apply(lambda p: 100.0 if p >= 18 else 0.0)

        title_probs = {
            row["Team"]: 100.0
            for _, row in table_df.iterrows()
            if row["Position"] == 1
        }

    else:
        sim_results = run_live_monte_carlo_simulation(
            played_matches=played,
            remaining_predictions=remaining_predictions,
            n_simulations=N_SIMULATIONS,
            seed=SEED,
        )

        summary = summarize_simulations(sim_results)
        forecast = format_forecast_table(summary)
        forecast = add_position_probability_column(forecast, sim_results, summary)

        table_df = build_table_df(forecast)
        title_probs = get_title_probabilities(summary)

    season_card_path = gen.create_season_forecast_card(
        table_df=table_df,
        title_probs=title_probs,
        season=display_season,
        forecast_date=as_of_date,
        league=league_display,
    )

    print(f"\nSeason forecast card saved: {season_card_path}")

    # --------------------------------------------------
    # Matchday cards
    # --------------------------------------------------
    if remaining_predictions.empty:
        print("\nNo remaining fixtures - skipping matchday cards.")
        return

    next_md = get_next_matchday_fixtures(remaining_predictions)
    label = matchday_label(remaining_predictions, next_md)

    if next_md.empty:
        print("\nCould not determine next matchday fixtures.")
        return

    # Archive this matchday's predictions before rendering the cards.
    # predicted_on is as_of_date (not today) so AS_OF_DATE_OVERRIDE runs
    # archive under the date the forecast represents. Re-running on the
    # same date is a no-op rather than a duplicate.
    archive_file = append_predictions(
        predictions=next_md,
        league=league_code,
        season=season,
        predicted_on=as_of_date,
    )

    print(f"Predictions archived: {archive_file}")

    overview_path = gen.create_matchday_overview_card(
        fixtures_df=next_md,
        season=display_season,
        matchday_label=label,
        league=league_display,
    )

    print(f"Matchday overview card saved: {overview_path}")

    for _, fixture in next_md.iterrows():
        detail_path = gen.create_match_detail_card(
            fixture=fixture,
            season=display_season,
            league=league_display,
        )
        print(f"  Match detail card saved: {detail_path}")


if __name__ == "__main__":
    main()