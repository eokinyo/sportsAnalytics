from __future__ import annotations

import time
import numpy as np
import pandas as pd

from src.live.season_state import (
    split_played_and_remaining,
    build_actual_table_so_far,
)

from src.models.poisson_model import (
    get_training_matches,
    estimate_league_goal_rates,
    estimate_team_attack_defence,
)

from src.models.team_strength import build_team_strength_table
from src.models.match_predictor import predict_fixture_list
from src.models.elo import apply_live_elo_to_strength_table
from src.models.strength_of_schedule import compute_strength_of_schedule

from src.simulation.season_simulator import simulate_remaining_matches
from src.simulation.league_table import build_league_table

from src.simulation.monte_carlo import (
    summarize_simulations,
    format_forecast_table,
    print_progress,
)


FORM_COLUMNS = [
    "HomeAttack",
    "AwayAttack",
    "AttackStrength",
    "HomeDefenceWeakness",
    "AwayDefenceWeakness",
    "DefenceWeakness",
]


def get_current_season_match_counts(
    played_matches: pd.DataFrame,
) -> pd.DataFrame:
    home_counts = played_matches[["HomeTeam"]].rename(
        columns={"HomeTeam": "Team"}
    )

    away_counts = played_matches[["AwayTeam"]].rename(
        columns={"AwayTeam": "Team"}
    )

    return (
        pd.concat([home_counts, away_counts], ignore_index=True)
        .value_counts("Team")
        .reset_index(name="CurrentSeasonMatches")
    )


def current_season_weight(
    matches_played: int,
    total_matches_per_team: int = 38,
    max_current_weight: float | None = None,
    curve_power: float = 0.75,
) -> float:
    if matches_played <= 0:
        return 0.0

    season_share = matches_played / total_matches_per_team
    season_share = min(max(season_share, 0.0), 1.0)

    weight = season_share ** curve_power

    if max_current_weight is not None:
        weight = min(weight, max_current_weight)

    return weight


def identify_promoted_or_no_recent_epl(
    preseason_strength: pd.DataFrame,
) -> set[str]:
    if "IsPromotedOrNoRecentEPL" not in preseason_strength.columns:
        return set()

    return set(
        preseason_strength.loc[
            preseason_strength["IsPromotedOrNoRecentEPL"] == True,
            "Team",
        ]
    )


def apply_promoted_team_shrinkage(
    strength: pd.DataFrame,
    promoted_teams: set[str],
    promoted_weight_multiplier: float = 0.60,
) -> pd.DataFrame:
    strength = strength.copy()

    if not promoted_teams:
        strength["IsPromotedLiveShrinkage"] = False
        return strength

    is_promoted = strength["Team"].isin(promoted_teams)

    strength["IsPromotedLiveShrinkage"] = is_promoted

    strength.loc[is_promoted, "CurrentSeasonWeight"] = (
        strength.loc[is_promoted, "CurrentSeasonWeight"]
        * promoted_weight_multiplier
    )

    return strength


def build_current_performance_table(
    played_matches: pd.DataFrame,
    teams: list[str],
) -> pd.DataFrame:
    rows = []

    for team in teams:
        home = played_matches[played_matches["HomeTeam"] == team]
        away = played_matches[played_matches["AwayTeam"] == team]

        played = len(home) + len(away)
        points = 0
        gd = 0
        gf = 0
        ga = 0

        for _, row in home.iterrows():
            hg = int(row["FTHG"])
            ag = int(row["FTAG"])

            gf += hg
            ga += ag
            gd += hg - ag

            if hg > ag:
                points += 3
            elif hg == ag:
                points += 1

        for _, row in away.iterrows():
            hg = int(row["FTHG"])
            ag = int(row["FTAG"])

            gf += ag
            ga += hg
            gd += ag - hg

            if ag > hg:
                points += 3
            elif ag == hg:
                points += 1

        ppg = points / played if played > 0 else np.nan
        gdpg = gd / played if played > 0 else np.nan

        rows.append(
            {
                "Team": team,
                "CurrentPlayed": played,
                "CurrentPoints": points,
                "CurrentPPG": ppg,
                "CurrentGF": gf,
                "CurrentGA": ga,
                "CurrentGD": gd,
                "CurrentGDPG": gdpg,
            }
        )

    return pd.DataFrame(rows)


