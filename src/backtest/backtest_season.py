from __future__ import annotations

import pandas as pd

from src.live.live_forecast import run_live_forecast
from src.simulation.league_table import build_league_table


def get_actual_final_table(
    matches: pd.DataFrame,
    season: str,
) -> pd.DataFrame:
    season_matches = matches[
        matches["Season"] == season
    ].copy()

    final_table = build_league_table(
        season_matches
    )

    return final_table


def compare_forecast_to_actual(
    forecast: pd.DataFrame,
    actual_table: pd.DataFrame,
) -> pd.DataFrame:
    forecast_clean = forecast[
        [
            "Team",
            "Rank",
            "Expected Position",
            "Expected Points",
            "Title %",
            "Top 4 %",
            "Top 6 %",
            "Relegation %",
        ]
    ].copy()

    actual_clean = actual_table[
        [
            "Team",
            "Position",
            "Points",
        ]
    ].copy()

    comparison = forecast_clean.merge(
        actual_clean,
        on="Team",
        how="left",
    )

    comparison = comparison.rename(
        columns={
            "Rank": "ForecastRank",
            "Position": "ActualPosition",
            "Points": "ActualPoints",
        }
    )

    comparison["PositionError"] = (
        comparison["ForecastRank"]
        - comparison["ActualPosition"]
    )

    comparison["AbsPositionError"] = (
        comparison["PositionError"].abs()
    )

    comparison["PointsError"] = (
        comparison["Expected Points"]
        - comparison["ActualPoints"]
    )

    comparison["AbsPointsError"] = (
        comparison["PointsError"].abs()
    )

    return comparison.sort_values(
        "ActualPosition"
    ).reset_index(drop=True)


def summarize_backtest_errors(
    comparison: pd.DataFrame,
) -> dict:
    mae_position = comparison["AbsPositionError"].mean()

    rmse_position = (
        (comparison["PositionError"] ** 2).mean()
        ** 0.5
    )

    mae_points = comparison["AbsPointsError"].mean()

    rmse_points = (
        (comparison["PointsError"] ** 2).mean()
        ** 0.5
    )

    champion_actual = comparison.loc[
        comparison["ActualPosition"] == 1,
        "Team",
    ].iloc[0]

    champion_forecast = comparison.loc[
        comparison["ForecastRank"] == 1,
        "Team",
    ].iloc[0]

    champion_correct = champion_actual == champion_forecast

    actual_top4 = set(
        comparison.loc[
            comparison["ActualPosition"] <= 4,
            "Team",
        ]
    )

    forecast_top4 = set(
        comparison.loc[
            comparison["ForecastRank"] <= 4,
            "Team",
        ]
    )

    top4_correct_count = len(
        actual_top4.intersection(forecast_top4)
    )

    actual_relegated = set(
        comparison.loc[
            comparison["ActualPosition"] >= 18,
            "Team",
        ]
    )

    forecast_relegated = set(
        comparison.loc[
            comparison["ForecastRank"] >= 18,
            "Team",
        ]
    )

    relegation_correct_count = len(
        actual_relegated.intersection(forecast_relegated)
    )

    return {
        "MAE_Position": mae_position,
        "RMSE_Position": rmse_position,
        "MAE_Points": mae_points,
        "RMSE_Points": rmse_points,
        "ActualChampion": champion_actual,
        "ForecastChampion": champion_forecast,
        "ChampionCorrect": champion_correct,
        "Top4CorrectCount": top4_correct_count,
        "RelegationCorrectCount": relegation_correct_count,
    }


def run_single_season_backtest(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
    n_recent_seasons: int = 5,
    season_decay: float = 0.50,
    total_matches_per_team: int = 38,
    promoted_weight_multiplier: float = 0.60,
    live_elo_k_factor: float = 25.0,
    live_elo_home_advantage: float = 60.0,
    n_simulations: int = 2000,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict]:

    _, forecast, _ = run_live_forecast(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
        n_recent_seasons=n_recent_seasons,
        season_decay=season_decay,
        total_matches_per_team=total_matches_per_team,
        promoted_weight_multiplier=promoted_weight_multiplier,
        live_elo_k_factor=live_elo_k_factor,
        live_elo_home_advantage=live_elo_home_advantage,
        n_simulations=n_simulations,
        seed=seed,
    )

    actual_final_table = get_actual_final_table(
        matches=matches,
        season=season,
    )

    comparison = compare_forecast_to_actual(
        forecast=forecast,
        actual_table=actual_final_table,
    )

    summary = summarize_backtest_errors(
        comparison
    )

    return comparison, summary