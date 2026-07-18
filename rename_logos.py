"""
update_logos_2026_27.py
=======================
Renames all logo files across five leagues to match the exact team name
strings used by football-data.co.uk CSVs. This is what the card generator
does an apostrophe-insensitive lookup against.

Run from the project root:
    python update_logos_2026_27.py

Safe to re-run: skips renames where the target already exists (no overwrite).
Prints a summary of what was done and what logos are still missing for 2026/27.
"""

from pathlib import Path

LOGOS_ROOT = Path("data/logos")

# ---------------------------------------------------------------------------
# Mapping: {league_folder: {current_filename_stem: target_stem}}
#
# Target stems are the EXACT strings football-data.co.uk uses in HomeTeam /
# AwayTeam columns (verified against historical CSVs and Wikipedia team pages).
#
# Apostrophe variants are handled at lookup time by card.py, so we use the
# canonical football-data string as the filename (e.g. "M'gladbach").
# ---------------------------------------------------------------------------

RENAMES: dict[str, dict[str, str]] = {

    # ------------------------------------------------------------------
    # EPL  (E0)
    # Only the three new 2026/27 logos need renaming; the rest are already
    # correctly named from previous seasons.
    # ------------------------------------------------------------------
    "epl": {
        "coventry-city-footballlogos-org": "Coventry",
        "hull-city-footballlogos-org":     "Hull",
        "ipswich-town-footballlogos-org":  "Ipswich",
    },

    # ------------------------------------------------------------------
    # BUNDESLIGA  (D1)
    # All logos use download-style names; rename every one.
    # football-data.co.uk strings verified against D1 CSV history.
    # ------------------------------------------------------------------
    "bundesliga": {
        "1-fc-koln-footballlogos-org":             "FC Koln",
        "bayer-leverkusen-footballlogos-org":       "Bayer Leverkusen",
        "bayern-munich-footballlogos-org":          "Bayern Munich",
        "borussia-dortmund-footballlogos-org":      "Dortmund",
        "borussia-monchengladbach-footballlogos-org": "M'gladbach",
        "eintracht-frankfurt-footballlogos-org":    "Ein Frankfurt",
        "fc-augsburg-footballlogos-org":            "Augsburg",
        "hamburger-sv-footballlogos-org":           "Hamburg",
        "mainz-05-footballlogos-org":               "Mainz",
        "rb-leipzig-footballlogos-org":             "RB Leipzig",
        "sc-freiburg-footballlogos-org":            "Freiburg",
        "sc-paderborn-07-footballlogos-org":        "Paderborn",
        "schalke-04-footballlogos-org":             "Schalke 04",
        "sv-elversberg-footballlogos-org":          "Elversberg",
        "tsg-hoffenheim-footballlogos-org":         "Hoffenheim",
        "union-berlin-footballlogos-org":           "Union Berlin",
        "vfb-stuttgart-footballlogos-org":          "Stuttgart",
        "werder-bremen-footballlogos-org":          "Werder Bremen",
    },

    # ------------------------------------------------------------------
    # LA LIGA  (SP1)
    # Oviedo, Girona, Mallorca are relegated; keep their files (harmless).
    # Racing Santander, Deportivo La Coruna, + playoff winner need adding.
    # football-data.co.uk strings verified against SP1 CSV history.
    # ------------------------------------------------------------------
    "laliga": {
        "athletic-club-bilbao-footballlogos-org":  "Ath Bilbao",
        "atletico-madrid-footballlogos-org":        "Ath Madrid",
        "celta-vigo-footballlogos-org":             "Celta",
        "deportivo-alaves-footballlogos-org":       "Alaves",
        "elche-cf-footballlogos-org":               "Elche",
        "fc-barcelona-footylogos":                  "Barcelona",
        "getafe-cf-footballlogos-org":              "Getafe",
        "girona-fc-footballlogos-org":              "Girona",
        "levante-ud-footballlogos-org":             "Levante",
        "osasuna-footballlogos-org":                "Osasuna",
        "rayo-vallecano-footballlogos-org":         "Vallecano",
        "rcd-espanyol-footballlogos-org":           "Espanol",
        "rcd-mallorca-footballlogos-org":           "Mallorca",
        "real-betis-footballlogos-org":             "Betis",
        "real-madrid-footballlogos-org":            "Real Madrid",
        "real-oviedo-footballlogos-org":            "Oviedo",
        "real-sociedad-footballlogos-org":          "Sociedad",
        "sevilla-fc-footballlogos-org":             "Sevilla",
        "valencia-cf-footballlogos-org":            "Valencia",
        "villarreal-cf-footballlogos-org":          "Villarreal",
    },

    # ------------------------------------------------------------------
    # LIGUE 1  (F1)
    # Nantes and Metz relegated; Troyes and Le Mans promoted (Le Mans logo
    # already present as le-mans-fc-footballlogos-org).
    # football-data.co.uk strings verified against F1 CSV history.
    # ------------------------------------------------------------------
    "ligue_1": {
        "aj-auxerre-footballlogos-org":          "Auxerre",
        "angers-sco-footballlogos-org":          "Angers",
        "as-monaco-footballlogos-org":           "Monaco",
        "brest-footballlogos-org":               "Brest",
        "fc-lorient-footballlogos-org":          "Lorient",
        "le-havre-ac-footballlogos-org":         "Le Havre",
        "le-mans-fc-footballlogos-org":          "Le Mans",
        "losc-lille-footballlogos-org":          "Lille",
        "marseille-footylogos":                  "Marseille",
        "ofc-nice-footballlogos-org":            "Nice",
        "olympique-lyonnais-footballlogos-org":  "Lyon",
        "paris-fc-footballlogos-org":            "Paris FC",
        "paris-saint-germain-footballlogos-org": "Paris SG",
        "rc-lens-footballlogos-org":             "Lens",
        "rc-strasbourg-alsace-footballlogos-org": "Strasbourg",
        "stade-rennais-footballlogos-org":       "Rennes",
        "toulouse-fc-footballlogos-org":         "Toulouse",
        "troyes-footballlogos-org":              "Troyes",
    },

    # ------------------------------------------------------------------
    # SERIE A  (I1)
    # Pisa, Hellas Verona, Cremonese relegated; Venezia already present.
    # Frosinone already present. Third promoted team (Serie B playoff
    # winner) still TBC — add their logo manually once confirmed.
    # football-data.co.uk strings verified against I1 CSV history.
    # ------------------------------------------------------------------
    "serie_a": {
        "ac-milan-footballlogos-org":      "AC Milan",
        "ac-monza-footballlogos-org":      "Monza",
        "atalanta-footylogos":             "Atalanta",
        "bologna-footballlogos-org":       "Bologna",
        "cagliari-footballlogos-org":      "Cagliari",
        "como-1907-footballlogos-org":     "Como",
        "fiorentina-footballlogos-org":    "Fiorentina",
        "frosinone-footballlogos-org":     "Frosinone",
        "genoa-footballlogos-org":         "Genoa",
        "inter-milan-footballlogos-org":   "Inter",
        "juventus-footballlogos-org":      "Juventus",
        "lazio-footballlogos-org":         "Lazio",
        "lecce-footballlogos-org":         "Lecce",
        "napoli-footylogos":               "Napoli",
        "parma-footballlogos-org":         "Parma",
        "roma-footylogos":                 "Roma",
        "sassuolo-footballlogos-org":      "Sassuolo",
        "torino-footballlogos-org":        "Torino",
        "udinese-footballlogos-org":       "Udinese",
        "venezia-fc-footylogos":           "Venezia",
    },
}

