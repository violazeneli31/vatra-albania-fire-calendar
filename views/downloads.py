"""Downloads: data (CSV), reports (PDF), art (poster, fire-season card), teachers (activity sheet)."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

import config as C
from src import data, filters, guide, ui
from src.i18n import t

f = filters.get()
lang = f["lang"]
name = filters.area_full(f["area"])
ui.page_title("⬇️", t("downloads_title"), escape(t("downloads_sub", area=name)))


def row(title, desc):
    ui.html(f'<div style="margin-top:6px"><b>{title}</b><div class="v-small v-muted">{escape(desc)}</div></div>')


c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(key="dcard_data"):
        ui.html(f'<h3>📊 {escape(t("dl_data"))}</h3>')
        cd = data.area_celldays(f["key"], f["low"], f["dn"])
        cd = cd[(cd["date"] >= pd.Timestamp(f["d0"])) & (cd["date"] <= pd.Timestamp(f["d1"]))]
        fr = data.area_fires(f["key"], f["low"], f["dn"])
        fr = fr[(fr["date"] >= pd.Timestamp(f["d0"])) & (fr["date"] <= pd.Timestamp(f["d1"]))]
        row("🔥 " + escape(t("dl_celldays")), t("dl_celldays_d", n=f"{len(cd):,}"))
        st.download_button(t("dl_csv"), guide.search_csv("celldays", f["key"], f["d0"], f["d1"], f["low"], f["dn"]), file_name=guide.fname("celldays", f),
                           mime="text/csv", icon="⬇️", key="dl1")
        row("🛰️ " + escape(t("dl_raw")), t("dl_raw_d", n=f"{len(fr):,}"))
        st.download_button(t("dl_csv"), guide.search_csv("hotspots", f["key"], f["d0"], f["d1"], f["low"], f["dn"]),
                           file_name=guide.fname("hotspots", f), mime="text/csv", icon="⬇️", key="dl2")
        tt = data.in_range(data.area_monthly(f["key"], f["low"], f["dn"]), f["d0"], f["d1"])
        row("📅 " + escape(t("dl_monthly")), t("dl_monthly_d"))
        st.download_button(t("dl_csv"), guide.search_csv("monthly", f["key"], f["d0"], f["d1"], f["low"], f["dn"]), file_name=guide.fname("monthly", f), mime="text/csv", icon="⬇️", key="dl3")
        ev = guide.area_events(f)
        row("🔥 " + escape(t("dl_events")), t("dl_events_d", n=f"{len(ev):,}"))
        st.download_button(t("dl_csv"), guide.csv_bytes(ev.sort_values("start")), file_name=guide.fname("events", f), mime="text/csv",
                           icon="⬇️", key="dl4")
        row("📦 " + escape(t("dl_full")), t("dl_full_d"))
        if C.DOI_URL:
            st.link_button(t("open_doi"), C.DOI_URL, icon="📦")
        else:
            st.link_button(t("open_github"), C.REPO_URL + "/tree/main/outputs", icon="💻")
with c2:
    with st.container(key="dcard_reports"):
        from src import report
        ui.html(f'<h3>📄 {escape(t("dl_reports"))}</h3>')
        row("📄 " + escape(t("dl_report_area", area=name)), t("dl_report_d"))
        rl = st.segmented_control(t("language"), ["en", "sq"], default=lang, format_func=lambda x: x.upper(), key="rep_lang",
                                  required=True)
        if st.button(t("make_pdf"), icon="📄", type="primary", key="rep_btn"):
            with st.spinner(t("making_pdf")):
                pdf, fn = report.make_cached(f["key"], name, f["d0"].isoformat(), f["d1"].isoformat(), rl, f["low"], f["dn"])
            st.download_button(t("download_pdf"), pdf, file_name=fn, mime="application/pdf", icon="⬇️", key="rep_dl")
        row("🏛️ " + escape(t("dl_any_area")), t("dl_any_area_d"))
        opts = [f"adm1:{c}" for c in data.counties()] + [f"adm2:{m}" for c in data.counties() for m in data.municipalities(c)]
        pick = st.selectbox(t("area"), opts, key="rep_any", label_visibility="collapsed",
                            format_func=lambda o: (o.split(":")[1] + (f" · {t('county')}" if o.startswith("adm1") else f" · {data.county_of(o.split(':')[1])}")))
        if st.button(t("make_pdf"), icon="📄", key="rep_any_btn"):
            lvl, nm = pick.split(":")
            with st.spinner(t("making_pdf")):
                pdf, fn = report.make_cached((lvl, nm), nm, data.first_date().isoformat(), data.data_end().isoformat(), rl, False, "both")
            st.download_button(t("download_pdf"), pdf, file_name=fn, mime="application/pdf", icon="⬇️", key="rep_any_dl")

with c2:
    with st.container(key="dcard_art"):
        ui.html(f'<h3>🧵 {escape(t("dl_art"))}</h3>')
        row("🧵 " + escape(t("dl_poster_t")), t("dl_poster_d"))
        st.page_link(st.session_state["_pages"]["calendar"], label=t("open_embroidery"), icon="🧵")
        row("🖼️ " + escape(t("season_card")), t("dl_card_d"))
        if f["area"]["level"] in ("adm1", "adm2", "country"):
            from src import cards as cardmod
            if st.button(t("make_card"), icon="🖼️", key="mk_card_btn"):
                county = f["area"]["name"] if f["area"]["level"] == "adm1" else data.county_of(f["area"]["name"]) if f["area"]["level"] == "adm2" else ""
                png = cardmod.make_cached(f["key"], filters.area_name(f["area"]), county, lang)
                st.image(png, width=260)
                st.download_button(t("download_png"), png, file_name=f"VATRA_card_{guide.safe(filters.area_name(f['area'], 'en'))}_{lang}.png",
                                   mime="image/png", icon="⬇️", key="mk_card_dl")
        else:
            st.caption(t("card_needs_area"))

with st.container(key="dcard_teach"):
    from src import report
    ui.html(f'<h3>🏫 {escape(t("dl_teachers"))}</h3>')
    row("✏️ " + escape(t("dl_sheet")), t("dl_sheet_d"))
    st.download_button(t("download_pdf"), report.activity_sheet_cached(lang), file_name=f"VATRA_activity_sheet_{lang}.pdf",
                       mime="application/pdf", icon="⬇️", key="sheet")
    row("🎮 " + escape(t("kids_entry")), t("kids_play_only"))
    st.page_link(st.session_state["_pages"]["kids"], label=t("play_now"), icon="🎮")

ui.html(f'<div class="v-src" style="margin-top:10px">{escape(t("dl_note"))}</div>')
