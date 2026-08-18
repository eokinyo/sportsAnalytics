# sportsAnalytics — Command Reference

Run everything from the project root:

```powershell
cd "C:\Users\ellyo\OneDrive\Work\X\Automation\sportsAnalytics"
```

League codes: `epl`, `laliga`, `bundesliga`, `ligue_1`, `serie_a`

---

## The one command

```powershell
python run_all_leagues.py
```

Runs four steps per league, in dependency order:

| Step | What it does | Output |
|---|---|---|
| `forecast` | Update data, preprocess, run live forecast | `outputs/tables/{league}/` |
| `results` | Score archived predictions against results now in | `outputs/results/{league}/` |
| `cards` | Season forecast + matchday cards, archive predictions | `outputs/cards/{league}/{league}_{DD-MM-YYYY}/` |
| `analytics` | 17 stat cards across eight categories | `outputs/analytics/{league}/{category}/` |

`results` runs before `cards` so the freshly-updated data scores last
matchday before the next matchday's predictions are archived.

Each step is isolated. One failure doesn't stop the others, and the
end-of-run summary shows exactly what passed:

```
League      forecast    results     cards       analytics
epl         OK          OK          OK          OK
laliga      OK          OK          FAILED      OK
```

Full output also goes to `logs/run_all_leagues_<timestamp>.log`.

### Narrowing it down

```powershell
python run_all_leagues.py --league epl
python run_all_leagues.py --steps analytics
python run_all_leagues.py --steps forecast cards
python run_all_leagues.py --skip analytics
python run_all_leagues.py --league epl --steps results
```

Step order is enforced regardless of how you type it, so
`--steps cards forecast` still runs forecast first.

---

## On-demand, outside the main run

**Referee report** — before a fixture you plan to post about:

```powershell
python referee_report.py --referee "A Taylor" --home "Arsenal" --away "Chelsea"
```

Partial names work (`"Taylor"`); an unrecognised name lists what's available.
Add `--league laliga` for other leagues.
Output → `outputs/analytics/{league}/referee/{Referee}__{Home}_vs_{Away}.png`

**Running accuracy record** — no cards, just the numbers:

```powershell
python generate_results.py --league epl --summary
```

**Rebuild one result card**:

```powershell
python generate_results.py --league epl --home Arsenal --away Chelsea --overwrite
```

---

## Season start — one-off

Pull the new season's data once football-data.co.uk publishes it
(404 means not live yet — retry in a few days):

```powershell
python src/data/update_data.py epl 2026_2027
python src/data/update_data.py laliga 2026_2027
python src/data/update_data.py bundesliga 2026_2027
python src/data/update_data.py ligue_1 2026_2027
python src/data/update_data.py serie_a 2026_2027
```

Then rebuild processed data:

```powershell
python src/data/preprocess.py epl
python src/data/preprocess.py laliga
python src/data/preprocess.py bundesliga
python src/data/preprocess.py ligue_1
python src/data/preprocess.py serie_a
```

Logos:

```powershell
python update_logos_2026_27.py --dry-run
python update_logos_2026_27.py
```

After that, `run_all_leagues.py` handles updating and preprocessing itself.

---

## Testing the model on a past matchday

Replays a matchday end to end: predicts as of a date before the fixtures
using only data available then, and scores against what happened.

```powershell
python backtest_matchday.py
python backtest_matchday.py --league epl
python backtest_matchday.py --no-cards
python backtest_matchday.py --predict-on 2026-02-05 --results-on 2026-02-10
```

Defaults to the 2025/26 matchday-33 weekend (predict 16 Apr, score 21 Apr).

Writes to `data/backtests/predictions/` and `outputs/backtests/`, both
separate from the live archive — a backtest can never contaminate the
season's real accuracy record.

Reports outcome accuracy, exact-score rate and Brier score per league,
with a combined row across all five.

---

## Occasional

**Backtesting** — slow. Run when model logic changes, not weekly.

```powershell
python run_all_backtests.py
```

**Historical snapshot** — to see the season as it looked on a past date,
set `AS_OF_DATE_OVERRIDE = "2025-12-31"` in **both** `main.py` and
`generate_cards.py`, run, then set both back to `None`.

Leaving it set will date every card *and every archived prediction* to
that day, which corrupts the accuracy record.

---

## Weekly rhythm

**Monday, after the weekend** — everything:

```powershell
python run_all_leagues.py
```

**Midweek** — refresh stat cards without rerunning forecasts:

```powershell
python run_all_leagues.py --steps analytics
```

**Before the fixtures** — new predictions, plus a referee angle:

```powershell
python run_all_leagues.py --steps forecast cards
python referee_report.py --referee "<name>" --home "<home>" --away "<away>"
```

---

## If something looks wrong

**"No data found for season"** — the processed file has no rows for the
current season. Run `python src/data/update_data.py {league}` then
`python src/data/preprocess.py {league}`.

**Result cards generate nothing** — either no predictions are archived yet
(`cards` must run before `results` can score anything), or the results
aren't in the processed data yet. Check `data/predictions/{league}/`.

**Referee cards skipped** — that league's data has no `Referee` column.
Currently EPL only. This is expected, not a failure.

**Cards dated to last December** — `AS_OF_DATE_OVERRIDE` is still set.
Both `main.py` and `generate_cards.py` should have `None`.
