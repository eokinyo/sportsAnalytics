from __future__ import annotations

import os
import unicodedata
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W   = 1080
CARD_H   = 1080
BG       = (255, 255, 255)
DARK     = ( 25,  25,  35)
ACCENT   = ( 30,  50, 120)
MID_GRAY = ( 90,  92, 105)
LT_GRAY  = (210, 212, 220)
GREEN    = ( 25, 130,  55)
RED      = (190,  35,  35)
AMBER    = (180, 130,   0)
GOLD     = (160, 120,  10)
DIVIDER  = (220, 222, 228)
COL_BG   = (245, 246, 250)


def _font(size: int, bold: bool = False):
    candidates = (
        ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
        else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
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
    norm = _normalize(team).replace("'", "").replace(" ", "_").lower()
    for fname in os.listdir(logo_dir):
        stem = _normalize(Path(fname).stem).replace("'", "").replace(" ", "_").lower()
        if stem == norm:
            try:
                img = Image.open(os.path.join(logo_dir, fname)).convert("RGBA")
                img.thumbnail((68, 68), Image.LANCZOS)
                return img
            except Exception:
                return None
    return None


def _paste_logo(canvas, logo, cx, cy):
    if logo is None:
        return
    x = cx - logo.width  // 2
    y = cy - logo.height // 2
    canvas.paste(logo, (x, y), logo)


def _signed(val: float) -> str:
    return f"+{val}" if val > 0 else str(val)


def _diff_color(val: float) -> tuple:
    if val > 0.1:  return RED
    if val < -0.1: return GREEN
    return MID_GRAY


def _draw_team_panel(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    stats: dict,
    ref_avg: dict,
    logo_dir: str,
    x: int,
    y: int,
    w: int,
    h: int,
):
    team  = stats["Team"]
    games = stats["Games"]

    # Panel background + border
    draw.rectangle([(x, y), (x + w, y + h)], fill=COL_BG, outline=LT_GRAY, width=1)

    # ── Logo + name ───────────────────────────────────────────────────────────
    logo    = _get_logo(logo_dir, team)
    logo_cy = y + 46
    if logo:
        _paste_logo(canvas, logo, x + w // 2, logo_cy)

    name_y = logo_cy + 44
    draw.text((x + w // 2, name_y),
              team, font=_font(19, bold=True), fill=DARK, anchor="mm")

    games_y = name_y + 20
    draw.text((x + w // 2, games_y),
              f"{games} game{'s' if games != 1 else ''} together",
              font=_font(12), fill=MID_GRAY, anchor="mm")

    if games == 0:
        draw.text((x + w // 2, y + h // 2),
                  "No data available", font=_font(14), fill=MID_GRAY, anchor="mm")
        return

    # ── Results section ───────────────────────────────────────────────────────
    sec_y = games_y + 20
    draw.line([(x + 10, sec_y), (x + w - 10, sec_y)], fill=DIVIDER, width=1)

    draw.text((x + w // 2, sec_y + 14),
              "RESULTS", font=_font(11, bold=True), fill=ACCENT, anchor="mm")

    result_y = sec_y + 36
    col_w    = w // 4
    for i, (label, val, color) in enumerate([
        ("W",   stats["Wins"],   GREEN),
        ("D",   stats["Draws"],  AMBER),
        ("L",   stats["Losses"], RED),
        ("Pts", stats["Points"], DARK),
    ]):
        cx = x + col_w * i + col_w // 2
        draw.text((cx, result_y),      str(val), font=_font(22, bold=True), fill=color,    anchor="mm")
        draw.text((cx, result_y + 20), label,    font=_font(11),            fill=MID_GRAY, anchor="mm")

    ppm_y = result_y + 44
    draw.text((x + w // 2, ppm_y),
              f"{stats['PPM']} pts / game",
              font=_font(12, bold=True), fill=ACCENT, anchor="mm")

    # ── Discipline section ────────────────────────────────────────────────────
    disc_y = ppm_y + 22
    draw.line([(x + 10, disc_y), (x + w - 10, disc_y)], fill=DIVIDER, width=1)

    draw.text((x + w // 2, disc_y + 14),
              "DISCIPLINE", font=_font(11, bold=True), fill=ACCENT, anchor="mm")

    metrics = [
        ("Yellows / Game", stats["YellowsPerGame"], stats["YellowVsAvg"]),
        ("Reds / Game",    stats["RedsPerGame"],    stats["RedVsAvg"]),
        ("Fouls / Game",   stats["FoulsPerGame"],   None),
        ("Cards / Game",   stats["CardsPerGame"],   stats["CardVsAvg"]),
    ]

    m_y = disc_y + 34
    for label, val, diff in metrics:
        draw.text((x + 14,     m_y), label,    font=_font(12),             fill=MID_GRAY, anchor="lm")
        draw.text((x + w - 14, m_y), str(val), font=_font(13, bold=True),  fill=DARK,     anchor="rm")
        if diff is not None:
            draw.text((x + w - 14, m_y + 15),
                      f"vs avg {_signed(diff)}",
                      font=_font(11), fill=_diff_color(diff), anchor="rm")
            m_y += 46
        else:
            m_y += 34


def create_referee_report_card(
    profile: dict,
    logo_dir: str,
    output_path: str,
    league_name: str    = "Premier League",
    as_of_date: str     = "",
    twitter_handle: str = "@e_okinyo",
) -> str:
    canvas = Image.new("RGB", (CARD_W, CARD_H), BG)
    draw   = ImageDraw.Draw(canvas)

    referee    = profile["referee"]
    ref_avg    = profile["referee_avg"]
    home_stats = profile["home_team"]
    away_stats = profile["away_team"]
    date_str   = as_of_date or datetime.now().strftime("%d %B %Y")

    # ── Header ────────────────────────────────────────────────────────────────
    draw.text((CARD_W // 2, 44),
              "Referee Report",
              font=_font(38, bold=True), fill=DARK, anchor="mm")
    draw.text((CARD_W // 2, 86),
              referee,
              font=_font(26, bold=True), fill=ACCENT, anchor="mm")
    draw.text((CARD_W // 2, 118),
              f"{league_name}  ·  Historical trends  ·  As of {date_str}",
              font=_font(14), fill=MID_GRAY, anchor="mm")
    draw.line([(48, 138), (CARD_W - 48, 138)], fill=ACCENT, width=2)

    # ── Referee overall averages ───────────────────────────────────────────────
    avg_y = 148
    draw.text((CARD_W // 2, avg_y + 12),
              f"Overall averages across {ref_avg['Games']} games officiated",
              font=_font(13, bold=True), fill=MID_GRAY, anchor="mm")

    avg_items = [
        ("Cards / Game",   ref_avg["CardsPerGame"]),
        ("Yellows / Game", ref_avg["YellowsPerGame"]),
        ("Reds / Game",    ref_avg["RedsPerGame"]),
        ("Fouls / Game",   ref_avg["FoulsPerGame"]),
    ]
    col_w = CARD_W // len(avg_items)
    for i, (label, val) in enumerate(avg_items):
        cx = i * col_w + col_w // 2
        draw.text((cx, avg_y + 40), str(val), font=_font(22, bold=True), fill=ACCENT,   anchor="mm")
        draw.text((cx, avg_y + 62), label,    font=_font(12),            fill=MID_GRAY, anchor="mm")

    draw.line([(48, avg_y + 80), (CARD_W - 48, avg_y + 80)], fill=DIVIDER, width=1)

    # ── Team panels ───────────────────────────────────────────────────────────
    panel_top = avg_y + 94
    panel_h   = 530
    gap       = 24
    pad       = 32
    panel_w   = (CARD_W - pad * 2 - gap) // 2
    left_x    = pad
    right_x   = pad + panel_w + gap

    _draw_team_panel(draw, canvas, home_stats, ref_avg, logo_dir,
                     left_x, panel_top, panel_w, panel_h)
    _draw_team_panel(draw, canvas, away_stats, ref_avg, logo_dir,
                     right_x, panel_top, panel_w, panel_h)

    # VS label between panels
    vs_cx = CARD_W // 2
    vs_cy = panel_top + panel_h // 2
    draw.text((vs_cx, vs_cy), "VS", font=_font(22, bold=True), fill=LT_GRAY, anchor="mm")

    # ── Context note ──────────────────────────────────────────────────────────
    note_y = panel_top + panel_h + 14
    draw.text((CARD_W // 2, note_y),
              "vs avg = difference from this referee's overall average  ·  "
              "Trends only — small samples may limit significance",
              font=_font(11), fill=LT_GRAY, anchor="mm")

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = CARD_H - 52
    draw.line([(0, footer_y), (CARD_W, footer_y)], fill=LT_GRAY, width=1)
    draw.text((56, footer_y + 26),
              "Stats · Predictions · Analysis",
              font=_font(14), fill=MID_GRAY, anchor="lm")
    draw.text((CARD_W - 56, footer_y + 26),
              f"For more stats, follow {twitter_handle}",
              font=_font(14, bold=True), fill=GOLD, anchor="rm")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, "PNG")
    return output_path