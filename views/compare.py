"""Compare: this month vs normal, two years, trend, and 'What if MODIS turns off?'."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import config as C
from src import api, charts, data, filters, ui
from src.i18n import fdate, month, num, pct, status_label, t

f = filters.get()
theme = f["theme"]
tt = data.area_monthly(f["key"], f["low"], f["dn"])
name = filters.area_full(f["area"])
ui.page_title("📊", t("compare_title"), escape(t("compare_sub", area=name)))

det, cdl, info = api.latest()
end = info.get("end") or data.data_end()
daily = data.area_daily(f["key"], f["low"], f["dn"]).copy()
if len(cdl):
    extra = cdl[data.mask(cdl, f["key"])].groupby("date")["weight"].sum()
    daily = pd.concat([daily, extra]).groupby(level=0).sum()

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(key="dcard_now"):
        w = data.window_compare(daily, end, end.day)
        ui.html(f'<h3>{escape(t("this_month_vs_normal"))}</h3>')
        g1, g2 = st.columns([1, 1.25], vertical_alignment="center")
        with g1:
            st.plotly_chart(charts.gauge(w["percentile"], w["status"], theme), config=charts.CFG_STATIC, theme=None, key="gauge")
        with g2:
            txt = t("month_so_far", m=month(end.month, full=True).capitalize(), y=end.year, d=end.day, v=num(w["value"], digits=1),
                    med=num(w["median"], digits=1), p=num(w["percentile"]), status=status_label(w["status"]).lower())
            ui.html(f'{ui.badge(w["status"])}<p class="v-small" style="margin-top:.5em">{escape(txt)}</p>'
                    f'<p class="v-src">{escape(t("early_warning_note"))} · '
                    f'{escape(t("data_to", end=fdate(end)) if info.get("end") else t("latest_unavailable", end=fdate(data.data_end())))}</p>')
            ui.listen(txt, "cmp_now")
with c2:
    with st.container(key="dcard_years"):
        yrs = list(range(C.BASE_YEARS[1] + 1, 2000, -1))
        yt = tt[(tt["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum()
        da = int(yt.idxmax()) if yt.sum() > 0 else 2021
        h1, h2, h3 = st.columns([2, 1, 1], vertical_alignment="center")
        ui.html_in(h1, f'<h3 style="margin:0">{escape(t("compare_two_years"))}</h3>')
        ya = h2.selectbox("A", yrs, index=yrs.index(da) if da in yrs else 0, key="cmp_a", label_visibility="collapsed")
        yb = h3.selectbox("B", yrs, index=yrs.index(C.BASE_YEARS[1]), key="cmp_b", label_visibility="collapsed")
        vc = data.value_col(f["mode"])
        st.plotly_chart(charts.two_years(tt, ya, yb, theme, 260, f["mode"]), config=charts.CFG, theme=None, key="two")
        a = tt[tt["year"] == ya][vc].sum()
        b = tt[tt["year"] == yb][vc].sum()
        d = (tt[tt["year"] == ya].set_index("month")[vc] - tt[tt["year"] == yb].set_index("month")[vc]).abs()
        diff = 100 * (b - a) / a if a > 0 else None
        ui.html(f'<div class="v-small">{escape(t("two_years_line", ya=ya, a=num(a), yb=yb, b=num(b), diff=pct(diff) if diff is not None else "–", m=month(int(d.idxmax()), full=True) if len(d) and d.max() > 0 else "–"))}</div>')

c3, c4 = st.columns(2, gap="medium")
with c3:
    with st.container(key="dcard_trend"):
        tr = data.trend_for(tt)
        ui.html(f'<h3>{escape(t("trend_title"))}</h3>')
        st.plotly_chart(charts.trend_chart(tt, tr, theme, 260), config=charts.CFG, theme=None, key="trend")
        if tr.get("slope") is None:
            txt = t("g_too_little", area=name)
        else:
            key = {"up": "g_trend_up", "down": "g_trend_down"}.get(tr["direction"], "g_trend_none")
            txt = t(key, area=name, pct=pct(tr["pct_per_year"], digits=1) if tr["pct_per_year"] is not None else "–",
                    p=num(tr["p"], digits=2), years=tr["years"].replace("-", "–"))
        ui.html(f'<p class="v-small">{escape(txt)}</p><p class="v-src">{escape(t("trend_caveat"))}</p>')
with c4:
    with st.container(key="dcard_modis"):
        ui.html(f'<h3>{escape(t("modis_off_title"))}</h3><p class="v-small v-muted" style="margin:0">{escape(t("modis_off_sub"))}</p>')
        off = st.slider(t("modis_off_year"), 2012, 2025, 2025, key="modis_off")
        st.plotly_chart(charts.modis_off(tt, off, theme, 240), config=charts.CFG, theme=None, key="modisoff")
        ui.html(f'<p class="v-small"><b>{escape(t("modis_retiring"))}</b></p>')

with st.container(key="card_sensor"):
    v = data.js("validation.json")["national"]["test"]
    ui.html(f'<h3>{escape(t("sensor_doesnt_matter"))}</h3>')
    st.plotly_chart(charts.sensor_match(tt, theme), config=charts.CFG, theme=None, key="sensor")
    ui.html(f'<div class="v-small v-muted">{escape(t("sensor_note", r=num(v["pearson"], digits=2), rho=num(v["spearman"], digits=2), bias=pct(v["bias_pct"]), mae=num(v["mae"], digits=1)))}</div>')
