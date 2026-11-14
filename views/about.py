"""About: who built VATRA and why, traditions, credits and licences, AI disclosure, disclaimer."""
from __future__ import annotations

from html import escape

import streamlit as st

import config as C
from src import data, ui
from src.i18n import fdate, t

theme, lang = ui.theme(), ui.lang()
ui.page_title("ℹ️", t("about_title"))
photo = ui.img_uri("viola_full_dark.png" if theme == "dark" else "viola_full_light.png")
s = data.summary()

a, b = st.columns([1, 2.6], gap="medium")
with a:
    ui.html(ui.card(f'<div style="text-align:center"><img src="{photo}" alt="Viola Zeneli in Albanian traditional costume" '
                    f'style="width:100%;max-width:320px;border-radius:12px;border:3px solid var(--gold)"><div class="v-cinzel" style="font-size:1.3rem;font-weight:700;margin-top:6px">'
                    f'Viola Zeneli</div><div class="v-small"><a href="{C.ORCID_URL}" target="_blank">ORCID 0009-0000-2815-6398</a></div><div class="v-small v-muted">Team Viola Fusion · {escape(t("solo"))} · Universal Event</div>'
                    f'<div class="v-small v-muted">✦ {escape(t("ai_photo"))} <span class="v-ai">AI</span></div></div>'))
with b:
    srcs = [("https://www.eeas.europa.eu/delegations/albania/united-response-eu-assistance-albania%E2%80%99s-summer-wildfires_en", "EU Delegation to Albania (2025)"),
            ("https://www.tiranatimes.com/fires-damage-many-forests-eu-helps-fight-them_112525/", "Tirana Times"),
            ("https://www.euronews.com/2024/07/17/albania-continues-to-tackle-wildfires-spreading-up-north-of-country", "Euronews (2024)"),
            ("https://exit.al/en/?p=153995", "Exit News (2021)")]
    src_html = (f'<div class="v-src" style="margin-bottom:.9rem">{escape(t("why_sources"))}: ' +
                " · ".join(f'<a href="{u}" target="_blank" rel="noopener">{escape(n)}</a>' for u, n in srcs) + "</div>")
    paras = [
        ("why_title", f'<p>{escape(t("why_text"))}</p><p>{escape(t("why_text2"))}</p>{src_html}'),
        ("traditions_title", f'<p>{escape(t("heritage_text"))}</p>'),
        ("challenge_title", f'<p>NASA Space Apps Challenge 2026 · <b>Harmonization of MODIS and VIIRS Hot Spots</b>. {escape(t("challenge_text"))}</p>'),
        ("credits_title", "<ul class='v-small'>" + "".join(f"<li>{x}</li>" for x in [
            t("credit_firms_short"), t("credit_effis"), t("credit_gb"), t("credit_ocha"), t("credit_tiles"), t("credit_fonts"), t("credit_tools"),
            t("credit_license")]) + "</ul>"),
    ]
    ui.html(ui.card("".join(f"<h3>{escape(t(k))}</h3>{v}" for k, v in paras), dia=True))
    with st.expander(t("full_citations")):
        cites = [("MODIS Collection 6.1, near real time (MCD14DL)", "10.5067/FIRMS/MODIS/MCD14DL.NRT.0061"),
                 ("MODIS Collection 6.1, standard archive (MCD14ML)", "10.5067/FIRMS/MODIS/MCD14ML"),
                 ("VIIRS 375 m, S-NPP (VNP14IMGTDL)", "10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002"),
                 ("VIIRS 375 m, NOAA-20 (VJ114IMGTDL)", "10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002"),
                 ("VIIRS 375 m, NOAA-21 (VJ214IMGTDL)", "10.5067/VIIRS/VJ214IMG_NRT.002"),
                 ("Giglio, Schroeder & Justice (2016), MODIS active fire algorithm", "10.1016/j.rse.2016.02.054"),
                 ("Schroeder et al. (2014), VIIRS 375 m active fire algorithm", "10.1016/j.rse.2013.12.008")]
        ui.html('<ul class="v-small" style="margin:0">' + "".join(
            f'<li>{escape(n)}: <a href="https://doi.org/{d}" target="_blank" rel="noopener">doi.org/{d}</a></li>' for n, d in cites)
            + f'<li>NASA FIRMS: <a href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noopener">firms.modaps.eosdis.nasa.gov</a> · LANCE, NASA ESDIS</li></ul>')
    tail = [
        ("ai_title", f'<p class="v-small">{escape(t("ai_text"))}</p>'),
        ("disclaimer_title", f'<p class="v-small">{escape(t("disclaimer"))}</p>'),
        ("data_status", f'<p class="v-small">{escape(t("data_status_text", end=fdate(s["data_end"]), built=s["build_time_utc"][:10]))}</p>'),
    ]
    ui.html(ui.card("".join(f"<h3>{escape(t(k))}</h3>{v}" for k, v in tail)))
    links = [("GitHub", C.REPO_URL, "💻")]
    if C.DOI_URL:
        links.append(("DOI", C.DOI_URL, "📦"))
    if C.VIDEO_URL:
        links.append((t("video"), C.VIDEO_URL, "🎬"))
    links.append(("NASA FIRMS", "https://firms.modaps.eosdis.nasa.gov/", "🛰️"))
    for col, (lab, url, ic) in zip(st.columns(len(links) + (4 - len(links)), gap="small"), links):
        col.link_button(lab, url, icon=ic, use_container_width=True)
