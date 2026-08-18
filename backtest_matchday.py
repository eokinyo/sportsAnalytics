"""
backtest_matchday.py

Replays a single past matchday end to end: predict as of a date before
the fixtures, then score against what actually happened.

The point is to exercise the real pipeline - the same strength model,
the same fixture selection, the same archive, the same cards - rather
than a simulation of it. Predictions are made using only matches played
before PREDICT_ON, so the model has no sight of the results it is later
scored against.

Nothing here touches your live prediction archive. Backtest predictions
are written to data/backtests/predictions/ and cards to
outputs/backtests/, both separate from the season's real record.

The fixture window is explicit: only matches kicking off between
WINDOW_FROM and WINDOW_TO are predicted and scored. Without that bound,
a rolling "next few days" window drifts into the following round and
scores fixtures that were never part of the matchday.

    python backtest_matchday.py
    python backtest_matchday.py --league epl
    python backtest_matchday.py --predict-on 2026-04-16 \
        --window-from 2026-04-17 --window-to 2026-04-20 \
        --results-on 2026-04-21
    python backtest_matchday.py --cumulative
    python backtest_matchday.py --no-cards
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.live.live_forecast import prepare_live_remaining_predictions
from src.live.matchday import get_next_matchday_fixtures, matchday_label

from src.data.predictions_archive import append_predictions
from src.analytics.results import join_predictions_to_results

from src.visualization.card import CardGenerator

from src.config.league_config import (
    LEAGUES,
    get_league_display,
    get_matches_per_team,
)


BASE_DIR = Path(__file__).resolve().parent

# Kept apart from data/predictions/ so a backtest can never contaminate
# the season's real accuracy record.
BACKTEST_ARCHIVE_DIR = BASE_DIR / "data" / "backtests" / "predictions"
BACKTEST_OUTPUT_DIR = BASE_DIR / "outputs" / "backtests"

# Defaults: EPL matchday 33 weekend, 2025/26.
#   predict on Thursday, fixtures Friday-Monday, score on Tuesday.
DEFAULT_PREDICT_ON = "2026-04-16"
DEFAULT_WINDOW_FROM = "2026-04-17"
DEFAULT_WINDOW_TO = "2026-04-20"
DEFAULT_RESULTS_ON = "2026-04-21"
DEFAULT_SEASON = "2025_2026"

# Must match generate_cards.py so the backtest reflects the real model.
N_RECENT_SEASONS = 5
SEASON_DECAY = 0.50
PROMOTED_WEIGHT_MULTIPLIER = 0.60


def season_label(season: str) -> str:
    start, end = season.split("_")
    return f"{start}/{end[2:]}"


def load_matches(league: str) -> pd.DataFrame | None:
    path = (
        BASE_DIR / "data" / "processed" / league
        / f"{league}_matches_clean.csv"
    )

    if not path.exists():
        print(f"  x Data file not found: {path}")
        return None

    return pd.read_csv(path, encoding="utf-8-sig")


def predict_matchday(
    league: str,
    matches: pd.DataFrame,
    season: str,
    predict_on: str,
    window_from: str | None,
    window_to: str | None,
) -> pd.DataFrame | None:
    """
    Build predictions for the matchday as of predict_on, using only
    matches played before that date.

    When window_from/window_to are given, the matchday is exactly the
    fixtures kicking off in that range. Otherwise it falls back to
    get_next_matchday_fixtures, whose rolling window can spill into the
    next round.
    """
    played, remaining, _strength = prepare_live_remaining_predictions(
        matches=matches,
        season=season,
        as_of_date=predict_on,
        n_recent_seasons=N_RECENT_SEASONS,
        season_decay=SEASON_DECAY,
        total_matches_per_team=get_matches_per_team(league),
        promoted_weight_multiplier=PROMOTED_WEIGHT_MULTIPLIER,
    )

    if remaining.empty:
        print(f"  x No remaining fixtures as of {predict_on}")
        return None

    if window_from or window_to:
        fixtures = remaining.copy()
        fixtures["Date"] = pd.to_datetime(fixtures["Date"], errors="coerce")

        if window_from:
            fixtures = fixtures[fixtures["Date"] >= pd.to_datetime(window_from)]
        if window_to:
            fixtures = fixtures[fixtures["Date"] <= pd.to_datetime(window_to)]

        label = f"{window_from or 'start'} to {window_to or 'end'}"

    else:
        fixtures = get_next_matchday_fixtures(remaining)
        label = matchday_label(remaining, fixtures) if not fixtures.empty else ""

    if fixtures.empty:
        print("  x No fixtures in the matchday window")
        return None

    dupes = fixtures.duplicated(subset=["HomeTeam"], keep=False).sum()
    warn = "  (!) a team appears more than once" if dupes else ""

    print(f"  Predicting: {label}  ({len(fixtures)} fixtures, "
          f"{len(played)} matches played to date){warn}")

    return fixtures


def render_prediction_cards(
    league: str,
    fixtures: pd.DataFrame,
    season: str,
    predict_on: str,
) -> None:
    out_dir = BACKTEST_OUTPUT_DIR / league / predict_on / "predictions"

    gen = CardGenerator(
        output_dir=str(out_dir),
        logos_dir=str(BASE_DIR / "data" / "logos" / league),
    )

    for _, fixture in fixtures.iterrows():
        gen.create_match_detail_card(
            fixture=fixture,
            season=season_label(season),
            league=get_league_display(league),
        )

    print(f"  Prediction cards -> {out_dir}")


def render_result_cards(
    league: str,
    scored: pd.DataFrame,
    season: str,
    predict_on: str,
) -> None:
    out_dir = BACKTEST_OUTPUT_DIR / league / predict_on / "results"

    gen = CardGenerator(
        output_dir=str(out_dir),
        logos_dir=str(BASE_DIR / "data" / "logos" / league),
    )

    for _, row in scored.iterrows():
        result = row.to_dict()
        date_str = pd.to_datetime(result["Date"]).strftime("%Y-%m-%d")
        fname = (
            f"{date_str}__{result['HomeTeam'].replace(' ', '_')}"
            f"_vs_{result['AwayTeam'].replace(' ', '_')}.png"
        )
        gen.create_result_card(
            result=result,
            season=season_label(season),
            league=get_league_display(league),
            filename=fname,
        )

    print(f"  Result cards     -> {out_dir}")


def _summarise(scored: pd.DataFrame) -> dict:
    """Accuracy over a specific set of scored fixtures.

    accuracy_summary() reads the whole archive, so it can't be used once
    the set has been narrowed to a single matchday.
    """
    n = len(scored)
    return {
        "Fixtures":        n,
        "OutcomeCorrect":  int(scored["OutcomeCorrect"].sum()),
        "OutcomeAccuracy": round(scored["OutcomeCorrect"].mean() * 100, 1),
        "ScoreCorrect":    int(scored["ScoreCorrect"].sum()),
        "ScoreAccuracy":   round(scored["ScoreCorrect"].mean() * 100, 1),
        "AvgProbOfActual": round(scored["ProbOfActual"].mean() * 100, 1),
        "AvgBrierScore":   round(scored["BrierScore"].mean(), 3),
    }


def run_league(
    league: str,
    season: str,
    predict_on: str,
    window_from: str | None,
    window_to: str | None,
    results_on: str,
    make_cards: bool,
    cumulative: bool,
) -> dict | None:
    print(f"\n[ {get_league_display(league)} ]")

    matches = load_matches(league)
    if matches is None:
        return None

    if season not in set(matches["Season"].dropna().unique()):
        print(f"  x Season {season} not present in data")
        return None

    # --- Predict ---------------------------------------------------------
    try:
        fixtures = predict_matchday(
            league=league,
            matches=matches,
            season=season,
            predict_on=predict_on,
            window_from=window_from,
            window_to=window_to,
        )
    except Exception as exc:
        print(f"  x Prediction failed: {exc!r}")
        return None

    if fixtures is None:
        return None

    append_predictions(
        predictions=fixtures,
        league=league,
        season=season,
        predicted_on=predict_on,
        archive_dir=BACKTEST_ARCHIVE_DIR,
    )

    if make_cards:
        render_prediction_cards(league, fixtures, season, predict_on)

    # --- Score -----------------------------------------------------------
    # Only count matches played by results_on, so the backtest reflects
    # what you would have known on that day.
    as_known = matches.copy()
    as_known["Date"] = pd.to_datetime(
        as_known["Date"], format="mixed", dayfirst=False, errors="coerce"
    )
    as_known = as_known[as_known["Date"] <= pd.to_datetime(results_on)]

    scored = join_predictions_to_results(
        matches=as_known,
        league=league,
        season=season,
        archive_dir=BACKTEST_ARCHIVE_DIR,
    )

    if scored.empty:
        print(f"  x No fixtures scored - none played by {results_on}")
        return None

    # The archive accumulates across runs, so by default score only the
    # fixtures this run predicted. --cumulative scores everything in it.
    if not cumulative:
        this_run = fixtures.copy()
        this_run["Date"] = pd.to_datetime(this_run["Date"], errors="coerce")

        scored = scored.merge(
            this_run[["Date", "HomeTeam", "AwayTeam"]],
            on=["Date", "HomeTeam", "AwayTeam"],
            how="inner",
        )

        if scored.empty:
            print(f"  x None of this matchday's fixtures played by {results_on}")
            return None

    stats = _summarise(scored)

    scope = "archive total" if cumulative else "this matchday"
    print(f"  Scored {stats['Fixtures']} fixtures ({scope}): "
          f"{stats['OutcomeCorrect']} outcomes ({stats['OutcomeAccuracy']}%), "
          f"{stats['ScoreCorrect']} exact ({stats['ScoreAccuracy']}%), "
          f"Brier {stats['AvgBrierScore']}")

    if make_cards:
        render_result_cards(league, scored, season, predict_on)

    stats["League"] = league
    return stats


def print_overall(all_stats: list[dict]) -> None:
    if not all_stats:
        print("\nNothing scored.")
        return

    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)

    header = (
        f"{'League':<14}{'Fixtures':>9}{'Outcome':>10}{'Exact':>9}"
        f"{'AvgProb':>10}{'Brier':>9}"
    )
    print(header)
    print("-" * len(header))

    for s in all_stats:
        print(
            f"{s['League']:<14}{s['Fixtures']:>9}"
            f"{s['OutcomeAccuracy']:>9.1f}%{s['ScoreAccuracy']:>8.1f}%"
            f"{s['AvgProbOfActual']:>9.1f}%{s['AvgBrierScore']:>9.3f}"
        )

    total = sum(s["Fixtures"] for s in all_stats)
    correct = sum(s["OutcomeCorrect"] for s in all_stats)
    exact = sum(s["ScoreCorrect"] for s in all_stats)
    brier = sum(s["AvgBrierScore"] * s["Fixtures"] for s in all_stats) / total

    print("-" * len(header))
    print(
        f"{'ALL':<14}{total:>9}"
        f"{correct / total * 100:>9.1f}%{exact / total * 100:>8.1f}%"
        f"{'':>10}{brier:>9.3f}"
    )

    print(
        "\nOutcome = H/D/A called correctly. Exact = scoreline called."
        "\nBrier scores the full probability distribution (lower is better;"
        "\nalways predicting the base rate scores about 0.66)."
    )


def main(
    leagues: list[str] | None = None,
    season: str = DEFAULT_SEASON,
    predict_on: str = DEFAULT_PREDICT_ON,
    window_from: str | None = DEFAULT_WINDOW_FROM,
    window_to: str | None = DEFAULT_WINDOW_TO,
    results_on: str = DEFAULT_RESULTS_ON,
    make_cards: bool = True,
    cumulative: bool = False,
) -> None:
    leagues = leagues or list(LEAGUES)

    window = (
        f"{window_from or 'start'} to {window_to or 'end'}"
        if (window_from or window_to)
        else "next matchday (rolling window)"
    )

    print("=" * 72)
    print("  Matchday backtest")
    print("=" * 72)
    print(f"  Season       : {season}")
    print(f"  Predicted on : {predict_on}")
    print(f"  Fixtures     : {window}")
    print(f"  Scored on    : {results_on}")
    print(f"  Scope        : {'whole archive' if cumulative else 'this matchday only'}")
    print(f"  Archive      : {BACKTEST_ARCHIVE_DIR}")
    print(f"  Cards        : {'yes' if make_cards else 'no'}")

    all_stats = []

    for league in leagues:
        try:
            stats = run_league(
                league=league,
                season=season,
                predict_on=predict_on,
                window_from=window_from,
                window_to=window_to,
                results_on=results_on,
                make_cards=make_cards,
                cumulative=cumulative,
            )
            if stats:
                all_stats.append(stats)
        except Exception as exc:
            import traceback
            print(f"  x {league} failed: {exc!r}")
            traceback.print_exc()

    print_overall(all_stats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replay a past matchday: predict, then score."
    )
    parser.add_argument("--league", choices=list(LEAGUES), default=None)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--predict-on", default=DEFAULT_PREDICT_ON,
                        help="Date the prediction is made (YYYY-MM-DD)")
    parser.add_argument("--window-from", default=DEFAULT_WINDOW_FROM,
                        help="First kickoff date in the matchday (YYYY-MM-DD)")
    parser.add_argument("--window-to", default=DEFAULT_WINDOW_TO,
                        help="Last kickoff date in the matchday (YYYY-MM-DD)")
    parser.add_argument("--rolling-window", action="store_true",
                        help="Ignore the explicit window and use "
                             "get_next_matchday_fixtures instead")
    parser.add_argument("--results-on", default=DEFAULT_RESULTS_ON,
                        help="Date results are scored as of (YYYY-MM-DD)")
    parser.add_argument("--cumulative", action="store_true",
                        help="Score every fixture in the backtest archive, "
                             "not just this matchday")
    parser.add_argument("--no-cards", action="store_true",
                        help="Numbers only, skip card rendering")
    args = parser.parse_args()

    main(
        leagues=[args.league] if args.league else None,
        season=args.season,
        predict_on=args.predict_on,
        window_from=None if args.rolling_window else args.window_from,
        window_to=None if args.rolling_window else args.window_to,
        results_on=args.results_on,
        make_cards=not args.no_cards,
        cumulative=args.cumulative,
    )
