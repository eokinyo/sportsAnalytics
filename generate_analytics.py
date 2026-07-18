"""
generate_analytics.py

Root orchestrator for all analytics cards.

Usage:
    python generate_analytics.py
    python generate_analytics.py --league epl
"""

import argparse
import os
from datetime import datetime

import pandas as pd

from src.analytics.attacking import (
    most_lethal,
    most_effective,
    best_chance_creators,
    most_clinical,
)
from src.analytics.defensive import defensive_record, best_shot_stoppers
from src.analytics.discipline import discipline_ranking
from src.analytics.referee import referee_strictness
from src.analytics.home_away import home_fortress, away_warriors
from src.analytics.comebacks import comeback_kings, bottle_jobs
from src.analytics.form import current_form, hot_streaks, cold_streaks, rolling_attack
from src.analytics.over_under import over_under_stats
from src.visualization.analytics_card import create_attacking_card, create_analytics_card

# ── Config ────────────────────────────────────────────────────────────────────

AS_OF_DATE_OVERRIDE = ""
TWITTER_HANDLE      = "@e_okinyo"

LEAGUE_CONFIG = {
    "epl": {
        "display_name":    "Premier League",
        "data_path":       r"data\processed\epl\epl_matches_clean.csv",
        "logo_dir":        r"data\logos\epl",
        "season":          "2025_2026",
        "season_label":    "2025/26",
        "total_matchdays": 38,
    },
    "laliga": {
        "display_name":    "La Liga",
        "data_path":       r"data\processed\laliga\laliga_matches_clean.csv",
        "logo_dir":        r"data\logos\laliga",
        "season":          "2025_2026",
        "season_label":    "2025/26",
        "total_matchdays": 38,
    },
    "bundesliga": {
        "display_name":    "Bundesliga",
        "data_path":       r"data\processed\bundesliga\bundesliga_matches_clean.csv",
        "logo_dir":        r"data\logos\bundesliga",
        "season":          "2025_2026",
        "season_label":    "2025/26",
        "total_matchdays": 34,
    },
    "ligue_1": {
        "display_name":    "Ligue 1",
        "data_path":       r"data\processed\ligue_1\ligue_1_matches_clean.csv",
        "logo_dir":        r"data\logos\ligue_1",
        "season":          "2025_2026",
        "season_label":    "2025/26",
        "total_matchdays": 34,
    },
    "serie_a": {
        "display_name":    "Serie A",
        "data_path":       r"data\processed\serie_a\serie_a_matches_clean.csv",
        "logo_dir":        r"data\logos\serie_a",
        "season":          "2025_2026",
        "season_label":    "2025/26",
        "total_matchdays": 38,
    },
}

# ── Metric definitions ────────────────────────────────────────────────────────

ATTACKING_METRICS = [
    {
        "fn":           most_lethal,
        "metric_col":   "GoalsPerMatch",
        "metric_label": "Goals / Match",
        "card_title":   "Most Lethal Attacking Force",
        "subtitle":     "Average goals scored per match · Season to date",
        "extra_col":    "",
        "extra_label":  "",
        "divider_label":"Struggling",
        "filename":     "lethal.png",
    },
    {
        "fn":           most_effective,
        "metric_col":   "GoalsPerSoT",
        "metric_label": "Goals / SoT",
        "card_title":   "Most Effective Striking Force",
        "subtitle":     "Goals scored per shot on target · Season to date",
        "extra_col":    "GoalsPerMatch",
        "extra_label":  "Goals / Match",
        "divider_label":"Struggling",
        "filename":     "effective.png",
    },
    {
        "fn":           best_chance_creators,
        "metric_col":   "SoTPerMatch",
        "metric_label": "SoT / Match",
        "card_title":   "Best Chance Creators",
        "subtitle":     "Shots on target per match · Season to date",
        "extra_col":    "ShotsPerMatch",
        "extra_label":  "Shots / Match",
        "divider_label":"Struggling",
        "filename":     "chance_creators.png",
    },
    {
        "fn":           most_clinical,
        "metric_col":   "GoalsPerShot",
        "metric_label": "Goals / Shot",
        "card_title":   "Most Clinical Finishers",
        "subtitle":     "Goals scored per total shot attempted · Season to date",
        "extra_col":    "GoalsPerMatch",
        "extra_label":  "Goals / Match",
        "divider_label":"Struggling",
        "filename":     "clinical.png",
    },
]

