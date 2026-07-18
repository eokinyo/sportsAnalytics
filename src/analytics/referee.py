from __future__ import annotations

import pandas as pd

MIN_GAMES = 3


def referee_strictness(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by total cards per game — strictest referees first."""
    if "Referee" not in matches.columns:
        return pd.DataFrame()

    df = matches.dropna(subset=["Referee"]).copy()
    records = []

    for ref, group in df.groupby("Referee"):
        games = len(group)
        if games < MIN_GAMES:
            continue

        yellows = int(group["HY"].sum() + group["AY"].sum())
        reds    = int(group["HR"].sum() + group["AR"].sum())
        fouls   = int(group["HF"].sum() + group["AF"].sum())
        cards   = yellows + reds

        records.append({
            "Referee":        ref,
            "Games":          games,
            "Yellows":        yellows,
            "Reds":           reds,
            "Fouls":          fouls,
            "YellowsPerGame": round(yellows / games, 2),
            "RedsPerGame":    round(reds    / games, 2),
            "FoulsPerGame":   round(fouls   / games, 2),
            "CardsPerGame":   round(cards   / games, 2),
        })

    if not records:
        return pd.DataFrame()

    return (
        pd.DataFrame(records)
        .sort_values("CardsPerGame", ascending=False)
        .reset_index(drop=True)
    )


def referee_team_profile(
    matches: pd.DataFrame,
    referee: str,
    team: str,
) -> dict:
    """
    Return historical stats for a specific referee-team pair,
    compared against that referee's overall averages.
    """
    if "Referee" not in matches.columns:
        raise ValueError("Referee column not found in match data.")

    df = matches.dropna(subset=["Referee", "HY", "AY", "HR", "AR", "HF", "AF"]).copy()

    # All games by this referee
    ref_games = df[df["Referee"] == referee]
    if ref_games.empty:
        raise ValueError(f"No games found for referee: {referee}")

    # Referee overall averages
    ref_total   = len(ref_games)
    ref_yellows = int(ref_games["HY"].sum() + ref_games["AY"].sum())
    ref_reds    = int(ref_games["HR"].sum() + ref_games["AR"].sum())
    ref_fouls   = int(ref_games["HF"].sum() + ref_games["AF"].sum())

    ref_avg = {
        "Games":          ref_total,
        "YellowsPerGame": round(ref_yellows / ref_total, 2),
        "RedsPerGame":    round(ref_reds    / ref_total, 2),
        "FoulsPerGame":   round(ref_fouls   / ref_total, 2),
        "CardsPerGame":   round((ref_yellows + ref_reds) / ref_total, 2),
    }

    def _team_stats(team_name: str) -> dict:
        home = ref_games[ref_games["HomeTeam"] == team_name]
        away = ref_games[ref_games["AwayTeam"] == team_name]
        all_games = pd.concat([home, away])
        games = len(all_games)

        if games == 0:
            return {"Games": 0}

        # Cards received by the team
        yellows = int(home["HY"].sum()) + int(away["AY"].sum())
        reds    = int(home["HR"].sum()) + int(away["AR"].sum())
        fouls   = int(home["HF"].sum()) + int(away["AF"].sum())

        # Results from team perspective
        home_wins  = (home["FTR"] == "H").sum()
        away_wins  = (away["FTR"] == "A").sum()
        home_draws = (home["FTR"] == "D").sum()
        away_draws = (away["FTR"] == "D").sum()
        wins  = int(home_wins  + away_wins)
        draws = int(home_draws + away_draws)
        losses = games - wins - draws
        points = wins * 3 + draws

        ypg = round(yellows / games, 2)
        rpg = round(reds    / games, 2)
        fpg = round(fouls   / games, 2)
        cpg = round((yellows + reds) / games, 2)

        # vs referee average
        yellow_vs_avg = round(ypg - ref_avg["YellowsPerGame"], 2)
        red_vs_avg    = round(rpg - ref_avg["RedsPerGame"],    2)
        card_vs_avg   = round(cpg - ref_avg["CardsPerGame"],   2)

        return {
            "Team":          team_name,
            "Games":         games,
            "Wins":          wins,
            "Draws":         draws,
            "Losses":        losses,
            "Points":        points,
            "PPM":           round(points / games, 2),
            "Yellows":       yellows,
            "Reds":          reds,
            "Fouls":         fouls,
            "YellowsPerGame":ypg,
            "RedsPerGame":   rpg,
            "FoulsPerGame":  fpg,
            "CardsPerGame":  cpg,
            "YellowVsAvg":   yellow_vs_avg,
            "RedVsAvg":      red_vs_avg,
            "CardVsAvg":     card_vs_avg,
        }

    return {
        "referee":     referee,
        "referee_avg": ref_avg,
        "home_team":   _team_stats(team),
        "away_team":   None,  # populated by caller for match report
    }


def referee_match_profile(
    matches: pd.DataFrame,
    referee: str,
    home_team: str,
    away_team: str,
) -> dict:
    """
    Full profile for a specific fixture — referee vs both teams.
    Returns all data needed to render the referee report card.
    """
    if "Referee" not in matches.columns:
        raise ValueError("Referee column not found in match data.")

    df = matches.dropna(subset=["Referee", "HY", "AY", "HR", "AR", "HF", "AF"]).copy()

    ref_games = df[df["Referee"] == referee]
    if ref_games.empty:
        raise ValueError(f"No games found for referee: {referee}")

    ref_total   = len(ref_games)
    ref_yellows = int(ref_games["HY"].sum() + ref_games["AY"].sum())
    ref_reds    = int(ref_games["HR"].sum() + ref_games["AR"].sum())
    ref_fouls   = int(ref_games["HF"].sum() + ref_games["AF"].sum())

    ref_avg = {
        "Games":          ref_total,
        "YellowsPerGame": round(ref_yellows / ref_total, 2),
        "RedsPerGame":    round(ref_reds    / ref_total, 2),
        "FoulsPerGame":   round(ref_fouls   / ref_total, 2),
        "CardsPerGame":   round((ref_yellows + ref_reds) / ref_total, 2),
    }

    def _team_stats(team_name: str) -> dict:
        home      = ref_games[ref_games["HomeTeam"] == team_name]
        away      = ref_games[ref_games["AwayTeam"] == team_name]
        all_games = pd.concat([home, away])
        games     = len(all_games)

        if games == 0:
            return {
                "Team": team_name, "Games": 0,
                "Wins": 0, "Draws": 0, "Losses": 0,
                "Points": 0, "PPM": 0.0,
                "Yellows": 0, "Reds": 0, "Fouls": 0,
                "YellowsPerGame": 0.0, "RedsPerGame": 0.0,
                "FoulsPerGame": 0.0, "CardsPerGame": 0.0,
                "YellowVsAvg": 0.0, "RedVsAvg": 0.0, "CardVsAvg": 0.0,
            }

        yellows = int(home["HY"].sum()) + int(away["AY"].sum())
        reds    = int(home["HR"].sum()) + int(away["AR"].sum())
        fouls   = int(home["HF"].sum()) + int(away["AF"].sum())

        wins   = int((home["FTR"] == "H").sum() + (away["FTR"] == "A").sum())
        draws  = int((home["FTR"] == "D").sum() + (away["FTR"] == "D").sum())
        losses = games - wins - draws
        points = wins * 3 + draws

        ypg = round(yellows / games, 2)
        rpg = round(reds    / games, 2)
        fpg = round(fouls   / games, 2)
        cpg = round((yellows + reds) / games, 2)

        return {
            "Team":           team_name,
            "Games":          games,
            "Wins":           wins,
            "Draws":          draws,
            "Losses":         losses,
            "Points":         points,
            "PPM":            round(points / games, 2),
            "Yellows":        yellows,
            "Reds":           reds,
            "Fouls":          fouls,
            "YellowsPerGame": ypg,
            "RedsPerGame":    rpg,
            "FoulsPerGame":   fpg,
            "CardsPerGame":   cpg,
            "YellowVsAvg":    round(ypg - ref_avg["YellowsPerGame"], 2),
            "RedVsAvg":       round(rpg - ref_avg["RedsPerGame"],    2),
            "CardVsAvg":      round(cpg - ref_avg["CardsPerGame"],   2),
        }

    return {
        "referee":     referee,
        "referee_avg": ref_avg,
        "home_team":   _team_stats(home_team),
        "away_team":   _team_stats(away_team),
    }