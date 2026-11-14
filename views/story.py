"""Story: "26 years of fire in Albania", nine short chapters built from the real numbers."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import config as C
from src import charts, data, motifs, ui
from src.i18n import month, num, pct, t

theme, lang = ui.theme(), ui.lang()
hl = data.js("headline.json")
stories = data.js(f"stories_{lang}.json")
nat = data.area_monthly(("country", C.COUNTRY))
seas = data.seasons_for(("country", C.COUNTRY))
yt = nat[(nat["year"] >= C.BASE_YEARS[0]) & (nat["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum()
top3 = yt.sort_values(ascending=False).head(3)
m = data.monthly()
cty = m[(m["area_level"] == "adm1") & (m["year"] <= C.BASE_YEARS[1])].groupby("area_name")["harmonized"].sum().sort_values(ascending=False)
mun = m[(m["area_level"] == "adm2") & (m["year"] <= C.BASE_YEARS[1])].groupby("area_name")["harmonized"].sum().sort_values(ascending=False)
v = data.js("validation.json")["national"]["test"]
photo = ui.img_uri("viola_circle_dark.png" if theme == "dark" else "viola_circle_light.png")

ui.html(f'<div style="text-align:center;padding:14px 0 4px">{motifs.rosette_svg(70)}'
        f'<h1 style="font-size:2.4rem;margin:.3rem 0">{escape(t("story_title"))}</h1>'
        f'<div class="v-row" style="justify-content:center;margin-bottom:22px"><span class="v-muted">{escape(t("story_by"))}</span></div></div>')


def chapter(i: int, title: str, text: str, visual, last: bool = False):
    a, b = st.columns([1, 1.2], gap="large", vertical_alignment="center")
    with a:
        ui.html(f'<div class="v-row" style="flex-wrap:nowrap">{motifs.rosette_svg(46, label=str(i))}'
                f'<h2 style="margin:0;padding:0">{escape(title)}</h2></div><p style="font-size:1.02rem;margin-top:.6rem">{escape(text)}</p>')
        ui.listen(f"{title}. {text}", f"story_{i}")
    with b:
        with st.container(key=f"card_story_{i}"):
            visual()
    if not last:
        ui.html('<div class="v-band" style="margin:14px 0 6px;opacity:.5"></div>')


def _rosette():
    ui.html(f'<div style="text-align:center">{motifs.rosette_svg(150)}</div>')


def _pixels():
    sq = "".join(f'<rect x="{150 + i * 27}" y="{20 + j * 27}" width="25" height="25" fill="{"#E08A3C" if (i + j) % 2 else "#F1CC7A"}" stroke="#A61E26"/>'
                 for i in range(3) for j in range(3))
    ui.html(f'<svg viewBox="0 0 260 125" width="100%" style="max-width:320px;display:block;margin:0 auto"><rect x="20" y="20" width="80" height="80" fill="#F1CC7A" stroke="#A61E26"/>'
            f'<text x="60" y="118" text-anchor="middle" font-size="11" fill="currentColor">MODIS · 1 km</text>{sq}'
            f'<text x="190" y="118" text-anchor="middle" font-size="11" fill="currentColor">VIIRS · 375 m</text></svg>'
            f'<div class="v-row" style="justify-content:center">{motifs.satellite("mo", 90)}{motifs.satellite("vee", 90)}</div>')


chapter(1, t("ch1_t"), t("ch1"), _rosette)
chapter(2, t("ch2_t"), t("ch2"), _pixels)
chapter(3, t("ch3_t"), t("ch3", raw=pct(hl["raw_change_pct"]), v12=num(hl["raw_viirs_2012"]), m11=num(hl["raw_modis_2011"])),
        lambda: st.plotly_chart(charts.raw_vs_harmonized(nat, theme, 240, harmonized=False), config=charts.CFG_STATIC, theme=None, key="s3"))
chapter(4, t("ch4_t"), t("ch4", harm=pct(hl["harm_change_pct"]), r=num(v["pearson"], digits=2)),
        lambda: st.plotly_chart(charts.raw_vs_harmonized(nat, theme, 240), config=charts.CFG_STATIC, theme=None, key="s4"))
n_i = 5
if seas.get("two_seasons"):
    chapter(n_i, t("ch5_t"), t("ch5", p2=month(seas["second_peak"], full=True), p1=month(seas["peak"], full=True)),
            lambda: st.plotly_chart(charts.profile(nat, None, None, theme, 260), config=charts.CFG_STATIC, theme=None, key="s5"))
    n_i += 1


def _hard():
    cd = data.celldays()
    cols = st.columns(3)
    for col, (y, val) in zip(cols, top3.items()):
        pts = cd[(cd["year"] == y) & ~cd["low_only"]].drop_duplicates("cell_id").copy()
        pts["color"] = "#F1CC7A"
        with col:
            st.plotly_chart(charts.outline_map(pts, theme, 200, labels=False, glow=False), config=charts.CFG_STATIC, theme=None, key=f"s6_{y}")
            ui.html(f'<div style="text-align:center"><b class="v-cinzel">{int(y)}</b><div class="v-small">{num(val)} {escape(t("unit_celldays_short"))}</div></div>')


ys = [str(int(y)) for y in top3.index]
chapter(n_i, t("ch6_t"), t("ch6", y1=ys[0], y2=ys[1], y3=ys[2], s1=stories["years"].get(ys[0], "")), _hard)
n_i += 1
chapter(n_i, t("ch7_t"), t("ch7", c1=cty.index[0], c2=cty.index[1], c3=cty.index[2], m1=mun.index[0], m2=mun.index[1],
                          share=num(100 * cty.iloc[:3].sum() / cty.sum())),
        lambda: st.plotly_chart(charts.ranking(list(cty.index), list(cty.values), theme, 260), config=charts.CFG_STATIC, theme=None, key="s7"))
n_i += 1
chapter(n_i, t("ch8_t"), t("ch8"),
        lambda: st.plotly_chart(charts.modis_off(nat, 2020, theme, 240), config=charts.CFG_STATIC, theme=None, key="s8"))
n_i += 1


def _act():
    st.page_link(st.session_state["_pages"]["calendar"], label=t("open_calendar"), icon="📅")
    st.page_link(st.session_state["_pages"]["downloads"], label=t("nav_downloads"), icon="⬇️")
    st.page_link(st.session_state["_pages"]["kids"], label=t("play_now"), icon="🎮")
    ui.html(f'<div class="v-small" style="margin-top:6px">🧯 {escape(t("safety_1"))}<br>👀 {escape(t("safety_2"))}</div>')


chapter(n_i, t("ch9_t"), t("ch9"), _act, last=True)
