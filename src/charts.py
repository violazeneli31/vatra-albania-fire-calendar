"""All plotly charts, so every page looks the same. Colour-blind safe ramps; hover shows exact numbers."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import config as C
from src import data
from src.i18n import month, months, num, status_label, t
from src.theme import RAMP, anom_scale, colors, ramp_color, ramp_scale, template

MARKERS = [(2012, "mark_2012"), (2018, "mark_2018"), (2023, "mark_2023")]
CFG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines"],
       "toImageButtonOptions": {"format": "png", "filename": "VATRA_chart", "scale": 2}}
CFG_STATIC = {**CFG, "displayModeBar": False}


def _base(theme, height=300, **kw):
    fig = go.Figure()
    fig.update_layout(template=template(theme), height=height, **kw)
    return fig


def _log_ticks(vmax: float):
    nice = [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    vals = [v for v in nice if v <= max(vmax, 1) * 1.05]
    return [math.log1p(v) for v in vals], [num(v) for v in vals]


# ------------------------------------------------------------------ calendar heatmap
def heatmap(t_: pd.DataFrame, mode: str, kind: str, y0: int, y1: int, d0, d1, theme: str, height=None, marks=True, scale=True):
    col = data.value_col(mode)
    tt = t_[(t_["year"] >= y0) & (t_["year"] <= y1)].copy()
    years = list(range(y0, y1 + 1))
    ym = tt["year"] * 100 + tt["month"]
    inside = (ym >= d0.year * 100 + d0.month) & (ym <= d1.year * 100 + d1.month)
    first_ym = int(data.summary()["first_month"].replace("-", ""))
    last_ym = int(data.summary()["last_month"].replace("-", ""))
    inside &= (ym >= first_ym) & (ym <= last_ym)
    if mode == "v":
        inside &= tt["year"] >= 2012
    piv = lambda c: tt.assign(v=np.where(inside, tt[c], np.nan)).pivot(index="year", columns="month", values="v").reindex(index=years, columns=range(1, 13))
    V = piv(col)
    med = tt.pivot(index="year", columns="month", values="median").reindex(index=years, columns=range(1, 13))
    st_ = tt.pivot(index="year", columns="month", values="status").reindex(index=years, columns=range(1, 13))
    terra = tt.pivot(index="year", columns="month", values="terra_only_flag").reindex(index=years, columns=range(1, 13)).fillna(False)
    H = piv("harmonized")
    if kind == "anom":
        Z = np.clip(np.log((H.to_numpy() + 1) / (med.to_numpy() + 1)), -2, 2)
        cs, zmin, zmax = anom_scale(), -2, 2
        cbar = dict(tickvals=[-2, -1, 0, 1, 2], ticktext=["÷7", "÷3", t("normal_short"), "×3", "×7"], title=dict(text=""))
    elif kind == "frp":
        F = piv("frp_sum")
        Z = np.log1p(F.to_numpy())
        cs, zmin, zmax = ramp_scale(), 0, np.nanmax(Z) if np.isfinite(np.nanmax(Z)) else 1
        tv, tx = _log_ticks(float(np.nanmax(F.to_numpy())) if np.isfinite(np.nanmax(F.to_numpy())) else 1)
        cbar = dict(tickvals=tv, ticktext=tx, title=dict(text="MW"))
    else:
        Z = np.log1p(V.to_numpy())
        vmax = float(np.nanmax(V.to_numpy())) if np.isfinite(np.nanmax(V.to_numpy())) else 1
        cs, zmin, zmax = ramp_scale(), 0, math.log1p(vmax)
        tv, tx = _log_ticks(vmax)
        if len(tv) > 5:  # fewer labels so the scale stays readable on phones
            tv, tx = tv[::2], tx[::2]
        cbar = dict(tickvals=tv, ticktext=tx, title=dict(text=""))
    unit = t("unit_celldays") if mode == "h" else t("unit_hotspots")
    vtxt = np.vectorize(lambda x: "–" if not np.isfinite(x) else num(x, digits=0 if mode != "h" or x >= 10 or x == 0 else 1))(V.to_numpy())
    mtxt = np.vectorize(lambda x: "–" if not np.isfinite(x) else num(x, digits=1 if x < 10 else 0))(med.to_numpy())
    stxt = np.vectorize(lambda s: status_label(s) if isinstance(s, str) and s else "")(st_.to_numpy())
    pctv = np.where(med.to_numpy() > 0, 100 * (H.to_numpy() - med.to_numpy()) / np.where(med.to_numpy() > 0, med.to_numpy(), 1), np.nan)
    ptxt = np.vectorize(lambda x: "" if not np.isfinite(x) else (f"{'+' if x > 0 else ''}{num(x)}%"))(pctv)
    est = np.where(terra.to_numpy(), t("terra_estimated"), "")
    mnames = [month(m, full=True) for m in range(1, 13)]
    custom = np.dstack([vtxt, mtxt, stxt, ptxt, est, np.tile(mnames, (len(years), 1))])
    c = colors(theme)
    fig = go.Figure(go.Heatmap(
        z=Z, x=months(), y=years, colorscale=cs, zmin=zmin, zmax=zmax, xgap=2, ygap=2,
        customdata=custom, hoverongaps=False, showscale=scale, colorbar=dict(thickness=10, len=.5, orientation="h", y=-.02, yanchor="top", x=.5, xanchor="center", **cbar),
        hovertemplate=(f"<b>%{{customdata[5]}} %{{y}}</b><br>%{{customdata[0]}} {unit}<br>{t('hover_normal')}: %{{customdata[1]}}"
                       f" %{{customdata[3]}}<br>%{{customdata[2]}}<br>%{{customdata[4]}}<extra></extra>")))
    ann = []
    for r, y in enumerate(years):
        for m in range(12):
            if terra.iloc[r, m] and np.isfinite(Z[r, m]):
                ann.append(dict(x=months()[m], y=y, text="≈", showarrow=False, font=dict(size=11, color="#6E6560"), xshift=-12, yshift=4))
    shapes = []
    if marks:
        for yr, key in MARKERS + ([(int(data.summary()["last_date_per_satellite"].get("S-NPP", "2026")[:4]), "mark_snpp")] if True else []):
            if y0 < yr <= y1 or (key == "mark_snpp" and y0 <= yr <= y1):
                if key == "mark_snpp":
                    ann.append(dict(x=1.005, xref="paper", y=yr, text="◀ " + t(key), showarrow=False, xanchor="left",
                                    font=dict(size=10.5, color=c["gold"])))
                    continue
                shapes.append(dict(type="line", xref="paper", x0=0, x1=1.0, y0=yr - .5, y1=yr - .5,
                                   yref="y", line=dict(color=c["gold"], width=2)))
                ann.append(dict(x=1.005, xref="paper", y=yr - .5, yref="y", text="— " + t(key), showarrow=False,
                                xanchor="left", font=dict(size=10.5, color=c["gold"])))
    fig.update_layout(template=template(theme), height=height or max(260, 24 * len(years) + 130),
                      margin=dict(l=46, r=100 if marks else 8, t=30, b=60 if scale else 8), annotations=ann, shapes=shapes,
                      xaxis=dict(side="top", showgrid=False, fixedrange=True),
                      yaxis=dict(autorange="reversed", showgrid=False, fixedrange=True, tickmode="linear", dtick=1 if len(years) <= 16 else 2, tickformat="d", zeroline=False),
                      dragmode=False)
    return fig


# ------------------------------------------------------------------ profiles and comparisons
def profile(t_: pd.DataFrame, year_sel: int | None, current_year: int | None, theme: str, height=320, title=None):
    c = colors(theme)
    n = data.normals_for(t_)
    fig = _base(theme, height)
    x = months()
    fig.add_trace(go.Scatter(x=x, y=n["p90"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x, y=n["p10"], fill="tonexty", fillcolor="rgba(201,162,74,.28)", line=dict(width=0),
                             name=t("normal_range"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=x, y=n["median"], name=t("median_base"), line=dict(color=c["gold"], width=3),
                             hovertemplate="%{x}: %{y:.1f}<extra></extra>"))
    for y, colr, dash in [(year_sel, c["red"], None), (current_year, c["blue"], "dash")]:
        if y is None:
            continue
        v = t_[t_["year"] == y].set_index("month").reindex(range(1, 13))["harmonized"]
        fig.add_trace(go.Scatter(x=x, y=v, name=str(y), mode="lines+markers", line=dict(color=colr, width=2.5, dash=dash),
                                 hovertemplate=f"{y} %{{x}}: %{{y:.1f}}<extra></extra>"))
    fig.update_layout(yaxis_title=t("unit_celldays"), title=title, hovermode="x unified")
    return fig


def yearly(t_: pd.DataFrame, col: str = "harmonized", y0=2001, y1=2025):
    return t_[(t_["year"] >= y0) & (t_["year"] <= y1)].groupby("year")[col].sum()


def trend_chart(t_: pd.DataFrame, tr: dict, theme: str, height=300):
    c = colors(theme)
    yt = yearly(t_, "harmonized", *C.TREND_YEARS).reindex(range(C.TREND_YEARS[0], C.TREND_YEARS[1] + 1), fill_value=0)
    mx = max(yt.max(), 1)
    fig = _base(theme, height)
    fig.add_trace(go.Bar(x=yt.index, y=yt.values, marker_color=[ramp_color(.2 + .7 * math.sqrt(v / mx)) for v in yt.values],
                         name=t("unit_celldays"), hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    if tr.get("slope") is not None:
        xs = np.arange(len(yt))
        fig.add_trace(go.Scatter(x=yt.index, y=tr["intercept"] + tr["slope"] * xs, name=t("sens_slope"),
                                 line=dict(color=c["blue"], width=3, dash="dash"), hoverinfo="skip"))
    fig.update_layout(showlegend=True, bargap=.15)
    return fig


def two_years(t_: pd.DataFrame, ya: int, yb: int, theme: str, height=300, mode: str = "h"):
    c = colors(theme)
    vc = data.value_col(mode)
    fig = _base(theme, height)
    for y, colr in [(ya, c["red"]), (yb, c["gold"])]:
        v = t_[t_["year"] == y].set_index("month").reindex(range(1, 13))[vc].fillna(0)
        fig.add_trace(go.Bar(x=months(), y=v, name=str(y), marker_color=colr, hovertemplate=f"{y} %{{x}}: %{{y:.1f}}<extra></extra>"))
    fig.update_layout(barmode="group", bargap=.2)
    return fig


def gauge(p: float, status: str, theme: str, height=210):
    c = colors(theme)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=p, number=dict(suffix="", prefix="P", valueformat=".0f", font=dict(size=30, color=c["text"])),
        gauge=dict(axis=dict(range=[0, 100], tickvals=[0, 10, 50, 90, 100], tickcolor=c["muted"]),
                   bar=dict(color=c["text"], thickness=.18),
                   steps=[dict(range=[0, 10], color=C.ANOM[0]), dict(range=[10, 90], color=c["line"]),
                          dict(range=[90, 99], color=C.RED), dict(range=[99, 100], color=C.BLACK)],
                   borderwidth=0)))
    fig.update_layout(template=template(theme), height=height, margin=dict(l=20, r=20, t=10, b=0))
    return fig


def modis_off(t_: pd.DataFrame, off: int, theme: str, height=300):
    c = colors(theme)
    yrs = list(range(2001, 2026))
    h = yearly(t_, "harmonized", 2001, 2025).reindex(yrs, fill_value=0)
    m = yearly(t_, "raw_modis_cd", 2001, 2025).reindex(yrs, fill_value=0)
    m = m.where(m.index <= off)
    fig = _base(theme, height)
    fig.add_trace(go.Scatter(x=yrs, y=m, name=t("modis_only"), line=dict(color=c["muted"], width=2.5, dash="dot"),
                             hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=h, name=t("vatra_harmonized"), line=dict(color=c["red"], width=3.2),
                             hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.add_vline(x=off + .5, line=dict(color=c["gold"], dash="dash", width=2))
    fig.add_annotation(x=off + .5, y=1, yref="paper", text=t("modis_off_label"), showarrow=False, xanchor="left",
                       font=dict(color=c["gold"], size=12), yanchor="top")
    fig.update_layout(yaxis=dict(type="log", dtick=1, title=t("unit_celldays")))
    return fig


def sensor_match(t_: pd.DataFrame, theme: str, height=320):
    """Real MODIS cell-days vs VIIRS converted to the MODIS scale, 2012-2025, with the uncertainty band."""
    c = colors(theme)
    yrs = list(range(2012, 2026))
    g = t_[(t_["year"] >= 2012) & (t_["year"] <= 2025)].groupby("year")[["raw_modis_cd", "harmonized", "low", "high"]].sum().reindex(yrs)
    fig = _base(theme, height)
    fig.add_trace(go.Scatter(x=yrs, y=g["high"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=yrs, y=g["low"], fill="tonexty", fillcolor="rgba(201,162,74,.3)", line=dict(width=0),
                             name=t("uncertainty_band"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=yrs, y=g["raw_modis_cd"], name=t("real_modis"), mode="lines+markers",
                             line=dict(color=c["text"], width=2.4), hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=yrs, y=g["harmonized"], name=t("calibrated_viirs"), mode="lines+markers",
                             line=dict(color=c["red"], width=2.6), hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.update_layout(yaxis=dict(type="log", dtick=1, title=t("unit_celldays")), hovermode="x unified")
    return fig


def raw_vs_harmonized(t_: pd.DataFrame, theme: str, height=320, log=True, harmonized=True):
    c = colors(theme)
    yrs = list(range(2001, 2026))
    raw = (yearly(t_, "raw_modis", 2001, 2025) + yearly(t_, "raw_viirs", 2001, 2025)).reindex(yrs, fill_value=0)
    h = yearly(t_, "harmonized", 2001, 2025).reindex(yrs, fill_value=0)
    fig = _base(theme, height)
    fig.add_trace(go.Scatter(x=yrs, y=raw, name=t("raw_all"), line=dict(color=c["muted"], width=2.4, dash="dash"),
                             hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    if harmonized:
        fig.add_trace(go.Scatter(x=yrs, y=h, name=t("vatra_harmonized"), line=dict(color=c["red"], width=3.2),
                                 hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.add_vline(x=2011.5, line=dict(color=c["gold"], dash="dot", width=2))
    fig.add_annotation(x=2011.6, y=1, yref="paper", text=t("viirs_starts"), showarrow=False, xanchor="left", yanchor="top",
                       font=dict(color=c["gold"]))
    if log:
        fig.update_layout(yaxis=dict(type="log", dtick=1))
    return fig


def effis_chart(tab: pd.DataFrame, theme: str, height=320):
    c = colors(theme)
    d = tab[(tab["period"] == "year")]
    fig = _base(theme, height)
    fig.add_trace(go.Bar(x=d["year"], y=d["harmonized"], name=t("vatra_harmonized"), marker_color=c["red"],
                         hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=d["year"], y=d["effis_area_ha"], name=t("effis_ha"), yaxis="y2", mode="lines+markers",
                             line=dict(color=c["gold"], width=2.6), hovertemplate="%{x}: %{y:,.0f} ha<extra></extra>"))
    fig.update_layout(yaxis=dict(title=t("unit_celldays"), rangemode="tozero"), barmode="group",
                      yaxis2=dict(title="ha", overlaying="y", side="right", showgrid=False, rangemode="tozero", tickfont=dict(color=c["muted"])))
    return fig


def ranking(names: list[str], values: list[float], theme: str, height=None, color=None):
    c = colors(theme)
    fig = _base(theme, height or max(200, 26 * len(names) + 40))
    fig.add_trace(go.Bar(y=names[::-1], x=values[::-1], orientation="h", marker_color=color or c["red"],
                         hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_layout(margin=dict(l=8, r=8, t=10, b=8), yaxis=dict(automargin=True))
    return fig


def mini_months(values, theme: str, highlight=None, height=180):
    c = colors(theme)
    cols = [c["red"] if (highlight and m in highlight) else "#E0C9A6" for m in range(1, 13)]
    fig = _base(theme, height)
    fig.add_trace(go.Bar(x=months(), y=values, marker_color=cols, hovertemplate="%{x}: %{y:.1f}<extra></extra>"))
    fig.update_layout(margin=dict(l=4, r=4, t=6, b=4), showlegend=False)
    return fig


def mini_curve_svg(values, w=110, h=26, col="#A61E26") -> str:
    v = np.asarray(values, float)
    mx = v.max() if v.max() > 0 else 1
    pts = " ".join(f"{i * (w / 11):.1f},{h - 2 - v[i] / mx * (h - 4):.1f}" for i in range(len(v)))
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/></svg>'


# ------------------------------------------------------------------ maps without tiles (instant)
def _outline_xy():
    gj = data.geojson("boundaries_adm0.geojson")
    xs, ys = [], []
    geom = gj["features"][0]["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        ring = poly[0]
        xs += [p[0] for p in ring] + [None]
        ys += [p[1] for p in ring] + [None]
    return xs, ys


def _county_lines():
    gj = data.geojson("boundaries_adm1.geojson")
    xs, ys = [], []
    for f in gj["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            xs += [p[0] for p in poly[0]] + [None]
            ys += [p[1] for p in poly[0]] + [None]
    return xs, ys


def outline_map(points: pd.DataFrame, theme: str, height=520, dark_card=True, labels=True, glow=True, counties=False):
    """Albania in gold lines with glowing fire dots (no map tiles)."""
    xs, ys = _outline_xy()
    fig = go.Figure()
    if counties:
        cx, cy = _county_lines()
        fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color="rgba(201,162,74,.35)", width=1), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.GOLD, width=2), fill="toself",
                             fillcolor="rgba(201,162,74,.06)", hoverinfo="skip"))
    if len(points):
        size = np.clip(4 + np.sqrt(points["max_frp"].fillna(5).to_numpy()) * .8, 4, 18)
        if glow:
            fig.add_trace(go.Scatter(x=points["lon"], y=points["lat"], mode="markers", hoverinfo="skip",
                                     marker=dict(size=size * 2.6, color="rgba(224,138,60,.16)", line=dict(width=0))))
        fig.add_trace(go.Scatter(x=points["lon"], y=points["lat"], mode="markers",
                                 marker=dict(size=size, color=points.get("color", "#F1CC7A"), line=dict(width=.6, color="#A61E26"),
                                             opacity=.92),
                                 text=points.get("label"), hovertemplate="%{text}<extra></extra>" if "label" in points else None,
                                 hoverinfo=None if "label" in points else "skip"))
    if labels:
        a = data.areas()
        a = a[a["level"] == "adm1"]
        fig.add_trace(go.Scatter(x=a["lon"], y=a["lat"], mode="text", text=a["name"], hoverinfo="skip",
                                 textfont=dict(family="Cinzel, Georgia, serif", size=10, color="rgba(201,162,74,.75)")))
    fig.update_layout(template=template(theme), height=height, showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis=dict(visible=False, range=[19.1, 21.2], fixedrange=True),
                      yaxis=dict(visible=False, range=[39.55, 42.75], scaleanchor="x", scaleratio=1 / math.cos(math.radians(41.2)),
                                 fixedrange=True),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", dragmode=False)
    return fig
