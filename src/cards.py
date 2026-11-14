"""Fire-season card, PNG 1080 x 1350 (Pillow): area name + landmark, monthly bars, season dates, app link."""
from __future__ import annotations

import io

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

import config as C
from src import data, stats
from src.i18n import month, months, t
from src.report import fonts
from src.theme import ramp_color

W, H = 1080, 1350


def _font(kind, size):
    try:
        return ImageFont.truetype(fonts()[kind], size)
    except Exception:
        return ImageFont.load_default()


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rosette(d: ImageDraw.ImageDraw, cx, cy, r, c1=C.GOLD, c2="#FFFFFF"):
    import math
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_hex(c1), width=max(2, int(r * .08)))
    for i in range(12):
        a = i * math.pi / 6
        pts = [(cx, cy)]
        for aa in np.linspace(a - .22, a + .22, 7):
            rr = r * (.85 + .13 * math.cos((aa - a) / .22 * math.pi / 2))
            pts.append((cx + rr * math.cos(aa), cy + rr * math.sin(aa)))
        d.polygon(pts, fill=_hex(c1 if i % 2 else c2))
    d.ellipse([cx - r * .32, cy - r * .32, cx + r * .32, cy + r * .32], fill=_hex(c2), outline=_hex(c1), width=3)


@st.cache_data(show_spinner=False, max_entries=48)
def make_cached(key, name, county, lang) -> bytes:
    return make(key, name, county, lang)


def make(key, name, county, lang="en") -> bytes:
    tt = data.area_monthly(key)
    n = stats.month_normals(tt, "harmonized")
    s = stats.seasons(n)
    vals = n["median"].where(n["median"] > 0, n["mean"]).to_numpy()
    img = Image.new("RGB", (W, H), _hex("#FAF7F2"))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 250], fill=_hex(C.RED))
    for x in range(0, W, 30):
        d.polygon([(x, 250), (x + 30, 250), (x + 15, 276)], fill=_hex(C.GOLD))
    rosette(d, 120, 125, 70)
    d.text((220, 62), name, font=_font("title", 74 if len(name) < 14 else 56), fill="white")
    d.text((224, 160), t("card_tag", lang), font=_font("reg", 34), fill="white")
    # bars
    y0, bar_h = 320, 56
    mx = max(vals.max(), 1e-9)
    for i, m in enumerate(months(lang)):
        y = y0 + i * (bar_h + 10)
        d.text((60, y + 12), m, font=_font("bold", 32), fill=_hex("#1E1816"))
        w = int(40 + (W - 330) * (vals[i] / mx))
        d.rounded_rectangle([150, y, 150 + w, y + bar_h], radius=12, fill=_hex(ramp_color(.08 + .85 * (vals[i] / mx) ** .6)))
        if s.get("season_months") and (i + 1) in s["season_months"]:
            d.text((150 + w + 14, y + 14), "🔥" if False else "●", font=_font("bold", 28), fill=_hex(C.RED))
    yb = y0 + 12 * (bar_h + 10) + 10
    if s.get("peak"):
        txt = t("card_season", lang, start=month(s["start"], lang, True), end=month(s["end"], lang, True), peak=month(s["peak"], lang, True))
    else:
        txt = t("card_little", lang)
    d.text((60, yb), txt, font=_font("bold", 34), fill=_hex("#1E1816"))
    d.text((60, yb + 52), t("card_note", lang), font=_font("reg", 26), fill=_hex("#6E6560"))
    # footer band
    d.rectangle([0, H - 90, W, H], fill=_hex("#1E1816"))
    for x in range(10, W, 36):
        d.polygon([(x, H - 90 - 12), (x + 18, H - 90), (x, H - 90 + 12), (x - 18, H - 90)], fill=_hex(C.RED))
    d.text((60, H - 62), f"VATRA · {C.APP_URL.replace('https://', '')} · NASA FIRMS", font=_font("reg", 30), fill=_hex(C.GOLD))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
