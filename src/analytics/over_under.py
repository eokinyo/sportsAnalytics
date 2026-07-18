from __future__ import annotations

import pandas as pd


def over_under_stats(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by Over 2.5 goals % — teams most involved in high-scoring games first."""
    completed = matches.dropna(subset=["FTHG", "FTAG"]).copy()
    teams     = sorted(set(completed["HomeTeam"]) | set(completed["AwayTeam"]))
    records   = []

    for team in teams:
        team_matches = completed[
            (completed["HomeTeam"] == team) | (completed["AwayTeam"] == team)
        ]
        played = len(team_matches)
        if played == 0:
            continue

        total_goals = team_matches["FTHG"] + team_matches["FTAG"]

        over_25 = (total_goals > 2.5).sum()
        over_15 = (total_goals > 1.5).sum()
        avg_goals = total_goals.mean()

        records.append({
            "Team":        team,
            "Played":      played,
            "Over25":      int(over_25),
            "Over25Pct":   round(over_25 / played * 100, 1),
            "Over15":      int(over_15),
            "Over15Pct":   round(over_15 / played * 100, 1),
            "AvgGoals":    round(avg_goals, 2),
        })

    return (
        pd.DataFrame(records)
        .sort_values("Over25Pct", ascending=False)
        .reset_index(drop=True)
    )