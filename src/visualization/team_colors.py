"""
src/visualization/team_colors.py

A small database of club colors for teams that appear in the
processed match data, covering the Premier League, La Liga,
Bundesliga, Ligue 1, and Serie A (epl_matches_clean.csv,
laliga_matches_clean.csv, bundesliga_matches_clean.csv,
ligue_1_matches_clean.csv, serie_a_matches_clean.csv), including teams
that have since been relegated/promoted.

Used by card.py to color the Home/Draw/Away outcome bars with each
team's own colors instead of a fixed blue/red, while:
  - keeping the Draw segment a neutral grey (no team association),
  - falling back to a team's secondary color when its primary color
    would clash with the opposing team's color (e.g. Arsenal vs
    Liverpool, both reds),
  - darkening colors that would be too light to read clearly on a
    white card background (e.g. Leeds yellow, Tottenham white/navy).

Colors are approximate, commonly-recognized club colors - the goal is
clear visual identity and good contrast, not exact brand specs.

Non-EPL team names follow football-data.co.uk's naming convention
(e.g. "Ath Madrid" for Atletico Madrid, "Sociedad" for Real Sociedad,
"Ein Frankfurt" for Eintracht Frankfurt, "Paris SG" for PSG).
If a team's colors aren't showing up on a card, its name in that
league's *_matches_clean.csv may differ slightly from the key used
here - check df["HomeTeam"].unique() / df["AwayTeam"].unique() and
adjust or
add the entry below. A missing/mismatched entry doesn't break
anything; that team's bars just fall back to DEFAULT_PRIMARY /
DEFAULT_SECONDARY.
"""

from __future__ import annotations


