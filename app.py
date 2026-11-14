"""VATRA · Albania's Fire Calendar. Run: streamlit run app.py"""
from __future__ import annotations

import streamlit as st

import config as C

st.set_page_config(page_title="VATRA · Albania's Fire Calendar", page_icon=str(C.ASSETS / "favicon.png"),
                   layout="wide", initial_sidebar_state="collapsed",
                   menu_items={"About": "VATRA · Albania's Fire Calendar · NASA Space Apps Challenge 2026 · Viola Zeneli"})

from src import filters, guide, ui  # noqa: E402
from src.i18n import t  # noqa: E402

if not (C.OUT / "monthly_harmonized.parquet").exists():
    st.error("outputs/ is missing. Run `python build.py` once, then restart the app.")
    st.stop()

filters.init()
ss = st.session_state
ss["w_lang"] = ss["lang"]
ui.inject_css()  # first, so the opening screen covers everything from the very start
ui.loader()

NO_MODE = {"downloads"}  # pages where the Harmonized / Raw switch changes nothing
PAGES = [  # (id, file, title key, icon, show filter bar)
    ("home", "views/home.py", "nav_home", "🏠", True),
    ("calendar", "views/calendar.py", "nav_calendar", "📅", True),
    ("map", "views/map.py", "nav_map", "🗺️", True),
    ("compare", "views/compare.py", "nav_compare", "📊", True),
    ("regions", "views/regions.py", "nav_regions", "🏔️", True),
    ("story", "views/story.py", "nav_story", "📖", False),
]
MORE = [
    ("heritage", "views/heritage.py", "nav_heritage", "🏛️", False),
    ("method", "views/method.py", "nav_method", "⚙️", False),
    ("downloads", "views/downloads.py", "nav_downloads", "⬇️", True),
    ("kids", "views/kids.py", "nav_kids", "🎮", False),
    ("about", "views/about.py", "nav_about", "ℹ️", False),
]
objs = {}
for pid, path, key, icon, _ in PAGES + MORE:
    objs[pid] = st.Page(path, title=t(key), icon=icon, url_path=pid, default=(pid == "home"))
ss["_pages"] = objs
pg = st.navigation({"": [objs[p[0]] for p in PAGES], t("nav_more"): [objs[p[0]] for p in MORE]}, position="top")
current = next((p for p in PAGES + MORE if objs[p[0]] == pg), PAGES[0])
ss["_page_id"] = current[0]

ui.header()
if current[4]:
    filters.render(show_mode=current[0] not in NO_MODE)

pg.run()

ui.footer()
guide.fab()

if not ss.get("_toast_shown"):
    ss["_toast_shown"] = True
    st.toast(t("toast_new"), icon="👋")