DEFENSIVE_METRICS = [
    {
        "fn":           defensive_record,
        "metric_col":   "ConcededPerMatch",
        "metric_label": "Conceded / Match",
        "card_title":   "Defensive Solidity",
        "subtitle":     "Goals conceded per match · Season to date",
        "extra_col":    "CleanSheetPct",
        "extra_label":  "Clean Sheet %",
        "divider_label":"Most Vulnerable",
        "filename":     "defensive_record.png",
    },
    {
        "fn":           best_shot_stoppers,
        "metric_col":   "SoTFacedPerMatch",
        "metric_label": "SoT Faced / Match",
        "card_title":   "Best Shot Stoppers",
        "subtitle":     "Shots on target faced per match · Season to date",
        "extra_col":    "ConcededPerMatch",
        "extra_label":  "Conceded / Match",
        "divider_label":"Most Exposed",
        "filename":     "shot_stoppers.png",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_as_of_date() -> str:
    if AS_OF_DATE_OVERRIDE:
        return AS_OF_DATE_OVERRIDE
    return datetime.now().strftime("%d %B %Y")


def get_current_matchday(matches: pd.DataFrame) -> int:
    home_counts = matches.groupby("HomeTeam").size()
    away_counts = matches.groupby("AwayTeam").size()
    all_teams   = set(home_counts.index) | set(away_counts.index)
    return int(max(
        home_counts.get(t, 0) + away_counts.get(t, 0)
        for t in all_teams
    ))


def _card_kwargs(config: dict, as_of: str, matchday: int) -> dict:
    return dict(
        logo_dir        = config["logo_dir"],
        league_name     = config["display_name"],
        season          = config["season_label"],
        as_of_date      = as_of,
        matchday        = matchday,
        total_matchdays = config["total_matchdays"],
        twitter_handle  = TWITTER_HANDLE,
    )


# ── Card generators ───────────────────────────────────────────────────────────

def generate_attacking_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "attacking")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    for m in ATTACKING_METRICS:
        ranked = m["fn"](matches)
        create_attacking_card(
            df_ranked     = ranked,
            metric_col    = m["metric_col"],
            metric_label  = m["metric_label"],
            card_title    = m["card_title"],
            subtitle      = m["subtitle"],
            output_path   = os.path.join(out_dir, m["filename"]),
            extra_col     = m["extra_col"],
            extra_label   = m["extra_label"],
            divider_label = m["divider_label"],
            **kwargs,
        )
        print(f"  ✓ {m['card_title']}")


def generate_defensive_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "defensive")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    for m in DEFENSIVE_METRICS:
        ranked = m["fn"](matches)
        create_attacking_card(
            df_ranked     = ranked,
            metric_col    = m["metric_col"],
            metric_label  = m["metric_label"],
            card_title    = m["card_title"],
            subtitle      = m["subtitle"],
            output_path   = os.path.join(out_dir, m["filename"]),
            extra_col     = m["extra_col"],
            extra_label   = m["extra_label"],
            divider_label = m["divider_label"],
            **kwargs,
        )
        print(f"  ✓ {m['card_title']}")


