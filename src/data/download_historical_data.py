from pathlib import Path
import requests
import time


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"

LEAGUES = {
    "epl": {
        "code": "E0",
        "folder": RAW_DIR / "epl",
        "name": "English Premier League",
    },
    "championship": {
        "code": "E1",
        "folder": RAW_DIR / "championship",
        "name": "English Championship",
    },
    "laliga": {
        "code": "SP1",
        "folder": RAW_DIR / "laliga",
        "name": "Spanish La Liga",
    },
    "bundesliga": {
        "code": "D1",
        "folder": RAW_DIR / "bundesliga",
        "name": "German Bundesliga",
    },
    "serie_a": {
        "code": "I1",
        "folder": RAW_DIR / "serie_a",
        "name": "Italian Serie A",
    },
    "ligue_1": {
        "code": "F1",
        "folder": RAW_DIR / "ligue_1",
        "name": "French Ligue 1",
    },
}


def season_code(start_year: int) -> str:
    """
    Converts 2000 into '0001', 2024 into '2425', etc.
    """
    return f"{str(start_year)[-2:]}{str(start_year + 1)[-2:]}"


def download_season(league_key: str, start_year: int) -> None:
    league = LEAGUES[league_key]
    code = league["code"]
    folder = league["folder"]
    folder.mkdir(parents=True, exist_ok=True)

    s_code = season_code(start_year)
    url = f"https://www.football-data.co.uk/mmz4281/{s_code}/{code}.csv"

    filename = f"{league_key}_{start_year}_{start_year + 1}.csv"
    output_path = folder / filename

    print(f"Downloading {league['name']} {start_year}/{start_year + 1}...")

    try:
        response = requests.get(url, timeout=20)

        if response.status_code == 200 and response.text.strip():
            output_path.write_text(response.text, encoding="utf-8")
            print(f"Saved: {output_path}")
        else:
            print(f"Skipped: no data found for {league['name']} {start_year}/{start_year + 1}")

    except requests.RequestException as e:
        print(f"Failed: {league['name']} {start_year}/{start_year + 1}")
        print(f"Reason: {e}")


def download_all(
    leagues=None,
    start_year: int = 2000,
    end_year: int = 2025,
    pause_seconds: float = 0.5,
) -> None:
    """
    Downloads historical data from start_year/start_year+1
    up to end_year/end_year+1.

    Example:
    start_year=2000, end_year=2025 downloads:
    2000/01 through 2025/26.
    """
    if leagues is None:
        leagues = list(LEAGUES.keys())

    for league_key in leagues:
        if league_key not in LEAGUES:
            print(f"Unknown league skipped: {league_key}")
            continue

        for year in range(start_year, end_year + 1):
            download_season(league_key, year)
            time.sleep(pause_seconds)


if __name__ == "__main__":
    download_all(
        leagues=["epl", "championship", "laliga", "bundesliga", "serie_a", "ligue_1"],
        start_year=2000,
        end_year=2025,
    )