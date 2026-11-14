"""A3 embroidery poster: 'Vatra: 26 years of Albanian fire, stitched' drawn with fpdf2 (real vector stitches)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import config as C
from src import data
from src.i18n import months, t
from src.motifs import STITCH_COLORS, stitch_classes
from src.report import Doc, _rgb


@st.cache_data(show_spinner=False, max_entries=24)
def make_cached(key, area_name, y0, y1, mode, lang, low, dn, d0, d1) -> bytes:
    return make(key, area_name, y0, y1, mode, lang, low, dn, d0, d1)


def make(key, area_name, y0, y1, mode="h", lang="en", low=False, dn="both", d0=None, d1=None) -> bytes:
    tt = data.area_monthly(key, low, dn)
    col = data.value_col(mode)
    years = list(range(y0, y1 + 1))
    sub = tt[(tt["year"] >= y0) & (tt["year"] <= y1)]
    ym = sub["year"] * 100 + sub["month"]
    s = data.summary()
    lo = max(int(s["first_month"].replace("-", "")), int(d0[:7].replace("-", "")) if d0 else 0)
    hi = min(int(s["last_month"].replace("-", "")), int(d1[:7].replace("-", "")) if d1 else 999999)
    ok = (ym >= lo) & (ym <= hi)
    grid = sub.assign(v=np.where(ok, sub[col], np.nan)).pivot(index="year", columns="month", values="v").reindex(index=years, columns=range(1, 13))
    k, q = stitch_classes(grid.to_numpy(float))

    pdf = Doc(lang, fmt="A3", footer_text=f"VATRA · {C.APP_URL} · NASA FIRMS")
    pdf.add_page()
    W, H = pdf.w, pdf.h
    # cloth
    pdf.set_fill_color(*_rgb("#F6EEDD"))
    pdf.rect(10, 10, W - 20, H - 26, "F")
    pdf.set_fill_color(*_rgb("#E4D6BA"))
    for x in np.arange(13, W - 12, 3.2):
        for y in np.arange(13, H - 18, 3.2):
            pdf.ellipse(x, y, .35, .35, "F")
    # diamond border
    def dia(cx, cy, r):
        pdf.set_fill_color(*_rgb(C.RED))
        pdf.polygon([(cx, cy - r), (cx + r * 1.4, cy), (cx, cy + r), (cx - r * 1.4, cy)], style="F")
        pdf.set_fill_color(*_rgb(C.BLACK))
        pdf.polygon([(cx, cy - r * .45), (cx + r * .63, cy), (cx, cy + r * .45), (cx - r * .63, cy)], style="F")
    x = 16
    while x < W - 14:
        dia(x, 16, 3)
        dia(x, H - 22, 3)
        x += 8.6
    y = 26
    while y < H - 28:
        dia(16, y, 3)
        dia(W - 16, y, 3)
        y += 8.6
    # title
    pdf.set_text_color(*_rgb(C.RED))
    pdf.set_font("Cinzel", "", 30)
    pdf.set_xy(24, 28)
    pdf.cell(W - 48, 14, t("r_poster_title", lang), align="C")
    pdf.set_font("Inter", "", 12)
    pdf.set_text_color(*_rgb("#6E6560"))
    pdf.set_xy(24, 43)
    pdf.cell(W - 48, 7, f"{area_name} · {y0}–{y1} · " + (t("unit_celldays", lang) if mode == "h" else t("unit_hotspots", lang)), align="C")
    # grid
    L, T = 50, 64
    cw = (W - L - 34) / 12
    ch = min(9.5, (H - T - 60) / max(len(years), 1))
    pdf.set_font("Cinzel", "", 11)
    pdf.set_text_color(*_rgb(C.BLACK))
    for i, m in enumerate(months(lang)):
        pdf.set_xy(L + i * cw, T - 9)
        pdf.cell(cw, 6, m.upper(), align="C")
    for r, yv in enumerate(years):
        cy = T + r * ch + ch / 2
        pdf.set_xy(L - 22, cy - 3)
        pdf.cell(18, 6, str(yv), align="R")
        for m in range(12):
            kk = int(k[r, m])
            cx = L + m * cw + cw / 2
            if kk <= 0:
                if kk == 0:
                    pdf.set_fill_color(*_rgb("#D9C9A8"))
                    pdf.ellipse(cx - .4, cy - .4, .8, .8, "F")
                continue
            sz = .9 + kk * .55
            pdf.set_draw_color(*_rgb(STITCH_COLORS[kk]))
            pdf.set_line_width(.25 + kk * .22)
            pdf.line(cx - sz, cy - sz, cx + sz, cy + sz)
            pdf.line(cx + sz, cy - sz, cx - sz, cy + sz)
    # legend
    ly = T + len(years) * ch + 10
    pdf.set_font("Inter", "", 10)
    pdf.set_text_color(*_rgb("#6E6560"))
    pdf.set_xy(L, ly)
    pdf.cell(40, 6, t("r_poster_key", lang))
    for kk in range(1, 6):
        cx = L + 48 + (kk - 1) * 26
        sz = .9 + kk * .55
        pdf.set_draw_color(*_rgb(STITCH_COLORS[kk]))
        pdf.set_line_width(.25 + kk * .22)
        pdf.line(cx - sz, ly + 3 - sz, cx + sz, ly + 3 + sz)
        pdf.line(cx + sz, ly + 3 - sz, cx - sz, ly + 3 + sz)
        lab = f"> {q[kk - 2]:.0f}" if kk >= 2 and q else "> 0"
        pdf.set_xy(cx + 4, ly)
        pdf.cell(18, 6, lab)
    pdf.set_xy(24, ly + 10)
    pdf.multi_cell(W - 48, 5, t("r_poster_note", lang), align="C", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
