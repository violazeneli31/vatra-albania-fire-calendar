"""Guide "Viola": prepared answers computed from the app's data (no language model).

Every answer = one plain sentence + key numbers + a small chart + "Learn more" + Listen (English).
Answers follow the current area, dates and language. Numbers are never invented.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from datetime import timedelta
from html import escape

import numpy as np
import pandas as pd
import streamlit as st

import config as C
from src import charts, data, filters, ui
from src.i18n import fdate, month, num, pct, status_label, t


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def questions() -> list[dict]:
    return data.content("guide.json")["questions"]


TALK = {  # small talk, matched before the fire questions
    "hello": ["hi", "hello", "hey", "hej", "pershendetje", "tung", "ckemi", "mirdita", "miremengjes", "good morning", "good evening"],
    "thanks": ["thanks", "thank", "thx", "faleminderit", "flm", "rrofsh", "merci"],
    "who": ["who are you", "what are you", "your name", "who is viola", "kush je", "cfare je", "si te quajne", "emri yt", "are you ai", "are you a bot", "chatbot"],
    "help": ["help", "what can you do", "what do you know", "ndihme", "cfare di", "cfare mund", "me ndihmo"],
    "bye": ["bye", "goodbye", "see you", "mirupafshim", "ciao", "naten e mire"],
}


def talk(text: str) -> str | None:
    n = " " + " ".join(re.findall(r"[\w]+", _norm(text))) + " "
    words = n.split()
    for kind, keys in TALK.items():
        for k in keys:
            if (" " in k and f" {k} " in n) or (" " not in k and k in words):
                # a greeting followed by a real question goes to the question
                if kind == "hello" and len(words) > 3:
                    continue
                return kind
    return None


def scores(text: str) -> list[tuple[str, float]]:
    """Keyword match (EN + SQ), tolerant to typos. Returns (question id, score), best first."""
    words = re.findall(r"[\w]+", _norm(text or ""))
    out = []
    for q in questions():
        kws = [_norm(k) for k in q.get("keywords_en", []) + q.get("keywords_sq", [])]
        score = 0.0
        for w in words:
            if len(w) < 3:
                continue
            for k in kws:
                if w == k or (len(k) >= 4 and (w.startswith(k) or k.startswith(w))):
                    score += 1.0
                else:
                    r = difflib.SequenceMatcher(None, w, k).ratio()
                    if r >= .8:
                        score += r * .8
        out.append((q["id"], score))
    return sorted(out, key=lambda x: -x[1])


def match(text: str) -> str | None:
    if not text or not text.strip():
        return None
    best = scores(text)
    return best[0][0] if best and best[0][1] >= .8 else None


def suggestions(text: str, n: int = 3) -> list[str]:
    ranked = [q for q, sc in scores(text) if sc > 0 and q not in ("tour", "kids")]
    for d in ("months", "now", "harmonization", "events", "latest"):
        if d not in ranked:
            ranked.append(d)
    return ranked[:n]


# ------------------------------------------------------------------ answers
def _ctx():
    f = filters.get()
    tt = data.area_monthly(f["key"], f["low"], f["dn"])
    return f, tt, filters.area_full(f["area"])


def _ans(text, chart=None, page=None, extra=None, numbers=None):
    return {"text": text, "chart": chart, "page": page, "extra": extra, "numbers": numbers or []}


def a_report(theme):
    f, tt, name = _ctx()

    def extra():
        from src import report
        if st.button(t("g_make_pdf"), key="g_pdf_btn", type="primary"):
            with st.spinner(t("making_pdf")):
                pdf, fname = report.make_cached(f["key"], filters.area_full(f["area"]), f["d0"].isoformat(), f["d1"].isoformat(), f["lang"], f["low"], f["dn"])
            st.download_button(t("download_pdf"), pdf, file_name=fname, mime="application/pdf", key="g_pdf_dl", icon="⬇️")
    return _ans(t("g_report", area=name, d0=fdate(f["d0"]), d1=fdate(f["d1"])), page="downloads", extra=extra)


def a_months(theme):
    f, tt, name = _ctx()
    n = data.normals_for(tt)
    if n["mean"].sum() <= 0:
        return _ans(t("g_too_little", area=name))
    s = data.seasons_for(f["key"], None if data.is_predefined(f["area"]) and not f["low"] and f["dn"] == "both" else tt)
    order = n.sort_values(["median", "mean"], ascending=False)["month"].tolist()[:3]
    nat = data.normals_for(data.area_monthly(("country", C.COUNTRY)))
    share = 100 * n["mean"].sum() / nat["mean"].sum() if nat["mean"].sum() else None
    txt = t("g_months", area=name, m1=month(order[0], full=True), m2=month(order[1], full=True), m3=month(order[2], full=True),
            start=month(s["start"], full=True) if s["start"] else "–", end=month(s["end"], full=True) if s["end"] else "–",
            peak=month(s["peak"], full=True) if s["peak"] else "–")
    if share is not None and f["area"]["level"] != "country":
        txt += " " + t("g_share", share=num(share, digits=1))
    return _ans(txt, charts.mini_months(n["median"].where(n["median"] > 0, n["mean"]).to_numpy(), theme, s["season_months"]), "calendar")


def a_now(theme):
    from src import api
    f, tt, name = _ctx()
    det, cdl, info = api.latest()
    daily = data.area_daily(f["key"], f["low"], f["dn"]).copy()
    if len(cdl):
        extra = cdl[data.mask(cdl, f["key"])].groupby("date")["weight"].sum()
        daily = pd.concat([daily, extra]).groupby(level=0).sum()
    end = info.get("end") or data.data_end()
    w30 = data.window_compare(daily, end, 30)
    w7 = data.window_compare(daily, end, 7)
    txt = t("g_now", area=name, v7=num(w7["value"], digits=1), m7=num(w7["median"], digits=1), v30=num(w30["value"], digits=1),
            m30=num(w30["median"], digits=1), p=num(w30["percentile"]), status=status_label(w30["status"]).lower(), end=fdate(end))
    if not info.get("end"):
        txt += " " + t("latest_unavailable", end=fdate(data.data_end()))
    return _ans(txt, charts.gauge(w30["percentile"], w30["status"], theme, 180), "compare")


def a_two_years(theme):
    f, tt, name = _ctx()
    yt = tt[(tt["year"] >= 2001) & (tt["year"] <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum()
    if yt.sum() <= 0:
        return _ans(t("g_too_little", area=name))
    ya = int(yt.idxmax())
    yb = C.BASE_YEARS[1] if ya != C.BASE_YEARS[1] else C.BASE_YEARS[1] - 1
    a, b = yt.get(ya, 0), yt.get(yb, 0)
    diff = 100 * (a - b) / b if b else None
    d = (tt[tt["year"] == ya].set_index("month")["harmonized"] - tt[tt["year"] == yb].set_index("month")["harmonized"]).abs()
    txt = t("g_two_years", area=name, ya=ya, yb=yb, a=num(a), b=num(b), diff=pct(diff) if diff is not None else "–",
            m=month(int(d.idxmax()), full=True) if len(d) else "–")
    return _ans(txt, charts.two_years(tt, ya, yb, theme, 200), "compare")


def a_trend(theme):
    f, tt, name = _ctx()
    tr = data.trend_for(tt)
    if tr.get("slope") is None:
        return _ans(t("g_too_little", area=name))
    key = {"up": "g_trend_up", "down": "g_trend_down"}.get(tr["direction"], "g_trend_none")
    txt = t(key, area=name, pct=pct(tr["pct_per_year"], digits=1) if tr["pct_per_year"] is not None else "–",
            p=num(tr["p"], digits=2), years=tr["years"].replace("-", "–")) + " " + t("trend_caveat")
    return _ans(txt, charts.trend_chart(tt, tr, theme, 200), "compare")


def a_sensors(theme):
    return _ans(t("g_sensors"), page="method")


def a_harmonization(theme):
    v = data.js("validation.json")["national"]["test"]
    txt = t("g_harmonization", r=num(v["pearson"], digits=2), rho=num(v["spearman"], digits=2), bias=pct(v["bias_pct"], digits=0))
    nat = data.area_monthly(("country", C.COUNTRY))
    return _ans(txt, charts.raw_vs_harmonized(nat, theme, 200), "method")


def a_csv(theme):
    f, tt, name = _ctx()

    def extra():
        st.download_button(t("dl_celldays_csv"), search_csv("celldays", f["key"], f["d0"], f["d1"], f["low"], f["dn"]),
                           file_name=fname("hotspots", f), mime="text/csv", key="g_csv", icon="⬇️")
    return _ans(t("g_csv", area=name), page="downloads", extra=extra)


def a_where(theme):
    f, tt, name = _ctx()
    cd = data.area_celldays(f["key"], f["low"], f["dn"])
    cd = cd[(cd["date"] >= pd.Timestamp(f["d0"])) & (cd["date"] <= pd.Timestamp(f["d1"]))]
    col = "adm2" if f["area"]["level"] in ("adm1", "adm2", "circle", "polygon") else "adm1"
    r = cd.groupby(col, observed=True)["weight"].sum().sort_values(ascending=False).head(6)
    r = r[r > 0]
    if len(r) == 0:
        return _ans(t("g_too_little", area=name))
    txt = t("g_where", area=name, list=", ".join(f"{k} ({num(v)})" for k, v in r.head(3).items()))
    return _ans(txt, charts.ranking(list(r.index), list(r.values), theme, 200), "regions")


def a_heritage(theme):
    f, tt, name = _ctx()
    hn = data.csv("heritage_nearby.csv")
    hn = hn[(hn["year"] >= f["d0"].year) & (hn["year"] <= f["d1"].year)]
    s = hn.groupby("name_en")["fire_celldays_5km"].sum().sort_values(ascending=False)
    if len(s) == 0:
        return _ans(t("g_too_little", area=name))
    names = data.content("heritage_sites.csv").set_index("name_en")["name_sq"].to_dict()
    lab = lambda k: names.get(k, k) if st.session_state.get("lang") == "sq" else k
    txt = t("g_heritage", list=", ".join(f"{lab(k)} {num(v)}" for k, v in s.head(4).items()), y0=f["d0"].year, y1=f["d1"].year)
    return _ans(txt, charts.ranking([lab(k) for k in s.head(6).index], list(s.head(6).values), theme, 200, C.GOLD), "heritage")


def a_events(theme):
    f, tt, name = _ctx()
    ev = area_events(f)
    if len(ev) == 0:
        return _ans(t("g_too_little", area=name))
    e = ev.iloc[0]
    near = t("g_near", km=num(e["site_km"], digits=1), site=e["nearest_site"]) if pd.notna(e["site_km"]) and e["site_km"] <= 10 else ""
    txt = t("g_events", area=name, start=fdate(e["start"]), end=fdate(e["end"]), mun=e["municipality"], days=int(e["days"]),
            cd=int(e["cell_days"]), near=near, n=len(ev))
    top = ev.head(8)
    lab = [f"{fdate(r.start, with_year=True)} · {r.municipality}" for r in top.itertuples()]
    return _ans(txt, charts.ranking(lab, list(top["cell_days"]), theme, 220), "regions")


def a_latest(theme):
    from src import api
    f, tt, name = _ctx()
    det, cdl, info = api.latest()
    end = info.get("end")
    cd = data.area_celldays(f["key"], f["low"], f["dn"])
    last = (end or data.data_end())
    start = last - timedelta(days=6)
    recent = cd[cd["date"] >= pd.Timestamp(start)]
    n_file = len(recent)
    n_api = int(data.mask(cdl, f["key"]).sum()) if len(cdl) else 0
    if not end:
        txt = t("g_latest_noapi", area=name, n=num(n_file), end=fdate(data.data_end()))
    else:
        txt = t("g_latest", area=name, n=num(n_file + n_api), start=fdate(start), end=fdate(last))
    return _ans(txt, page="map")


def a_daynight(theme):
    f, tt, name = _ctx()
    fr = data.area_fires(f["key"], f["low"], "both")
    fr = fr[(fr["date"] >= pd.Timestamp(f["d0"])) & (fr["date"] <= pd.Timestamp(f["d1"]))]
    if len(fr) == 0:
        return _ans(t("g_too_little", area=name))
    d = float((fr["daynight"] == "D").mean() * 100)
    return _ans(t("g_daynight", area=name, d=num(d), n=num(100 - d)), page="calendar")


def a_confidence(theme):
    ci = data.summary()["cleaning"]
    return _ans(t("g_confidence", t23=num(ci["type_2_or_3_dropped"]), st=num(ci["nrt_in_static_cells_dropped"]),
                  out=num(ci["outside_country_dropped"]), low=num(ci["low_confidence_rows"])), page="method")


def a_effis(theme):
    e = data.js("validation.json")["effis"]
    nat = e["national"]
    txt = t("g_effis", r=num(nat.get("yearly_pearson"), digits=2), rho=num(nat.get("yearly_spearman"), digits=2),
            share=num(100 * e["share_celldays_inside"]), ev=num(100 * (e.get("top50_events_matched_share") or 0)))
    tab = data.csv("effis_comparison.csv")
    tab = tab[(tab["area_level"] == "country")]
    return _ans(txt, charts.effis_chart(tab, theme, 200), "method")


def a_colours(theme):
    return _ans(t("g_colours"), page="calendar", extra=lambda: ui.html(ui.legend_ramp() + ui.legend_ramp(True)))


def a_kids(theme):
    return _ans(t("g_kids"), page="kids")


ANSWERS = {"report": a_report, "months": a_months, "now": a_now, "two_years": a_two_years, "trend": a_trend,
           "sensors": a_sensors, "harmonization": a_harmonization, "csv": a_csv, "where": a_where, "heritage": a_heritage,
           "events": a_events, "latest": a_latest, "daynight": a_daynight, "confidence": a_confidence, "effis": a_effis,
           "colours": a_colours, "tour": None, "kids": a_kids}


# ------------------------------------------------------------------ helpers shared with pages
def area_events(f) -> pd.DataFrame:
    ev = data.events()
    ev = ev[(ev["start"] >= pd.Timestamp(f["d0"])) & (ev["start"] <= pd.Timestamp(f["d1"]))]
    lvl = f["area"]["level"]
    if lvl == "adm1":
        ev = ev[ev["county"] == f["area"]["name"]]
    elif lvl == "adm2":
        ev = ev[ev["municipality"] == f["area"]["name"]]
    elif lvl in ("circle", "polygon"):
        ev = ev[data.mask(ev, f["key"])]
    return ev.sort_values("cell_days", ascending=False)


@st.cache_data(show_spinner=False, max_entries=32)
def search_csv(kind: str, key: tuple, d0, d1, low: bool, dn: str) -> bytes:
    """CSV of the current search, cached so the Downloads page stays fast."""
    if kind == "celldays":
        df = data.area_celldays(key, low, dn)
        df = df[(df["date"] >= pd.Timestamp(d0)) & (df["date"] <= pd.Timestamp(d1))].drop(columns=["year", "month"])
    elif kind == "hotspots":
        df = data.area_fires(key, low, dn)
        df = df[(df["date"] >= pd.Timestamp(d0)) & (df["date"] <= pd.Timestamp(d1))].drop(columns=["hhmm", "year", "month"], errors="ignore")
    else:
        df = data.in_range(data.area_monthly(key, low, dn), d0, d1)
    return csv_bytes(df)


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8-sig")


def safe(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^A-Za-z0-9-]+", "_", s).strip("_")


def fname(kind: str, f: dict, ext: str = "csv") -> str:
    return f"VATRA_{kind}_{safe(filters.area_name(f['area'], 'en'))}_{f['d0']:%Y%m%d}_{f['d1']:%Y%m%d}.{ext}"


# ------------------------------------------------------------------ the panel
def _ask(qid):
    st.session_state["g_q"] = qid


def _on_text():
    txt = st.session_state.get("g_text", "")
    if not txt.strip():
        return
    k = talk(txt)
    if k:
        st.session_state["g_q"] = "__talk__" + k
        return
    q = match(txt)
    if not q:
        st.session_state["g_sugg"] = suggestions(txt)
    st.session_state["g_q"] = q or "__none__"


def _bubble(text: str, theme: str):
    photo = ui.img_uri("viola_circle_dark.png" if theme == "dark" else "viola_circle_light.png")
    ui.html(f'<div class="v-answer"><div class="v-row" style="flex-wrap:nowrap;align-items:flex-start">'
            f'<img src="{photo}" width="30" height="30" class="v-ring" alt="Viola">'
            f'<div class="v-small">{escape(text)}</div></div></div>')


def render_answer(theme):
    qid = st.session_state.get("g_q")
    if not qid:
        return
    lang = ui.lang()
    if qid.startswith("__talk__"):
        _bubble(t("g_" + qid[8:]), theme)
        return
    if qid == "__none__":
        _bubble(t("g_fallback"), theme)
        qs = {q["id"]: q for q in questions()}
        for sid in st.session_state.get("g_sugg", ["months", "now", "harmonization"]):
            if sid in qs:
                st.button("👉 " + (qs[sid]["sq"] if lang == "sq" else qs[sid]["en"]), key=f"gs_{sid}", on_click=_ask,
                          args=(sid,), type="primary", use_container_width=True)
        ui.html(f'<div class="v-src">{escape(t("g_fallback_more"))}</div>')
        return
    fn = ANSWERS.get(qid)
    if fn is None:
        return
    try:
        a = fn(theme)
    except Exception as e:  # never break the page because of one answer
        ui.html(f'<div class="v-answer v-small">{escape(t("g_error"))}</div>')
        return
    _bubble(a["text"], theme)
    if a["chart"] is not None:
        st.plotly_chart(a["chart"], config=charts.CFG_STATIC, theme=None, key=f"g_chart_{qid}")
    if a["extra"]:
        a["extra"]()
    cols = st.columns([1, 1])
    with cols[0]:
        ui.listen(a["text"], f"g_listen_{qid}")
    with cols[1]:
        if a["page"]:
            st.page_link(st.session_state["_pages"][a["page"]], label=t("learn_more"))


@st.fragment
def panel():
    theme = ui.theme()
    lang = ui.lang()
    ui.html('<div class="v-band"></div>')
    full = "viola_full_dark.png" if theme == "dark" else "viola_full_light.png"
    if (C.ASSETS / full).exists():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            ui.html(f'<div style="text-align:center"><img src="{ui.img_uri(full)}" alt="Viola" '
                    f'style="width:200px;max-width:100%;height:auto;border-radius:10px"></div>')
    ui.html(f'<div class="v-src" style="text-align:center">✦ {escape(t("ai_photo"))}</div>'
            f'<h3 style="margin:.4rem 0 .1rem">{escape(t("g_hi"))}</h3><div class="v-small">{escape(t("g_hi_text"))}</div>'
            f'<div class="v-src" style="margin-top:4px">{escape(t("g_label"))}</div>')
    tab1, tab2, tab3 = st.tabs([f"🔥 {t('g_tab_fire')}", f"🇦🇱 {t('g_tab_albania')}", f"🧭 {t('g_tab_tour')}"],
                               key="g_tabs")
    with tab1:
        st.text_input(t("g_type"), key="g_text", on_change=_on_text, placeholder=t("g_type_ph"), label_visibility="collapsed")
        render_answer(theme)
        for q in questions():
            if q["id"] == "tour":
                continue
            label = q["sq"] if lang == "sq" else q["en"]
            if q["id"] == "kids":
                st.page_link(st.session_state["_pages"]["kids"], label=label, icon="🎮")
                continue
            st.button(label, key=f"gq_{q['id']}", on_click=_ask, args=(q["id"],), use_container_width=True)
    with tab2:
        for i, c in enumerate(data.content("albania_corner.json")["cards"]):
            title = c[f"title_{lang}"]
            text = c[f"text_{lang}"]
            ui.html(f'<div class="v-answer"><b>{escape(c.get("icon", ""))} {escape(title)}</b><div class="v-small">{escape(text)}</div>'
                    f'{ui.src_link(c.get("source", ""))}</div>')
            ui.listen(f"{title}. {text}", f"g_corner_{i}")
        st.page_link(st.session_state["_pages"]["heritage"], label=t("g_open_corner"))
    with tab3:
        for i, (pid, k) in enumerate([("home", "tour_filters"), ("calendar", "tour_calendar"), ("map", "tour_map"),
                                      ("compare", "tour_compare"), ("regions", "tour_regions"), ("downloads", "tour_downloads")]):
            ui.html(f'<div class="v-answer"><b>{i + 1}. {escape(t(k + "_t"))}</b><div class="v-small">{escape(t(k))}</div></div>')
            st.page_link(st.session_state["_pages"][pid], label=t("go_there"))


def fab():
    with st.container(key="viola_fab"):
        with st.popover("Viola", help=t("ask_viola")):
            panel()
