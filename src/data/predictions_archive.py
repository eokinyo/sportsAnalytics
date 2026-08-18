"""
predictions_archive.py

Persists fixture-level predictions so they survive past the run that made them.
Every run appends a row per fixture with a PredictedOn timestamp; nothing is
ever overwritten. The result card and accuracy tracking read from here.
"""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR   = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = BASE_DIR / "data" / "predictions"

ARCHIVE_COLUMNS = [
    "PredictedOn",
    "League",
    "Season",
    "Date",
    "HomeTeam",
    "AwayTeam",
    "HomeExpectedGoals",
    "AwayExpectedGoals",
    "HomeWinProb",
    "DrawProb",
    "AwayWinProb",
    "PredictedHomeGoals",
    "PredictedAwayGoals",
]


def archive_path(
    league: str,
    season: str,
    archive_dir: Path | str | None = None,
) -> Path:
    base = Path(archive_dir) if archive_dir else ARCHIVE_DIR
    return base / league / f"{season}.csv"


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def _outcome_of(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


def _most_likely_score(
    home_xg: float,
    away_xg: float,
    outcome: str | None = None,
    max_goals: int = 8,
) -> tuple[int, int]:
    """
    Most likely scoreline *within the predicted outcome*.

    The unconditional mode of the joint Poisson is usually 1-1, because a
    draw is one concentrated cell while a home win is spread across many
    (1-0, 2-0, 2-1, ...). That makes the modal scoreline contradict the
    outcome the model actually calls - a card would show 1-1 while the
    verdict scored a home win. Conditioning on the called outcome keeps
    the displayed scoreline and the scored outcome consistent.

    If `outcome` is None it is taken as the most likely of H/D/A, derived
    from the same Poisson grid.
    """
    grid = {
        (h, a): _poisson_pmf(h, home_xg) * _poisson_pmf(a, away_xg)
        for h in range(max_goals + 1)
        for a in range(max_goals + 1)
    }

    if outcome is None:
        totals = {"H": 0.0, "D": 0.0, "A": 0.0}
        for (h, a), p in grid.items():
            totals[_outcome_of(h, a)] += p
        outcome = max(totals, key=totals.get)

    candidates = {
        k: v for k, v in grid.items()
        if _outcome_of(k[0], k[1]) == outcome
    }

    if not candidates:
        candidates = grid

    return max(candidates, key=candidates.get)


def append_predictions(
    predictions: pd.DataFrame,
    league: str,
    season: str,
    predicted_on: str | None = None,
    archive_dir: Path | str | None = None,
) -> Path:
    """
    Append this run's fixture predictions to the season archive.

    `predictions` is the DataFrame returned by predict_fixture_list() —
    Date, Season, HomeTeam, AwayTeam, HomeExpectedGoals, AwayExpectedGoals,
    HomeWinProb, DrawProb, AwayWinProb.
    """
    if predictions is None or predictions.empty:
        return archive_path(league, season, archive_dir)

    stamp = predicted_on or datetime.now().strftime("%Y-%m-%d")

    df = predictions.copy()
    df["PredictedOn"] = stamp
    df["League"]      = league

    if "Season" not in df.columns:
        df["Season"] = season

    # Most likely scoreline per fixture, conditioned on the outcome the
    # model calls. Taking the outcome from the row's own probabilities
    # keeps this in step with results.py, which scores the same argmax.
    def _row_outcome(row) -> str | None:
        probs = {
            "H": row.get("HomeWinProb"),
            "D": row.get("DrawProb"),
            "A": row.get("AwayWinProb"),
        }
        if any(v is None or pd.isna(v) for v in probs.values()):
            return None
        return max(probs, key=probs.get)

    scores = [
        _most_likely_score(
            row["HomeExpectedGoals"],
            row["AwayExpectedGoals"],
            outcome=_row_outcome(row),
        )
        for _, row in df.iterrows()
    ]
    df["PredictedHomeGoals"] = [s[0] for s in scores]
    df["PredictedAwayGoals"] = [s[1] for s in scores]

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    for col in ARCHIVE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[ARCHIVE_COLUMNS]

    path = archive_path(league, season, archive_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = pd.read_csv(path, encoding="utf-8-sig")

        # Skip fixtures already predicted today — makes re-runs idempotent
        key = ["PredictedOn", "Date", "HomeTeam", "AwayTeam"]
        merged = df.merge(
            existing[key].drop_duplicates(),
            on=key,
            how="left",
            indicator=True,
        )
        df = df[merged["_merge"].values == "left_only"]

        if df.empty:
            return path

        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df

    combined.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def load_archive(
    league: str,
    season: str,
    archive_dir: Path | str | None = None,
) -> pd.DataFrame:
    path = archive_path(league, season, archive_dir)
    if not path.exists():
        return pd.DataFrame(columns=ARCHIVE_COLUMNS)
    return pd.read_csv(path, encoding="utf-8-sig")


def latest_predictions(
    league: str,
    season: str,
    archive_dir: Path | str | None = None,
) -> pd.DataFrame:
    """
    One row per fixture — the most recent prediction made before the match.
    This is what a fixture gets scored against.
    """
    df = load_archive(league, season, archive_dir)
    if df.empty:
        return df

    df["PredictedOn"] = pd.to_datetime(df["PredictedOn"], errors="coerce")
    df["Date"]        = pd.to_datetime(df["Date"],        errors="coerce")

    # Only predictions made on or before matchday count
    df = df[df["PredictedOn"] <= df["Date"]]

    if df.empty:
        return df

    return (
        df.sort_values("PredictedOn")
          .groupby(["Date", "HomeTeam", "AwayTeam"], as_index=False)
          .last()
    )
