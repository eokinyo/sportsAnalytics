# Sports Analytics

Automated football analytics pipeline covering the English Premier League, La Liga, Bundesliga, Ligue 1, and Serie A. It ingests historical and live match data, generates predictive models, backtests them across multiple seasons, and produces visual analytics cards and referee reports.

## What it does

- **Prediction models** – Elo ratings, Poisson-based scoring models, and pseudo-xG estimates combine into match predictions
- **Season simulation** – Monte Carlo simulation projects final league tables and title/relegation probabilities
- **Backtesting** – validates model performance against 2010–2024 historical seasons, tracked per matchday cutoff
- **Live forecasting** – updates predictions as a season progresses
- **Analytics cards** – auto-generated visual summaries (attacking output, defensive record, form, home/away splits, discipline, over/under trends, comeback stats) per league
- **Referee reports** – analytics on referee tendencies

## Project structure

```
src/
├── analytics/       # Descriptive stats and card generation
├── backtest/        # Historical validation harness
├── config/          # League and season configuration
├── data/             # Data loading and preprocessing
├── evaluation/       # Model performance metrics and diagnostics
├── live/              # In-season forecast updates
├── models/           # (private — see note below)
├── simulation/        # (private — see note below)
├── utils/
└── visualization/     # Card and chart rendering
```

## Note on the prediction engine

The core prediction models (`src/models/`) and season simulation logic (`src/simulation/`), along with model calibration parameters, are kept private and are not included in this repository. This repo shows the data pipeline, backtesting harness, live forecasting orchestration, and visualization layer around them.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

See `run_all_leagues.py` and `run_all_backtests.py` for batch runs across all leagues.