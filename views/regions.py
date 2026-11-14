"""Regions: 12 counties (history, nature, fire profile) and 61 municipalities (fire profile)."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import config as C
from src import charts, data, filters, guide, motifs, ui
from src.i18n import fdate, month, num, t

ss = st.session_state
f = filters.get()
theme, lang = f["theme"], f["lang"]
a = f["area"]
county = a["name"] if a["level"] == "adm1" else (data.county_of(a["name"]) if a["level"] == "adm2" else None)
mun = a["name"] if a["level"] == "adm2" else None

ui.page_title("🏔️", t("regions_title"), escape(t("regions_sub")))


def _pick_county():
    v = ss.get("w_reg_county")
    if v:
        filters.set_area("adm1", v)


def _pick_mun():
    v = ss.get("w_reg_mun")
    c = ss.get("w_reg_county") or county
    if v and v != "__all__":
        filters.set_area("adm2", v)
    elif c:
        filters.set_area("adm1", c)


ss["w_reg_county"] = county
st.pills(t("pick_county"), data.counties(), key="w_reg_county", on_change=_pick_county,
         format_func=lambda c: f"{c}")
if not county:
    from src import countycards
    countycards.render(lang, "reg")
    m_ = data.monthly()
    cty_ = m_[(m_["area_level"] == "adm1") & (m_["year"] <= C.BASE_YEARS[1])].groupby("area_name")["harmonized"].sum().sort_values(ascending=False)
    with st.container(key="card_rank"):
        ui.html(f'<h3>{escape(t("r_ranking"))} · 2000–{C.BASE_YEARS[1]}</h3>')
        st.plotly_chart(charts.ranking(list(cty_.index), list(cty_.values), theme), config=charts.CFG_STATIC, theme=None, key="reg_rank")
else:

    ss["w_reg_mun"] = mun or "__all__"
    st.selectbox(t("pick_municipality"), ["__all__"] + data.municipalities(county), key="w_reg_mun", on_change=_pick_mun,
                 format_func=lambda m: t("whole_county", c=county) if m == "__all__" else m)

    key = ("adm2", mun) if mun else ("adm1", county)
    tt = data.area_monthly(key, f["low"], f["dn"])
    cinfo = next((c for c in data.content("counties.json")["counties"] if c["name"] == county), None)

    # ------------------------------------------------------------------ banner
    title = mun or county
    subtitle = (t("municipality_in", c=county) if mun else
                f"{t('county')} · {len(data.municipalities(county))} {t('municipalities')}")
    ui.html(f'<div class="v-card" style="padding:0;overflow:hidden"><div style="background:linear-gradient(90deg,#A61E26,#6E1218);'
            f'padding:18px 22px;display:flex;align-items:center;gap:18px">'
            f'<div style="width:84px;height:84px;background:rgba(255,255,255,.08);border-radius:14px;padding:8px">'
            f'{motifs.county_icon(county, C.GOLD, 68)}</div><div><div class="v-cinzel v-white" style="font-size:2rem;font-weight:700">'
            f'{escape(title)}</div><div class="v-white" style="opacity:.85">{escape(subtitle)}</div></div></div>'
            f'<div class="v-band" style="margin:6px 14px"></div>' +
            (f'<div class="v-grid v-g3" style="padding:6px 16px 16px">' + "".join(
                f'<div><h3>{ic} {escape(t(k))}</h3>' + "".join(
                    f'<p class="v-small" style="margin:.2rem 0">{escape(it["text_" + lang])}</p>{ui.src_link(it.get("source", ""))}'
                    for it in cinfo.get(field, [])) + "</div>"
                for ic, k, field in [("🏛️", "ancient_roots", "roots"), ("🌲", "nature", "nature"), ("💡", "did_you_know", "did_you_know")])
             + "</div>" if (cinfo and not mun) else "") + "</div>")

    # ------------------------------------------------------------------ fire profile
    s = data.seasons_for(key, None if (not f["low"] and f["dn"] == "both") else tt)
    n = data.normals_for(tt)
    yt = tt[(tt["year"] >= C.BASE_YEARS[0]) & (tt["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum()
    worst = yt.sort_values(ascending=False).head(3)
    cd = data.area_celldays(key, f["low"], f["dn"])
    top_m = cd.groupby("adm2", observed=True)["weight"].sum().sort_values(ascending=False).head(3) if not mun else None

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(key="dcard_profile"):
            season = (f'{escape(t("season"))}: <b>{month(s["start"], full=True)} – {month(s["end"], full=True)}</b> · '
                      f'{escape(t("peak"))}: <b>{month(s["peak"], full=True)}</b>' if s.get("peak") else escape(t("g_too_little", area=title)))
            if s.get("two_seasons") and s.get("second_peak"):
                season += f' · {escape(t("second_peak"))}: <b>{month(s["second_peak"], full=True)}</b>'
            ui.html(f'<h3>🔥 {escape(t("fire_profile"))}</h3><div class="v-small">{season}</div>')
            st.plotly_chart(charts.profile(tt, None, None, theme, 230), config=charts.CFG_STATIC, theme=None, key="reg_prof")
            line = f'<b>{escape(t("worst_years"))}:</b> ' + ", ".join(f"{int(y)} ({num(v)})" for y, v in worst.items() if v > 0)
            if top_m is not None and len(top_m):
                line += f' · <b>{escape(t("top_municipalities"))}:</b> ' + ", ".join(escape(k) for k in top_m.index)
            ui.html(f'<div class="v-small">{line}</div>')
    with c2:
        with st.container(key="dcard_regcal"):
            y1 = data.data_end().year
            ui.html(f'<h3>📅 {escape(title)} · {y1 - 9}–{y1}</h3>')
            st.plotly_chart(charts.heatmap(tt, f["mode"], "act", y1 - 9, y1, data.first_date(), data.data_end(), theme, height=330, marks=False),
                            config=charts.CFG_STATIC, theme=None, key="reg_cal")
            ui.html(ui.legend_ramp())

    # ------------------------------------------------------------------ biggest events (cards, not a wide table)
    ev = guide.area_events({**f, "area": {"level": key[0], "name": key[1]}, "key": key, "d0": data.first_date(), "d1": data.data_end()}).head(6)
    ui.html(f'<h3 style="margin-top:14px">{escape(t("biggest_events_in", area=title))}</h3>')
    if len(ev):
        cards = []
        for e in ev.itertuples():
            near = (f'<br>📍 {escape(t("near"))} {escape(e.nearest_site)} ({num(e.site_km, digits=1)} km)' if pd.notna(e.site_km) and e.site_km <= 10 else "")
            eff = (f'<br>✓ EFFIS {num(e.effis_area_ha)} ha' if getattr(e, "effis_match", "no") == "yes" else "")
            cards.append(f'<div class="v-card v-small"><b>{fdate(e.start)} → {fdate(e.end)}</b><br>{escape(e.municipality)} · '
                         f'{int(e.days)} {escape(t("days"))} · {int(e.cell_days)} {escape(t("unit_celldays_short"))}'
                         f'{" · max " + num(e.max_frp) + " MW" if pd.notna(e.max_frp) else ""}{near}{eff}</div>')
        ui.html(f'<div class="v-grid v-g3">{"".join(cards)}</div><div class="v-src" style="margin-top:6px">{escape(t("events_note"))}</div>')
    else:
        st.caption(t("no_events"))

    # ------------------------------------------------------------------ actions
    b1, b2, b3 = st.columns(3, gap="small")
    with b1:
        from src import report
        if st.button(t("county_report") if not mun else t("municipality_report"), icon="📄", type="primary", use_container_width=True):
            with st.spinner(t("making_pdf")):
                pdf, fn = report.make_cached(key, title if mun else f"{county}", data.first_date().isoformat(),
                                             data.data_end().isoformat(), lang, f["low"], f["dn"])
            st.download_button(t("download_pdf"), pdf, file_name=fn, mime="application/pdf", icon="⬇️", use_container_width=True)
    with b2:
        from src import cards as cardmod
        if st.button(t("season_card"), icon="🖼️", use_container_width=True):
            png = cardmod.make_cached(key, title, county, lang)
            st.image(png, width=280)
            st.download_button(t("download_png"), png, file_name=f"VATRA_card_{guide.safe(title)}_{lang}.png", mime="image/png",
                               icon="⬇️", use_container_width=True)
    with b3:
        if st.button(t("open_on_map"), icon="🗺️", use_container_width=True):
            st.switch_page(ss["_pages"]["map"])
