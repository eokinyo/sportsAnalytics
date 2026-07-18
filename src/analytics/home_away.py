from __future__ import annotations

import pandas as pd


def _home_stats(matches: pd.DataFrame) -> pd.DataFrame:
    records = []

    teams = sorted(matches["HomeTeam"].unique())

    for team in teams:
        home = matches[matches["HomeTeam"] == team]
        played = len(home)
        if played == 0:
            continue

        wins   = (home["FTR"] == "H").sum()
        draws  = (home["FTR"] == "D").sum()
        losses = (home["FTR"] == "A").sum()
        gf     = int(home["FTHG"].sum())
        ga     = int(home["FTAG"].sum())
        points = wins * 3 + draws

        records.append({
            "Team":          team,
            "HomePlayed":    played,
            "HomeWins":      int(wins),
            "HomeDraws":     int(draws),
            "HomeLosses":    int(losses),
            "HomeGF":        gf,
            "HomeGA":        ga,
            "HomeGD":        gf - ga,
            "HomePoints":    int(points),
            "HomePPM":       round(points / played, 2),
            "HomeWinPct":    round(wins   / played * 100, 1),
            "HomeGFPerMatch":round(gf     / played, 2),
            "HomeGAPerMatch":round(ga     / played, 2),
        })

    return pd.DataFrame(records)


def _away_stats(matches: pd.DataFrame) -> pd.DataFrame:
    records = []

    teams = sorted(matches["AwayTeam"].unique())

    for team in teams:
        away = matches[matches["AwayTeam"] == team]
        played = len(away)
        if played == 0:
            continue

        wins   = (away["FTR"] == "A").sum()
        draws  = (away["FTR"] == "D").sum()
        losses = (away["FTR"] == "H").sum()
        gf     = int(away["FTAG"].sum())
        ga     = int(away["FTHG"].sum())
        points = wins * 3 + draws

        records.append({
            "Team":          team,
            "AwayPlayed":    played,
            "AwayWins":      int(wins),
            "AwayDraws":     int(draws),
            "AwayLosses":    int(losses),
            "AwayGF":        gf,
            "AwayGA":        ga,
            "AwayGD":        gf - ga,
            "AwayPoints":    int(points),
            "AwayPPM":       round(points / played, 2),
            "AwayWinPct":    round(wins   / played * 100, 1),
            "AwayGFPerMatch":round(gf     / played, 2),
            "AwayGAPerMatch":round(ga     / played, 2),
        })

    return pd.DataFrame(records)


def home_fortress(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by home points per match — best home teams first."""
    return _home_stats(matches).sort_values("HomePPM", ascending=False).reset_index(drop=True)


def away_warriors(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by away points per match — best away teams first."""
    return _away_stats(matches).sort_values("AwayPPM", ascending=False).reset_index(drop=True)