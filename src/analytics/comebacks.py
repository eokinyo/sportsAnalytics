from __future__ import annotations

import pandas as pd


def _team_comeback_stats(matches: pd.DataFrame) -> pd.DataFrame:
    completed = matches.dropna(subset=["HTHG", "HTAG", "FTHG", "FTAG"]).copy()
    records   = []
    teams     = sorted(set(completed["HomeTeam"]) | set(completed["AwayTeam"]))

    for team in teams:
        home = completed[completed["HomeTeam"] == team]
        away = completed[completed["AwayTeam"] == team]

        # Losing at HT
        losing_ht_home = home[home["HTHG"] < home["HTAG"]]
        losing_ht_away = away[away["HTAG"] < away["HTHG"]]
        losing_ht      = len(losing_ht_home) + len(losing_ht_away)

        # Comeback wins (losing at HT, won at FT)
        comeback_home = losing_ht_home[losing_ht_home["FTHG"] > losing_ht_home["FTAG"]]
        comeback_away = losing_ht_away[losing_ht_away["FTAG"] > losing_ht_away["FTHG"]]
        comebacks     = len(comeback_home) + len(comeback_away)

        # Winning at HT
        winning_ht_home = home[home["HTHG"] > home["HTAG"]]
        winning_ht_away = away[away["HTAG"] > away["HTHG"]]
        winning_ht      = len(winning_ht_home) + len(winning_ht_away)

        # Blown leads (winning at HT, lost at FT)
        blown_home  = winning_ht_home[winning_ht_home["FTHG"] < winning_ht_home["FTAG"]]
        blown_away  = winning_ht_away[winning_ht_away["FTAG"] < winning_ht_away["FTHG"]]
        blown_leads = len(blown_home) + len(blown_away)

        comeback_pct   = round(comebacks   / losing_ht  * 100, 1) if losing_ht  > 0 else 0.0
        blown_lead_pct = round(blown_leads / winning_ht * 100, 1) if winning_ht > 0 else 0.0

        records.append({
            "Team":          team,
            "Played":        len(home) + len(away),
            "LosingAtHT":    losing_ht,
            "Comebacks":     comebacks,
            "ComebackPct":   comeback_pct,
            "WinningAtHT":   winning_ht,
            "BlownLeads":    blown_leads,
            "BlownLeadPct":  blown_lead_pct,
        })

    return pd.DataFrame(records)


def comeback_kings(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by comeback wins descending — most resilient teams first."""
    df = _team_comeback_stats(matches)
    return df.sort_values(
        ["Comebacks", "ComebackPct"], ascending=[False, False]
    ).reset_index(drop=True)


def bottle_jobs(matches: pd.DataFrame) -> pd.DataFrame:
    """Ranked by blown leads descending — most leads thrown away first."""
    df = _team_comeback_stats(matches)
    return df.sort_values(
        ["BlownLeads", "BlownLeadPct"], ascending=[False, False]
    ).reset_index(drop=True)