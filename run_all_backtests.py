"""
run_all_backtests.py

Runs the backtest pipeline for every league in SEASONS_BY_LEAGUE
(defined in backtest.py), one league at a time.

Designed for unattended/overnight runs:
  - Each league is wrapped in its own try/except, so one league
    failing doesn't stop the rest.
  - All output is written to logs/run_all_backtests_<timestamp>.log
    (as well as the console, if one is attached).
  - A pass/fail summary is printed at the end.

    python run_all_backtests.py
"""

import sys
import time
import traceback
from pathlib import Path

import backtest as backtest_module
from backtest import SEASONS_BY_LEAGUE


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"


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


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"run_all_backtests_{timestamp}.log"

    log_file = open(log_path, "w", encoding="utf-8")

    real_stdout = sys.__stdout__
    real_stderr = sys.__stderr__

    sys.stdout = Tee(real_stdout, log_file)
    sys.stderr = Tee(real_stderr, log_file)

    try:
        print(f"run_all_backtests started: {timestamp}")
        print(f"Log file: {log_path}")
        print(f"Leagues: {list(SEASONS_BY_LEAGUE)}")

        results = {}

        for league in SEASONS_BY_LEAGUE:
            print("\n" + "=" * 70)
            print(f"League: {league} "
                  f"({len(SEASONS_BY_LEAGUE[league])} seasons, "
                  f"{len(SEASONS_BY_LEAGUE[league]) * 4} checkpoints)")
            print("=" * 70)

            try:
                backtest_module.main(league=league)
                results[league] = "OK"

            except Exception as exc:
                print(f"\n*** {league} FAILED: {exc!r} ***")
                traceback.print_exc()
                results[league] = f"FAILED: {exc!r}"

        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)

        for league, status in results.items():
            print(f"{league}: {status}")

        end_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        print(f"\nrun_all_backtests finished: {end_timestamp}")

    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr
        log_file.close()


if __name__ == "__main__":
    main()