"""
generate_results.py

Generate "prediction vs result" cards for fixtures that have been played.

Usage:
    python generate_results.py                          # all new results, all leagues
    python generate_results.py --league epl             # one league
    python generate_results.py --league epl --home Arsenal --away Chelsea
    python generate_results.py --league epl --summary   # accuracy record only
"""

import argparse
import os

import pandas as pd

from src.analytics.results import (
    join_predictions_to_results,
    accuracy_summary,
)
from src.visualization.card import CardGenerator

TWITTER_HANDLE = "@e_okinyo"

LEAGUE_CONFIG = {
    "epl":        {"display_name": "Premier League",
                   "data_path": r"data\processed\epl\epl_matches_clean.csv",
                   "logo_dir":  r"data\logos\epl"},
    "laliga":     {"display_name": "La Liga",
                   "data_path": r"data\processed\laliga\laliga_matches_clean.csv",
                   "logo_dir":  r"data\logos\laliga"},
    "bundesliga": {"display_name": "Bundesliga",
                   "data_path": r"data\processed\bundesliga\bundesliga_matches_clean.csv",
                   "logo_dir":  r"data\logos\bundesliga"},
    "ligue_1":    {"display_name": "Ligue 1",
                   "data_path": r"data\processed\ligue_1\ligue_1_matches_clean.csv",
                   "logo_dir":  r"data\logos\ligue_1"},
    "serie_a":    {"display_name": "Serie A",
                   "data_path": r"data\processed\serie_a\serie_a_matches_clean.csv",
                   "logo_dir":  r"data\logos\serie_a"},
}


def current_season(matches: pd.DataFrame) -> str:
    return sorted(matches["Season"].dropna().unique())[-1]


def run(league: str,
        home: str | None = None,
        away: str | None = None,
        summary_only: bool = False,
        overwrite: bool = False):
    config = LEAGUE_CONFIG[league]

    if not os.path.exists(config["data_path"]):
        print(f"  x Data file not found: {config['data_path']}")
        return

    matches = pd.read_csv(config["data_path"], encoding="utf-8-sig")
    season  = current_season(matches)

    joined = join_predictions_to_results(matches, league, season)

    if joined.empty:
        print(f"  x No archived predictions matched to played fixtures yet.")
        return

    stats = accuracy_summary(matches, league, season)
    print(f"  Record: {stats['OutcomeCorrect']}/{stats['Fixtures']} outcomes "
          f"({stats['OutcomeAccuracy']}%)  ·  "
          f"{stats['ScoreCorrect']} exact scores ({stats['ScoreAccuracy']}%)  ·  "
          f"Brier {stats['AvgBrierScore']}")

    if summary_only:
        return

    if home and away:
        joined = joined[(joined["HomeTeam"] == home) & (joined["AwayTeam"] == away)]
        if joined.empty:
            print(f"  x No result found for {home} vs {away}")
            return

    out_dir = os.path.join("outputs", "results", league)
    os.makedirs(out_dir, exist_ok=True)

    generator = CardGenerator(
        output_dir=out_dir,
        logos_dir=config["logo_dir"],
    )

    season_label = season.replace("_", "/")[:5] + season[-2:]

    made = 0
    for _, row in joined.iterrows():
        result   = row.to_dict()
        date_str = pd.to_datetime(result["Date"]).strftime("%Y-%m-%d")
        fname    = (f"{date_str}__{result['HomeTeam'].replace(' ', '_')}"
                    f"_vs_{result['AwayTeam'].replace(' ', '_')}.png")

        if os.path.exists(os.path.join(out_dir, fname)) and not overwrite:
            continue

        generator.create_result_card(
            result   = result,
            season   = season_label,
            league   = config["display_name"],
            filename = fname,
        )
        made += 1

    print(f"  + {made} new result card{'s' if made != 1 else ''} "
          f"({len(joined) - made} already existed)")


def main(league: str | None = None) -> None:
    """Convenience entry point matching main.py / generate_cards.py."""
    leagues = [league] if league else list(LEAGUE_CONFIG.keys())
    for lg in leagues:
        print(f"[ {LEAGUE_CONFIG[lg]['display_name']} ]")
        run(lg)
        print()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate prediction-vs-result cards")
    p.add_argument("--league",    choices=list(LEAGUE_CONFIG.keys()), default=None)
    p.add_argument("--home",      default=None, help="Filter to one fixture")
    p.add_argument("--away",      default=None)
    p.add_argument("--summary",   action="store_true", help="Print record only")
    p.add_argument("--overwrite", action="store_true", help="Rebuild existing cards")
    args = p.parse_args()

    leagues = [args.league] if args.league else list(LEAGUE_CONFIG.keys())

    print(f"\n{'='*56}")
    print("  Result Card Generator")
    print(f"{'='*56}\n")

    for lg in leagues:
        print(f"[ {LEAGUE_CONFIG[lg]['display_name']} ]")
        try:
            run(lg, args.home, args.away, args.summary, args.overwrite)
        except Exception as e:
            import traceback
            print(f"  x Error: {e}")
            traceback.print_exc()
        print()

    print("Done.\n")