def add_live_performance_strengths(
    strength: pd.DataFrame,
    played_matches: pd.DataFrame,
    preseason_strength: pd.DataFrame,
) -> pd.DataFrame:
    strength = strength.copy()

    performance = build_current_performance_table(
        played_matches=played_matches,
        teams=strength["Team"].tolist(),
    )

    strength = strength.merge(
        performance,
        on="Team",
        how="left",
    )

    strength["CurrentPPG"] = strength["CurrentPPG"].fillna(
        strength["CurrentPPG"].mean()
    )

    strength["CurrentGDPG"] = strength["CurrentGDPG"].fillna(
        strength["CurrentGDPG"].mean()
    )

    ppg_mean = strength["CurrentPPG"].mean()

    strength["PPGStrength"] = (
        strength["CurrentPPG"] / ppg_mean
        if ppg_mean > 0
        else 1.0
    )

    gd_shifted = (
        strength["CurrentGDPG"]
        - strength["CurrentGDPG"].min()
        + 0.10
    )

    gd_mean = gd_shifted.mean()

    strength["GDStrength"] = (
        gd_shifted / gd_mean
        if gd_mean > 0
        else 1.0
    )

    sos = compute_strength_of_schedule(
        played_matches=played_matches,
        preseason_strength=preseason_strength,
    )

    strength = strength.merge(
        sos,
        on="Team",
        how="left",
    )

    strength["StrengthOfSchedule"] = (
        strength["StrengthOfSchedule"].fillna(
            strength["StrengthOfSchedule"].mean()
        )
    )

    league_average_sos = strength["StrengthOfSchedule"].mean()

    strength["SOSAdjustment"] = (
        strength["StrengthOfSchedule"] / league_average_sos
        if league_average_sos > 0
        else 1.0
    )

    strength["PPGStrength"] = (
        strength["PPGStrength"]
        * strength["SOSAdjustment"]
    )

    strength["GDStrength"] = (
        strength["GDStrength"]
        * strength["SOSAdjustment"]
    )

    return strength


