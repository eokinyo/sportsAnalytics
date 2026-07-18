from __future__ import annotations

import pandas as pd

FORM_WINDOW = 5


def _get_team_matches(matches: pd.DataFrame, team: str) -> pd.DataFrame:
    df = matches.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False, errors="coerce")
    team_matches = df[
        (df["HomeTeam"] == team) | (df["AwayTeam"] == team)
    ].sort_values("Date")
    return team_matches


def _last_n_matches(matches: pd.DataFrame, team: str, n: int = FORM_WINDOW) -> pd.DataFrame:
    return _get_team_matches(matches, team).tail(n)


def _match_result(row, team: str) -> str:
    if row["HomeTeam"] == team:
        if row["FTR"] == "H": return "W"
        if row["FTR"] == "D": return "D"
        return "L"
    else:
        if row["FTR"] == "A": return "W"
        if row["FTR"] == "D": return "D"
        return "L"


def _goals_for(row, team: str) -> int:
    return int(row["FTHG"]) if row["HomeTeam"] == team else int(row["FTAG"])


def _goals_against(row, team: str) -> int:
    return int(row["FTAG"]) if row["HomeTeam"] == team else int(row["FTHG"])


def _form_stats(matches: pd.DataFrame, n: int = FORM_WINDOW) -> pd.DataFrame:
    completed = matches.dropna(subset=["FTHG", "FTAG", "FTR"]).copy()
    teams     = sorted(set(completed["HomeTeam"]) | set(completed["AwayTeam"]))
    records   = []

    for team in teams:
        last = _last_n_matches(completed, team, n)
        if len(last) == 0:
            continue

        results = [_match_result(row, team) for _, row in last.iterrows()]
        gf      = sum(_goals_for(row,     team) for _, row in last.iterrows())
        ga      = sum(_goals_against(row, team) for _, row in last.iterrows())
        wins    = results.count("W")
        draws   = results.count("D")
        points  = wins * 3 + draws

        records.append({
            "Team":           team,
            "FormMatches":    len(last),
            "FormPoints":     points,
            "FormWins":       wins,
            "FormDraws":      draws,
            "FormLosses":     results.count("L"),
            "FormGF":         gf,
            "FormGA":         ga,
            "FormGD":         gf - ga,
            "FormGFPerMatch": round(gf / len(last), 2),
            "FormStr":        "".join(results),
        })

    return pd.DataFrame(records)


def _streak_stats(matches: pd.DataFrame) -> pd.DataFrame:
    completed = matches.dropna(subset=["FTHG", "FTAG", "FTR"]).copy()
    completed["Date"] = pd.to_datetime(completed["Date"], format="mixed", dayfirst=False, errors="coerce")
    completed = completed.sort_values("Date")
    teams     = sorted(set(completed["HomeTeam"]) | set(completed["AwayTeam"]))
    records   = []

    for team in teams:
        team_matches = completed[
            (completed["HomeTeam"] == team) | (completed["AwayTeam"] == team)
        ].sort_values("Date")

        results = [_match_result(row, team) for _, row in team_matches.iterrows()]

        unbeaten = 0
        for r in reversed(results):
            if r in ("W", "D"): unbeaten += 1
            else: break

        win_streak = 0
        for r in reversed(results):
            if r == "W": win_streak += 1
            else: break

        lose_streak = 0
        for r in reversed(results):
            if r == "L": lose_streak += 1
            else: break

        records.append({
            "Team":           team,
            "UnbeatenStreak": unbeaten,
            "WinStreak":      win_streak,
            "LoseStreak":     lose_streak,
        })

    return pd.DataFrame(records)


def current_form(matches: pd.DataFrame) -> pd.DataFrame:
    df = _form_stats(matches)
    return df.sort_values(
        ["FormPoints", "FormGD", "FormGF"],
        ascending=[False, False, False]
    ).reset_index(drop=True)


def hot_streaks(matches: pd.DataFrame) -> pd.DataFrame:
    df = _streak_stats(matches)
    return df.sort_values(
        ["UnbeatenStreak", "WinStreak"],
        ascending=[False, False]
    ).reset_index(drop=True)


def cold_streaks(matches: pd.DataFrame) -> pd.DataFrame:
    df = _streak_stats(matches)
    return df.sort_values(
        ["LoseStreak"], ascending=[False]
    ).reset_index(drop=True)


def rolling_attack(matches: pd.DataFrame) -> pd.DataFrame:
    df = _form_stats(matches)
    return df.sort_values(
        ["FormGF", "FormGFPerMatch"],
        ascending=[False, False]
    ).reset_index(drop=True)