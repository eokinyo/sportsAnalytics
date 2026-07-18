"""
debug.py
Fully automatic flow from Monte Carlo simulation
"""

from src.simulation.monte_carlo import (
    run_monte_carlo_simulation,
    summarize_simulations,
    get_title_probabilities,
)
from src.visualization.card import CardGenerator
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_dummy_fixtures(n_matches: int = 120) -> pd.DataFrame:
    """Creates dummy fixtures with all required columns."""
    teams = [
        "Arsenal", "Man City", "Liverpool", "Chelsea", "Tottenham",
        "Aston Villa", "Newcastle", "Man United", "West Ham", "Crystal Palace",
        "Brighton", "Fulham", "Wolves", "Bournemouth", "Brentford",
        "Everton", "Leicester", "Ipswich", "Southampton", "Leeds"
    ]
    records = []
    base_date = datetime(2025, 8, 15)

    for i in range(n_matches):
        home, away = np.random.choice(teams, 2, replace=False)
        home_win = np.random.uniform(0.28, 0.52)
        draw = np.random.uniform(0.22, 0.32)
        away_win = 1 - home_win - draw

        total_xg = np.random.uniform(2.5, 3.1)
        home_xg = round(total_xg * (home_win + 0.12), 2)
        away_xg = round(total_xg - home_xg, 2)

        match_date = base_date + timedelta(days=i * 3)

        records.append({
            "Date": match_date.strftime("%Y-%m-%d"),
            "Season": "2025_2026",
            "HomeTeam": home,
            "AwayTeam": away,
            "HomeWinProb": round(home_win, 4),
            "DrawProb": round(draw, 4),
            "AwayWinProb": round(away_win, 4),
            "HomeExpectedGoals": home_xg,
            "AwayExpectedGoals": away_xg,
        })

    return pd.DataFrame(records)


# ============================================================
# MAIN DEBUG FLOW
# ============================================================

print("Creating dummy fixtures...")
fixtures_with_probs = create_dummy_fixtures(n_matches=120)

print("\nRunning Monte Carlo simulation...")
sim_results = run_monte_carlo_simulation(
    fixtures_with_probs=fixtures_with_probs,
    n_simulations=3000,
    seed=42,
    progress_every=500,
)

print("\nSummarizing simulation results...")
summary = summarize_simulations(sim_results)

# Automatically extract title probabilities
title_probs = get_title_probabilities(summary)

print("\nTop 5 Title Probabilities (from simulation):")
for team, prob in list(title_probs.items())[:5]:
    print(f"  {team}: {prob}%")

# ============================================================
# Build the league table DIRECTLY from simulation results
# ============================================================
current_table = summary[[
    "ExpectedRank", 
    "Team", 
    "ExpectedPoints", 
    "ExpectedGD"
]].copy()

current_table.columns = ["Position", "Team", "Points", "GD"]

print("\nGenerating forecast card (everything from simulation)...")
generator = CardGenerator()

path = generator.create_season_forecast_card(
    table_df=current_table,           # ← Built from simulation
    title_probs=title_probs,          # ← Built from simulation
    season="2025/26",
    forecast_date="June 12, 2026",
    league="Premier League"
)

print(f"\n✅ Card saved to: {path}")