def blend_preseason_and_current_strength(
    preseason_strength: pd.DataFrame,
    played_matches: pd.DataFrame,
    total_matches_per_team: int = 38,
    max_current_weight: float | None = None,
    promoted_weight_multiplier: float = 0.60,
    live_elo_k_factor: float = 25.0,
    live_elo_home_advantage: float = 60.0,
) -> pd.DataFrame:
    strength = preseason_strength.copy()

    strength = apply_live_elo_to_strength_table(
        preseason_strength=strength,
        played_matches=played_matches,
        k=live_elo_k_factor,
        home_advantage=live_elo_home_advantage,
    )

    if played_matches.empty:
        strength["CurrentSeasonMatches"] = 0
        strength["CurrentSeasonWeight"] = 0.0
        strength["IsPromotedLiveShrinkage"] = False
        strength["CurrentPPG"] = np.nan
        strength["CurrentGDPG"] = np.nan
        strength["PPGStrength"] = 1.0
        strength["GDStrength"] = 1.0
        strength["StrengthOfSchedule"] = 1.0
        strength["SOSAdjustment"] = 1.0
        strength["DefenceStrength"] = 1 / strength["DefenceWeakness"]
        strength["EloStrengthNorm"] = (
            strength["EloStrength"] / strength["EloStrength"].mean()
        )
        return strength

    current_strength = estimate_team_attack_defence(
        played_matches,
        prior_matches=10.0,
    )

    match_counts = get_current_season_match_counts(
        played_matches
    )

    current_strength = current_strength.merge(
        match_counts,
        on="Team",
        how="left",
    )

    strength = strength.merge(
        current_strength[
            ["Team", "CurrentSeasonMatches"] + FORM_COLUMNS
        ],
        on="Team",
        how="left",
        suffixes=("", "_Current"),
    )

    strength["CurrentSeasonMatches"] = (
        strength["CurrentSeasonMatches"]
        .fillna(0)
        .astype(int)
    )

    strength["CurrentSeasonWeight"] = strength["CurrentSeasonMatches"].apply(
        lambda n: current_season_weight(
            matches_played=n,
            total_matches_per_team=total_matches_per_team,
            max_current_weight=max_current_weight,
        )
    )

    promoted_teams = identify_promoted_or_no_recent_epl(
        preseason_strength
    )

    strength = apply_promoted_team_shrinkage(
        strength=strength,
        promoted_teams=promoted_teams,
        promoted_weight_multiplier=promoted_weight_multiplier,
    )

    for col in FORM_COLUMNS:
        current_col = f"{col}_Current"

        if current_col not in strength.columns:
            continue

        strength[col] = (
            (1.0 - strength["CurrentSeasonWeight"]) * strength[col]
            + strength["CurrentSeasonWeight"]
            * strength[current_col].fillna(strength[col])
        )

    strength = add_live_performance_strengths(
        strength=strength,
        played_matches=played_matches,
        preseason_strength=preseason_strength,
    )

    strength["DefenceStrength"] = 1 / strength["DefenceWeakness"]

    strength["EloStrengthNorm"] = (
        strength["EloStrength"] / strength["EloStrength"].mean()
    )

    live_weight = strength["CurrentSeasonWeight"]

    elo_weight = 0.40 * (1.0 - live_weight)
    attack_weight = 0.25 + (0.15 * live_weight)
    defence_weight = 0.15 + (0.10 * live_weight)
    ppg_weight = 0.15 * live_weight
    gd_weight = 0.10 * live_weight

    strength["OverallStrength"] = (
        elo_weight * strength["EloStrengthNorm"]
        + attack_weight * strength["AttackStrength"]
        + defence_weight * strength["DefenceStrength"]
        + ppg_weight * strength["PPGStrength"]
        + gd_weight * strength["GDStrength"]
    )

    drop_cols = [
        col for col in strength.columns
        if col.endswith("_Current")
    ]

    strength = strength.drop(columns=drop_cols)

    if "StrengthRank" in strength.columns:
        strength = strength.drop(columns=["StrengthRank"])

    strength = strength.sort_values(
        "OverallStrength",
        ascending=False,
    ).reset_index(drop=True)

    strength.insert(
        0,
        "StrengthRank",
        range(1, len(strength) + 1),
    )

    return strength


