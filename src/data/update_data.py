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


def download_football_data_csv(
    league: str,
    season: str,
    timeout: int = 30,
) -> Path:
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

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to download data from {url}. "
            f"Status code: {response.status_code}"
        )

    text = response.text.strip()

    if len(text) < 100:
        raise RuntimeError(
            f"Downloaded file from {url} looks too small. "
            "The season may not be available yet."
        )

    output_path.write_text(
        text,
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")

    return output_path


def update_league_data(
    league: str,
    season: str,
) -> Path:
    return download_football_data_csv(
        league=league,
        season=season,
    )


def update_current_league_data(
    league: str = "epl",
    season: str | None = None,
) -> Path:
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

    update_current_league_data(
        league=league,
        season=season,
    )