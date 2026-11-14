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


def _fire_rows(points: pd.DataFrame):
    """Compact rows for the fire layer. The popup text (same content as before) is built in the browser when a point
    is clicked, so the page does not carry thousands of ready-made popups."""
    import json as _json
    p = points.copy()
    span = max((p["date"].max() - p["date"].min()).days, 1)
    rec = ((p["date"] - p["date"].min()).dt.days / span).to_numpy()
    lvl = np.clip(np.round((1 - rec) * 20), 0, 20).astype(int)  # recent = brighter (lighter)
    pal = [ramp_color(.25 + .6 * (k / 20)) for k in range(21)]
    rad = np.clip(3 + np.sqrt(p["frp"].fillna(4).to_numpy()) * .55, 3, 11).round(1)
    site, km = _nearest(p["lat"], p["lon"])
    site = np.where(km > 10, "", site)
    sats = sorted(p["satellite"].astype(str).unique())
    confs = sorted(p["confidence"].astype(str).unique())
    munis = sorted({f"{a} ({b})" for a, b in zip(p["adm2"].astype(str), p["adm1"].astype(str))})
    sites = sorted({x for x in site if x})
    si = {v: i for i, v in enumerate(sats)}
    ci = {v: i for i, v in enumerate(confs)}
    mi = {v: i for i, v in enumerate(munis)}
    ti = {v: i for i, v in enumerate(sites)}
    dates = [fdate(d) for d in p["date"]]
    frp = [None if pd.isna(v) else num(v, digits=1) for v in p["frp"]]
    rows = [[round(la, 4), round(lo, 4), int(lv), float(r), d, str(tm), si[str(sa)], ci[str(cf)], fv,
             mi[f"{a2} ({a1})"], ti.get(st, -1), num(float(k), digits=1)]
            for la, lo, lv, r, d, tm, sa, cf, fv, a2, a1, st, k in
            zip(p["lat"], p["lon"], lvl, rad, dates, p["time"], p["satellite"], p["confidence"], frp, p["adm2"], p["adm1"], site, km)]
    E = lambda xs: _json.dumps([escape(x) for x in xs], ensure_ascii=False)
    lab = {k: escape(t(k)) for k in ("fire_detection", "satellite", "confidence", "intensity", "municipality", "nearest_site")}
    conf_lab = E([t("conf_" + c) for c in confs])
    callback = (
        "(function(){var PAL=" + _json.dumps(pal) + ",SAT=" + E(sats) + ",CONF=" + conf_lab + ",MUN=" + E(munis)
        + ",SITE=" + E(sites) + ",LB=" + _json.dumps(lab, ensure_ascii=False) + ";"
        "return function(row){var m=L.circleMarker(new L.LatLng(row[0],row[1]),{radius:row[3],color:'#2A0B0E',weight:0.6,"
        "fillColor:PAL[row[2]],fillOpacity:0.88});"
        "m.bindPopup(function(){var s='<b>🔥 '+LB.fire_detection+'</b><br>'+row[4]+' · '+row[5]+' UTC<br>'+LB.satellite+': '+SAT[row[6]]"
        "+' · '+LB.confidence+': '+CONF[row[7]]+'<br>'+LB.intensity+': '+(row[8]===null?'–':row[8])+' MW<br>'+LB.municipality+': '+MUN[row[9]];"
        "if(row[10]>=0){s+='<br>'+LB.nearest_site+': '+SITE[row[10]]+' ('+row[11]+' km)';}return s;},{maxWidth:260});"
        "return m;};})()")
    return rows, callback


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
            rows, callback = _fire_rows(points)
            fg = folium.FeatureGroup(name=t("layer_fires"), show=True)
            plugins.FastMarkerCluster(rows, callback=callback, options={"maxClusterRadius": 38, "disableClusteringAtZoom": 11}).add_to(fg)
            fg.add_to(m)
        else:  # aggregated grid (0.05 degree) when there are too many points: one layer, not one shape per cell
            g = points.assign(gi=np.floor(points["lat"] / .05).astype(int), gj=np.floor(points["lon"] / .05).astype(int))
            agg = g.groupby(["gi", "gj"]).size().reset_index(name="n")
            mx = agg["n"].max()
            unit = t("unit_hotspots")
            feats = [{"type": "Feature",
                      "properties": {"c": ramp_color(.15 + .8 * np.sqrt(r.n / mx)), "tip": f"{num(r.n)} {unit}"},
                      "geometry": {"type": "Polygon", "coordinates": [[
                          [round(r.gj * .05, 3), round(r.gi * .05, 3)], [round(r.gj * .05 + .05, 3), round(r.gi * .05, 3)],
                          [round(r.gj * .05 + .05, 3), round(r.gi * .05 + .05, 3)], [round(r.gj * .05, 3), round(r.gi * .05 + .05, 3)],
                          [round(r.gj * .05, 3), round(r.gi * .05, 3)]]]}}
                     for r in agg.itertuples()]
            folium.GeoJson({"type": "FeatureCollection", "features": feats}, name=t("layer_fires_grid"),
                           style_function=lambda f: {"weight": 0, "fillColor": f["properties"]["c"], "fillOpacity": .75},
                           tooltip=folium.GeoJsonTooltip(["tip"], labels=False)).add_to(m)

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