def prepare_live_remaining_predictions(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
    n_recent_seasons: int = 5,
    season_decay: float = 0.50,
    total_matches_per_team: int = 38,
    max_current_weight: float | None = None,
    promoted_weight_multiplier: float = 0.60,
    live_elo_k_factor: float = 25.0,
    live_elo_home_advantage: float = 60.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    played, remaining = split_played_and_remaining(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
    )

    training_matches = get_training_matches(
        matches=matches,
        target_season=season,
        n_seasons=n_recent_seasons,
        decay=season_decay,
    )

    league_rates = estimate_league_goal_rates(
        training_matches
    )

    preseason_strength = build_team_strength_table(
        matches=matches,
        target_season=season,
        n_recent_seasons=n_recent_seasons,
        decay=season_decay,
    )

    strength_table = blend_preseason_and_current_strength(
        preseason_strength=preseason_strength,
        played_matches=played,
        total_matches_per_team=total_matches_per_team,
        max_current_weight=max_current_weight,
        promoted_weight_multiplier=promoted_weight_multiplier,
        live_elo_k_factor=live_elo_k_factor,
        live_elo_home_advantage=live_elo_home_advantage,
    )

    remaining_predictions = predict_fixture_list(
        fixtures=remaining,
        strength_table=strength_table,
        league_rates=league_rates,
    )

    return played, remaining_predictions, strength_table


def run_live_monte_carlo_simulation(
    played_matches: pd.DataFrame,
    remaining_predictions: pd.DataFrame,
    n_simulations: int = 2000,
    seed: int = 42,
    progress_every: int = 100,
) -> pd.DataFrame:

    rng = np.random.default_rng(seed)
    records = []

    start_time = time.time()

    for sim in range(n_simulations):
        simulated_remaining = simulate_remaining_matches(
            fixtures_with_probs=remaining_predictions,
            seed=int(rng.integers(0, 1_000_000_000)),
        )

        full_simulated_season = pd.concat(
            [played_matches, simulated_remaining],
            ignore_index=True,
        )

        final_table = build_league_table(
            full_simulated_season
        )

        for _, row in final_table.iterrows():
            records.append(
                {
                    "Simulation": sim + 1,
                    "Team": row["Team"],
                    "Position": row["Position"],
                    "Points": row["Points"],
                    "GF": row["GF"],
                    "GA": row["GA"],
                    "GD": row["GD"],
                }
            )

        current = sim + 1

        if (
            current == 1
            or current % progress_every == 0
            or current == n_simulations
        ):
            print_progress(
                current=current,
                total=n_simulations,
                start_time=start_time,
            )

    print()

    return pd.DataFrame(records)


def run_live_forecast(
    matches: pd.DataFrame,
    season: str,
    as_of_date: str,
    n_recent_seasons: int = 5,
    season_decay: float = 0.50,
    total_matches_per_team: int = 38,
    max_current_weight: float | None = None,
    promoted_weight_multiplier: float = 0.60,
    live_elo_k_factor: float = 25.0,
    live_elo_home_advantage: float = 60.0,
    n_simulations: int = 2000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    played, remaining_predictions, strength_table = (
        prepare_live_remaining_predictions(
            matches=matches,
            season=season,
            as_of_date=as_of_date,
            n_recent_seasons=n_recent_seasons,
            season_decay=season_decay,
            total_matches_per_team=total_matches_per_team,
            max_current_weight=max_current_weight,
            promoted_weight_multiplier=promoted_weight_multiplier,
            live_elo_k_factor=live_elo_k_factor,
            live_elo_home_advantage=live_elo_home_advantage,
        )
    )

    actual_table = build_actual_table_so_far(
        matches=matches,
        season=season,
        as_of_date=as_of_date,
    )

    if remaining_predictions.empty:
        forecast = actual_table.copy()

        forecast = forecast.rename(
            columns={
                "Position": "Rank",
                "Points": "Expected Points",
            }
        )

        forecast["Expected Position"] = forecast["Rank"]
        forecast["Title %"] = 0.0
        forecast["Top 4 %"] = 0.0
        forecast["Top 6 %"] = 0.0
        forecast["Relegation %"] = 0.0

        forecast.loc[
            forecast["Rank"] == 1,
            "Title %",
        ] = 100.0

        forecast.loc[
            forecast["Rank"] <= 4,
            "Top 4 %",
        ] = 100.0

        forecast.loc[
            forecast["Rank"] <= 6,
            "Top 6 %",
        ] = 100.0

        forecast.loc[
            forecast["Rank"] >= 18,
            "Relegation %",
        ] = 100.0

        forecast = forecast[
            [
                "Rank",
                "Team",
                "Expected Position",
                "Expected Points",
                "Played",
                "Won",
                "Drawn",
                "Lost",
                "GF",
                "GA",
                "GD",
                "Title %",
                "Top 4 %",
                "Top 6 %",
                "Relegation %",
            ]
        ]

        return actual_table, forecast, strength_table

    sim_results = run_live_monte_carlo_simulation(
        played_matches=played,
        remaining_predictions=remaining_predictions,
        n_simulations=n_simulations,
        seed=seed,
    )

    summary = summarize_simulations(
        sim_results
    )

    forecast = format_forecast_table(
        summary
    )

    return actual_table, forecast, strength_table