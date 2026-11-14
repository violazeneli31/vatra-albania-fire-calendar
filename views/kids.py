"""For Kids: VATRA Kids · Sky Twins (played only inside the app) + certificate."""
from __future__ import annotations

from html import escape

import streamlit as st

import config as C
from src import ui
from src.i18n import t

lang, theme = ui.lang(), ui.theme()
photo = ui.img_uri("viola_circle_light.png")
ui.html(f'<div class="v-row" style="flex-wrap:nowrap;margin:.4rem 0 .6rem"><img src="{photo}" width="64" height="64" class="v-ring" alt="Viola">'
        f'<div><h1 style="margin:0">🎮 VATRA Kids: Sky Twins</h1><div class="v-muted">{escape(t("kids_hello"))}</div></div></div>')

html = (C.GAME / "sky_twins.html").read_text(encoding="utf-8").replace("__LANG__", lang).replace("__VIOLA__", photo)
st.iframe(html, height=760)
ui.html(f'<div class="v-src">{escape(t("kids_privacy"))}</div>')

with st.expander(t("cert_backup_title")):
    from src import certificate
    name = st.text_input(t("cert_name_label"), max_chars=30, key="cert_name", placeholder=t("cert_name_label"))
    ok = certificate.valid(name)
    if name and not ok:
        st.caption(t("cert_name_rule"))
    c1, c2 = st.columns(2)
    if ok:
        png = certificate.png(name, lang)
        st.image(png, use_container_width=True)
        c1.download_button("⬇ PNG", png, file_name=certificate.filename(name, "png"), mime="image/png", use_container_width=True)
        c2.download_button("⬇ PDF (A4)", certificate.pdf(name, lang), file_name=certificate.filename(name, "pdf"),
                           mime="application/pdf", use_container_width=True)
