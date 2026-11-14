"""Shared filter bar and session state. Values live in plain session keys (f_*) so they survive page changes;
widgets (w_*) are synced from them on every run."""
from __future__ import annotations

from datetime import date, timedelta
from html import escape

import streamlit as st

import config as C
from src import data
from src.i18n import area_label, fdate, t

DEFAULTS = {"lang": "en", "theme": "light", "f_area": {"level": "country", "name": C.COUNTRY},
            "f_mode": "h", "f_low": False, "f_dn": "both", "f_quick": "all"}


def init():
    ss = st.session_state
    for k, v in DEFAULTS.items():
        if k not in ss:
            ss[k] = v.copy() if isinstance(v, dict) else v
    if "f_d0" not in ss:
        ss["f_d0"], ss["f_d1"] = default_dates()


def default_dates() -> tuple[date, date]:
    return data.first_date(), latest_date()


def latest_date() -> date:
    from src import api
    lat = api.latest_info().get("end")
    end = data.data_end()
    return max(end, lat) if lat else end


def get() -> dict:
    ss = st.session_state
    area = ss["f_area"]
    return {"area": area, "key": data.area_key(area), "d0": ss["f_d0"], "d1": ss["f_d1"], "mode": ss["f_mode"],
            "low": ss["f_low"], "dn": ss["f_dn"], "lang": ss["lang"], "theme": ss["theme"]}


# ------------------------------------------------------------------ setters used by pages and callbacks
def set_area(level: str, name: str | None = None, **kw):
    a = {"level": level, "name": name or C.COUNTRY}
    a.update(kw)
    st.session_state["f_area"] = a


def set_dates(d0: date, d1: date, quick: str | None = None):
    st.session_state["f_d0"], st.session_state["f_d1"] = d0, d1
    st.session_state["f_quick"] = quick


def reset():
    for k, v in DEFAULTS.items():
        if k not in ("lang", "theme"):
            st.session_state[k] = v.copy() if isinstance(v, dict) else v
    st.session_state["f_d0"], st.session_state["f_d1"] = default_dates()


def on_lang():
    v = st.session_state.get("w_lang")
    if v:
        st.session_state["lang"] = v


def toggle_theme():
    st.session_state["theme"] = "dark" if st.session_state.get("theme") == "light" else "light"


def _on_area():
    v = st.session_state.get("w_area")
    if not v or v == "custom":
        return
    lvl, _, name = v.partition(":")
    set_area(lvl, name or C.COUNTRY)


def _on_dates():
    v = st.session_state.get("w_dates")
    if isinstance(v, (tuple, list)) and len(v) == 2:
        set_dates(v[0], v[1], None)


def _on_quick():
    q = st.session_state.get("w_quick")
    end = latest_date()
    if q == "30":
        set_dates(end - timedelta(days=29), end, "30")
    elif q == "year":
        set_dates(date(end.year, 1, 1), end, "year")
    elif q == "all":
        set_dates(data.first_date(), end, "all")


def _on_mode():
    v = st.session_state.get("w_mode")
    if v:
        st.session_state["f_mode"] = v


def _on_opts():
    st.session_state["f_low"] = bool(st.session_state.get("w_low"))
    st.session_state["f_dn"] = st.session_state.get("w_dn") or "both"


def _use_circle():
    set_area("circle", "circle", lat=float(st.session_state["w_lat"]), lon=float(st.session_state["w_lon"]),
             r_km=float(st.session_state["w_r"]))


# ------------------------------------------------------------------ labels
def area_code(a: dict) -> str:
    if a["level"] in ("circle", "polygon"):
        return "custom"
    if a["level"] == "country":
        return "country"
    return f"{a['level']}:{a['name']}"


def area_name(a: dict | None = None, lang: str | None = None) -> str:
    a = a or st.session_state["f_area"]
    lang = lang or st.session_state.get("lang", "en")
    if a["level"] == "circle":
        return t("area_circle", lang, lat=f"{a['lat']:.2f}", lon=f"{a['lon']:.2f}", r=f"{a['r_km']:g}")
    if a["level"] == "polygon":
        return t("area_drawn", lang)
    if a["level"] == "country":
        return C.COUNTRY_SQ if lang == "sq" else C.COUNTRY
    return a["name"]


def area_full(a: dict | None = None) -> str:
    a = a or st.session_state["f_area"]
    if a["level"] in ("adm1", "adm2"):
        return area_label(a["level"], a["name"])
    return area_name(a)


def mode_label(m: str) -> str:
    return {"h": t("mode_h"), "m": t("mode_m"), "v": t("mode_v")}[m]


