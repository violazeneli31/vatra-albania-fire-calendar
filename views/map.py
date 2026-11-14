"""Map: every fire detection, borders, EFFIS burnt areas, heritage, parks; draw your own area."""
from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import config as C
from src import api, data, filters, mapview, ui
from src.i18n import month, num, t

ss = st.session_state
if "map_month" in ss:  # coming from the calendar's month window
    y, m = ss.pop("map_month")
    filters.set_dates(date(y, m, 1), (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).date(), None)
    st.rerun()

f = filters.get()
theme = f["theme"]
ui.page_title("🗺️", t("map_title"), escape(t("map_sub")))

LAYERS = ["fires", "counties", "municipalities", "effis", "heritage", "parks"]
c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
with c1:
    layers = st.pills(t("layers"), LAYERS, selection_mode="multi", default=["fires", "counties"],
                      format_func=lambda k: t("layer_" + k), key="map_layers")
with c2:
    mon = st.select_slider(t("month_slider"), options=[0] + list(range(1, 13)), value=0, key="map_month_slider",
                           format_func=lambda x: t("all_dates") if x == 0 else month(x))

fr = data.area_fires(f["key"], f["low"], f["dn"])
fr = fr[(fr["date"] >= pd.Timestamp(f["d0"])) & (fr["date"] <= pd.Timestamp(f["d1"]))]
det, cdl, info = api.latest()
if len(det):
    d2 = det[data.mask(det, f["key"])]
    d2 = d2[(d2["date"] >= pd.Timestamp(f["d0"])) & (d2["date"] <= pd.Timestamp(f["d1"]))]
    if not f["low"]:
        d2 = d2[d2["confidence"] != "low"]
    fr = pd.concat([fr, d2], ignore_index=True)
if mon:
    fr = fr[fr["date"].dt.month == mon]
if f["mode"] == "m":
    fr = fr[fr["sensor"] == "MODIS"]
elif f["mode"] == "v":
    fr = fr[fr["sensor"] == "VIIRS"]

a = f["area"]
bounds = None
if a["level"] in ("adm1", "adm2"):
    ar = data.areas()
    r = ar[(ar["level"] == a["level"]) & (ar["name"] == a["name"])]
    if len(r):
        bounds = r["bounds"].iloc[0]
elif a["level"] == "circle":
    dlat = a["r_km"] / 111.0
    dlon = dlat / 0.75
    bounds = [a["lon"] - dlon, a["lat"] - dlat, a["lon"] + dlon, a["lat"] + dlat]
elif a["level"] == "polygon":
    xs, ys = zip(*a["coords"])
    bounds = [min(xs), min(ys), max(xs), max(ys)]


@st.fragment
def map_fragment():
    m = mapview.build(fr, theme, layers or [], a, bounds, f["d0"], f["d1"])
    out = st_folium(m, height=600, use_container_width=True, returned_objects=["last_active_drawing"], key="folium_map")
    drawing = (out or {}).get("last_active_drawing")
    info_l, btn = st.columns([3, 1.2], vertical_alignment="center")
    capped = len(fr) > C.MAP_POINT_CAP
    msg = t("map_count", n=num(len(fr))) + " · " + (t("map_capped", cap=num(C.MAP_POINT_CAP)) if capped else t("map_legend"))
    ui.html_in(info_l, f'<div class="v-small">{escape(msg)}</div>')
    if drawing and drawing.get("geometry", {}).get("type") == "Polygon":
        coords = [tuple(p) for p in drawing["geometry"]["coordinates"][0]]
        if btn.button(t("use_drawn_area"), type="primary", icon="✏️", use_container_width=True):
            filters.set_area("polygon", "drawn", coords=coords)
            st.rerun()
    else:
        ui.html_in(btn, f'<div class="v-small v-muted">{escape(t("draw_hint"))}</div>')


map_fragment()
if info.get("status") in ("ok", "partial") and len(det):
    ui.html(f'<div class="v-src">{escape(t("map_api_note"))}</div>')
