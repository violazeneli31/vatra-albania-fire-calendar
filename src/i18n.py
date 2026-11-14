"""Text in English and Albanian: t(key), numbers (1,234 / 1.234), months and dates."""
from __future__ import annotations

import json
import logging
import math
from datetime import date, datetime
from functools import lru_cache

import config as C

log = logging.getLogger("vatra.i18n")

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "sq": ["Jan", "Shk", "Mar", "Pri", "Maj", "Qer", "Kor", "Gus", "Sht", "Tet", "Nën", "Dhj"],
}
MONTHS_FULL = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
    "sq": ["janar", "shkurt", "mars", "prill", "maj", "qershor", "korrik", "gusht", "shtator", "tetor",
           "nëntor", "dhjetor"],
}

# Albanian genitive ("of August" = "i gushtit")
MONTHS_GEN_SQ = ["janarit", "shkurtit", "marsit", "prillit", "majit", "qershorit", "korrikut", "gushtit",
                 "shtatorit", "tetorit", "nëntorit", "dhjetorit"]


@lru_cache(maxsize=1)
def _strings() -> dict:
    p = C.CONTENT / "strings.json"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def current_lang() -> str:
    try:
        import streamlit as st
        return st.session_state.get("lang", "en")
    except Exception:
        return "en"


def t(key: str, lang: str | None = None, **kw) -> str:
    lang = lang or current_lang()
    entry = _strings().get(key)
    if entry is None:
        log.warning("missing string key: %s", key)
        text = key
    else:
        text = entry.get(lang)
        if not text:
            if lang != "en":
                log.warning("missing %s text for key %s", lang, key)
            text = entry.get("en", key)
    if kw:
        try:
            text = text.format(**kw)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def num(x, lang: str | None = None, digits: int = 0) -> str:
    """1,234 (EN) or 1.234 (SQ); decimals with . (EN) or , (SQ)."""
    lang = lang or current_lang()
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = f"{x:,.{digits}f}"
    if lang == "sq":
        s = s.replace(",", " ").replace(".", ",").replace(" ", ".")
    return s


def pct(x, lang: str | None = None, digits: int = 0, sign: bool = True) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    s = num(abs(x), lang, digits)
    pre = ("+" if x > 0 else "−" if x < 0 else "") if sign else ("−" if x < 0 else "")
    return f"{pre}{s}%"


def month(m: int, lang: str | None = None, full: bool = False) -> str:
    lang = lang or current_lang()
    names = MONTHS_FULL if full else MONTHS
    return names.get(lang, names["en"])[int(m) - 1]


def month_cap(m: int, lang: str | None = None) -> str:
    s = month(m, lang, full=True)
    return s[:1].upper() + s[1:]


def months(lang: str | None = None) -> list[str]:
    lang = lang or current_lang()
    return MONTHS.get(lang, MONTHS["en"])


def fdate(d, lang: str | None = None, with_year: bool = True) -> str:
    """'7 Nov 2026' (EN) / '7 nën 2026' (SQ)."""
    lang = lang or current_lang()
    if d is None:
        return "–"
    if isinstance(d, str):
        d = datetime.fromisoformat(d[:10]).date()
    if isinstance(d, datetime):
        d = d.date()
    m = MONTHS[lang][d.month - 1]
    m = m.lower() if lang == "sq" else m
    return f"{d.day} {m} {d.year}" if with_year else f"{d.day} {m}"


def ddmmyyyy(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def status_label(status: str, lang: str | None = None) -> str:
    return t(f"status_{status}", lang) if status else "–"


def area_label(level: str, name: str, lang: str | None = None) -> str:
    lang = lang or current_lang()
    if level == "country":
        return C.COUNTRY_SQ if lang == "sq" else C.COUNTRY
    if level == "adm1":
        return f"{name} ({'qarku' if lang == 'sq' else 'county'})"
    if level == "adm2":
        return f"{name} ({'bashkia' if lang == 'sq' else 'municipality'})"
    return name