def generate_discipline_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "discipline")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    ranked = discipline_ranking(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("FoulsPerMatch",   "Fouls / Match"),
            ("YellowsPerMatch", "Yellows / Match"),
            ("RedsPerMatch",    "Reds / Match"),
            ("DisciplineScore", "Score"),
        ],
        card_title    = "Fair Play & Discipline",
        subtitle      = "Score = Fouls + (Yellows x2) + (Reds x5) per match · Season to date",
        output_path   = os.path.join(out_dir, "discipline.png"),
        divider_label = "Most Undisciplined",
        **kwargs,
    )
    print("  ✓ Fair Play & Discipline")


def generate_referee_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "referee")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    ranked = referee_strictness(matches)
    if ranked.empty:
        print("  ✗ Referee Strictness — no referee data available, skipping")
        return
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("FoulsPerGame",   "Fouls / Game"),
            ("YellowsPerGame", "Yellows / Game"),
            ("RedsPerGame",    "Reds / Game"),
            ("CardsPerGame",   "Cards / Game"),
        ],
        card_title    = "Referee Strictness",
        subtitle      = "Average cards and fouls per game officiated · Season to date",
        output_path   = os.path.join(out_dir, "strictness.png"),
        divider_label = "Most Lenient",
        name_col      = "Referee",
        show_logo     = False,
        **kwargs,
    )
    print("  ✓ Referee Strictness")


def generate_home_away_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "home_away")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    # Home fortress
    ranked = home_fortress(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("HomeWinPct",    "Win %"),
            ("HomeGFPerMatch","GF / Match"),
            ("HomeGAPerMatch","GA / Match"),
            ("HomePPM",       "Points / Match"),
        ],
        card_title    = "Home Fortress",
        subtitle      = "Home record ranked by points per match · Season to date",
        output_path   = os.path.join(out_dir, "home_fortress.png"),
        divider_label = "Weakest at Home",
        **kwargs,
    )
    print("  ✓ Home Fortress")

    # Away warriors
    ranked = away_warriors(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("AwayWinPct",    "Win %"),
            ("AwayGFPerMatch","GF / Match"),
            ("AwayGAPerMatch","GA / Match"),
            ("AwayPPM",       "Points / Match"),
        ],
        card_title    = "Away Warriors",
        subtitle      = "Away record ranked by points per match · Season to date",
        output_path   = os.path.join(out_dir, "away_warriors.png"),
        divider_label = "Weakest Away",
        **kwargs,
    )
    print("  ✓ Away Warriors")


def generate_comeback_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "comebacks")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    # Comeback Kings
    ranked = comeback_kings(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("LosingAtHT",  "Times Losing at HT"),
            ("Comebacks",   "Comeback Wins"),
            ("ComebackPct", "Comeback %"),
        ],
        card_title    = "Comeback Kings",
        subtitle      = "Wins from losing positions at half time · Season to date",
        output_path   = os.path.join(out_dir, "comeback_kings.png"),
        divider_label = "Never Say Never... or Do They?",
        **kwargs,
    )
    print("  ✓ Comeback Kings")

    # Bottle Jobs
    ranked = bottle_jobs(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("WinningAtHT",  "Times Leading at HT"),
            ("BlownLeads",   "Leads Blown"),
            ("BlownLeadPct", "Blown Lead %"),
        ],
        card_title    = "Bottle Jobs",
        subtitle      = "Leads thrown away from winning positions at half time · Season to date",
        output_path   = os.path.join(out_dir, "bottle_jobs.png"),
        divider_label = "Most Reliable",
        **kwargs,
    )
    print("  ✓ Bottle Jobs")


