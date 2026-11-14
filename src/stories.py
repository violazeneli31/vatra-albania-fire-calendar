"""Step 16 + 19: the headline finding and short data stories, written by templates from the numbers only."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from src.i18n import MONTHS_GEN_SQ, fdate, month, month_cap, num, pct

RAW_BEFORE = (2007, 2011)
RAW_AFTER = (2012, 2016)


def _mean_year(s: pd.Series, y0: int, y1: int) -> float:
    return float(s.reindex(range(y0, y1 + 1), fill_value=0).mean())


def headline(nat: pd.DataFrame, trend_res: dict, cty_tot: pd.Series, normals: pd.DataFrame) -> dict:
    """nat: national monthly table with raw_modis, raw_viirs, harmonized."""
    yr = nat.groupby("year")[["raw_modis", "raw_viirs", "harmonized"]].sum()
    raw_after = _mean_year(yr["raw_modis"] + yr["raw_viirs"], *RAW_AFTER)
    raw_before = _mean_year(yr["raw_modis"], *RAW_BEFORE)
    h_after = _mean_year(yr["harmonized"], *RAW_AFTER)
    h_before = _mean_year(yr["harmonized"], *RAW_BEFORE)
    raw_change = 100 * (raw_after / raw_before - 1) if raw_before else None
    h_change = 100 * (h_after / h_before - 1) if h_before else None
    base = yr.loc[C.BASE_YEARS[0]:C.BASE_YEARS[1]]
    worst_year = int(base["harmonized"].idxmax())
    full = nat[(nat["year"] >= C.BASE_YEARS[0]) & (nat["year"] <= C.BASE_YEARS[1])]
    wm = full.loc[full["harmonized"].idxmax()]
    danger_month = int(normals.loc[normals["median"].idxmax(), "month"])
    top_county = str(cty_tot.idxmax())
    h = {
        "raw_window": list(RAW_AFTER), "before_window": list(RAW_BEFORE),
        "raw_mean_before": raw_before, "raw_mean_after": raw_after, "raw_change_pct": raw_change,
        "harm_mean_before": h_before, "harm_mean_after": h_after, "harm_change_pct": h_change,
        "raw_viirs_2012": float(yr.loc[2012, "raw_viirs"]) if 2012 in yr.index else None,
        "raw_modis_2011": float(yr.loc[2011, "raw_modis"]) if 2011 in yr.index else None,
        "trend": trend_res, "worst_year": worst_year, "worst_year_value": float(base.loc[worst_year, "harmonized"]),
        "worst_month": {"year": int(wm["year"]), "month": int(wm["month"]), "value": float(wm["harmonized"])},
        "most_dangerous_month": danger_month, "most_dangerous_month_median": float(normals["median"].max()),
        "top_county": top_county, "top_county_value": float(cty_tot.max()),
        "top_county_share_pct": float(100 * cty_tot.max() / cty_tot.sum()) if cty_tot.sum() else None,
    }
    for lang in ["en", "sq"]:
        h[f"text_{lang}"] = headline_text(h, lang)
        h[f"short_{lang}"] = headline_short(h, lang)
    return h


def headline_short(h: dict, lang: str) -> str:
    r, s = h["raw_change_pct"], h["harm_change_pct"]
    if lang == "sq":
        return (f"Numërimet e papërpunuara tregojnë {pct(r, 'sq')} zjarre pas vitit 2012. Ky kërcim vjen nga "
                f"sateliti i ri, jo nga zjarre të reja: në regjistrin e harmonizuar të VATRA-s ndryshimi është {pct(s, 'sq')}.")
    return (f"Raw satellite counts suggest fires rose {pct(r, 'en')} after 2012. That jump is the new satellite, "
            f"not new fires: in VATRA's harmonized record the change is {pct(s, 'en')}.")


def headline_text(h: dict, lang: str) -> str:
    tr = h["trend"]
    wm = h["worst_month"]
    if lang == "sq":
        if tr.get("direction") == "none":
            ttxt = f"Për {tr['years'].replace('-', '–')} nuk ka një tendencë të qartë (Mann–Kendall p = {num(tr['p'], 'sq', 2)})."
        else:
            d = "rritje" if tr["direction"] == "up" else "rënie"
            ttxt = f"Për {tr['years'].replace('-', '–')} ka një tendencë {d} ({pct(tr['pct_per_year'], 'sq', 1)} në vit, p = {num(tr['p'], 'sq', 3)})."
        return (headline_short(h, "sq") + " " + ttxt +
                f" Viti më i keq ishte {h['worst_year']}, muaji më i keq {month(wm['month'], 'sq', True)} {wm['year']}, "
                f"dhe qarku me më shumë zjarre është {h['top_county']}.")
    if tr.get("direction") == "none":
        ttxt = f"Over {tr['years'].replace('-', '–')} there is no clear trend (Mann–Kendall p = {num(tr['p'], 'en', 2)})."
    else:
        d = "rising" if tr["direction"] == "up" else "falling"
        ttxt = f"Over {tr['years'].replace('-', '–')} activity is {d} ({pct(tr['pct_per_year'], 'en', 1)} per year, p = {num(tr['p'], 'en', 3)})."
    return (headline_short(h, "en") + " " + ttxt +
            f" The worst year was {h['worst_year']}, the worst month {month(wm['month'], 'en', True)} {wm['year']}, "
            f"and the county with the most fire activity is {h['top_county']}.")


def year_stories(nat: pd.DataFrame, cty: pd.DataFrame, events: pd.DataFrame) -> dict:
    """One short fact sheet per year (EN + SQ)."""
    yr = nat.groupby("year")["harmonized"].sum()
    base = yr.loc[C.BASE_YEARS[0]:C.BASE_YEARS[1]]
    med = float(base.median()) if len(base) else 0
    out = {"en": {}, "sq": {}}
    for y, v in yr.items():
        y = int(y)
        m = nat[nat["year"] == y]
        if m["harmonized"].sum() <= 0:
            continue
        wm = m.loc[m["harmonized"].idxmax()]
        c = cty[cty["year"] == y].groupby("area_name")["harmonized"].sum()
        top_c = str(c.idxmax()) if len(c) and c.max() > 0 else None
        ev = events[events["year"] == y]
        big = ev.loc[ev["cell_days"].idxmax()] if len(ev) else None
        ratio = v / med if med > 0 else None
        rank = int((base > v).sum() + 1) if C.BASE_YEARS[0] <= y <= C.BASE_YEARS[1] else None
        partial = bool(m["partial_flag"].any()) if "partial_flag" in m else False
        terra = bool(m["terra_only_flag"].any()) if "terra_only_flag" in m else False
        for lang in ["en", "sq"]:
            parts = []
            if lang == "en":
                parts.append(f"In {y}, VATRA recorded {num(v, 'en')} fire cell-days" +
                             (f" ({num(ratio, 'en', 1)} times a typical year)" if ratio else "") + ".")
                if rank:
                    parts.append(f"It ranks {rank} of {len(base)} in {C.BASE_YEARS[0]}–{C.BASE_YEARS[1]}.")
                parts.append(f"The busiest month was {month(int(wm['month']), 'en', True)} with {num(wm['harmonized'], 'en')}.")
                if top_c:
                    parts.append(f"Most activity: {top_c} county.")
                if big is not None:
                    site = f", {num(big['site_km'], 'en', 1)} km from {big['nearest_site']}" if pd.notna(big.get("site_km")) and big["site_km"] <= 10 else ""
                    parts.append(f"Biggest event: {fdate(big['start'], 'en')} – {fdate(big['end'], 'en')} in {big['municipality']}, "
                                 f"{int(big['days'])} days, {int(big['cell_days'])} cell-days{site}.")
                if terra:
                    parts.append("Some months are estimated from Terra only.")
                if partial:
                    parts.append("The year is not complete yet.")
            else:
                parts.append(f"Në vitin {y}, VATRA regjistroi {num(v, 'sq')} qeliza-ditë zjarri" +
                             (f" ({num(ratio, 'sq', 1)} herë një vit tipik)" if ratio else "") + ".")
                if rank:
                    parts.append(f"Renditet i {rank}-i nga {len(base)} në {C.BASE_YEARS[0]}–{C.BASE_YEARS[1]}.")
                parts.append(f"Muaji më i ngarkuar ishte {month(int(wm['month']), 'sq', True)} me {num(wm['harmonized'], 'sq')}.")
                if top_c:
                    parts.append(f"Më shumë aktivitet: qarku {top_c}.")
                if big is not None:
                    site = f", {num(big['site_km'], 'sq', 1)} km nga {big['nearest_site']}" if pd.notna(big.get("site_km")) and big["site_km"] <= 10 else ""
                    parts.append(f"Ngjarja më e madhe: {fdate(big['start'], 'sq')} – {fdate(big['end'], 'sq')} në bashkinë {big['municipality']}, "
                                 f"{int(big['days'])} ditë, {int(big['cell_days'])} qeliza-ditë{site}.")
                if terra:
                    parts.append("Disa muaj janë vlerësuar vetëm nga Terra.")
                if partial:
                    parts.append("Viti nuk ka përfunduar ende.")
            out[lang][str(y)] = " ".join(parts)
    return out


def event_stories(events: pd.DataFrame, monthly: pd.DataFrame, top: int = 50) -> dict:
    """One fact sheet per top event, e.g. 'August 2021, Vlorë area: the fire lasted 9 days ...'."""
    cm = monthly[monthly["area_level"] == "adm1"].set_index(["area_name", "year", "month"])
    out = {"en": {}, "sq": {}}
    for _, e in events.nlargest(min(top, len(events)), "cell_days").iterrows():
        key = (e["county"], int(e["year"]), int(e["month"]))
        times = None
        if key in cm.index:
            r = cm.loc[key]
            if r["median"] > 0:
                times = r["harmonized"] / r["median"]
        near = pd.notna(e.get("site_km")) and e["site_km"] <= 15
        eid = str(int(e["event_id"]))
        en = (f"{month_cap(e['month'], 'en')} {e['year']}, {e['municipality']} ({e['county']} county): the fire lasted "
              f"{int(e['days'])} days and covered {int(e['cell_days'])} fire cell-days"
              + (f", with a peak intensity of {num(e['max_frp'], 'en')} MW" if pd.notna(e['max_frp']) else "") + ". ")
        if times:
            en += f"That month the county had {num(times, 'en', 1)} times its normal {month(e['month'], 'en', True)} activity. "
        if near:
            en += f"It was {num(e['site_km'], 'en', 1)} km from {e['nearest_site']}. "
        if e.get("effis_match") == "yes":
            en += f"EFFIS mapped a burnt area of {num(e['effis_area_ha'], 'en')} ha here."
        sq = (f"{month_cap(e['month'], 'sq')} {e['year']}, {e['municipality']} (qarku {e['county']}): zjarri zgjati "
              f"{int(e['days'])} ditë dhe mbuloi {int(e['cell_days'])} qeliza-ditë zjarri"
              + (f", me intensitet maksimal {num(e['max_frp'], 'sq')} MW" if pd.notna(e['max_frp']) else "") + ". ")
        if times:
            sq += f"Atë muaj qarku pati {num(times, 'sq', 1)} herë aktivitetin normal të {MONTHS_GEN_SQ[int(e['month']) - 1]}. "
        if near:
            sq += f"Ishte {num(e['site_km'], 'sq', 1)} km nga {e['nearest_site']}. "
        if e.get("effis_match") == "yes":
            sq += f"EFFIS hartografoi këtu një sipërfaqe të djegur prej {num(e['effis_area_ha'], 'sq')} ha."
        out["en"][eid] = en.strip()
        out["sq"][eid] = sq.strip()
    return out
