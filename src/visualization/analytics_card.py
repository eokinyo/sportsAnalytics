from __future__ import annotations

import os
import unicodedata
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W      = 1080
BG_COLOR    = (255, 255, 255)
DARK        = ( 30,  30,  40)
MID_GRAY    = ( 90,  92, 105)
LIGHT_GRAY  = (210, 212, 220)
ACCENT      = ( 30,  50, 120)
GOLD        = (160, 120,  10)
GREEN       = ( 25, 130,  55)
RED         = (190,  35,  35)
DIVIDER_COL = (200, 202, 210)

LOGO_SIZE   = 56
ROW_H       = 80
HEADER_H    = 178
FOOTER_H    = 52
TOP_N       = 5
BOT_N       = 3


def _font(size: int, bold: bool = False):
    candidates = (
        ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["arial.ttf",   "Arial.ttf",      "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _normalize(name: str) -> str:
    return unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()


def _get_logo(logo_dir: str, team: str) -> Image.Image | None:
    if not logo_dir or not os.path.isdir(logo_dir):
        return None
    norm_team = _normalize(team).replace("'", "").replace(" ", "_").lower()
    for fname in os.listdir(logo_dir):
        stem = _normalize(Path(fname).stem).replace("'", "").replace(" ", "_").lower()
        if stem == norm_team:
            try:
                img = Image.open(os.path.join(logo_dir, fname)).convert("RGBA")
                img.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
                return img
            except Exception:
                return None
    return None


def _paste_logo(canvas: Image.Image, logo: Image.Image | None, cx: int, cy: int):
    if logo is None:
        return
    x = cx - logo.width  // 2
    y = cy - logo.height // 2
    canvas.paste(logo, (x, y), logo)


def _draw_row(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    rank: int,
    team: str,
    values: list[tuple[str, str]],  # [(value, label), ...] — 1, 2, or 3 items
    y: int,
    logo_dir: str,
    is_top: bool,
    show_logo: bool = True,
):
    PAD         = 48
    value_color = GREEN if is_top else RED

    if rank % 2 == 0:
        draw.rectangle([(PAD, y), (CARD_W - PAD, y + ROW_H - 1)], fill=(245, 246, 250))

    draw.line([(PAD, y), (CARD_W - PAD, y)], fill=DIVIDER_COL, width=1)

    cy = y + ROW_H // 2

    # rank
    draw.text((PAD + 20, cy), str(rank), font=_font(15, bold=True), fill=ACCENT, anchor="mm")

    # logo
    logo    = _get_logo(logo_dir, team)
    logo_cx = PAD + 62
    if show_logo:
        if logo:
            _paste_logo(canvas, logo, logo_cx, cy)
        else:
            draw.ellipse(
                [(logo_cx - 22, cy - 22), (logo_cx + 22, cy + 22)],
                outline=LIGHT_GRAY, width=2,
            )

    # team name
    name_x = PAD + 108 if show_logo else PAD + 52
    draw.text((name_x, cy), team, font=_font(23, bold=True), fill=DARK, anchor="lm")

    # value columns — right-aligned, evenly spaced
    n        = len(values)
    col_w    = 160
    right_x  = CARD_W - PAD - 16

    for i, (val, lbl) in enumerate(reversed(values)):
        x      = right_x - i * col_w
        color  = value_color if i == 0 else MID_GRAY
        f_size = 26 if i == 0 else 22
        draw.text((x, cy - 11), val, font=_font(f_size, bold=True), fill=color,    anchor="rm")
        draw.text((x, cy + 13), lbl, font=_font(13,     bold=True), fill=DARK,     anchor="rm")


def create_analytics_card(
    df_ranked,
    columns: list[tuple[str, str]],  # [(col, label), ...] primary first
    card_title: str,
    subtitle: str,
    logo_dir: str,
    output_path: str,
    league_name: str     = "Premier League",
    season: str          = "",
    as_of_date: str      = "",
    matchday: int        = 0,
    total_matchdays: int = 0,
    divider_label: str   = "Struggling",
    top_n: int           = TOP_N,
    bot_n: int           = BOT_N,
    name_col: str        = "Team",
    show_logo: bool      = True,
    twitter_handle: str  = "@e_okinyo",
) -> str:
    top_rows = df_ranked.head(top_n).reset_index(drop=True)
    bot_rows = df_ranked.tail(bot_n).reset_index(drop=True)

    gap_h   = 32
    body_h  = (top_n + bot_n) * ROW_H + gap_h
    total_h = HEADER_H + body_h + FOOTER_H + 8

    canvas = Image.new("RGB", (CARD_W, total_h), BG_COLOR)
    draw   = ImageDraw.Draw(canvas)

    # ── Header ────────────────────────────────────────────────────────────────
    date_str = as_of_date or datetime.now().strftime("%d %B %Y")
    season_str = f"  ·  {season}" if season else ""
    md_str     = f"  ·  Matchday {matchday}/{total_matchdays}" if matchday and total_matchdays else ""

    draw.text((CARD_W // 2, 44),  card_title, font=_font(36, bold=True), fill=DARK,     anchor="mm")
    draw.text((CARD_W // 2, 82),  subtitle,   font=_font(17),            fill=MID_GRAY, anchor="mm")
    draw.text((CARD_W // 2, 112),
              f"{league_name}{season_str}{md_str}",
              font=_font(15, bold=True), fill=ACCENT, anchor="mm")
    draw.text((CARD_W // 2, 134),
              f"As of {date_str}",
              font=_font(14), fill=MID_GRAY, anchor="mm")

    draw.line([(48, 150), (CARD_W - 48, 150)], fill=ACCENT, width=2)

    # ── Column headers ────────────────────────────────────────────────────────
    col_w   = 160
    right_x = CARD_W - 48 - 16
    for i, (_, lbl) in enumerate(reversed(columns)):
        x = right_x - i * col_w
        draw.text((x, 164), lbl, font=_font(12, bold=True), fill=ACCENT, anchor="rm")

    # ── Top rows ──────────────────────────────────────────────────────────────
    y = HEADER_H
    for i, row in top_rows.iterrows():
        vals = [(str(row[col]), lbl) for col, lbl in columns]
        _draw_row(draw, canvas, rank=i + 1, team=row[name_col],
                  values=vals, y=y, logo_dir=logo_dir, is_top=True,
                  show_logo=show_logo)
        y += ROW_H

    # ── Divider ───────────────────────────────────────────────────────────────
    draw.line([(48, y + 4), (CARD_W - 48, y + 4)], fill=RED, width=1)
    draw.text((CARD_W // 2, y + 16), f"▼  {divider_label}  ▼",
              font=_font(12, bold=True), fill=RED, anchor="mm")
    y += gap_h

    # ── Bottom rows ───────────────────────────────────────────────────────────
    for i, row in bot_rows.iterrows():
        vals = [(str(row[col]), lbl) for col, lbl in columns]
        _draw_row(draw, canvas, rank=len(df_ranked) - bot_n + i + 1,
                  team=row[name_col], values=vals, y=y, logo_dir=logo_dir,
                  is_top=False, show_logo=show_logo)
        y += ROW_H

    draw.line([(48, y), (CARD_W - 48, y)], fill=DIVIDER_COL, width=1)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = total_h - FOOTER_H
    draw.line([(0, footer_y), (CARD_W, footer_y)], fill=LIGHT_GRAY, width=1)
    draw.text((56, footer_y + FOOTER_H // 2),
              "Stats · Predictions · Analysis",
              font=_font(14), fill=MID_GRAY, anchor="lm")
    draw.text((CARD_W - 56, footer_y + FOOTER_H // 2),
              f"For more stats, follow {twitter_handle}",
              font=_font(14, bold=True), fill=GOLD, anchor="rm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path


# ── Backwards-compatible wrapper ──────────────────────────────────────────────
def create_attacking_card(
    df_ranked,
    metric_col: str,
    metric_label: str,
    card_title: str,
    subtitle: str,
    logo_dir: str,
    output_path: str,
    league_name: str     = "Premier League",
    season: str          = "",
    as_of_date: str      = "",
    matchday: int        = 0,
    total_matchdays: int = 0,
    extra_col: str       = "",
    extra_label: str     = "",
    divider_label: str   = "Struggling",
    top_n: int           = TOP_N,
    bot_n: int           = BOT_N,
    twitter_handle: str  = "@e_okinyo",
) -> str:
    columns = [(metric_col, metric_label)]
    if extra_col:
        columns.append((extra_col, extra_label))

    return create_analytics_card(
        df_ranked       = df_ranked,
        columns         = columns,
        card_title      = card_title,
        subtitle        = subtitle,
        logo_dir        = logo_dir,
        output_path     = output_path,
        league_name     = league_name,
        season          = season,
        as_of_date      = as_of_date,
        matchday        = matchday,
        total_matchdays = total_matchdays,
        divider_label   = divider_label,
        top_n           = top_n,
        bot_n           = bot_n,
        twitter_handle  = twitter_handle,
    )