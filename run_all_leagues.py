"""
run_all_leagues.py

Runs the full pipeline for every league configured in
src/config/league_config.py (LEAGUES), one league at a time.

Four steps per league, in dependency order:

  1. forecast   - update raw data, preprocess, run the live forecast,
                  save tables to outputs/tables/{league}/
  2. results    - score archived predictions against results that have
                  arrived, writing cards to outputs/results/{league}/
  3. cards      - season forecast + matchday cards, and archive this
                  matchday's predictions to data/predictions/{league}/
  4. analytics  - 17 stat cards to outputs/analytics/{league}/

Results runs before cards so the freshly-updated data is used to score
last matchday before the next matchday's predictions are archived.

Designed for unattended/overnight runs:
  - Each step is wrapped in its own try/except, so a failure in one
    step doesn't stop the others, and a failure in one league doesn't
    stop the rest.
  - All output is written to logs/run_all_leagues_<timestamp>.log
    (as well as the console, if one is attached).
  - A per-step pass/fail summary is printed at the end.

    python run_all_leagues.py
    python run_all_leagues.py --league epl
    python run_all_leagues.py --steps forecast cards
    python run_all_leagues.py --skip analytics
"""

import argparse
import sys
import time
import traceback
from pathlib import Path

import main as main_module
import generate_cards
import generate_analytics
import generate_results
from src.config.league_config import LEAGUES


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

# Order matters - see module docstring.
STEPS = {
    "forecast":  lambda league: main_module.main(league=league),
    "results":   lambda league: generate_results.run(league),
    "cards":     lambda league: generate_cards.main(league=league),
    "analytics": lambda league: generate_analytics.run_league(league),
}

STEP_ORDER = ["forecast", "results", "cards", "analytics"]


class Tee:
    """Writes to multiple streams at once (e.g. console + log file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            try:
                stream.write(data)
                stream.flush()
            except Exception:
                pass

    def flush(self):
        for stream in self.streams:
            try:
                stream.flush()
            except Exception:
                pass


def run_league(league: str, steps: list[str]) -> dict:
    """Run the requested steps for one league. Returns per-step status."""
    status = {}

    for step in steps:
        print("\n" + "-" * 70)
        print(f"{league} :: {step}")
        print("-" * 70)

        try:
            STEPS[step](league)
            status[step] = "OK"

        except Exception as exc:
            print(f"\n*** {league} :: {step} FAILED: {exc!r} ***")
            traceback.print_exc()
            status[step] = "FAILED"

    return status


def print_summary(results: dict, steps: list[str]) -> None:
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    col_w = max([len("League")] + [len(lg) for lg in results]) + 2

    header = "League".ljust(col_w) + "".join(s.ljust(12) for s in steps)
    print(header)
    print("-" * len(header))

    for league, status in results.items():
        row = league.ljust(col_w)
        for step in steps:
            row += status.get(step, "-").ljust(12)
        print(row)

    failures = [
        f"{lg}/{step}"
        for lg, status in results.items()
        for step in steps
        if status.get(step) == "FAILED"
    ]

    if failures:
        print(f"\n{len(failures)} failure(s): {', '.join(failures)}")
    else:
        print("\nAll steps completed successfully.")


def main(leagues: list[str] | None = None, steps: list[str] | None = None):
    leagues = leagues or list(LEAGUES)
    steps = steps or list(STEP_ORDER)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"run_all_leagues_{timestamp}.log"

    log_file = open(log_path, "w", encoding="utf-8")

    real_stdout = sys.__stdout__
    real_stderr = sys.__stderr__

    sys.stdout = Tee(real_stdout, log_file)
    sys.stderr = Tee(real_stderr, log_file)

    try:
        print(f"run_all_leagues started: {timestamp}")
        print(f"Log file: {log_path}")
        print(f"Leagues: {leagues}")
        print(f"Steps:   {steps}")

        results = {}

        for league in leagues:
            print("\n" + "=" * 70)
            print(f"League: {league}")
            print("=" * 70)

            results[league] = run_league(league, steps)

        print_summary(results, steps)

        end_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        print(f"\nrun_all_leagues finished: {end_timestamp}")

    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr
        log_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the full pipeline across all leagues."
    )
    parser.add_argument(
        "--league",
        choices=list(LEAGUES),
        default=None,
        help="Run a single league (default: all).",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=STEP_ORDER,
        default=None,
        help="Run only these steps (default: all, in dependency order).",
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=STEP_ORDER,
        default=None,
        help="Run everything except these steps.",
    )
    args = parser.parse_args()

    selected = args.steps or list(STEP_ORDER)

    if args.skip:
        selected = [s for s in selected if s not in args.skip]

    # Keep dependency order regardless of the order given on the command line
    selected = [s for s in STEP_ORDER if s in selected]

    if not selected:
        parser.error("No steps left to run.")

    main(
        leagues=[args.league] if args.league else None,
        steps=selected,
    )
