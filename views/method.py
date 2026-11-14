"""How it works: the method in four steps, the 2012 jump before/after, validation, EFFIS check, limitations."""
from __future__ import annotations

from html import escape

import streamlit as st

import config as C
from src import charts, data, motifs, ui
from src.i18n import num, pct, t

theme = ui.theme()
nat = data.area_monthly(("country", C.COUNTRY))
val = data.js("validation.json")
cal = data.js("calibration.json")
ui.page_title("⚙️", t("method_title"), escape(t("method_sub")))

icons = [motifs.satellite("mo", 70), f'<div style="width:70px">{motifs.cross_stitch_row(4, 60)}</div>', motifs.rosette_svg(50), motifs.icon("columns", C.GOLD, 50)]
ui.html('<div class="v-grid v-g4">' + "".join(
    f'<div class="v-card v-dia"><div style="height:56px;display:flex;align-items:center">{icons[i]}</div>'
    f'<div class="v-cinzel" style="color:var(--red);font-size:1.1rem;font-weight:700">{i + 1} · {escape(t(f"step{i + 1}_t"))}</div>'
    f'<div class="v-small">{escape(t(f"step{i + 1}"))}</div></div>' for i in range(4)) + "</div>")

with st.container(key="card_jump"):
    ui.html(f'<h3>{escape(t("before_after"))}</h3>')
    st.plotly_chart(charts.raw_vs_harmonized(nat, theme, 330), config=charts.CFG, theme=None, key="m_jump")
    hl = data.js("headline.json")
    ui.html(f'<div class="v-small">{escape(hl["short_" + ui.lang()])}</div>')

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(key="card_val"):
        n, te, tr = val["national"], val["national"]["test"], val["national"]["train"]
        cm = val["counties"]["median"]
        rows = [("MAE", "mae", 1), ("RMSE", "rmse", 1), (t("bias"), "bias_pct", 0), ("Pearson r", "pearson", 2), ("Spearman ρ", "spearman", 2)]

        def fmt(d, k, dg):
            x = d.get(k)
            return "–" if x is None else (pct(x, digits=dg) if k == "bias_pct" else num(x, digits=dg))
        body = "".join(f"<tr><td>{escape(lbl)}</td><td>{fmt(tr, k, dg)}</td><td><b>{fmt(te, k, dg)}</b></td><td>{fmt(cm, k, dg)}</td></tr>"
                       for lbl, k, dg in rows)
        ui.html(f'<h3>{escape(t("validation_title"))}</h3><table class="v-t"><tr><th>{escape(t("measure"))}</th>'
                f'<th>{escape(t("train"))} {n["fit_years"][0]}–{n["fit_years"][1]}</th><th>{escape(t("test"))} {n["test_years"][0]}–{n["test_years"][1]}</th>'
                f'<th>{escape(t("counties_median"))}</th></tr>{body}</table>'
                f'<div class="v-small v-muted" style="margin-top:6px">{escape(t("validation_note", n=te["n"], n21=num(val["noaa21"]["test"].get("pearson"), digits=2)))}</div>')
        st.image(str(C.OUT / "validation_chart.png"), caption=t("validation_chart_cap"))
with c2:
    with st.container(key="card_effis"):
        e = val["effis"]
        tab = data.csv("effis_comparison.csv")
        ui.html(f'<h3>{escape(t("effis_title"))}</h3>')
        st.plotly_chart(charts.effis_chart(tab[tab["area_level"] == "country"], theme, 300), config=charts.CFG, theme=None, key="m_effis")
        ui.html(f'<div class="v-small">{escape(t("effis_line", r=num(e["national"].get("yearly_pearson"), digits=2), rho=num(e["national"].get("yearly_spearman"), digits=2), share=num(100 * e["share_celldays_inside"]), fs=num(100 * e["share_fire_season"]), ev=num(100 * (e.get("top50_events_matched_share") or 0))))}</div>'
                f'<div class="v-src" style="margin-top:6px">{escape(t("effis_caveat", ind=num(100 * e["effis_independent_share"])))}</div>')

with st.container(key="card_calib"):
    ui.html(f'<h3>{escape(t("calibration_title"))}</h3>')
    rows = "".join(f'<tr><td>{s}</td><td>{escape(t("season_" + se))}</td><td>{num(c["a"], digits=2)}</td><td>{num(c["b"], digits=2)}</td>'
                   f'<td>{num(c["sd"], digits=2)}</td><td>{num(c["r2"], digits=2)}</td><td>{c["n"]}</td></tr>'
                   for s, d in cal["national"].items() for se, c in d.items())
    tr_ = cal["terra_only_ratio"]
    ui.html(f'<div style="overflow-x:auto"><table class="v-t"><tr><th>{escape(t("satellite"))}</th><th>{escape(t("season"))}</th><th>a</th><th>b</th>'
            f'<th>σ</th><th>R²</th><th>n</th></tr>{rows}</table></div>'
            f'<div class="v-small v-muted" style="margin-top:6px">{escape(t("calibration_note", fire=num(tr_["fire"]["ratio"], digits=2), off=num(tr_["off"]["ratio"], digits=2)))}</div>')

lims = [t(f"lim{i}") for i in range(1, 7)]
ui.html(ui.card(f'<h3>{escape(t("limitations"))}</h3><ul class="v-small">' + "".join(f"<li>{escape(x)}</li>" for x in lims) + "</ul>",
                style="margin-top:14px"))
ui.link_buttons()
