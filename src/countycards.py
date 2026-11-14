"""The 12 county cards (icon, fire curve, did-you-know, Open button). Shown on the Regions page."""
from __future__ import annotations

from html import escape

import streamlit as st

import config as C
from src import charts, data, filters, motifs
from src.i18n import t


def render(lang: str, key_prefix: str = "cty"):
    from src import ui
    counties = data.content("counties.json")["counties"]
    m = data.monthly()
    for i in range(0, len(counties), 4):
        cols = st.columns(4, gap="small")
        for c, col in zip(counties[i:i + 4], cols):
            with col:
                with st.container(key=f"dcard_{key_prefix}_{c['id']}"):
                    med = m[(m["area_level"] == "adm1") & (m["area_name"] == c["name"])].groupby("month")["median"].first()
                    dyk = c["did_you_know"][0][f"text_{lang}"] if c.get("did_you_know") else ""
                    ui.html(f'<div class="v-row" style="flex-wrap:nowrap">{motifs.county_icon(c["name"], C.GOLD, 44)}'
                            f'<div><b class="v-cinzel" style="font-size:1.05rem">{escape(c["name"])}</b>'
                            f'<div>{charts.mini_curve_svg(med.reindex(range(1, 13)).fillna(0).to_numpy(), col="var(--red)")}</div></div></div>'
                            f'<div class="v-small v-muted" style="margin-top:6px;min-height:3.6em">💡 {escape(dyk)}</div>')
                    st.button(t("open_region"), key=f"{key_prefix}_{c['id']}", on_click=filters.set_area,
                              args=("adm1", c["name"]), use_container_width=True)
