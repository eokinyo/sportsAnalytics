from __future__ import annotations

from pathlib import Path
from datetime import datetime
import requests


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


FOOTBALL_DATA_LEAGUE_CODES = {
    "epl": "E0",
    "laliga": "SP1",
    "bundesliga": "D1",
    "ligue_1": "F1",
    "serie_a": "I1",
}


# Status codes that mean "this season's file isn't on the server yet",
# rather than something being broken.
#
# 404 is the obvious one. 300 (Multiple Choices) is what football-data.co.uk
# actually returns for a missing CSV - its Apache content negotiation offers
# alternatives instead of a clean not-found. Both mean the same thing here:
# the season hasn't started, or no results have been published for it yet.
NOT_PUBLISHED_STATUS_CODES = {300, 404}

# A published-but-empty file (headers only, or a stub) is also treated as
# not yet available.
MIN_USABLE_BYTES = 100


def season_to_football_data_code(season: str) -> str:
    start_year, end_year = season.split("_")
    return start_year[-2:] + end_year[-2:]


def infer_season_from_today() -> str:
    today = datetime.today()

    if today.month >= 8:
        return f"{today.year}_{today.year + 1}"

    return f"{today.year - 1}_{today.year}"


def football_data_url(league: str, season: str) -> str:
    league = league.lower()

    if league not in FOOTBALL_DATA_LEAGUE_CODES:
        raise ValueError(
            f"Unsupported league: {league}. "
            f"Supported leagues: {list(FOOTBALL_DATA_LEAGUE_CODES)}"
        )

    season_code = season_to_football_data_code(season)
    league_code = FOOTBALL_DATA_LEAGUE_CODES[league]

    return (
        "https://www.football-data.co.uk/mmz4281/"
        f"{season_code}/{league_code}.csv"
    )


def raw_output_path(league: str, season: str) -> Path:
    league = league.lower()

    league_dir = RAW_DIR / league
    league_dir.mkdir(parents=True, exist_ok=True)

    return league_dir / f"{league}_{season}.csv"


def _print_not_published(league: str, season: str, reason: str) -> None:
    print(f"Not available yet: {reason}")
    print(
        f"football-data.co.uk publishes a season's CSV once matches have "
        f"been played, so {league} {season} should appear shortly after the "
        f"first matchday. Continuing with existing data."
    )


def download_football_data_csv(
    league: str,
    season: str,
    timeout: int = 30,
) -> Path | None:
    """
    Download one league-season CSV from football-data.co.uk.

    Returns the saved path on success, or None if the season isn't
    published yet (an expected state before a season starts, not an error).
    Genuine failures - network problems, server errors, blocked requests -
    still raise.
    """
    url = football_data_url(
        league=league,
        season=season,
    )

    output_path = raw_output_path(
        league=league,
        season=season,
    )

    print("\nUpdating raw data")
    print("-" * 40)
    print(f"League: {league}")
    print(f"Season: {season}")
    print(f"URL: {url}")

    response = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "sportsAnalytics/1.0 "
                "(football forecasting project)"
            )
        },
    )

    if response.status_code in NOT_PUBLISHED_STATUS_CODES:
        _print_not_published(
            league=league,
            season=season,
            reason=f"server returned {response.status_code} for this season",
        )
        return None

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download data from {url}. "
            f"Status code: {response.status_code}"
        )

    text = response.text.strip()

    if len(text) < MIN_USABLE_BYTES:
        _print_not_published(
            league=league,
            season=season,
            reason="the file exists but is empty",
        )
        return None

    output_path.write_text(
        text,
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")

    return output_path


def update_league_data(
    league: str,
    season: str,
) -> Path | None:
    return download_football_data_csv(
        league=league,
        season=season,
    )


def update_current_league_data(
    league: str = "epl",
    season: str | None = None,
) -> Path | None:
    if season is None:
        season = infer_season_from_today()

    return update_league_data(
        league=league,
        season=season,
    )


if __name__ == "__main__":
    import sys

    league  = sys.argv[1] if len(sys.argv) > 1 else "epl"
    season  = sys.argv[2] if len(sys.argv) > 2 else None

    saved = update_current_league_data(
        league=league,
        season=season,
    )

    # Exit 1 when there was nothing to download, so a scheduled task or
    # shell loop can tell "updated" from "not published yet" without
    # parsing output. Not an error condition - just a different outcome.
    sys.exit(0 if saved else 1)
