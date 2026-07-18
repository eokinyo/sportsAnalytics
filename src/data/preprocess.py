from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


CORE_COLUMNS = [
    "Div",
    "Date",
    "Time",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "HTHG",
    "HTAG",
    "HTR",
    "HS",
    "AS",
    "HST",
    "AST",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
    "HF",
    "AF",
    "Referee",
]


NUMERIC_COLUMNS = [
    "FTHG",
    "FTAG",
    "HTHG",
    "HTAG",
    "HS",
    "AS",
    "HST",
    "AST",
    "HC",
    "AC",
    "HY",
    "AY",
    "HR",
    "AR",
    "HF",
    "AF",
]


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = (
        df.columns
        .str.replace("ï»¿", "", regex=False)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    return df


def parse_dates_cleanly(date_series: pd.Series) -> pd.Series:
    dates = date_series.astype(str).str.strip()

    parsed = pd.to_datetime(dates, format="%d/%m/%y", errors="coerce")

    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            dates.loc[missing], format="%d/%m/%Y", errors="coerce"
        )

    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            dates.loc[missing], format="%Y-%m-%d", errors="coerce"
        )

    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            dates.loc[missing], dayfirst=True, errors="coerce"
        )

    return parsed


def load_raw_file(path: Path, league: str, season: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        usecols=lambda col: (
            col.strip()
            .replace("ï»¿", "")
            .replace("\ufeff", "")
            in CORE_COLUMNS
        ),
        engine="python",
    )

    df = clean_column_names(df)
    df["League"] = league
    df["Season"] = season
    df["Date"]   = parse_dates_cleanly(df["Date"])

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam"])

    return df


def preprocess_league(league: str) -> pd.DataFrame:
    league_dir = RAW_DIR / league
    files      = sorted(league_dir.glob("*.csv"))

    all_seasons = []

    for path in files:
        season = path.stem.replace(f"{league}_", "")
        print(f"Processing {league}: {season}")
        season_df = load_raw_file(path, league=league, season=season)
        all_seasons.append(season_df)

    if not all_seasons:
        raise FileNotFoundError(f"No CSV files found in {league_dir}")

    df = pd.concat(all_seasons, ignore_index=True)

    df = df.drop_duplicates(
        subset=["League", "Season", "Date", "HomeTeam", "AwayTeam"],
        keep="last",
    )

    df = df.sort_values(["Date", "HomeTeam", "AwayTeam"]).reset_index(drop=True)

    league_output_dir = PROCESSED_DIR / league
    league_output_dir.mkdir(parents=True, exist_ok=True)

    output_path = league_output_dir / f"{league}_matches_clean.csv"
    df.to_csv(output_path, index=False)

    print(f"Saved cleaned data to: {output_path}")
    print(f"Rows: {len(df)}")
    print()
    print("Summary")
    print("-" * 40)
    print(f"Total rows: {len(df):,}")
    print(df.groupby("Season").size().sort_index())

    return df


if __name__ == "__main__":
    import sys
    league = sys.argv[1] if len(sys.argv) > 1 else "epl"
    preprocess_league(league)