"""Folium map: fires (clustered, coloured by date, sized by FRP), borders, EFFIS, heritage, parks, drawing tools."""
from __future__ import annotations

import json
from html import escape

import folium
import numpy as np
import pandas as pd
from folium import plugins

import config as C
from src import data, motifs
from src.i18n import fdate, num, t
from src.theme import TILES, colors, ramp_color

FIRE_JS = """
function (row) {
  var m = L.circleMarker(new L.LatLng(row[0], row[1]),
    {radius: row[3], color: '#2A0B0E', weight: 0.6, fillColor: row[2], fillOpacity: 0.88});
  m.bindPopup(row[4], {maxWidth: 260});
  return m;
}"""


def _fire_popup(r) -> str:
    near = f"<br>{escape(t('nearest_site'))}: {escape(str(r.site))} ({num(r.site_km, digits=1)} km)" if r.site else ""
    return (f"<b>🔥 {escape(t('fire_detection'))}</b><br>{fdate(r.date)} · {r.time} UTC<br>{escape(t('satellite'))}: {escape(str(r.satellite))}"
            f" · {escape(t('confidence'))}: {escape(t('conf_' + str(r.confidence)))}<br>{escape(t('intensity'))}: "
            f"{num(r.frp, digits=1) if pd.notna(r.frp) else '–'} MW<br>{escape(t('municipality'))}: {escape(str(r.adm2))}"
            f" ({escape(str(r.adm1))}){near}")


def _sites():
    return data.content("heritage_sites.csv")


def _nearest(lat, lon):
    s = _sites()
    la, lo = np.radians(np.asarray(lat))[:, None], np.radians(np.asarray(lon))[:, None]
    sl, so = np.radians(s["lat"].to_numpy())[None, :], np.radians(s["lon"].to_numpy())[None, :]
    a = np.sin((sl - la) / 2) ** 2 + np.cos(la) * np.cos(sl) * np.sin((so - lo) / 2) ** 2
    d = 6371 * 2 * np.arcsin(np.sqrt(a))
    k = d.argmin(axis=1)
    name = s["name_sq" if st_lang() == "sq" else "name_en"].to_numpy()[k]
    return name, d[np.arange(len(k)), k]


def st_lang():
    import streamlit as st
    return st.session_state.get("lang", "en")


