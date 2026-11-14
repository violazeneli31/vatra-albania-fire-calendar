"""Home: "26 years of fire in Albania, in one calendar"."""
from __future__ import annotations

import random
from datetime import timedelta
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

import config as C
from src import api, charts, data, filters, motifs, ui
from src.i18n import fdate, month, num, pct, t
from src.theme import ramp_color

f = filters.get()
theme, lang = f["theme"], f["lang"]
hl = data.js("headline.json")
tt = data.area_monthly(f["key"], f["low"], f["dn"])
name = filters.area_full(f["area"])
det, cdl, info = api.latest()
end = info.get("end") or data.data_end()

# ------------------------------------------------------------------ 1 hero
left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")
with left:
    ui.html(f'<div class="v-kicker">NASA Space Apps 2026 · MODIS + VIIRS</div>'
            f'<h1 style="font-size:2.3rem;margin:.2rem 0 .4rem;line-height:1.15">{escape(t("home_title"))}</h1>'
            f'<p style="font-size:1.05rem">{escape(t("home_sub"))}</p>'
            f'<div class="v-headline"><div class="k">★ {escape(t("headline_finding"))}</div>'
            f'<div style="margin-top:4px">{escape(hl["short_" + lang])}</div></div>')
    summ = data.js("summary.json")
    facts = [(num(summ["detections_clean"]), t("fact_detections")), ("5", t("fact_satellites")),
             (num(summ["events"]), t("fact_events"))]
    ui.html('<div class="v-facts">' + "".join(f'<div><b>{v}</b><span>{escape(k)}</span></div>' for v, k in facts) + '</div>')
    b1, b2 = st.columns([1, 1], vertical_alignment="center")
    with b1:
        with st.container(key="cal_btn"):
            st.page_link(st.session_state["_pages"]["calendar"], label=t("see_full_calendar"), icon="📅")
    with b2:
        ui.html(f'<div class="v-small v-muted" style="margin-bottom:1rem;text-align:right">💬 {escape(t("ask_viola_hint"))}</div>')
with right:
    cd_all = data.celldays()
    since = pd.Timestamp(end - timedelta(days=365))
    pts = cd_all[(cd_all["date"] >= since) & ~cd_all["low_only"]].drop_duplicates("cell_id", keep="last").copy()
    if len(cdl):
        pts = pd.concat([pts, cdl.drop_duplicates("cell_id")], ignore_index=True)
    if len(pts):
        age = ((pd.Timestamp(end) - pts["date"]).dt.days / 365).clip(0, 1).to_numpy()
        pts["color"] = [ramp_color(.15 + .55 * a) for a in age]
        pts["label"] = [f"{fdate(d)} · {m}" for d, m in zip(pts["date"], pts["adm2"])]
    with st.container(key="hero_map"):
        st.plotly_chart(charts.outline_map(pts, theme, 400), config=charts.CFG_STATIC, theme=None, key="hero")
        ui.html(f'<div class="v-small" style="color:{C.GOLD};text-align:center;margin-top:-6px">{escape(t("hero_caption", n=num(len(pts)), end=fdate(end)))}</div>')
ui.html("""<style>.st-key-hero_map{background:#1b1515;border-radius:14px;padding:10px 10px 20px;border:1px solid #3a2f2f}</style>""")

# ------------------------------------------------------------------ 2 Albania now + 3 tiles
daily = data.area_daily(f["key"], f["low"], f["dn"]).copy()
if len(cdl):
    extra = cdl[data.mask(cdl, f["key"]) & (~cdl["low_only"] if not f["low"] else True)].groupby("date")["weight"].sum()
    daily = pd.concat([daily, extra]).groupby(level=0).sum()
w7 = data.window_compare(daily, end, 7)
w30 = data.window_compare(daily, end, 30)
sentence = t("now_" + {"below": "quiet", "normal": "normal", "above": "busy", "extreme": "extreme"}[w30["status"]],
             month=month(end.month, full=True).capitalize())
avail = (t("latest_unavailable", end=fdate(data.data_end())) if not info.get("end")
         else t("data_to", end=fdate(end)))

y0r, y1r = max(f["d0"].year, C.BASE_YEARS[0]), min(f["d1"].year, C.BASE_YEARS[1])
rng = data.in_range(tt, f["d0"], f["d1"])
total = rng["harmonized"].sum()
yt = tt[(tt["year"] >= y0r) & (tt["year"] <= y1r)].groupby("year")["harmonized"].sum()
n = data.normals_for(tt)
tr = data.trend_for(tt)
arrow = {"up": "↗", "down": "↘"}.get(tr.get("direction"), "→")

