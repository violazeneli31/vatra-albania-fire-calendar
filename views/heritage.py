"""Heritage ("Albania corner"): timeline, UNESCO, motifs, myths of nature, heritage near fire, big fire years."""
from __future__ import annotations

from html import escape

import streamlit as st

import config as C
from src import data, motifs, ui
from src.i18n import num, t

theme, lang = ui.theme(), ui.lang()
cc = data.content("albania_corner.json")
ui.page_title("🏛️", t("heritage_title"), escape(t("heritage_sub")))

c1, c2 = st.columns(2, gap="medium")
with c1:
    items = "".join(
        f'<div class="ev">{motifs.rosette_svg(28)}<div class="v-small" style="color:var(--gold);font-weight:700">{escape(e["when_" + lang])}</div>'
        f'<b>{escape(e["title_" + lang])}</b><div class="v-small">{escape(e["text_" + lang])}</div>{ui.src_link(e["source"])}</div>'
        for e in cc["timeline"])
    ui.html(ui.card(f'<h3>{escape(t("timeline"))}</h3><div class="v-tl">{items}</div>', dia=True))
with c2:
    rows = "".join(f'<div class="v-dl"><div><b>{escape(u["name_" + lang])}</b><div class="v-small v-muted">{escape(u["kind_" + lang])}</div></div>'
                   f'<div style="text-align:right">{ui.src_link(u["source"], "UNESCO")}</div></div>' for u in cc["unesco"])
    ui.html(ui.card(f'<h3>{escape(t("unesco_title"))}</h3>{rows}<div class="v-src" style="margin-top:6px">{escape(t("unesco_note"))}</div>', dia=True))

ui.html(f'<h2>{escape(t("motifs_title"))}</h2>')
mot = [("zigzag", motifs.zigzag_svg(160)), ("diamond", '<div class="v-band" style="height:16px;background-size:24px 12px"></div>'),
       ("rosette", motifs.rosette_svg(60)), ("stitch", motifs.cross_stitch_row())]
ui.html('<div class="v-grid v-g4">' + "".join(
    f'<div class="v-card"><b>{escape(t("motif_" + k))}</b><div style="margin:10px 0;min-height:44px;display:flex;align-items:center;justify-content:center">{svg}</div>'
    f'<div class="v-small v-muted">{escape(t("motif_" + k + "_d"))}</div></div>' for k, svg in mot) + "</div>")
ui.html(f'<div class="v-src" style="margin-top:6px">{escape(t("motifs_note"))}</div>')

ui.html(f'<h2>{escape(t("myths_title"))}</h2>')
ui.html('<div class="v-grid v-g4">' + "".join(
    f'<div class="v-card v-dia"><b>{escape(m.get("icon", ""))} {escape(m["title_" + lang])}</b><div class="v-small">{escape(m["text_" + lang])}</div>'
    f'{ui.src_link(m["source"])}</div>' for m in cc["myths"]) + "</div>")

ui.html(f'<h2>{escape(t("heritage_fire_title"))}</h2>')
sites = data.content("heritage_sites.csv")
hn = data.csv("heritage_nearby.csv")
tot = hn.groupby("site_id")["fire_celldays_5km"].sum()
yrs = hn.groupby("site_id")["year"].nunique()
sel = sites[sites["type"] != "park"].copy()
sel["n"] = sel["site_id"].map(tot).fillna(0)
sel = sel.sort_values("n", ascending=False)
ui.html('<div class="v-grid v-g3">' + "".join(
    f'<div class="v-card"><div class="v-row" style="flex-wrap:nowrap">{motifs.rosette_svg(28)}<b class="v-cinzel">'
    f'{escape(r["name_" + lang])}</b></div><div class="v-small">{escape(r["story_" + lang])}</div>'
    f'<div class="v-small" style="margin-top:6px">🔥 <b>{num(r["n"])}</b> {escape(t("fires_within_5km"))} · '
    f'{escape(t("in_years", n=int(yrs.get(r["site_id"], 0))))}</div>{ui.src_link(r["source"])}</div>' for _, r in sel.iterrows()) + "</div>")

parks = sites[sites["type"] == "park"].copy()
parks["n"] = parks["site_id"].map(tot).fillna(0)
parks = parks.sort_values("n", ascending=False)
ui.html(f'<h2>{escape(t("parks_title"))}</h2>')
ui.html('<div class="v-grid v-g4">' + "".join(
    f'<div class="v-card v-small"><b>🌲 {escape(r["name_" + lang])}</b><br>{escape(r["story_" + lang])}<br>🔥 <b>{num(r["n"])}</b> '
    f'{escape(t("fires_within_5km"))}{ui.src_link(r["source"])}</div>' for _, r in parks.iterrows()) + "</div>")

ui.html(f'<h2>{escape(t("big_years_title"))}</h2>')
stories = data.js(f"stories_{lang}.json")
nat = data.area_monthly(("country", C.COUNTRY))
top = nat[(nat["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum().sort_values(ascending=False).head(4)
ui.html('<div class="v-grid v-g2">' + "".join(
    f'<div class="v-card v-dia"><b class="v-cinzel" style="font-size:1.2rem">{int(y)}</b><div class="v-small">{escape(stories["years"].get(str(int(y)), ""))}</div></div>'
    for y in top.index) + "</div>")
ui.html(f'<div class="v-src" style="margin-top:8px">{escape(t("facts_rule"))}</div>')