def build(points: pd.DataFrame, theme: str, layers: list[str], area: dict, bounds=None, d0=None, d1=None,
          height=600, draw=True):
    c = colors(theme)
    tiles, attr = TILES[theme]
    m = folium.Map(location=[41.15, 20.1], zoom_start=7, tiles=None, control_scale=True, prefer_canvas=True)
    folium.TileLayer(tiles=tiles, attr=attr, name="Esri World Imagery" if theme == "dark" else "Esri Light Gray",
                     control=False, max_zoom=18).add_to(m)

    # fires
    n = len(points)
    if "fires" in layers and n:
        if n <= C.MAP_POINT_CAP:
            p = points.copy()
            span = max((p["date"].max() - p["date"].min()).days, 1)
            rec = ((p["date"] - p["date"].min()).dt.days / span).to_numpy()
            p["color"] = [ramp_color(.25 + .6 * (1 - r)) for r in rec]  # recent = brighter (lighter)
            p["radius"] = np.clip(3 + np.sqrt(p["frp"].fillna(4).to_numpy()) * .55, 3, 11).round(1)
            p["site"], p["site_km"] = _nearest(p["lat"], p["lon"])
            p.loc[p["site_km"] > 10, "site"] = ""
            p["popup"] = [_fire_popup(r) for r in p.itertuples()]
            rows = p[["lat", "lon", "color", "radius", "popup"]].values.tolist()
            fg = folium.FeatureGroup(name=t("layer_fires"), show=True)
            plugins.FastMarkerCluster(rows, callback=FIRE_JS, options={"maxClusterRadius": 38, "disableClusteringAtZoom": 11}).add_to(fg)
            fg.add_to(m)
        else:  # aggregated grid (0.05 degree) when there are too many points
            g = points.assign(gi=(points["lat"] / .05).astype(int), gj=(points["lon"] / .05).astype(int))
            agg = g.groupby(["gi", "gj"]).size().reset_index(name="n")
            mx = agg["n"].max()
            fg = folium.FeatureGroup(name=t("layer_fires_grid"), show=True)
            for r in agg.itertuples():
                lat0, lon0 = r.gi * .05, r.gj * .05
                folium.Rectangle([[lat0, lon0], [lat0 + .05, lon0 + .05]], weight=0, fill=True,
                                 fill_color=ramp_color(.15 + .8 * np.sqrt(r.n / mx)), fill_opacity=.75,
                                 tooltip=f"{num(r.n)} {t('unit_hotspots')}").add_to(fg)
            fg.add_to(m)

    # borders
    if "counties" in layers:
        folium.GeoJson(data.geojson("boundaries_adm1.geojson"), name=t("layer_counties"),
                       style_function=lambda f: {"color": C.GOLD, "weight": 2, "fill": False},
                       tooltip=folium.GeoJsonTooltip(["name"], labels=False)).add_to(m)
    if "municipalities" in layers:
        folium.GeoJson(data.geojson("boundaries_adm2.geojson"), name=t("layer_municipalities"),
                       style_function=lambda f: {"color": "#8E8576" if theme == "light" else "#DDD", "weight": 1, "fill": False,
                                                 "dashArray": "3 3"},
                       tooltip=folium.GeoJsonTooltip(["name", "county"], labels=False)).add_to(m)
    if "effis" in layers:
        gj = data.geojson("effis_burnt_areas.geojson")
        y0, y1 = (d0.year, d1.year) if d0 else (2000, 2100)
        feats = [f for f in gj["features"] if y0 <= int(f["properties"].get("year") or 0) <= y1]
        if feats:
            folium.GeoJson({"type": "FeatureCollection", "features": feats}, name=t("layer_effis"),
                           style_function=lambda f: {"color": "#7A1420", "weight": 1, "fillColor": "#7A1420", "fillOpacity": .25,
                                                     "dashArray": "2 2"},
                           tooltip=folium.GeoJsonTooltip(["initialdate", "area_ha", "municipality"],
                                                         aliases=[t("date"), "ha", t("municipality")])).add_to(m)
    s = _sites()
    hn = data.csv("heritage_nearby.csv")
    tot = hn.groupby("site_id")["fire_celldays_5km"].sum()
    lang = st_lang()
    for kind, layer in [("heritage", "layer_heritage"), ("parks", "layer_parks")]:
        if kind not in layers:
            continue
        fg = folium.FeatureGroup(name=t(layer))
        sel = s[s["type"] == "park"] if kind == "parks" else s[s["type"] != "park"]
        for r in sel.itertuples():
            nm = r.name_sq if lang == "sq" else r.name_en
            story = r.story_sq if lang == "sq" else r.story_en
            n_f = int(tot.get(r.site_id, 0))
            html = (f"<b>{escape(nm)}</b><br><span style='font-size:12px'>{escape(story)}</span><br>"
                    f"<b>{num(n_f)}</b> {escape(t('fires_within_5km'))}<br>"
                    f"<a href='{escape(r.source)}' target='_blank' style='font-size:11px'>{escape(t('source'))}</a>")
            if kind == "parks":
                icon = folium.DivIcon(html='<div style="background:#2f6b3a;border:2px solid #fff;border-radius:50%;width:18px;height:18px;'
                                           'color:#fff;font-size:10px;text-align:center;line-height:15px">▲</div>', icon_size=(18, 18),
                                      icon_anchor=(9, 9))
            else:
                icon = folium.DivIcon(html=motifs.rosette_svg(24, C.GOLD, C.RED), icon_size=(24, 24), icon_anchor=(12, 12))
            folium.Marker([r.lat, r.lon], icon=icon, popup=folium.Popup(html, max_width=260), tooltip=nm).add_to(fg)
        fg.add_to(m)

    # current area outline
    if area.get("level") == "circle":
        folium.Circle([area["lat"], area["lon"]], radius=area["r_km"] * 1000, color=c["red"], weight=2, fill=True,
                      fill_opacity=.08, dash_array="6 4").add_to(m)
    elif area.get("level") == "polygon":
        folium.Polygon([[y, x] for x, y in area["coords"]], color=C.GOLD, weight=2.5, fill=True, fill_opacity=.08,
                       dash_array="6 4").add_to(m)
    elif area.get("level") in ("adm1", "adm2"):
        gj = data.geojson("boundaries_adm1.geojson" if area["level"] == "adm1" else "boundaries_adm2.geojson")
        feats = [f for f in gj["features"] if f["properties"]["name"] == area["name"]]
        if feats:
            folium.GeoJson({"type": "FeatureCollection", "features": feats},
                           style_function=lambda f: {"color": c["red"], "weight": 3, "fill": False}).add_to(m)
    if draw:
        plugins.Draw(export=False, position="topleft",
                     draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False,
                                   "rectangle": {"shapeOptions": {"color": C.GOLD}}, "polygon": {"shapeOptions": {"color": C.GOLD}}},
                     edit_options={"edit": False}).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    if bounds:
        w, s_, e, n_ = bounds
        m.fit_bounds([[s_, w], [n_, e]])
    return m
