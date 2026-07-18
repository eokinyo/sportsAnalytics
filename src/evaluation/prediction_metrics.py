"""
Evaluation metrics for season-level probability forecasts.

Consumes the per-checkpoint comparison CSVs produced by
src/backtest/backtest_season.py (one row per team, with predicted
Title %, Top 4 %, Top 6 %, Relegation % and the actual final position).

This module is read-only / analysis-only: it does not call or modify
any prediction logic. It simply loads existing backtest outputs and
scores the probabilities that were already produced.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


OUTCOME_COLUMNS = {
    "Title": "Title %",
    "Top4": "Top 4 %",
    "Top6": "Top 6 %",
    "Relegation": "Relegation %",
}

# How each outcome is derived from ActualPosition.
# Assumes a 20-team league (standard EPL).
OUTCOME_RULES = {
    "Title": lambda pos: pos == 1,
    "Top4": lambda pos: pos <= 4,
    "Top6": lambda pos: pos <= 6,
    "Relegation": lambda pos: pos >= 18,
}

FILENAME_PATTERN = re.compile(
    r"^(?P<season>\d{4}_\d{4})_backtest_(?P<date>\d{4}-\d{2}-\d{2})\.csv$"
)


def load_all_backtests(backtest_dir: str | Path) -> pd.DataFrame:
    """
    Load every per-checkpoint comparison CSV in `backtest_dir` and
    stack them into one long DataFrame, tagging each row with the
    Season and AsOfDate it came from.

    Expects filenames of the form:
        {season}_backtest_{as_of_date}.csv
    e.g. 2015_2016_backtest_2015-12-31.csv
    """
    backtest_dir = Path(backtest_dir)

    frames = []

    for path in sorted(backtest_dir.glob("*_backtest_*.csv")):
        match = FILENAME_PATTERN.match(path.name)

        if not match:
            continue

        df = pd.read_csv(path)

        df["Season"] = match.group("season")
        df["AsOfDate"] = match.group("date")
        df["SourceFile"] = path.name

        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            f"No files matching '*_backtest_*.csv' found in {backtest_dir}"
        )

    return pd.concat(frames, ignore_index=True)


def add_checkpoint_label(
    df: pd.DataFrame,
    checkpoint_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Add a human-readable Checkpoint column (September/December/March/May)
    based on the month of AsOfDate. If checkpoint_map is not provided,
    a default month -> checkpoint mapping is used matching backtest.py:
        09 -> September
        12 -> December
        03 -> March
        05 -> May
    """
    if checkpoint_map is None:
        checkpoint_map = {
            "09": "September",
            "12": "December",
            "03": "March",
            "05": "May",
        }

    df = df.copy()

    month = df["AsOfDate"].str.slice(5, 7)

    df["Checkpoint"] = month.map(checkpoint_map)

    return df


