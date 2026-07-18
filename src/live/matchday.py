"""
src/live/matchday.py

Small helper for slicing the next "matchday" out of the full set of
remaining-fixture predictions produced by
src.live.live_forecast.prepare_live_remaining_predictions
(i.e. the `remaining_predictions` DataFrame, which already has
HomeTeam, AwayTeam, HomeExpectedGoals, AwayExpectedGoals, HomeWinProb,
DrawProb, AwayWinProb, Date, Season columns from predict_fixture_list).

This is intentionally read-only / non-invasive: it does not change how
predictions are computed, it just selects which rows belong to the
"next matchday" for display purposes.
"""

from __future__ import annotations

import pandas as pd


# EPL matchdays are typically played across a Friday-Monday window.
# A 4-day window from the earliest remaining fixture date comfortably
# covers a single round without pulling in the following one.
DEFAULT_MATCHDAY_WINDOW_DAYS = 4


def get_next_matchday_fixtures(
    remaining_predictions: pd.DataFrame,
    window_days: int = DEFAULT_MATCHDAY_WINDOW_DAYS,
) -> pd.DataFrame:
    """
    Return the subset of `remaining_predictions` whose Date falls
    within `window_days` of the earliest remaining fixture date.

    `remaining_predictions` must contain a 'Date' column. Dates are
    parsed with dayfirst=True, matching the dd/mm/yyyy convention used
    elsewhere in this project (e.g. src/models/elo.py).

    Returns a copy of the matching rows, sorted by Date, with the
    original columns preserved (no extra columns added).
    """
    if remaining_predictions.empty:
        return remaining_predictions.copy()

    df = remaining_predictions.copy()

    parsed_dates = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

    if parsed_dates.isna().all():
        # Couldn't parse any dates - fall back to returning everything
        # rather than silently returning an empty frame.
        return df.reset_index(drop=True)

    earliest = parsed_dates.min()
    cutoff = earliest + pd.Timedelta(days=window_days)

    mask = parsed_dates <= cutoff

    next_matchday = df[mask].copy()
    next_matchday["_ParsedDate"] = parsed_dates[mask]

    next_matchday = next_matchday.sort_values("_ParsedDate")
    next_matchday = next_matchday.drop(columns=["_ParsedDate"])

    return next_matchday.reset_index(drop=True)


def matchday_label(remaining_predictions: pd.DataFrame, next_matchday: pd.DataFrame) -> str:
    """
    Build a human-readable label for the matchday card, e.g.
    "Matchday fixtures: 16-19 Aug 2025".

    Falls back to a generic label if dates can't be parsed.
    """
    if next_matchday.empty or "Date" not in next_matchday.columns:
        return "Upcoming Fixtures"

    parsed = pd.to_datetime(next_matchday["Date"], errors="coerce", dayfirst=True)

    if parsed.isna().all():
        return "Upcoming Fixtures"

    start = parsed.min()
    end = parsed.max()

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def fmt(ts, include_month=True, include_year=True):
        parts = [str(ts.day)]
        if include_month:
            parts.append(months[ts.month - 1])
        if include_year:
            parts.append(str(ts.year))
        return " ".join(parts)

    if start.date() == end.date():
        return f"Fixtures: {fmt(start)}"

    if start.month == end.month and start.year == end.year:
        return f"Fixtures: {fmt(start, include_month=False, include_year=False)}-{fmt(end)}"

    return f"Fixtures: {fmt(start, include_year=(start.year != end.year))} - {fmt(end)}"