# {team_name: {"primary": "#RRGGBB", "secondary": "#RRGGBB"}}
TEAM_COLORS: dict[str, dict[str, str]] = {
    "Arsenal": {"primary": "#EF0107", "secondary": "#063672"},
    "Aston Villa": {"primary": "#670E36", "secondary": "#95BFE5"},
    "Birmingham": {"primary": "#1F3F8B", "secondary": "#FFFFFF"},
    "Blackburn": {"primary": "#009EE0", "secondary": "#FFFFFF"},
    "Blackpool": {"primary": "#FF6600", "secondary": "#1A1A1A"},
    "Bolton": {"primary": "#263C7E", "secondary": "#FFFFFF"},
    "Bournemouth": {"primary": "#DA291C", "secondary": "#1A1A1A"},
    "Bradford": {"primary": "#8A0707", "secondary": "#FFA500"},
    "Brentford": {"primary": "#D2122E", "secondary": "#FFB81C"},
    "Brighton": {"primary": "#0057B8", "secondary": "#FFCD00"},
    "Burnley": {"primary": "#6C1D45", "secondary": "#99D6EA"},
    "Cardiff": {"primary": "#0070B5", "secondary": "#D11524"},
    "Charlton": {"primary": "#D2122E", "secondary": "#1A1A1A"},
    "Chelsea": {"primary": "#034694", "secondary": "#D1AB5E"},
    "Coventry": {"primary": "#6CABDD", "secondary": "#1A1A1A"},
    "Crystal Palace": {"primary": "#1B458F", "secondary": "#C4122E"},
    "Derby": {"primary": "#1A1A1A", "secondary": "#FFD700"},
    "Everton": {"primary": "#003399", "secondary": "#FFD200"},
    "Fulham": {"primary": "#1A1A1A", "secondary": "#CC0000"},
    "Hull": {"primary": "#F5A12D", "secondary": "#1A1A1A"},
    "Ipswich": {"primary": "#1D4496", "secondary": "#F2A900"},
    "Leeds": {"primary": "#FFCD00", "secondary": "#1D428A"},
    "Leicester": {"primary": "#003090", "secondary": "#FDBE11"},
    "Liverpool": {"primary": "#C8102E", "secondary": "#F6EB16"},
    "Luton": {"primary": "#F78F1E", "secondary": "#002D62"},
    "Man City": {"primary": "#6CABDD", "secondary": "#1C2C5B"},
    "Man United": {"primary": "#DA291C", "secondary": "#FBE122"},
    "Middlesbrough": {"primary": "#E21A23", "secondary": "#1A1A1A"},
    "Newcastle": {"primary": "#41B6E6", "secondary": "#1A1A1A"},
    "Norwich": {"primary": "#FFF200", "secondary": "#00A650"},
    "Nott'm Forest": {"primary": "#DD0000", "secondary": "#FFD700"},
    "Portsmouth": {"primary": "#001489", "secondary": "#C8102E"},
    "QPR": {"primary": "#1D5BA4", "secondary": "#E03A3E"},
    "Reading": {"primary": "#004494", "secondary": "#FFB81C"},
    "Sheffield United": {"primary": "#EE2737", "secondary": "#1A1A1A"},
    "Sheffield Weds": {"primary": "#0066B3", "secondary": "#FFD200"},
    "Southampton": {"primary": "#D71920", "secondary": "#FFC20E"},
    "Stoke": {"primary": "#E03A3E", "secondary": "#1B449C"},
    "Sunderland": {"primary": "#EB172B", "secondary": "#1A1A1A"},
    "Swansea": {"primary": "#1A1A1A", "secondary": "#00543C"},
    "Tottenham": {"primary": "#132257", "secondary": "#FFD700"},
    "Watford": {"primary": "#FBEE23", "secondary": "#ED2127"},
    "West Brom": {"primary": "#122F67", "secondary": "#FDB913"},
    "West Ham": {"primary": "#7A263A", "secondary": "#1BB1E7"},
    "Wigan": {"primary": "#1D59AF", "secondary": "#DA291C"},
    "Wolves": {"primary": "#FDB913", "secondary": "#231F20"},

    # ------------------------------------------------------------
    # La Liga (football-data.co.uk SP1 naming conventions)
    # ------------------------------------------------------------
    "Real Madrid": {"primary": "#00529F", "secondary": "#FEBE10"},
    "Barcelona": {"primary": "#A50044", "secondary": "#004D98"},
    "Ath Madrid": {"primary": "#CB3524", "secondary": "#272E61"},
    "Ath Bilbao": {"primary": "#EE2523", "secondary": "#1A1A1A"},
    "Valencia": {"primary": "#EE8E25", "secondary": "#1A1A1A"},
    "Sevilla": {"primary": "#CD122D", "secondary": "#0B2A5B"},
    "Villarreal": {"primary": "#FFE667", "secondary": "#005187"},
    "Sociedad": {"primary": "#0066B3", "secondary": "#1A1A1A"},
    "Betis": {"primary": "#00954C", "secondary": "#1A1A1A"},
    "Celta": {"primary": "#8AC3EE", "secondary": "#1A1A1A"},
    "Espanol": {"primary": "#0046AA", "secondary": "#FFD200"},
    "Getafe": {"primary": "#005999", "secondary": "#1A1A1A"},
    "La Coruna": {"primary": "#0E5FAE", "secondary": "#1A1A1A"},
    "Zaragoza": {"primary": "#1E50A2", "secondary": "#1A1A1A"},
    "Santander": {"primary": "#048A4B", "secondary": "#1A1A1A"},
    "Osasuna": {"primary": "#D2122E", "secondary": "#08234B"},
    "Mallorca": {"primary": "#CC0000", "secondary": "#1A1A1A"},
    "Levante": {"primary": "#004B87", "secondary": "#B6022A"},
    "Granada": {"primary": "#C60C30", "secondary": "#1A1A1A"},
    "Malaga": {"primary": "#1B68B3", "secondary": "#1A1A1A"},
    "Vallecano": {"primary": "#E30613", "secondary": "#1A1A1A"},
    "Elche": {"primary": "#017F4A", "secondary": "#1A1A1A"},
    "Almeria": {"primary": "#D2122E", "secondary": "#1A1A1A"},
    "Eibar": {"primary": "#0B3B8C", "secondary": "#7A1E3C"},
    "Las Palmas": {"primary": "#FFE667", "secondary": "#005BAA"},
    "Leganes": {"primary": "#0A3D7A", "secondary": "#1A1A1A"},
    "Alaves": {"primary": "#1E50A2", "secondary": "#1A1A1A"},
    "Girona": {"primary": "#CD2534", "secondary": "#1A1A1A"},
    "Cadiz": {"primary": "#FFE100", "secondary": "#003DA5"},
    "Valladolid": {"primary": "#5E2750", "secondary": "#1A1A1A"},
    "Huesca": {"primary": "#1E5BB8", "secondary": "#0F9D58"},
    "Sp Gijon": {"primary": "#EE2E24", "secondary": "#1A1A1A"},
    "Numancia": {"primary": "#D2122E", "secondary": "#1A1A1A"},
    "Recreativo": {"primary": "#1A3E8C", "secondary": "#1A1A1A"},
    "Murcia": {"primary": "#9A1023", "secondary": "#1A1A1A"},
    "Tenerife": {"primary": "#003DA5", "secondary": "#1A1A1A"},
    "Hercules": {"primary": "#1E5BB8", "secondary": "#1A1A1A"},
    "Cordoba": {"primary": "#0F9D58", "secondary": "#1A1A1A"},
    "Oviedo": {"primary": "#0E5FAE", "secondary": "#1A1A1A"},

    # ------------------------------------------------------------
    # Bundesliga (football-data.co.uk D1 naming conventions)
    # ------------------------------------------------------------
    "Bayern Munich": {"primary": "#DC052D", "secondary": "#0066B2"},
    "Dortmund": {"primary": "#FDE100", "secondary": "#1A1A1A"},
    "RB Leipzig": {"primary": "#DD0741", "secondary": "#041E42"},
    "Leverkusen": {"primary": "#E32221", "secondary": "#1A1A1A"},
    "Wolfsburg": {"primary": "#65B32E", "secondary": "#1A1A1A"},
    "Ein Frankfurt": {"primary": "#E1000F", "secondary": "#1A1A1A"},
    "M'gladbach": {"primary": "#1A1A1A", "secondary": "#65B32E"},
    "Hoffenheim": {"primary": "#1C63B7", "secondary": "#1A1A1A"},
    "Freiburg": {"primary": "#1A1A1A", "secondary": "#E2001A"},
    "Mainz": {"primary": "#C3141E", "secondary": "#1A1A1A"},
    "Union Berlin": {"primary": "#EB1923", "secondary": "#FFD700"},
    "Augsburg": {"primary": "#BA3733", "secondary": "#046A38"},
    "Stuttgart": {"primary": "#E0001C", "secondary": "#1A1A1A"},
    "Werder Bremen": {"primary": "#1D9053", "secondary": "#1A1A1A"},
    "Heidenheim": {"primary": "#C00316", "secondary": "#0455A1"},
    "FC Koln": {"primary": "#ED1C24", "secondary": "#1A1A1A"},
    "Hamburg": {"primary": "#0F5EA8", "secondary": "#1A1A1A"},
    "St Pauli": {"primary": "#8B4513", "secondary": "#1A1A1A"},

    # ------------------------------------------------------------
    # Ligue 1 (football-data.co.uk F1 naming conventions)
    # ------------------------------------------------------------
    "Paris SG": {"primary": "#004170", "secondary": "#DA291C"},
    "Marseille": {"primary": "#2FAEE0", "secondary": "#1A1A1A"},
    "Lyon": {"primary": "#0E3293", "secondary": "#E2001A"},
    "Monaco": {"primary": "#E2001A", "secondary": "#1A1A1A"},
    "Lille": {"primary": "#E2001A", "secondary": "#001A4B"},
    "Rennes": {"primary": "#E2001A", "secondary": "#1A1A1A"},
    "Nice": {"primary": "#E2001A", "secondary": "#1A1A1A"},
    "Lens": {"primary": "#E2001A", "secondary": "#FFD700"},
    "Strasbourg": {"primary": "#0066B3", "secondary": "#1A1A1A"},
    "Nantes": {"primary": "#FFD700", "secondary": "#1A8A3D"},
    "Toulouse": {"primary": "#6A0DAD", "secondary": "#1A1A1A"},
    "Brest": {"primary": "#E2001A", "secondary": "#1A1A1A"},
    "Le Havre": {"primary": "#0066B3", "secondary": "#1A1A1A"},
    "Auxerre": {"primary": "#1A3E8C", "secondary": "#1A1A1A"},
    "Angers": {"primary": "#1A1A1A", "secondary": "#E2001A"},
    "Metz": {"primary": "#8B0000", "secondary": "#7EC0EE"},
    "Lorient": {"primary": "#FF6600", "secondary": "#1A1A1A"},
    "Paris FC": {"primary": "#0033A0", "secondary": "#E2001A"},

    # ------------------------------------------------------------
    # Serie A (football-data.co.uk I1 naming conventions)
    # ------------------------------------------------------------
    "Juventus": {"primary": "#1A1A1A", "secondary": "#FEBE10"},
    "Inter": {"primary": "#003D7C", "secondary": "#1A1A1A"},
    "Milan": {"primary": "#FB090B", "secondary": "#1A1A1A"},
    "Napoli": {"primary": "#12A0D7", "secondary": "#1A1A1A"},
    "Roma": {"primary": "#8E1F2F", "secondary": "#F0BC42"},
    "Lazio": {"primary": "#87CEEB", "secondary": "#1A1A1A"},
    "Fiorentina": {"primary": "#5B2C86", "secondary": "#1A1A1A"},
    "Atalanta": {"primary": "#0033A0", "secondary": "#1A1A1A"},
    "Torino": {"primary": "#7B1127", "secondary": "#1A1A1A"},
    "Genoa": {"primary": "#C8102E", "secondary": "#002F6C"},
    "Udinese": {"primary": "#2D2D2D", "secondary": "#FFFFFF"},
    "Bologna": {"primary": "#C8102E", "secondary": "#003C71"},
    "Sassuolo": {"primary": "#00A650", "secondary": "#1A1A1A"},
    "Lecce": {"primary": "#FDB927", "secondary": "#C8102E"},
    "Verona": {"primary": "#FFD700", "secondary": "#003DA5"},
    "Cagliari": {"primary": "#C8102E", "secondary": "#002B5C"},
    "Parma": {"primary": "#FFD700", "secondary": "#003DA5"},
    "Como": {"primary": "#1A4FA0", "secondary": "#1A1A1A"},
    "Cremonese": {"primary": "#C8102E", "secondary": "#6E6E6E"},
    "Pisa": {"primary": "#003366", "secondary": "#1A1A1A"},
}