def summary_line(show_mode: bool = True) -> str:
    f = get()
    span = f"{fdate(f['d0'])} – {fdate(f['d1'])}"
    extra = []
    if f["low"]:
        extra.append(t("opt_low_short"))
    if f["dn"] != "both":
        extra.append(t("dn_" + f["dn"]))
    mode = f" · {mode_label(f['mode'])}" if show_mode else ""
    return f"📍 {area_full(f['area'])} · {span}{mode}" + (" · " + " · ".join(extra) if extra else "")


def _area_options() -> list[str]:
    opts = ["country"] + [f"adm1:{c}" for c in data.counties()]
    for c in data.counties():
        opts += [f"adm2:{m}" for m in data.municipalities(c)]
    if st.session_state["f_area"]["level"] in ("circle", "polygon"):
        opts = ["custom"] + opts
    return opts


def _fmt_area(code: str) -> str:
    if code == "custom":
        return "✏️ " + area_name()
    if code == "country":
        return "🇦🇱 " + (C.COUNTRY_SQ if st.session_state["lang"] == "sq" else C.COUNTRY)
    lvl, _, name = code.partition(":")
    if lvl == "adm1":
        return f"{name} · {t('county')}"
    return f"   {name} · {data.county_of(name)}"


# ------------------------------------------------------------------ the bar
def render(compact: bool = False, show_mode: bool = True):
    ss = st.session_state
    end = latest_date()
    first = data.first_date()
    # sync widgets from the stored values
    ss["w_area"] = area_code(ss["f_area"])
    ss["w_dates"] = (ss["f_d0"], ss["f_d1"])
    ss["w_quick"] = ss.get("f_quick")
    ss["w_mode"] = ss["f_mode"]
    ss["w_low"] = ss["f_low"]
    ss["w_dn"] = ss["f_dn"]
    with st.container(key="filterbar"):
        r1 = st.container(key="fb_row1").columns([2.4, 1.25, 2.1, 3.2], vertical_alignment="center", gap="small")
        with r1[0]:
            st.selectbox(t("area"), _area_options(), format_func=_fmt_area, key="w_area", on_change=_on_area,
                         label_visibility="collapsed", help=t("area_help"))
        with r1[1]:
            with st.popover(t("custom_area"), icon="📍", use_container_width=True):
                st.markdown(f"**{t('custom_area_title')}**")
                a = ss["f_area"]
                c1, c2, c3 = st.columns(3)
                c1.number_input(t("lat"), 39.5, 42.8, float(a.get("lat", 40.47)), 0.01, format="%.2f", key="w_lat")
                c2.number_input(t("lon"), 19.0, 21.2, float(a.get("lon", 19.49)), 0.01, format="%.2f", key="w_lon")
                c3.number_input(t("radius_km"), 1.0, 100.0, float(a.get("r_km", 15.0)), 1.0, key="w_r")
                st.button(t("use_circle"), on_click=_use_circle, type="primary", use_container_width=True)
                st.page_link(ss["_pages"]["map"], label=t("draw_on_map"), icon="🗺️")
        with r1[2]:
            st.date_input(t("dates"), min_value=first, max_value=max(end, date.today()), key="w_dates",
                          on_change=_on_dates, format="DD.MM.YYYY", label_visibility="collapsed")
        with r1[3]:
            st.pills(t("quick"), ["30", "year", "all"], format_func=lambda q: t("quick_" + q), key="w_quick",
                     on_change=_on_quick, label_visibility="collapsed")
        if show_mode:
            r2 = st.container(key="fb_row2").columns([3.4, 1.3, .9, 4.4], vertical_alignment="center", gap="small")
            with r2[0]:
                st.segmented_control(t("mode"), ["h", "m", "v"], format_func=mode_label, key="w_mode", on_change=_on_mode,
                                     label_visibility="collapsed", required=True, help=t("mode_help"))
            r2 = r2[1:]
        else:
            r2 = st.container(key="fb_row2").columns([1.3, .9, 7.8], vertical_alignment="center", gap="small")
        with r2[0]:
            with st.popover(t("options"), icon="⚙️", use_container_width=True):
                st.checkbox(t("opt_low"), key="w_low", on_change=_on_opts, help=t("opt_low_help"))
                st.radio(t("daynight"), ["both", "day", "night"], format_func=lambda x: t("dn_" + x), key="w_dn",
                         on_change=_on_opts, horizontal=True)
        with r2[1]:
            st.button(t("reset"), on_click=reset, type="tertiary", help=t("reset_help"))
        with r2[2]:
            st.html(f'<div class="v-summary">{escape(summary_line(show_mode))}</div>')
