"""Calendar: the burning activity calendar, standard heatmap or Albanian cross-stitch embroidery."""
from __future__ import annotations

from datetime import date
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

import config as C
from src import charts, data, filters, guide, motifs, ui
from src.i18n import fdate, month, months, num, pct, status_label, t
from src.theme import ramp_color

f = filters.get()
theme, lang, mode = f["theme"], f["lang"], f["mode"]
tt = data.area_monthly(f["key"], f["low"], f["dn"])
name = filters.area_full(f["area"])
y0, y1 = f["d0"].year, f["d1"].year

ui.page_title("📅", t("cal_title"), escape(t("cal_sub")))

c1, c2, c3 = st.columns([1.3, 2.4, 3], vertical_alignment="center")
with c1:
    view = st.segmented_control(t("view"), ["std", "emb"], format_func=lambda v: t("view_" + v), default="std",
                                key="cal_view", required=True)
with c2:
    kinds = ["act", "anom", "frp"]
    kind = st.segmented_control(t("values"), kinds, format_func=lambda v: t("val_" + v), default="act", key="cal_kind",
                                required=True)
with c3:
    if mode != "h":
        ui.html(f'<div class="v-small" style="color:var(--red)">⚠ {escape(t("raw_note"))}</div>')
    elif kind == "act":
        ui.html(f'<div class="v-small v-muted">{escape(t("harm_note"))}</div>')
    if kind != "act" and mode != "h":
        ui.html(f'<div class="v-small v-muted">{escape(t("anom_harm_only"))}</div>')


# ------------------------------------------------------------------ month details dialog
@st.dialog(" ", width="large")
def month_dialog(y: int, m: int):
    ui.html(f'<h2 style="margin-top:0">{escape(month(m, full=True).capitalize())} {y} · {escape(name)}</h2>')
    row = tt[(tt["year"] == y) & (tt["month"] == m)]
    if not len(row):
        st.write(t("no_data"))
        return
    r = row.iloc[0]
    cd = data.area_celldays(f["key"], f["low"], f["dn"])
    cdm = cd[(cd["year"] == y) & (cd["month"] == m)]
    fr = data.area_fires(f["key"], f["low"], f["dn"])
    frm = fr[(fr["year"] == y) & (fr["month"] == m)]
    a, b = st.columns([1, 1.15], gap="medium")
    with a:
        pts = cdm.drop_duplicates("cell_id").copy()
        if len(pts):
            pts["color"] = "#F1CC7A"
            pts["label"] = [f"{fdate(d)} · {mu} · {s}" for d, mu, s in zip(pts["date"], pts["adm2"], pts["satellite"])]
        st.plotly_chart(charts.outline_map(pts, theme, 380, labels=False, counties=True), config=charts.CFG_STATIC, theme=None, key="dlg_map")
    with b:
        v = r["harmonized"]
        med = r["median"]
        p = 100 * (v - med) / med if med > 0 else None
        ui.html(f'<div class="v-tile"><div class="lbl">{escape(t("unit_celldays"))}</div><div class="big">{num(v, digits=1 if v < 10 else 0)}</div></div>'
                f'<p>{escape(t("dlg_normal", m=month(m, full=True)))}: <b>{num(med, digits=1)}</b>'
                f'{" (" + pct(p) + ")" if p is not None else ""} {ui.badge(r["status"])}</p>'
                f'<p class="v-small v-muted">{escape(t("raw_counts"))}: MODIS {num(r["raw_modis"])} · VIIRS {num(r["raw_viirs"])} '
                f'{escape(t("unit_hotspots"))}{" · " + escape(t("terra_estimated")) if r["terra_only_flag"] else ""}</p>')
        top = cdm.groupby("adm2", observed=True)["weight"].sum().sort_values(ascending=False).head(3)
        top = top[top > 0]
        if len(top):
            ui.html(f'<h3>{escape(t("top_municipalities"))}</h3><ol class="v-small" style="margin:0 0 8px;padding-left:20px">' +
                    "".join(f"<li>{escape(k)} · {num(v, digits=1)}</li>" for k, v in top.items()) + "</ol>")
        ev = guide.area_events({**f, "d0": date(y, m, 1), "d1": (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).date()}).head(3)
        if len(ev):
            ui.html(f'<h3>{escape(t("biggest_events"))}</h3><div class="v-small">' + "<br>".join(
                f"• {fdate(e.start, with_year=False)} – {fdate(e.end)}: {escape(e.municipality)}, {int(e.days)} {escape(t('days'))}, "
                f"{int(e.cell_days)} {escape(t('unit_celldays_short'))}"
                + (f", max {num(e.max_frp)} MW" if pd.notna(e.max_frp) else "") for e in ev.itertuples()) + "</div>")
        out = frm.drop(columns=["hhmm", "year", "month"], errors="ignore")
        st.download_button(t("dl_month_csv"), guide.csv_bytes(out), mime="text/csv", icon="⬇️",
                           file_name=f"VATRA_hotspots_{guide.safe(filters.area_name(f['area'], 'en'))}_{y}-{m:02d}.csv",
                           disabled=len(out) == 0)
        if st.button(t("open_on_map"), icon="🗺️"):
            st.session_state["map_month"] = (y, m)
            st.switch_page(st.session_state["_pages"]["map"])


