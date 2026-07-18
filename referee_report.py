"""
referee_report.py

Generate a referee report card for a specific fixture.

Usage:
    python referee_report.py --referee "A Taylor" --home "Arsenal" --away "Chelsea"
    python referee_report.py --referee "A Taylor" --home "Arsenal" --away "Chelsea" --league epl
"""

import argparse
import os
from datetime import datetime

import pandas as pd

from src.analytics.referee import referee_match_profile
from src.visualization.referee_card import create_referee_report_card

# ── Config ────────────────────────────────────────────────────────────────────

TWITTER_HANDLE = "@e_okinyo"

LEAGUE_CONFIG = {
    "epl": {
        "display_name": "Premier League",
        "data_path":    r"data\processed\epl\epl_matches_clean.csv",
        "logo_dir":     r"data\logos\epl",
    },
    "laliga": {
        "display_name": "La Liga",
        "data_path":    r"data\processed\laliga\laliga_matches_clean.csv",
        "logo_dir":     r"data\logos\laliga",
    },
    "bundesliga": {
        "display_name": "Bundesliga",
        "data_path":    r"data\processed\bundesliga\bundesliga_matches_clean.csv",
        "logo_dir":     r"data\logos\bundesliga",
    },
    "ligue_1": {
        "display_name": "Ligue 1",
        "data_path":    r"data\processed\ligue_1\ligue_1_matches_clean.csv",
        "logo_dir":     r"data\logos\ligue_1",
    },
    "serie_a": {
        "display_name": "Serie A",
        "data_path":    r"data\processed\serie_a\serie_a_matches_clean.csv",
        "logo_dir":     r"data\logos\serie_a",
    },
}


def run(referee: str, home_team: str, away_team: str, league: str):
    config = LEAGUE_CONFIG[league]

    if not os.path.exists(config["data_path"]):
        print(f"✗ Data file not found: {config['data_path']}")
        return

    matches = pd.read_csv(config["data_path"], encoding="utf-8-sig")

    if "Referee" not in matches.columns:
        print("✗ Referee column not found. Please reprocess data with updated preprocess.py.")
        return

    # Fuzzy referee name match — helps with partial names
    available = matches["Referee"].dropna().unique()
    if referee not in available:
        close = [r for r in available if referee.lower() in r.lower()]
        if not close:
            print(f"✗ Referee '{referee}' not found.")
            print(f"  Available referees: {sorted(available)}")
            return
        if len(close) == 1:
            print(f"  Matched '{referee}' → '{close[0]}'")
            referee = close[0]
        else:
            print(f"  Multiple matches for '{referee}': {close}")
            print("  Please be more specific.")
            return

    print(f"\nGenerating referee report...")
    print(f"  Referee : {referee}")
    print(f"  Fixture : {home_team} vs {away_team}")
    print(f"  League  : {config['display_name']}")

    try:
        profile = referee_match_profile(
            matches   = matches,
            referee   = referee,
            home_team = home_team,
            away_team = away_team,
        )
    except ValueError as e:
        print(f"✗ {e}")
        return

    ref_avg = profile["referee_avg"]
    home_s  = profile["home_team"]
    away_s  = profile["away_team"]

    print(f"\n  Referee overall: {ref_avg['Games']} games, "
          f"{ref_avg['CardsPerGame']} cards/game, "
          f"{ref_avg['YellowsPerGame']}Y {ref_avg['RedsPerGame']}R")
    print(f"  {home_team}: {home_s['Games']} games together — "
          f"{home_s['Wins']}W {home_s['Draws']}D {home_s['Losses']}L, "
          f"{home_s['YellowsPerGame']}Y {home_s['RedsPerGame']}R/game")
    print(f"  {away_team}: {away_s['Games']} games together — "
          f"{away_s['Wins']}W {away_s['Draws']}D {away_s['Losses']}L, "
          f"{away_s['YellowsPerGame']}Y {away_s['RedsPerGame']}R/game")

    safe_ref  = referee.replace(" ", "_")
    safe_home = home_team.replace(" ", "_")
    safe_away = away_team.replace(" ", "_")
    filename  = f"{safe_ref}__{safe_home}_vs_{safe_away}.png"
    out_path  = os.path.join("outputs", "analytics", league, "referee", filename)

    create_referee_report_card(
        profile        = profile,
        logo_dir       = config["logo_dir"],
        output_path    = out_path,
        league_name    = config["display_name"],
        as_of_date     = datetime.now().strftime("%d %B %Y"),
        twitter_handle = TWITTER_HANDLE,
    )

    print(f"\n✓ Saved: {out_path}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate referee report card for a fixture")
    parser.add_argument("--referee",  required=True, help="Referee name e.g. 'A Taylor'")
    parser.add_argument("--home",     required=True, help="Home team name")
    parser.add_argument("--away",     required=True, help="Away team name")
    parser.add_argument("--league",   default="epl", choices=list(LEAGUE_CONFIG.keys()))
    args = parser.parse_args()

    run(
        referee   = args.referee,
        home_team = args.home,
        away_team = args.away,
        league    = args.league,
    )