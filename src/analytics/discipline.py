from __future__ import annotations

import pandas as pd


YELLOW_WEIGHT = 2
RED_WEIGHT    = 5


def _team_discipline_stats(matches: pd.DataFrame) -> pd.DataFrame:
    records = []

    teams = sorted(set(matches["HomeTeam"]) | set(matches["AwayTeam"]))

    for team in teams:
        home = matches[matches["HomeTeam"] == team]
        away = matches[matches["AwayTeam"] == team]

        played  = len(home) + len(away)
        if played == 0:
            continue

        yellows = int(home["HY"].sum()) + int(away["AY"].sum())
        reds    = int(home["HR"].sum()) + int(away["AR"].sum())
        fouls   = int(home["HF"].sum()) + int(away["AF"].sum())

        composite = fouls + (yellows * YELLOW_WEIGHT) + (reds * RED_WEIGHT)

        records.append({
            "Team":               team,
            "Played":             played,
            "Yellows":            yellows,
            "Reds":               reds,
            "Fouls":              fouls,
            "YellowsPerMatch":    round(yellows / played, 2),
            "RedsPerMatch":       round(reds    / played, 2),
            "FoulsPerMatch":      round(fouls   / played, 2),
            "DisciplineScore":    round(composite / played, 2),
        })

    return pd.DataFrame(records)


def discipline_ranking(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by discipline score ascending — fairest teams first."""
    df = _team_discipline_stats(matches)
    return df.sort_values("DisciplineScore", ascending=True).reset_index(drop=True)