# ------------------------------------------------------------------ standard view
if view == "std":
    with st.container(key="card_cal"):
        fig = charts.heatmap(tt, mode, kind, y0, y1, f["d0"], f["d1"], theme)
        ev = st.plotly_chart(fig, config=charts.CFG, theme=None, key="cal_heat", on_select="rerun", selection_mode="points")
        try:
            pts = ev.selection.points if ev and ev.selection else []
        except Exception:
            pts = []
        if pts:
            p = pts[0]
            sel = (int(p["y"]), months().index(p["x"]) + 1)
            if st.session_state.get("_last_sel") != sel:
                st.session_state["_last_sel"] = sel
                month_dialog(*sel)
        lg1, lg2 = st.columns([2, 2])
        ui.html_in(lg1, ui.legend_ramp(kind == "anom"))
        ui.html_in(lg2, f'<div class="v-small v-muted" style="text-align:right">{escape(t("cal_legend_note"))}</div>')
        with st.expander(t("open_month_fallback")):
            a1, a2, a3 = st.columns([1, 1, 1], vertical_alignment="bottom")
            yy = a1.selectbox(t("year"), list(range(y1, y0 - 1, -1)), key="cal_y")
            mm = a2.selectbox(t("month"), list(range(1, 13)), format_func=lambda x: month(x, full=True), key="cal_m",
                              index=7)
            if a3.button(t("open_month"), type="primary", use_container_width=True):
                month_dialog(int(yy), int(mm))
else:
    # ------------------------------------------------------------------ embroidery view
    years = list(range(y0, y1 + 1))
    sub = tt[(tt["year"] >= y0) & (tt["year"] <= y1)]
    col = data.value_col(mode)
    ym = sub["year"] * 100 + sub["month"]
    first_ym = int(data.summary()["first_month"].replace("-", ""))
    last_ym = int(data.summary()["last_month"].replace("-", ""))
    ok = (ym >= max(first_ym, f["d0"].year * 100 + f["d0"].month)) & (ym <= min(last_ym, f["d1"].year * 100 + f["d1"].month))
    grid = sub.assign(v=np.where(ok, sub[col], np.nan)).pivot(index="year", columns="month", values="v").reindex(index=years, columns=range(1, 13))
    terra = sub.pivot(index="year", columns="month", values="terra_only_flag").reindex(index=years, columns=range(1, 13)).fillna(False)
    G = grid.to_numpy(float)
    unit = t("unit_celldays") if mode == "h" else t("unit_hotspots")
    title = t("emb_title", area=filters.area_name(f["area"]), y0=y0, y1=y1)
    svg = motifs.embroidery_svg(G, years, months(), title, t("emb_sub"),
                                lambda r, m: f"{month(m + 1, full=True)} {years[r]}: {num(G[r, m], digits=1) if np.isfinite(G[r, m]) else '–'} {unit}",
                                terra.to_numpy())
    with st.container(key="card_emb"):
        ui.html(f'<div>{svg}</div>')
        ui.html(f'<div class="v-small v-muted">{escape(t("emb_legend"))}</div>')
        d1, d2, _ = st.columns([1, 1, 2])
        d1.download_button(t("dl_svg"), svg.encode("utf-8"), file_name=f"VATRA_embroidery_{guide.safe(filters.area_name(f['area'], 'en'))}_{y0}-{y1}.svg",
                           mime="image/svg+xml", icon="🧵", use_container_width=True)
        with d2:
            from src import poster
            if st.button(t("make_poster"), icon="🖼️", use_container_width=True):
                with st.spinner(t("making_pdf")):
                    pdf = poster.make_cached(f["key"], filters.area_name(f["area"]), y0, y1, mode, lang, f["low"], f["dn"],
                                             f["d0"].isoformat(), f["d1"].isoformat())
                st.download_button(t("dl_poster"), pdf, file_name=f"VATRA_poster_{guide.safe(filters.area_name(f['area'], 'en'))}_{y0}-{y1}_{lang}.pdf",
                                   mime="application/pdf", icon="⬇️", type="primary", use_container_width=True)

# ------------------------------------------------------------------ month profile
with st.container(key="card_profile"):
    h1, h2 = st.columns([3, 1], vertical_alignment="center")
    ui.html_in(h1, f'<h3 style="margin:0">{escape(t("profile_title"))}</h3>')
    yrs = sorted(tt.loc[tt["harmonized"] > 0, "year"].unique().tolist(), reverse=True) or [data.data_end().year]
    worst = int(tt[(tt["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum().idxmax()) if tt["harmonized"].sum() > 0 else yrs[0]
    ysel = h2.selectbox(t("year"), yrs, index=yrs.index(worst) if worst in yrs else 0, key="prof_year", label_visibility="collapsed")
    cur = data.data_end().year
    st.plotly_chart(charts.profile(tt, int(ysel), cur if cur != ysel else None, theme), config=charts.CFG, theme=None, key="prof")
    ui.html(f'<div class="v-small v-muted">{escape(t("profile_note"))}</div>')