DEFAULT_PRIMARY = "#1E40AF"
DEFAULT_SECONDARY = "#DC2626"


def _normalize_team_name(team_name: str) -> str:
    return team_name.strip()


def _team_entry(team_name: str) -> dict[str, str]:
    name = _normalize_team_name(team_name)

    if name in TEAM_COLORS:
        return TEAM_COLORS[name]

    # Try without apostrophes (e.g. "Nott'm Forest" variants).
    stripped = name.replace("'", "")
    for key, entry in TEAM_COLORS.items():
        if key.replace("'", "") == stripped:
            return entry

    return {"primary": DEFAULT_PRIMARY, "secondary": DEFAULT_SECONDARY}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, c)) for c in rgb])


def color_distance(hex_a: str, hex_b: str) -> float:
    """
    Euclidean distance between two colors in RGB space (0-441).
    """
    ra, ga, ba = hex_to_rgb(hex_a)
    rb, gb, bb = hex_to_rgb(hex_b)
    return ((ra - rb) ** 2 + (ga - gb) ** 2 + (ba - bb) ** 2) ** 0.5


def relative_luminance(hex_color: str) -> float:
    """
    Perceived brightness in [0, 1], using the standard luminance
    weighting. 0 = black, 1 = white.
    """
    r, g, b = hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def ensure_visible(hex_color: str, max_luminance: float = 0.75) -> str:
    """
    Darken a color if it's too light to read clearly as text or as a
    bar fill on a white background (e.g. bright yellows).
    """
    luminance = relative_luminance(hex_color)

    if luminance <= max_luminance or luminance == 0:
        return hex_color

    factor = (max_luminance / luminance) * 0.9
    r, g, b = hex_to_rgb(hex_color)

    return rgb_to_hex((int(r * factor), int(g * factor), int(b * factor)))


