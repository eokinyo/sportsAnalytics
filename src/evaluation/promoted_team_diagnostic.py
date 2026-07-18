"""
Diagnostic: does the flat PROMOTED_ATTACK / PROMOTED_DEFENCE_WEAKNESS
hardcoding in src/models/team_strength.py explain the September
relegation miscalibration found in calibration.py?

This script is read-only / analysis-only. It:
  1. Loads the backtest comparison CSVs (via prediction_metrics)
  2. Identifies which teams were "promoted" into each target_season,
     using epl_matches_clean.csv (a team is promoted if it played in
     target_season but not in the prior season)
  3. Splits the Relegation @ September calibration curve into
     promoted vs. non-promoted teams
  4. Compares Brier scores and observed relegation rates for each group

Does not call or modify any prediction logic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.evaluation.prediction_metrics import (
    load_and_score,
    brier_score,
    reference_brier_score,
    build_calibration_pairs,
)
from src.evaluation.calibration import calibration_curve, format_curve


def previous_season(season: str) -> str:
    """
    Given "2015_2016", return "2014_2015".
    """
    start, end = season.split("_")
    return f"{int(start) - 1}_{int(end) - 1}"


def build_promoted_team_lookup(matches: pd.DataFrame) -> dict[str, set[str]]:
    """
    Build a mapping of season -> set of teams that are "promoted"
    into that season, i.e. teams that played in `season` but did
    not play (home or away) in the immediately preceding season.

    Returns a dict keyed by season string, e.g. "2015_2016" ->
    {"Bournemouth", "Watford", "Norwich"}.
    """
    seasons = sorted(matches["Season"].dropna().unique())

    teams_by_season = {}

    for season in seasons:
        season_matches = matches[matches["Season"] == season]
        teams = set(season_matches["HomeTeam"]) | set(season_matches["AwayTeam"])
        teams_by_season[season] = teams

    promoted_by_season = {}

    for season in seasons:
        prev = previous_season(season)

        current_teams = teams_by_season.get(season, set())
        prev_teams = teams_by_season.get(prev, set())

        if not prev_teams:
            # No data for the prior season (e.g. start of dataset) -
            # can't determine promotion status, treat as unknown/none.
            promoted_by_season[season] = set()
            continue

        promoted_by_season[season] = current_teams - prev_teams

    return promoted_by_season


def annotate_promoted_status(
    raw: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add an IsPromoted boolean column to the raw comparison DataFrame,
    based on (Season, Team) lookup against build_promoted_team_lookup.
    """
    promoted_lookup = build_promoted_team_lookup(matches)

    raw = raw.copy()

    def is_promoted(row):
        promoted_teams = promoted_lookup.get(row["Season"], set())
        return row["Team"] in promoted_teams

    raw["IsPromoted"] = raw.apply(is_promoted, axis=1)

    return raw


def compare_promoted_vs_rest(
    raw: pd.DataFrame,
    checkpoint: str = "September",
    outcome_name: str = "Relegation",
) -> dict:
    """
    For a given checkpoint and outcome, compute Brier score, base
    rate (observed frequency), and mean predicted probability,
    separately for promoted and non-promoted teams.
    """
    subset = raw[raw["Checkpoint"] == checkpoint]

    pairs = build_calibration_pairs(subset, outcome_name)

    # build_calibration_pairs drops IsPromoted, so re-merge it back
    # via the index (pairs preserves the original row index).
    pairs = pairs.join(subset["IsPromoted"])

    results = {}

    for label, group_mask in [
        ("Promoted", pairs["IsPromoted"]),
        ("NotPromoted", ~pairs["IsPromoted"]),
    ]:
        gdf = pairs[group_mask]

        if len(gdf) == 0:
            continue

        results[label] = {
            "N": len(gdf),
            "ObservedFrequency": gdf["Actual"].mean(),
            "MeanPredicted": gdf["PredictedProb"].mean(),
            "Brier": brier_score(gdf["PredictedProb"], gdf["Actual"]),
            "RefBrier": reference_brier_score(gdf["Actual"]),
        }

    return results, pairs


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python -m src.evaluation.promoted_team_diagnostic "
            "<backtest_dir> <matches_csv>"
        )
        sys.exit(1)

    backtest_dir = sys.argv[1]
    matches_path = sys.argv[2]

    matches = pd.read_csv(matches_path)

    results = load_and_score(backtest_dir, group_by=["Checkpoint"])
    raw = results["raw"]

    raw = annotate_promoted_status(raw, matches)

    pd.set_option("display.width", 160)

    print("=" * 70)
    print("Relegation @ September: Promoted vs Not-Promoted")
    print("=" * 70)

    group_results, pairs = compare_promoted_vs_rest(
        raw, checkpoint="September", outcome_name="Relegation"
    )

    for label, stats in group_results.items():
        print(f"\n{label}:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

    print()
    print("=" * 70)
    print("Calibration curve - Promoted teams only (Relegation @ September)")
    print("=" * 70)

    promoted_pairs = pairs[pairs["IsPromoted"]]
    curve = calibration_curve(promoted_pairs)
    print(format_curve(curve).to_string(index=False))

    print()
    print("=" * 70)
    print("Calibration curve - Non-promoted teams only (Relegation @ September)")
    print("=" * 70)

    not_promoted_pairs = pairs[~pairs["IsPromoted"]]
    curve = calibration_curve(not_promoted_pairs)
    print(format_curve(curve).to_string(index=False))

    print()
    print("=" * 70)
    print("Promoted-team rows: predicted vs actual, by team/season")
    print("=" * 70)

    promoted_detail = promoted_pairs[
        ["Season", "Team", "PredictedProb", "Actual"]
    ].sort_values(["Season", "Team"])

    print(promoted_detail.to_string(index=False))