"""
src/visualization/card.py

Pillow-based forecast cards:

  - create_season_forecast_card:
        League table (Position, Team, Points, GD, Probability) plus a
        Title Race Probabilities highlight section.

  - create_matchday_overview_card:
        All fixtures for the next matchday, each with team logos and
        a Home/Draw/Away outcome bar.

  - create_match_detail_card:
        A single fixture, with team logos, predicted scoreline,
        expected goals, and a larger Home/Draw/Away outcome bar.

Data sources (see src/simulation/monte_carlo.py and src/live/matchday.py):

  - table_df for create_season_forecast_card should come from
    add_position_probability_column(format_forecast_table(summary), ...)
    with columns: Position (renamed from 'Rank'), Team, Points
    (rounded 'Expected Points'), GD (rounded 'Expected GD'),
    Probability.

  - title_probs comes from get_title_probabilities(summary).

  - fixtures_df / fixture for the matchday cards come from
    get_next_matchday_fixtures(remaining_predictions), which has
    HomeTeam, AwayTeam, HomeExpectedGoals, AwayExpectedGoals,
    HomeWinProb, DrawProb, AwayWinProb, Date, Season. Probabilities
    are fractions in [0, 1].
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from pathlib import Path
import logging
import math

from src.visualization.team_colors import get_team_colors_for_fixture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CardGenerator:
    """Generates forecast cards for season tables and match predictions."""

    # Brand colours
    COLOR_HEADER_BG = "#1E3A8A"
    COLOR_HEADER_TEXT = "#FFFFFF"
    COLOR_TEXT = "#0F172A"
    COLOR_SUBTEXT = "#64748B"
    COLOR_ROW_ALT = "#F8FAFC"
    COLOR_ROW = "#FFFFFF"
    COLOR_BAR_BG = "#E2E8F0"
    COLOR_BAR_HOME = "#1E40AF"
    COLOR_BAR_DRAW = "#94A3B8"
    COLOR_BAR_AWAY = "#DC2626"

    def __init__(
        self,
        output_dir: str = "outputs/cards",
        logos_dir: str = "data/logos/epl",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logos_dir = Path(logos_dir)

        self.handle = "@e_okinyo"
        self.brand_text = f"For more stats, follow {self.handle}"

        try:
            self.font_large = ImageFont.truetype("arial.ttf", 40)
            self.font_medium = ImageFont.truetype("arial.ttf", 24)
            self.font_small = ImageFont.truetype("arial.ttf", 20)
            self.font_tiny = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            self.font_large = ImageFont.load_default(size=40)
            self.font_medium = ImageFont.load_default(size=24)
            self.font_small = ImageFont.load_default(size=20)
            self.font_tiny = ImageFont.load_default(size=16)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _get_logo_path(self, team_name: str) -> Path | None:
        # Try the team name as-is, with apostrophes stripped (e.g.
        # "Nott'm Forest" -> "Nottm Forest"), and each of those with
        # spaces converted to underscores or removed entirely.
        base_variants = [team_name, team_name.replace("'", "")]

        candidates = []
        for base in base_variants:
            candidates.append(base)
            candidates.append(base.replace(" ", "_"))
            candidates.append(base.replace(" ", ""))

        for name in candidates:
            path = self.logos_dir / f"{name}.png"
            if path.exists():
                return path

        return None

    def _paste_logo(
        self,
        card: Image.Image,
        team_name: str,
        xy: tuple[int, int],
        size: int,
    ) -> None:
        logo_path = self._get_logo_path(team_name)
        if not logo_path:
            return
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((size, size))
            card.paste(logo, xy, logo)
        except Exception:
            logger.warning(f"Could not load logo for '{team_name}' from {logo_path}")

    def _get_text_width(self, text: str, font) -> int:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    @staticmethod
    def _predicted_scoreline(home_xg: float, away_xg: float) -> tuple[int, int]:
        """
        Round expected goals to the nearest integer to produce a
        simple "predicted scoreline" (e.g. xG 2.1-0.8 -> "2-1").

        Note: this is the rounded MEAN of each team's Poisson
        distribution, not the most likely joint scoreline - see
        _most_likely_scoreline for that. For xG values below ~2, the
        Poisson mode is floor(xG) rather than round(xG), so this
        figure tends to look more "high-scoring" than the actual
        most likely result.
        """
        return int(round(home_xg)), int(round(away_xg))

    @staticmethod
    def _poisson_pmf(k: int, lam: float) -> float:
        return (math.exp(-lam) * lam ** k) / math.factorial(k)

    @classmethod
    def _most_likely_scoreline(
        cls,
        home_xg: float,
        away_xg: float,
        max_goals: int = 6,
    ) -> tuple[int, int]:
        """
        Return the (HomeGoals, AwayGoals) combination with the highest
        joint probability under independent Poisson(home_xg) /
        Poisson(away_xg) distributions - i.e. the actual mode of the
        score distribution (what's most likely to happen), as opposed
        to _predicted_scoreline's rounded means.

        max_goals=6 is more than enough: for typical xG values (well
        under 4), joint probabilities beyond 4-5 goals per side are
        negligible and never the maximum.
        """
        best = (0, 0)
        best_prob = -1.0

        for h in range(max_goals + 1):
            home_prob = cls._poisson_pmf(h, home_xg)

            for a in range(max_goals + 1):
                away_prob = cls._poisson_pmf(a, away_xg)
                joint_prob = home_prob * away_prob

                if joint_prob > best_prob:
                    best_prob = joint_prob
                    best = (h, a)

        return best

    @staticmethod
    def _format_date(value) -> str:
        """
        Format a date value for display, handling pandas Timestamps
        (which str() would otherwise render as "2026-01-01 00:00:00"),
        plain date/datetime objects, and strings.
        """
        if value is None:
            return ""

        if hasattr(value, "strftime"):
            try:
                return value.strftime("%d %b %Y")
            except (ValueError, TypeError):
                pass

        return str(value)

    def _draw_outcome_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        home_pct: float,
        draw_pct: float,
        away_pct: float,
        font=None,
        label: bool = True,
        home_color: str | None = None,
        away_color: str | None = None,
    ) -> None:
        """
        Draw a three-segment horizontal bar representing Home/Draw/Away
        probabilities (each given as a percentage, 0-100), with
        optional percentage labels below the bar.

        home_color / away_color override the default blue/red fill
        for the Home and Away segments (e.g. with each team's own
        color via team_colors.get_team_colors_for_fixture). The Draw
        segment always stays a neutral grey, regardless of teams.
        """
        font = font or self.font_tiny

        home_color = home_color or self.COLOR_BAR_HOME
        away_color = away_color or self.COLOR_BAR_AWAY

        total = max(home_pct + draw_pct + away_pct, 1e-9)
        home_w = int(width * home_pct / total)
        draw_w = int(width * draw_pct / total)
        away_w = width - home_w - draw_w

        draw.rectangle([x, y, x + width, y + height], fill=self.COLOR_BAR_BG)

        if home_w > 0:
            draw.rectangle([x, y, x + home_w, y + height], fill=home_color)
        if draw_w > 0:
            draw.rectangle(
                [x + home_w, y, x + home_w + draw_w, y + height],
                fill=self.COLOR_BAR_DRAW,
            )
        if away_w > 0:
            draw.rectangle(
                [x + home_w + draw_w, y, x + width, y + height],
                fill=away_color,
            )

        if label:
            label_y = y + height + 14
            draw.text(
                (x, label_y), f"H {home_pct:.0f}%",
                fill=home_color, font=font, anchor="lm",
            )
            draw.text(
                (x + width // 2, label_y), f"D {draw_pct:.0f}%",
                fill=self.COLOR_BAR_DRAW, font=font, anchor="mm",
            )
            draw.text(
                (x + width, label_y), f"A {away_pct:.0f}%",
                fill=away_color, font=font, anchor="rm",
            )

    # ------------------------------------------------------------
    # Season forecast card
    # ------------------------------------------------------------

    def create_season_forecast_card(
        self,
        table_df: pd.DataFrame,
        title_probs: dict | None = None,
        season: str = "2025/26",
        forecast_date: str | None = None,
        league: str = "Premier League",
        filename: str | None = None,
    ) -> str:
        """
        table_df must contain columns:
            Position, Team, Points, GD, Probability

        and may optionally also contain:
            Top 4 %, Relegation %

        Probability is the percentage chance (0-100) that the team
        finishes in that exact Position (see
        monte_carlo.add_position_probability_column). Top 4 % and
        Relegation % come directly from format_forecast_table's
        output and give the broader "zone" probabilities for each
        team, which are often more informative than the exact-position
        probability for mid-table teams.

        title_probs: {Team: probability_percent} for the title-race
        highlight section (see monte_carlo.get_title_probabilities).
        """
        if filename is None:
            filename = (
                f"{league.lower().replace(' ', '_')}_"
                f"{season.replace('/', '-')}_forecast.png"
            )

        # === League Table layout ===
        #
        # Column spec: (header, dataframe_column, formatter).
        # "Team" is special-cased (logo + left-aligned name) and is
        # not driven by this spec.
        table_top = 155
        left_margin = 120
        logo_size = 30
        logo_space = 82
        padding = 7

        row_height = max(logo_size, self.font_small.size) + padding * 2

        value_columns = [
            ("Position", "Position", lambda v: str(int(v))),
            ("Points", "Points", lambda v: str(int(v))),
            ("GD", "GD", lambda v: str(int(v))),
            ("Finish Here %", "Probability", lambda v: f"{v:.1f}%"),
            ("Top 4 %", "Top 4 %", lambda v: f"{v:.1f}%"),
            ("Releg %", "Relegation %", lambda v: f"{v:.1f}%"),
        ]

        # Only include columns that are actually present in table_df,
        # so callers can omit Top 4 % / Relegation % if not available.
        value_columns = [
            (header, key, fmt) for header, key, fmt in value_columns
            if key in table_df.columns
        ]

        team_width = max(
            self._get_text_width(t, self.font_small) for t in table_df["Team"]
        ) + logo_space + 12

        col_widths = {"Team": team_width}

        for header, key, fmt in value_columns:
            labels = [fmt(v) for v in table_df[key]] + [header]
            col_widths[key] = max(
                self._get_text_width(label, self.font_small) for label in labels
            ) + 30

        # Build column order: Position first, then Team, then the
        # remaining value columns in spec order.
        position_header, position_key, position_fmt = next(
            c for c in value_columns if c[1] == "Position"
        )
        other_columns = [c for c in value_columns if c[1] != "Position"]

        ordered_columns = [("Position", position_key, position_fmt, col_widths["Position"])]
        ordered_columns.append(("Team", "Team", None, col_widths["Team"]))
        for header, key, fmt in other_columns:
            ordered_columns.append((header, key, fmt, col_widths[key]))

        col_x = []
        running_x = left_margin
        for header, key, fmt, col_width in ordered_columns:
            col_x.append(running_x + col_width // 2)
            running_x += col_width

        table_right = running_x + 35

        # A short explanatory caption is shown below the table when
        # the "Finish Here %" column is present, since that metric
        # (probability of finishing in exactly the position shown) is
        # not self-explanatory the way Top 4 % / Relegation % are.
        has_position_probability = "Probability" in table_df.columns

        caption_text = (
            "Finish Here % = chance of ending the season in exactly "
            "the position shown above"
        )

        # === Canvas size ===
        #
        # Width must fit the table, the title-race bar section (if
        # present), and the caption (if present); height depends on
        # table length and whether those sections are shown.
        if title_probs:
            pct_labels = [f"{p:.1f}%" for p in title_probs.values()]
            max_pct_width = max(
                self._get_text_width(label, self.font_small) for label in pct_labels
            )
            bar_max_width = 400
            title_required_width = left_margin + 195 + bar_max_width + 12 + max_pct_width + 40
        else:
            title_required_width = 0

        if has_position_probability:
            caption_required_width = left_margin + self._get_text_width(caption_text, self.font_tiny) + 40
        else:
            caption_required_width = 0

        width = max(table_right + 40, title_required_width, caption_required_width)

        table_bottom = table_top + 48 + len(table_df) * row_height

        if has_position_probability:
            caption_top = table_bottom + 16
            content_bottom = caption_top + self.font_tiny.size + 8
        else:
            content_bottom = table_bottom

        if title_probs:
            n_bars = min(len(title_probs), 5)
            bar_height = 24
            bar_gap = 6
            title_section_top = content_bottom + 20
            bar_start_y = title_section_top + 32
            bars_bottom = bar_start_y + n_bars * (bar_height + bar_gap) - bar_gap
            height = bars_bottom + 60
        else:
            height = content_bottom + 80

        card = Image.new("RGB", (width, height), color="#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header
        draw.text(
            (width // 2, 50), f"{league} - Season {season} Forecast",
            fill=self.COLOR_TEXT, font=self.font_large, anchor="mm",
        )
        if forecast_date:
            draw.text(
                (width // 2, 95), f"As of {forecast_date}",
                fill=self.COLOR_SUBTEXT, font=self.font_medium, anchor="mm",
            )

        # === League Table ===

        # Table header
        header_y = table_top
        draw.rectangle(
            [left_margin - 18, header_y - 14, table_right, header_y + 34],
            fill=self.COLOR_HEADER_BG,
        )

        for x, (header, _, _, _) in zip(col_x, ordered_columns):
            draw.text(
                (x, header_y + 10), header,
                fill=self.COLOR_HEADER_TEXT, font=self.font_small, anchor="mm",
            )

        # Table rows
        team_col_index = next(
            i for i, c in enumerate(ordered_columns) if c[1] == "Team"
        )

        for i, row in table_df.reset_index(drop=True).iterrows():
            y_center = table_top + 48 + i * row_height + row_height // 2

            bg_color = self.COLOR_ROW_ALT if i % 2 == 0 else self.COLOR_ROW
            draw.rectangle(
                [left_margin - 18, y_center - row_height // 2, table_right, y_center + row_height // 2],
                fill=bg_color,
            )

            for col_idx, (header, key, fmt, _) in enumerate(ordered_columns):
                x = col_x[col_idx]

                if key == "Team":
                    self._paste_logo(
                        card, row["Team"],
                        (x - 78, y_center - logo_size // 2), logo_size,
                    )
                    draw.text(
                        (x - 34, y_center), row["Team"],
                        fill=self.COLOR_TEXT, font=self.font_small, anchor="lm",
                    )
                else:
                    draw.text(
                        (x, y_center), fmt(row[key]),
                        fill=self.COLOR_TEXT, font=self.font_small, anchor="mm",
                    )

        # === Caption explaining "Finish Here %" ===
        if has_position_probability:
            draw.text(
                (left_margin - 18, caption_top), caption_text,
                fill=self.COLOR_SUBTEXT, font=self.font_tiny, anchor="lm",
            )

        # === Title Race Probabilities Section ===
        if title_probs:
            prob_start_y = title_section_top

            draw.text(
                (width // 2, prob_start_y), "Title Race Probabilities (%)",
                fill=self.COLOR_TEXT, font=self.font_medium, anchor="mm",
            )

            bar_start_y = prob_start_y + 32
            bar_height = 24
            bar_max_width = 400
            sorted_probs = sorted(title_probs.items(), key=lambda x: x[1], reverse=True)[:5]

            for idx, (team, prob) in enumerate(sorted_probs):
                y = bar_start_y + idx * (bar_height + 6)

                self._paste_logo(card, team, (left_margin + 15, y + 2), 20)

                draw.text(
                    (left_margin + 50, y + 12), team,
                    fill=self.COLOR_TEXT, font=self.font_small, anchor="lm",
                )

                bar_x = left_margin + 195
                draw.rectangle(
                    [bar_x, y + 3, bar_x + bar_max_width, y + bar_height - 3],
                    fill=self.COLOR_BAR_BG,
                )

                fill_width = int((prob / 100) * bar_max_width)
                if fill_width > 0:
                    draw.rectangle(
                        [bar_x, y + 3, bar_x + fill_width, y + bar_height - 3],
                        fill=self.COLOR_BAR_HOME,
                    )

                draw.text(
                    (bar_x + bar_max_width + 12, y + 12), f"{prob:.1f}%",
                    fill=self.COLOR_TEXT, font=self.font_small, anchor="lm",
                )

        # Footer
        draw.text(
            (width - 60, height - 45), self.brand_text,
            fill=self.COLOR_SUBTEXT, font=self.font_small, anchor="rm",
        )

        save_path = self.output_dir / filename
        card.save(save_path, dpi=(240, 240))

        logger.info(f"Season forecast card saved: {save_path}")
        return str(save_path)

    # ------------------------------------------------------------
    # Matchday overview card
    # ------------------------------------------------------------

    def create_matchday_overview_card(
        self,
        fixtures_df: pd.DataFrame,
        season: str = "2025/26",
        matchday_label: str | None = None,
        league: str = "Premier League",
        filename: str | None = None,
    ) -> str:
        """
        fixtures_df must contain columns:
            HomeTeam, AwayTeam, HomeWinProb, DrawProb, AwayWinProb

        Probabilities are expected as fractions in [0, 1] (as produced
        by predict_fixture_list / remaining_predictions); they are
        converted to percentages for display.

        One row is drawn per fixture, with team logos and a
        Home/Draw/Away outcome bar.
        """
        if filename is None:
            label_part = (matchday_label or "matchday").lower().replace(" ", "_")
            label_part = "".join(
                c for c in label_part if c.isalnum() or c in ("_", "-")
            )
            filename = (
                f"{league.lower().replace(' ', '_')}_"
                f"{season.replace('/', '-')}_{label_part}.png"
            )

        fixtures_df = fixtures_df.reset_index(drop=True)
        n_fixtures = len(fixtures_df)

        width = 1200
        row_height = 100
        header_height = 140
        footer_height = 70
        height = header_height + max(n_fixtures, 1) * row_height + footer_height

        card = Image.new("RGB", (width, height), color="#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header
        draw.text(
            (width // 2, 50), f"{league} - {season}",
            fill=self.COLOR_TEXT, font=self.font_large, anchor="mm",
        )

        subtitle = matchday_label or "Upcoming Fixtures"
        draw.text(
            (width // 2, 95), subtitle,
            fill=self.COLOR_SUBTEXT, font=self.font_medium, anchor="mm",
        )

        # Fixtures
        left_margin = 60
        logo_size = 36
        bar_width = 360
        bar_height = 22
        team_col_width = 280

        for i, row in fixtures_df.iterrows():
            y_center = header_height + i * row_height + row_height // 2

            bg_color = self.COLOR_ROW_ALT if i % 2 == 0 else self.COLOR_ROW
            draw.rectangle(
                [0, y_center - row_height // 2, width, y_center + row_height // 2],
                fill=bg_color,
            )

            home = row["HomeTeam"]
            away = row["AwayTeam"]

            # Home team: name right-aligned, logo to its right
            home_text_x = left_margin + team_col_width - logo_size - 10
            draw.text(
                (home_text_x, y_center - 14), home,
                fill=self.COLOR_TEXT, font=self.font_small, anchor="rm",
            )
            self._paste_logo(
                card, home,
                (home_text_x + 10, y_center - 14 - logo_size // 2), logo_size,
            )

            # "vs"
            vs_x = left_margin + team_col_width + 40
            draw.text(
                (vs_x, y_center - 14), "vs",
                fill=self.COLOR_SUBTEXT, font=self.font_small, anchor="mm",
            )

            # Away team: logo to its left, name left-aligned
            away_text_x = vs_x + 40
            self._paste_logo(
                card, away,
                (away_text_x, y_center - 14 - logo_size // 2), logo_size,
            )
            draw.text(
                (away_text_x + logo_size + 10, y_center - 14), away,
                fill=self.COLOR_TEXT, font=self.font_small, anchor="lm",
            )

            # Outcome bar
            bar_x = width - left_margin - bar_width
            home_pct = row["HomeWinProb"] * 100
            draw_pct = row["DrawProb"] * 100
            away_pct = row["AwayWinProb"] * 100

            home_color, away_color = get_team_colors_for_fixture(home, away)

            self._draw_outcome_bar(
                draw,
                x=bar_x,
                y=y_center - bar_height // 2 - 8,
                width=bar_width,
                height=bar_height,
                home_pct=home_pct,
                draw_pct=draw_pct,
                away_pct=away_pct,
                home_color=home_color,
                away_color=away_color,
            )

        # Footer
        draw.text(
            (width - 60, height - 30), self.brand_text,
            fill=self.COLOR_SUBTEXT, font=self.font_small, anchor="rm",
        )

        save_path = self.output_dir / filename
        card.save(save_path, dpi=(240, 240))

        logger.info(f"Matchday overview card saved: {save_path}")
        return str(save_path)

    # ------------------------------------------------------------
    # Match detail card
    # ------------------------------------------------------------

    def create_match_detail_card(
        self,
        fixture: pd.Series | dict,
        season: str = "2025/26",
        league: str = "Premier League",
        filename: str | None = None,
    ) -> str:
        """
        fixture must contain:
            HomeTeam, AwayTeam, HomeExpectedGoals, AwayExpectedGoals,
            HomeWinProb, DrawProb, AwayWinProb
        and optionally Date.

        Probabilities are expected as fractions in [0, 1].
        """
        home = fixture["HomeTeam"]
        away = fixture["AwayTeam"]

        if filename is None:
            safe_home = home.replace(" ", "_")
            safe_away = away.replace(" ", "_")
            filename = f"{safe_home}_vs_{safe_away}.png"

        width, height = 1080, 630
        card = Image.new("RGB", (width, height), color="#FFFFFF")
        draw = ImageDraw.Draw(card)

        draw.text(
            (width // 2, 50), f"{league} - {season}",
            fill=self.COLOR_SUBTEXT, font=self.font_medium, anchor="mm",
        )

        date_value = fixture.get("Date") if hasattr(fixture, "get") else None
        if date_value:
            draw.text(
                (width // 2, 85), self._format_date(date_value),
                fill=self.COLOR_SUBTEXT, font=self.font_small, anchor="mm",
            )

        # Team names + logos
        center_y = 220
        logo_size = 100

        self._paste_logo(
            card, home,
            (width // 4 - logo_size // 2, center_y - logo_size // 2), logo_size,
        )
        draw.text(
            (width // 4, center_y + logo_size // 2 + 25), home,
            fill=self.COLOR_TEXT, font=self.font_medium, anchor="mm",
        )

        self._paste_logo(
            card, away,
            (3 * width // 4 - logo_size // 2, center_y - logo_size // 2), logo_size,
        )
        draw.text(
            (3 * width // 4, center_y + logo_size // 2 + 25), away,
            fill=self.COLOR_TEXT, font=self.font_medium, anchor="mm",
        )

        # Predicted scoreline
        home_goals, away_goals = self._predicted_scoreline(
            fixture["HomeExpectedGoals"], fixture["AwayExpectedGoals"]
        )

        ml_home_goals, ml_away_goals = self._most_likely_scoreline(
            fixture["HomeExpectedGoals"], fixture["AwayExpectedGoals"]
        )

        draw.text(
            (width // 2, center_y), f"{home_goals} - {away_goals}",
            fill=self.COLOR_TEXT, font=self.font_large, anchor="mm",
        )
        draw.text(
            (width // 2, center_y + 50), "Predicted Score",
            fill=self.COLOR_SUBTEXT, font=self.font_tiny, anchor="mm",
        )
        draw.text(
            (width // 2, center_y + 78),
            f"Most Likely Score: {ml_home_goals}-{ml_away_goals}",
            fill=self.COLOR_SUBTEXT, font=self.font_tiny, anchor="mm",
        )

        # Expected goals (precise)
        xg_y = center_y + 138
        draw.text(
            (width // 2, xg_y),
            f"xG: {fixture['HomeExpectedGoals']:.2f} - {fixture['AwayExpectedGoals']:.2f}",
            fill=self.COLOR_SUBTEXT, font=self.font_small, anchor="mm",
        )

        # Outcome probabilities
        prob_y = xg_y + 70
        draw.text(
            (width // 2, prob_y), "Match Outcome Probability",
            fill=self.COLOR_TEXT, font=self.font_medium, anchor="mm",
        )

        bar_width = 700
        bar_height = 32
        bar_x = (width - bar_width) // 2
        bar_y = prob_y + 35

        home_color, away_color = get_team_colors_for_fixture(home, away)

        self._draw_outcome_bar(
            draw,
            x=bar_x,
            y=bar_y,
            width=bar_width,
            height=bar_height,
            home_pct=fixture["HomeWinProb"] * 100,
            draw_pct=fixture["DrawProb"] * 100,
            away_pct=fixture["AwayWinProb"] * 100,
            font=self.font_small,
            home_color=home_color,
            away_color=away_color,
        )

        # Footer
        draw.text(
            (width - 40, height - 35), self.brand_text,
            fill=self.COLOR_SUBTEXT, font=self.font_tiny, anchor="rm",
        )

        save_path = self.output_dir / filename
        card.save(save_path, dpi=(240, 240))

        logger.info(f"Match detail card saved: {save_path}")
        return str(save_path)