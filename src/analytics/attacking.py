from __future__ import annotations

import pandas as pd


def _team_attacking_stats(matches: pd.DataFrame) -> pd.DataFrame:
    records = []

    teams = sorted(set(matches["HomeTeam"]) | set(matches["AwayTeam"]))

    for team in teams:
        home = matches[matches["HomeTeam"] == team]
        away = matches[matches["AwayTeam"] == team]

        played = len(home) + len(away)
        if played == 0:
            continue

        goals = int(home["FTHG"].sum()) + int(away["FTAG"].sum())
        shots = home["HS"].sum() + away["AS"].sum()
        shots_on_target = home["HST"].sum() + away["AST"].sum()

        goals_per_match = goals / played
        shots_per_match = shots / played
        sot_per_match = shots_on_target / played
        goals_per_sot = goals / shots_on_target if shots_on_target > 0 else 0.0
        goals_per_shot = goals / shots if shots > 0 else 0.0

        records.append({
            "Team": team,
            "Played": played,
            "Goals": goals,
            "Shots": int(shots),
            "ShotsOnTarget": int(shots_on_target),
            "GoalsPerMatch": round(goals_per_match, 2),
            "ShotsPerMatch": round(shots_per_match, 2),
            "SoTPerMatch": round(sot_per_match, 2),
            "GoalsPerSoT": round(goals_per_sot, 3),
            "GoalsPerShot": round(goals_per_shot, 3),
        })

    return pd.DataFrame(records)


def most_lethal(matches: pd.DataFrame) -> pd.DataFrame:
    """Highest goals per match — overall striking output."""
    df = _team_attacking_stats(matches)
    return df.sort_values("GoalsPerMatch", ascending=False).reset_index(drop=True)


def most_effective(matches: pd.DataFrame) -> pd.DataFrame:
    """Best conversion of shots on target into goals."""
    df = _team_attacking_stats(matches)
    return df.sort_values("GoalsPerSoT", ascending=False).reset_index(drop=True)


def best_chance_creators(matches: pd.DataFrame) -> pd.DataFrame:
    """Highest shots on target per match — best at manufacturing chances."""
    df = _team_attacking_stats(matches)
    return df.sort_values("SoTPerMatch", ascending=False).reset_index(drop=True)


def most_clinical(matches: pd.DataFrame) -> pd.DataFrame:
    """Highest goals per total shot — most efficient use of all attempts."""
    df = _team_attacking_stats(matches)
    return df.sort_values("GoalsPerShot", ascending=False).reset_index(drop=True)


def all_attacking_stats(matches: pd.DataFrame) -> pd.DataFrame:
    """All attacking metrics in one DataFrame, sorted by goals per match."""
    return most_lethal(matches)