def add_outcome_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add binary actual-outcome columns (TitleActual, Top4Actual,
    Top6Actual, RelegationActual) derived from ActualPosition.
    """
    df = df.copy()

    for outcome_name, rule in OUTCOME_RULES.items():
        df[f"{outcome_name}Actual"] = (
            df["ActualPosition"].apply(rule).astype(int)
        )

    return df


def _prepare_outcome_frame(
    df: pd.DataFrame,
    outcome_name: str,
) -> pd.DataFrame:
    """
    Build a (predicted_prob, actual) frame for a single outcome type,
    with predicted probabilities rescaled from percent to [0, 1].
    """
    prob_col = OUTCOME_COLUMNS[outcome_name]
    actual_col = f"{outcome_name}Actual"

    out = df[[prob_col, actual_col, "Checkpoint", "Season", "Team"]].copy()

    out = out.rename(
        columns={
            prob_col: "PredictedProb",
            actual_col: "Actual",
        }
    )

    out["PredictedProb"] = out["PredictedProb"] / 100.0

    return out


def brier_score(predicted_prob: pd.Series, actual: pd.Series) -> float:
    """
    Brier score: mean squared error between predicted probability
    and binary outcome. Range [0, 1], lower is better.
    A model that always predicts the base rate scores
    base_rate * (1 - base_rate).
    """
    return float(((predicted_prob - actual) ** 2).mean())


def log_loss(
    predicted_prob: pd.Series,
    actual: pd.Series,
    eps: float = 1e-15,
) -> float:
    """
    Log loss (cross-entropy). Lower is better. Probabilities are
    clipped to [eps, 1 - eps] to avoid log(0) for predictions of
    exactly 0% or 100% (which do occur in this data, e.g. 0.0%
    relegation chance for a runaway title favourite).
    """
    p = predicted_prob.clip(eps, 1 - eps)
    a = actual

    losses = -(a * np.log(p) + (1 - a) * np.log(1 - p))

    return float(losses.mean())


def reference_brier_score(actual: pd.Series) -> float:
    """
    Brier score of a "naive" model that always predicts the
    observed base rate for this outcome. Useful as a baseline:
    a forecasting model should beat this.
    """
    base_rate = actual.mean()

    return float(base_rate * (1 - base_rate))


def summarize_outcome(
    df: pd.DataFrame,
    outcome_name: str,
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """
    Compute Brier score, log loss, sample size, base rate, and the
    naive reference Brier score for one outcome type, optionally
    grouped by columns such as ["Checkpoint"].
    """
    frame = _prepare_outcome_frame(df, outcome_name)

    if group_by is None:
        groups = [((), frame)]
    else:
        groups = list(frame.groupby(group_by))

        if len(group_by) == 1:
            groups = [((g,), gdf) for g, gdf in groups]

    rows = []

    for key, gdf in groups:
        row = {}

        if group_by is not None:
            for col_name, val in zip(group_by, key):
                row[col_name] = val

        row["Outcome"] = outcome_name
        row["N"] = len(gdf)
        row["BaseRate"] = gdf["Actual"].mean()
        row["Brier"] = brier_score(gdf["PredictedProb"], gdf["Actual"])
        row["RefBrier"] = reference_brier_score(gdf["Actual"])
        row["BrierSkillScore"] = (
            1 - row["Brier"] / row["RefBrier"]
            if row["RefBrier"] > 0
            else float("nan")
        )
        row["LogLoss"] = log_loss(gdf["PredictedProb"], gdf["Actual"])

        rows.append(row)

    return pd.DataFrame(rows)


def summarize_all_outcomes(
    df: pd.DataFrame,
    group_by: list[str] | None = None,
) -> pd.DataFrame:
    """
    Run summarize_outcome for Title, Top4, Top6, and Relegation,
    concatenated into a single table.
    """
    frames = [
        summarize_outcome(df, outcome_name, group_by=group_by)
        for outcome_name in OUTCOME_RULES
    ]

    return pd.concat(frames, ignore_index=True)


def build_calibration_pairs(
    df: pd.DataFrame,
    outcome_name: str,
) -> pd.DataFrame:
    """
    Return the raw (PredictedProb, Actual, Checkpoint, Season, Team)
    rows for a single outcome type. This is the input expected by
    src/evaluation/calibration.py to build reliability diagrams /
    bucketed calibration curves.
    """
    return _prepare_outcome_frame(df, outcome_name)


def load_and_score(
    backtest_dir: str | Path,
    group_by: list[str] | None = ["Checkpoint"],
) -> dict[str, pd.DataFrame]:
    """
    Convenience entry point:
      1. Load all per-checkpoint comparison CSVs from backtest_dir
      2. Add Checkpoint labels and binary outcome columns
      3. Score Title/Top4/Top6/Relegation predictions

    Returns a dict with:
      "raw":     the combined, annotated DataFrame (all rows)
      "overall": summary metrics across all checkpoints
      "by_group": summary metrics grouped by `group_by` (default Checkpoint)
    """
    raw = load_all_backtests(backtest_dir)
    raw = add_checkpoint_label(raw)
    raw = add_outcome_columns(raw)

    overall = summarize_all_outcomes(raw, group_by=None)

    result = {
        "raw": raw,
        "overall": overall,
    }

    if group_by is not None:
        result["by_group"] = summarize_all_outcomes(raw, group_by=group_by)

    return result


if __name__ == "__main__":
    import sys

    backtest_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs/backtests"

    results = load_and_score(backtest_dir)

    pd.set_option("display.width", 160)

    print("=" * 70)
    print("Overall (all checkpoints pooled)")
    print("=" * 70)
    print(
        results["overall"][
            ["Outcome", "N", "BaseRate", "Brier", "RefBrier", "BrierSkillScore", "LogLoss"]
        ].to_string(index=False)
    )

    print()
    print("=" * 70)
    print("By checkpoint")
    print("=" * 70)
    print(
        results["by_group"][
            ["Checkpoint", "Outcome", "N", "BaseRate", "Brier", "RefBrier", "BrierSkillScore", "LogLoss"]
        ].to_string(index=False)
    )