def generate_form_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "form")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    # Current form — last 5 matches
    ranked = current_form(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("FormWins",   "Wins"),
            ("FormGD",     "GD"),
            ("FormPoints", "Points"),
        ],
        card_title    = "Current Form",
        subtitle      = "Last 5 matches — points, goal difference and wins",
        output_path   = os.path.join(out_dir, "current_form.png"),
        divider_label = "Worst Form",
        **kwargs,
    )
    print("  ✓ Current Form")

    # Hot & cold streaks
    ranked = hot_streaks(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("WinStreak",     "Win Streak"),
            ("UnbeatenStreak","Unbeaten Run"),
        ],
        card_title    = "Hot Streaks",
        subtitle      = "Current unbeaten and winning runs · Season to date",
        output_path   = os.path.join(out_dir, "hot_streaks.png"),
        divider_label = "Coldest Teams",
        **kwargs,
    )
    print("  ✓ Hot Streaks")

    ranked = cold_streaks(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("WinStreak",    "Win Streak"),
            ("LoseStreak",   "Losing Run"),
        ],
        card_title    = "Cold Streaks",
        subtitle      = "Current losing runs · Season to date",
        output_path   = os.path.join(out_dir, "cold_streaks.png"),
        divider_label = "On a Better Run",
        **kwargs,
    )
    print("  ✓ Cold Streaks")

    # Rolling attack — last 5 matches
    ranked = rolling_attack(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("FormGFPerMatch","Goals / Match"),
            ("FormGF",        "Goals Scored"),
        ],
        card_title    = "Rolling Attack",
        subtitle      = "Goals scored in last 5 matches",
        output_path   = os.path.join(out_dir, "rolling_attack.png"),
        divider_label = "Misfiring",
        **kwargs,
    )
    print("  ✓ Rolling Attack")


def generate_over_under_cards(league_key: str, config: dict, matches: pd.DataFrame):
    as_of    = get_as_of_date()
    matchday = get_current_matchday(matches)
    out_dir  = os.path.join("outputs", "analytics", league_key, "over_under")
    os.makedirs(out_dir, exist_ok=True)
    kwargs   = _card_kwargs(config, as_of, matchday)

    ranked = over_under_stats(matches)
    create_analytics_card(
        df_ranked     = ranked,
        columns       = [
            ("AvgGoals",  "Avg Total Goals"),
            ("Over15Pct", "Over 1.5 %"),
            ("Over25Pct", "Over 2.5 %"),
        ],
        card_title    = "Over / Under Trends",
        subtitle      = "Average total goals (both teams) per game · Season to date",
        output_path   = os.path.join(out_dir, "over_under.png"),
        divider_label = "Low-Scoring Games",
        **kwargs,
    )
    print("  ✓ Over / Under Trends")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(leagues: list[str]):
    as_of = get_as_of_date()
    print(f"\n{'='*56}")
    print(f"  Analytics Card Generator — {as_of}")
    print(f"{'='*56}\n")

    for league_key in leagues:
        config = LEAGUE_CONFIG[league_key]
        print(f"[ {config['display_name']} ]")

        if not os.path.exists(config["data_path"]):
            print(f"  ✗ Data file not found: {config['data_path']}\n")
            continue

        try:
            matches = pd.read_csv(config["data_path"], encoding="utf-8-sig")
            current = matches[matches["Season"] == config["season"]]
            if current.empty:
                print(f"  ✗ No data found for season {config['season']}\n")
                continue

            matchday = get_current_matchday(current)
            print(f"  Loaded {len(current)} matches · Matchday {matchday}/{config['total_matchdays']}")

            generate_attacking_cards(league_key, config, current)
            generate_defensive_cards(league_key, config, current)
            generate_discipline_cards(league_key, config, current)
            generate_referee_cards(league_key, config, current)
            generate_home_away_cards(league_key, config, current)
            generate_comeback_cards(league_key, config, current)
            generate_form_cards(league_key, config, current)
            generate_over_under_cards(league_key, config, current)

        except Exception as e:
            import traceback
            print(f"  ✗ Error: {e}")
            traceback.print_exc()
            print()
            continue

        print()

    print("Done.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--league",
        choices=list(LEAGUE_CONFIG.keys()),
        default=None,
        help="Generate for a single league only (default: all leagues)",
    )
    args    = parser.parse_args()
    leagues = [args.league] if args.league else list(LEAGUE_CONFIG.keys())
    run(leagues)