def get_team_color(team_name: str, variant: str = "primary") -> str:
    """
    Return a team's color (primary or secondary), darkened if
    necessary for visibility on a white background. Unknown teams
    get a default blue/red.
    """
    entry = _team_entry(team_name)
    color = entry.get(variant, entry["primary"])
    return ensure_visible(color)


def get_team_colors_for_fixture(
    home_team: str,
    away_team: str,
    clash_threshold: float = 80.0,
) -> tuple[str, str]:
    """
    Return (home_color, away_color) for an H/D/A outcome bar, using
    each team's primary color by default.

    If the two primary colors are too similar (e.g. Arsenal vs
    Liverpool, both reds), the away team's secondary color is used
    instead. If that still clashes, the home team's secondary color
    is used for the home side as a last resort.

    All returned colors are passed through ensure_visible() so they
    remain legible on a white card background.
    """
    home_entry = _team_entry(home_team)
    away_entry = _team_entry(away_team)

    home_color = ensure_visible(home_entry["primary"])
    away_color = ensure_visible(away_entry["primary"])

    if color_distance(home_color, away_color) < clash_threshold:
        away_color = ensure_visible(away_entry.get("secondary", away_entry["primary"]))

    if color_distance(home_color, away_color) < clash_threshold:
        home_color = ensure_visible(home_entry.get("secondary", home_entry["primary"]))

    return home_color, away_color