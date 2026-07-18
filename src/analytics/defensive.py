from __future__ import annotations

import pandas as pd


def _team_defensive_stats(matches: pd.DataFrame) -> pd.DataFrame:
    records = []

    teams = sorted(set(matches["HomeTeam"]) | set(matches["AwayTeam"]))

    for team in teams:
        home = matches[matches["HomeTeam"] == team]
        away = matches[matches["AwayTeam"] == team]

        played = len(home) + len(away)
        if played == 0:
            continue

        conceded       = int(home["FTAG"].sum()) + int(away["FTHG"].sum())
        sot_faced      = home["AST"].sum() + away["HST"].sum()
        shots_faced    = home["AS"].sum()  + away["HS"].sum()

        clean_sheets   = (
            (home["FTAG"] == 0).sum() +
            (away["FTHG"] == 0).sum()
        )

        conceded_per_match  = round(conceded / played, 2)
        sot_faced_per_match = round(sot_faced / played, 2)
        clean_sheet_pct     = round(clean_sheets / played * 100, 1)

        records.append({
            "Team":               team,
            "Played":             played,
            "Conceded":           conceded,
            "ShotsFaced":         int(shots_faced),
            "SoTFaced":           int(sot_faced),
            "CleanSheets":        int(clean_sheets),
            "ConcededPerMatch":   conceded_per_match,
            "SoTFacedPerMatch":   sot_faced_per_match,
            "CleanSheetPct":      clean_sheet_pct,
        })

    return pd.DataFrame(records)


def defensive_record(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by goals conceded per match (ascending — best defence first)."""
    df = _team_defensive_stats(matches)
    return df.sort_values("ConcededPerMatch", ascending=True).reset_index(drop=True)


def best_shot_stoppers(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by shots on target faced per match (ascending — best first)."""
    df = _team_defensive_stats(matches)
    return df.sort_values("SoTFacedPerMatch", ascending=True).reset_index(drop=True)