worst = (str(int(yt.idxmax())), t("tile_cd", v=num(yt.max()))) if len(yt) and yt.max() > 0 else ("–", "")
mm = int(n.sort_values(["median", "mean"], ascending=False)["month"].iloc[0]) if n["mean"].sum() > 0 else None
now_card = ui.card(
    f'<h3>🔥 {escape(t("albania_now"))} · {escape(name)}</h3>'
    f'<div class="v-row">{ui.badge(w30["status"])}<span class="v-small v-muted">{escape(t("last_30_days"))}</span></div>'
    f'<p style="margin:.55em 0">{escape(sentence)}</p>'
    f'<div class="v-row v-small"><div><b>{escape(t("days7"))}:</b> {num(w7["value"], digits=1)} ({escape(t("normal_short"))} {num(w7["median"], digits=1)})</div>'
    f'<div><b>{escape(t("days30"))}:</b> {num(w30["value"], digits=1)} ({escape(t("normal_short"))} {num(w30["median"], digits=1)})</div></div>'
    f'<div class="v-src" style="margin-top:6px">{escape(t("percentile"))} {num(w30["percentile"])} · {escape(avail)} · {escape(t("not_official"))}</div>',
    dia=True)
tiles = [
    ui.tile(t("tile_total", y0=f["d0"].year, y1=f["d1"].year), num(total), escape(t("unit_celldays"))),
    ui.tile(t("tile_worst_year"), worst[0], escape(worst[1])),
    ui.tile(t("tile_worst_month"), escape(month(mm, full=True)) if mm else "–",
            escape(t("tile_median", v=num(n["median"].max(), digits=1))) if mm else ""),
    ui.tile(t("tile_trend"), f'{arrow} {pct(tr["pct_per_year"], digits=1) if tr.get("pct_per_year") is not None else "–"}',
            escape(t("per_year") + " · " + (t("significant") if tr.get("direction") in ("up", "down") else t("not_significant"))
                   + (f" (p = {num(tr['p'], digits=2)})" if tr.get("p") is not None else ""))),
]
ui.html(f'<div class="v-nowrow">{now_card}<div class="v-grid v-g4 v-tiles">{"".join(tiles)}</div></div>')

# ------------------------------------------------------------------ 4 mini calendar
with st.container(key="card_minical"):
    ui.html(f'<h3 style="margin:0">📅 {escape(t("nav_calendar"))} · {end.year - 4}–{end.year} · {escape(name)}</h3>')
    fig = charts.heatmap(tt, f["mode"], "act", end.year - 4, end.year, data.first_date(), end, theme, height=230, marks=False, scale=False)
    st.plotly_chart(fig, config=charts.CFG_STATIC, theme=None, key="minical")
    ui.html(ui.legend_ramp())

# ------------------------------------------------------------------ 5 explore your region (compact; full cards on Regions)
ui.html(f'<h2>🏔️ {escape(t("explore_region"))}</h2>')


def _go_county():
    v = st.session_state.get("home_cty")
    if v:
        filters.set_area("adm1", v)
        st.session_state["_go_regions"] = True
        st.session_state["home_cty"] = None


st.pills(t("pick_county"), data.counties(), key="home_cty", on_change=_go_county, label_visibility="collapsed")
if st.session_state.pop("_go_regions", False):
    st.switch_page(st.session_state["_pages"]["regions"])

# ------------------------------------------------------------------ 6 entrances
e1, e2 = st.columns(2, gap="medium")
with e1:
    ui.html(f'<div class="v-card" style="background:linear-gradient(135deg,#A61E26,#5a0f14);border:0;color:#fff">'
            f'<div class="v-row" style="flex-wrap:nowrap">{motifs.rosette_svg(60, C.GOLD, "#fff")}<div>'
            f'<div class="v-cinzel v-white" style="font-size:1.35rem">📖 {escape(t("read_story"))}</div>'
            f'<div class="v-white" style="opacity:.85">{escape(t("story_teaser"))}</div></div></div></div>')
    st.page_link(st.session_state["_pages"]["story"], label=t("open_story"), icon="📖")
with e2:
    ui.html(f'<div class="v-card" style="background:linear-gradient(135deg,#FFD166,#F4A259,#7BD389);border:0">'
            f'<div class="v-row" style="flex-wrap:nowrap">{motifs.satellite("vee", 70)}<div>'
            f'<div style="font-size:1.35rem;font-weight:800;color:#2a1500">🎮 {escape(t("kids_entry"))}</div>'
            f'<div style="color:#2a1500">{escape(t("kids_teaser"))}</div></div></div></div>')
    st.page_link(st.session_state["_pages"]["kids"], label=t("play_now"), icon="🎮")

# ------------------------------------------------------------------ 7 who can use VATRA
who = [t(k) for k in ["who_civil", "who_mun", "who_parks", "who_farm", "who_schools", "who_research"]]
ui.html(ui.card(f'<h3>👥 {escape(t("who_title"))}</h3><div class="v-grid v-g3 v-small">' +
                "".join(f"<div>{escape(w)}</div>" for w in who) +
                f'</div><div class="v-src" style="margin-top:6px">{escape(t("who_note"))}</div>', style="margin-top:14px"))

# ------------------------------------------------------------------ 8 did you know
cards = data.content("albania_corner.json")["cards"]
if "dyk_i" not in st.session_state:
    st.session_state["dyk_i"] = random.randrange(len(cards))
c = cards[st.session_state["dyk_i"] % len(cards)]
ui.html(ui.card(f'<div class="v-row" style="flex-wrap:nowrap">{motifs.rosette_svg(36)}<div><b>{escape(t("did_you_know"))}</b> '
                f'{escape(c["text_" + lang])}{ui.src_link(c.get("source", ""))}</div></div>', style="margin-top:14px"))
