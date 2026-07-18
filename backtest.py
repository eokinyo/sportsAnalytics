from pathlib import Path
import pandas as pd

from src.backtest.backtest_season import (
    run_single_season_backtest,
)
from src.config.league_config import resolve_league, get_matches_per_team


BASE_DIR = Path(__file__).resolve().parent


# Backtest season range per league. Each season needs enough prior
# history for n_recent_seasons=5 below to produce stable
# team-strength estimates, and the most recent (in-progress) season
# should be excluded. 2020_2021 is excluded everywhere - COVID bubbles
# distort home-advantage and form calibration for every league.
SEASONS_BY_LEAGUE: dict[str, list[str]] = {
    "epl": [
        "2010_2011", "2011_2012", "2012_2013", "2013_2014",
        "2014_2015", "2015_2016", "2016_2017", "2017_2018",
        "2018_2019", "2019_2020",
        # 2020_2021 excluded: COVID
        "2021_2022", "2022_2023", "2023_2024",
    ],
    "laliga": [
        "2010_2011", "2011_2012", "2012_2013", "2013_2014",
        "2014_2015", "2015_2016", "2016_2017", "2017_2018",
        "2018_2019", "2019_2020",
        # 2020_2021 excluded: COVID
        "2021_2022", "2022_2023", "2023_2024",
    ],
    "bundesliga": [
        "2010_2011", "2011_2012", "2012_2013", "2013_2014",
        "2014_2015", "2015_2016", "2016_2017", "2017_2018",
        "2018_2019", "2019_2020",
        # 2020_2021 excluded: COVID
        "2021_2022", "2022_2023", "2023_2024",
    ],
    "ligue_1": [
        # 2010_2011 to 2022_2023: 20 teams, 38 matches/team.
        # get_backtest_matches_per_team() returns 38 for these seasons.
        "2010_2011", "2011_2012", "2012_2013", "2013_2014",
        "2014_2015", "2015_2016", "2016_2017", "2017_2018",
        "2018_2019",
        # 2019_2020 excluded: COVID - only 279/380 matches played.
        # 2020_2021 excluded: COVID bubbles.
        "2021_2022", "2022_2023",
        # 2023_2024 onwards: 18 teams, 34 matches/team.
        # get_backtest_matches_per_team() returns 34 for these.
        "2023_2024",
    ],
    "serie_a": [
        # All 20 teams / 38 matches from 2010_2011 onwards.
        "2010_2011", "2011_2012", "2012_2013", "2013_2014",
        "2014_2015", "2015_2016", "2016_2017", "2017_2018",
        "2018_2019", "2019_2020",
        # 2020_2021 excluded: COVID
        "2021_2022", "2022_2023", "2023_2024",
    ],
}


CHECKPOINTS = [
    ("September", "09-30"),
    ("December", "12-31"),
    ("March", "03-31"),
    ("May", "05-01"),
]


def get_backtest_matches_per_team(league: str, season: str) -> int:
    """
    Returns the correct total matches-per-team for a specific backtest
    season, handling leagues that changed team count over time.

    For most leagues this is just get_matches_per_team(league), but
    Ligue 1 had 20 teams (38 matches/team) from 2002_2003 to
    2022_2023, before dropping to 18 teams (34 matches/team) from
    2023_2024 onwards.
    """
    if league == "ligue_1":
        start_year = int(season.split("_")[0])
        return 38 if start_year <= 2022 else 34

    return get_matches_per_team(league)


def season_start_year(season: str) -> int:
    return int(season.split("_")[0])


def checkpoint_date_for_season(
    season: str,
    month_day: str,
) -> str:
    start_year = season_start_year(season)

    month = int(month_day.split("-")[0])

    if month >= 8:
        year = start_year
    else:
        year = start_year + 1

    return f"{year}-{month_day}"


def main(league: str | None = None):

    league = league or resolve_league()

    if league not in SEASONS_BY_LEAGUE:
        raise ValueError(
            f"No SEASONS_BY_LEAGUE entry for {league!r} yet. "
            f"Add one in backtest.py - check the league's available "
            f"seasons in its processed CSV first."
        )

    seasons = SEASONS_BY_LEAGUE[league]

    data_path = (
        BASE_DIR
        / "data"
        / "processed"
        / league
        / f"{league}_matches_clean.csv"
    )

    output_dir = (
        BASE_DIR
        / "outputs"
        / "backtests"
        / league
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    matches = pd.read_csv(data_path)

    print(f"Backtesting {league}: {seasons[0]} to {seasons[-1]} "
          f"({len(seasons)} seasons)")

    all_summaries = []

    for season in seasons:
        print("\n" + "=" * 70)
        print(f"Running backtests for {season}")
        print("=" * 70)

        for checkpoint_name, month_day in CHECKPOINTS:
            as_of_date = checkpoint_date_for_season(
                season=season,
                month_day=month_day,
            )

            print(f"\nCheckpoint: {checkpoint_name} ({as_of_date})")

            comparison, summary = run_single_season_backtest(
                matches=matches,
                season=season,
                as_of_date=as_of_date,
                n_recent_seasons=5,
                season_decay=0.50,
                total_matches_per_team=get_backtest_matches_per_team(league, season),
                promoted_weight_multiplier=0.60,
                live_elo_k_factor=25.0,
                live_elo_home_advantage=60.0,
                n_simulations=10000,
                seed=42,
            )

            comparison_file = (
                output_dir
                / f"{season}_backtest_{as_of_date}.csv"
            )

            comparison.to_csv(
                comparison_file,
                index=False,
            )

            summary_row = {
                "Season": season,
                "Checkpoint": checkpoint_name,
                "AsOfDate": as_of_date,
                **summary,
            }

            all_summaries.append(summary_row)

            print("Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")

            print(f"Saved: {comparison_file}")

    summary_df = pd.DataFrame(all_summaries)

    summary_file = (
        output_dir
        / f"backtest_summary_{seasons[0]}_to_{seasons[-1]}.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
    )

    print("\n" + "=" * 70)
    print("Combined Backtest Summary")
    print("=" * 70)
    print(summary_df)

    print("\nSaved combined summary:")
    print(summary_file)
    


if __name__ == "__main__":
    main()