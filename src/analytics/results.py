"""
results.py

Joins archived predictions to actual match results, and scores them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.predictions_archive import latest_predictions


def _outcome_from_score(hg: int, ag: int) -> str:
    if hg > ag: return "H"
    if hg < ag: return "A"
    return "D"


def _predicted_outcome(row) -> str:
    probs = {
        "H": row["HomeWinProb"],
        "D": row["DrawProb"],
        "A": row["AwayWinProb"],
    }
    return max(probs, key=probs.get)


def join_predictions_to_results(
    matches: pd.DataFrame,
    league: str,
    season: str,
    archive_dir: Path | str | None = None,
) -> pd.DataFrame:
    """
    Return one row per played fixture that was predicted, with both the
    prediction and the actual outcome side by side.
    """
    preds = latest_predictions(league, season, archive_dir)
    if preds.empty:
        return pd.DataFrame()

    played = matches.dropna(subset=["FTHG", "FTAG"]).copy()
    played = played[played["Season"] == season]
    if played.empty:
        return pd.DataFrame()

    played["Date"] = pd.to_datetime(played["Date"], format="mixed",
                                    dayfirst=False, errors="coerce")
    preds["Date"]  = pd.to_datetime(preds["Date"], errors="coerce")

    merged = preds.merge(
        played[["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]],
        on=["Date", "HomeTeam", "AwayTeam"],
        how="inner",
    )

    if merged.empty:
        return merged

    merged["ActualOutcome"]    = merged.apply(
        lambda r: _outcome_from_score(int(r["FTHG"]), int(r["FTAG"])), axis=1)
    merged["PredictedOutcome"] = merged.apply(_predicted_outcome, axis=1)
    merged["OutcomeCorrect"]   = merged["ActualOutcome"] == merged["PredictedOutcome"]
    merged["ScoreCorrect"]     = (
        (merged["PredictedHomeGoals"] == merged["FTHG"]) &
        (merged["PredictedAwayGoals"] == merged["FTAG"])
    )

    # Probability assigned to what actually happened — higher is better
    merged["ProbOfActual"] = merged.apply(
        lambda r: {
            "H": r["HomeWinProb"],
            "D": r["DrawProb"],
            "A": r["AwayWinProb"],
        }[r["ActualOutcome"]],
        axis=1,
    )

    # Brier score for the three-way outcome (0 = perfect, 2 = worst)
    def _brier(r):
        actual = r["ActualOutcome"]
        total  = 0.0
        for key, col in [("H", "HomeWinProb"), ("D", "DrawProb"), ("A", "AwayWinProb")]:
            target = 1.0 if key == actual else 0.0
            total += (r[col] - target) ** 2
        return total

    merged["BrierScore"] = merged.apply(_brier, axis=1)

    return merged.sort_values("Date").reset_index(drop=True)


def get_fixture_result(
    matches: pd.DataFrame,
    league: str,
    season: str,
    home_team: str,
    away_team: str,
    date: str | None = None,
    archive_dir: Path | str | None = None,
) -> dict | None:
    """Prediction + actual for one specific fixture."""
    joined = join_predictions_to_results(matches, league, season, archive_dir)
    if joined.empty:
        return None

    sel = joined[
        (joined["HomeTeam"] == home_team) &
        (joined["AwayTeam"] == away_team)
    ]

    if date:
        sel = sel[sel["Date"] == pd.to_datetime(date)]

    if sel.empty:
        return None

    return sel.iloc[-1].to_dict()


def accuracy_summary(
    matches: pd.DataFrame,
    league: str,
    season: str,
    archive_dir: Path | str | None = None,
) -> dict:
    """Running record across every scored fixture this season."""
    joined = join_predictions_to_results(matches, league, season, archive_dir)
    if joined.empty:
        return {"Fixtures": 0}

    n = len(joined)
    return {
        "Fixtures":        n,
        "OutcomeCorrect":  int(joined["OutcomeCorrect"].sum()),
        "OutcomeAccuracy": round(joined["OutcomeCorrect"].mean() * 100, 1),
        "ScoreCorrect":    int(joined["ScoreCorrect"].sum()),
        "ScoreAccuracy":   round(joined["ScoreCorrect"].mean() * 100, 1),
        "AvgProbOfActual": round(joined["ProbOfActual"].mean() * 100, 1),
        "AvgBrierScore":   round(joined["BrierScore"].mean(), 3),
    }