# ---------------------------------------------------------------------------
# Teams expected in 2026/27 that need logos downloaded/added manually.
# ---------------------------------------------------------------------------
MISSING_LOGOS: dict[str, list[str]] = {
    "laliga": [
        "Racing Santander",   # promoted (auto)
        "Deportivo",          # promoted (auto) — fd.co.uk uses "Deportivo"
        # Third promoted team TBC (Segunda playoff final ~21 Jun 2026):
        # Almeria / Malaga / Las Palmas / Castellon
        "??? (playoff winner — confirm after 21 Jun 2026)",
    ],
    "serie_a": [
        # Serie B playoff winner TBC — check football-data.co.uk string
        # once confirmed; Venezia and Frosinone logos already present.
        "??? (Serie B playoff winner — TBC)",
    ],
}


def rename_logos(dry_run: bool = False) -> None:
    total_renamed = 0
    total_skipped = 0
    total_missing = 0

    for league, mapping in RENAMES.items():
        league_dir = LOGOS_ROOT / league
        if not league_dir.exists():
            print(f"\n[{league}] ⚠  Directory not found: {league_dir}")
            continue

        print(f"\n[{league}]")
        for old_stem, new_stem in mapping.items():
            old_path = league_dir / f"{old_stem}.png"
            new_path = league_dir / f"{new_stem}.png"

            if not old_path.exists():
                # Already renamed in a prior run, or file genuinely missing
                if new_path.exists():
                    print(f"  ✓ Already done : {new_stem}.png")
                else:
                    print(f"  ✗ Source missing: {old_stem}.png")
                    total_missing += 1
                continue

            if new_path.exists():
                print(f"  ⚠ Target exists, skipping: {new_stem}.png")
                total_skipped += 1
                continue

            if dry_run:
                print(f"  [DRY RUN] {old_stem}.png  →  {new_stem}.png")
            else:
                old_path.rename(new_path)
                print(f"  Renamed: {old_stem}.png  →  {new_stem}.png")
            total_renamed += 1

    print("\n" + "=" * 60)
    print(f"Renamed : {total_renamed}")
    print(f"Skipped (target already exists): {total_skipped}")
    print(f"Source missing: {total_missing}")

    print("\n📋 LOGOS STILL NEEDED (download manually):")
    for league, teams in MISSING_LOGOS.items():
        print(f"\n  [{league}]")
        for team in teams:
            print(f"    • {team}.png")

    print(
        "\n💡 Filename must match football-data.co.uk HomeTeam/AwayTeam string exactly."
        "\n   The card generator strips apostrophes at lookup time, so e.g."
        "\n   \"M'gladbach.png\" will match team string \"M'gladbach\"."
    )


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN — no files will be changed ===\n")
    rename_logos(dry_run=dry_run)