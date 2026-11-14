"""Cached loaders for the app (reads outputs/ only) and fast per-area computations.

Any area (country, county, municipality, circle, drawn polygon) is handled the same way:
the harmonized value of an area = sum of the weights of the fire cell-days inside it.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

import config as C
from src import stats

OUT = C.OUT


# ------------------------------------------------------------------ loaders (read once per server)
@st.cache_data(show_spinner=False)
def monthly() -> pd.DataFrame:
    return pd.read_parquet(OUT / "monthly_harmonized.parquet")


@st.cache_data(show_spinner=False)
def celldays() -> pd.DataFrame:
    d = pd.read_parquet(OUT / "celldays_harmonized.parquet")
    for c in ["satellite", "sensor", "adm1", "adm2", "dn"]:
        d[c] = d[c].astype("category")
    return d


@st.cache_data(show_spinner=False)
def fires() -> pd.DataFrame:
    d = pd.read_parquet(OUT / "fires_clean.parquet")
    for c in ["satellite", "sensor", "source", "confidence", "daynight", "adm1", "adm2"]:
        d[c] = d[c].astype("category")
    return d


@st.cache_data(show_spinner=False)
def events() -> pd.DataFrame:
    return pd.read_parquet(OUT / "events.parquet")


@st.cache_data(show_spinner=False)
def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name, encoding="utf-8-sig")


@st.cache_data(show_spinner=False)
def js(name: str):
    with open(OUT / name, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def content(name: str):
    p = C.CONTENT / name
    if p.suffix == ".csv":
        return pd.read_csv(p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def geojson(name: str) -> dict:
    with open(OUT / name, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner=False)
def country_shape():
    from shapely.geometry import shape
    gj = geojson("boundaries_adm0.geojson")
    return shape(gj["features"][0]["geometry"])


@st.cache_resource(show_spinner=False)
def municipality_shapes():
    from shapely.geometry import shape
    from shapely.prepared import prep
    gj = geojson("boundaries_adm2.geojson")
    return [(f["properties"]["name"], f["properties"]["county"], prep(shape(f["geometry"])), shape(f["geometry"]))
            for f in gj["features"]]


def summary() -> dict:
    return js("summary.json")


def data_end() -> date:
    return date.fromisoformat(summary()["data_end"])


def first_date() -> date:
    s = summary()
    return date.fromisoformat(min(s["first_date_per_satellite"].values()))


def areas() -> pd.DataFrame:
    return pd.DataFrame(js("areas.json"))


def counties() -> list[str]:
    return [n for _, n in C.COUNTIES]


def municipalities(county: str | None = None) -> list[str]:
    a = areas()
    a = a[a["level"] == "adm2"]
    if county:
        a = a[a["county"] == county]
    return sorted(a["name"].tolist())


def county_of(municipality: str) -> str:
    a = areas()
    r = a[(a["level"] == "adm2") & (a["name"] == municipality)]
    return r["county"].iloc[0] if len(r) else ""


# ------------------------------------------------------------------ areas
def area_key(area: dict) -> tuple:
    lvl = area.get("level", "country")
    if lvl == "circle":
        return ("circle", round(area["lat"], 4), round(area["lon"], 4), round(area["r_km"], 2))
    if lvl == "polygon":
        return ("polygon", tuple((round(x, 4), round(y, 4)) for x, y in area["coords"]))
    return (lvl, area.get("name", C.COUNTRY))


def is_predefined(area: dict) -> bool:
    return area.get("level", "country") in ("country", "adm1", "adm2")


def _haversine(lat, lon, lat0, lon0):
    lat, lon = np.radians(lat), np.radians(lon)
    lat0, lon0 = np.radians(lat0), np.radians(lon0)
    a = np.sin((lat - lat0) / 2) ** 2 + np.cos(lat) * np.cos(lat0) * np.sin((lon - lon0) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def mask(df: pd.DataFrame, key: tuple) -> np.ndarray:
    lvl = key[0]
    if lvl == "country":
        return np.ones(len(df), dtype=bool)
    if lvl == "adm1":
        return (df["adm1"] == key[1]).to_numpy()
    if lvl == "adm2":
        return (df["adm2"] == key[1]).to_numpy()
    if lvl == "circle":
        _, lat0, lon0, r = key
        return _haversine(df["lat"].to_numpy(), df["lon"].to_numpy(), lat0, lon0) <= r
    if lvl == "polygon":
        import shapely
        from shapely.geometry import Polygon
        poly = Polygon(key[1])
        return shapely.contains_xy(poly, df["lon"].to_numpy(), df["lat"].to_numpy())
    return np.ones(len(df), dtype=bool)


def _opt_mask(df: pd.DataFrame, low: bool, dn: str, is_cd: bool) -> np.ndarray:
    m = np.ones(len(df), dtype=bool)
    if not low:
        m &= ~df["low_only"].to_numpy() if is_cd else (df["confidence"] != "low").to_numpy()
    if dn != "both":
        col = df["dn"] if is_cd else df["daynight"]
        want = "D" if dn == "day" else "N"
        m &= ((col == want) | (col == "B")).to_numpy() if is_cd else (col == want).to_numpy()
    return m


@st.cache_data(show_spinner=False, max_entries=64)
def area_celldays(key: tuple, low: bool = False, dn: str = "both") -> pd.DataFrame:
    cd = celldays()
    return cd[mask(cd, key) & _opt_mask(cd, low, dn, True)]


@st.cache_data(show_spinner=False, max_entries=64)
def area_fires(key: tuple, low: bool = False, dn: str = "both") -> pd.DataFrame:
    f = fires()
    return f[mask(f, key) & _opt_mask(f, low, dn, False)]


@st.cache_data(show_spinner=False)
def _national_sd() -> pd.DataFrame:
    m = monthly()
    n = m[m["area_level"] == "country"][["year", "month", "harmonized", "high"]].copy()
    n["sd"] = np.log((n["high"] + 1) / (n["harmonized"] + 1)) / C.PRED_INTERVAL_Z
    return n[["year", "month", "sd"]]


@st.cache_data(show_spinner=False, max_entries=64)
def area_monthly(key: tuple, low: bool = False, dn: str = "both") -> pd.DataFrame:
    """Monthly table for any area with normals and status (all months of the record)."""
    m = monthly()
    if key[0] in ("country", "adm1", "adm2") and not low and dn == "both":
        level, name = key
        t = m[(m["area_level"] == level) & (m["area_name"] == (C.COUNTRY if level == "country" else name))]
        return t.reset_index(drop=True)
    base = m[m["area_level"] == "country"][["year", "month", "terra_only_flag", "partial_flag", "viirs_satellites",
                                            "source_sensor"]].copy()
    cd = area_celldays(key, low, dn)
    f = area_fires(key, low, dn)
    w = cd.groupby(["year", "month"], observed=True)["weight"].sum().rename("harmonized")
    frp = cd.groupby(["year", "month"], observed=True)["max_frp"].sum().rename("frp_sum")
    cm = cd[cd["sensor"] == "MODIS"].groupby(["year", "month"], observed=True).size().rename("raw_modis_cd")
    cv = cd[cd["sensor"] == "VIIRS"].groupby(["year", "month"], observed=True).size().rename("raw_viirs_cd")
    rm = f[f["sensor"] == "MODIS"].groupby(["year", "month"], observed=True).size().rename("raw_modis")
    rv = f[f["sensor"] == "VIIRS"].groupby(["year", "month"], observed=True).size().rename("raw_viirs")
    t = base.set_index(["year", "month"]).join([w, frp, cm, cv, rm, rv]).fillna(0).reset_index()
    t = t.merge(_national_sd(), on=["year", "month"], how="left")
    H = t["harmonized"].to_numpy(float)
    sd = np.nan_to_num(t["sd"].to_numpy(float))
    t["low"] = np.clip((H + 1) * np.exp(-C.PRED_INTERVAL_Z * sd) - 1, 0, None)
    t["high"] = (H + 1) * np.exp(C.PRED_INTERVAL_Z * sd) - 1
    t = stats.add_anomalies(t.drop(columns="sd"), "harmonized")
    t.insert(0, "area_level", key[0])
    t.insert(1, "area_name", "custom")
    return t


def value_col(mode: str) -> str:
    return {"h": "harmonized", "m": "raw_modis", "v": "raw_viirs"}.get(mode, "harmonized")


def in_range(t: pd.DataFrame, d0: date, d1: date) -> pd.DataFrame:
    ym = t["year"] * 100 + t["month"]
    return t[(ym >= d0.year * 100 + d0.month) & (ym <= d1.year * 100 + d1.month)]


@st.cache_data(show_spinner=False, max_entries=64)
def area_daily(key: tuple, low: bool = False, dn: str = "both") -> pd.Series:
    cd = area_celldays(key, low, dn)
    return cd.groupby("date")["weight"].sum()


def window_compare(daily: pd.Series, end: date, days: int, extra: float = 0.0) -> dict:
    """Last `days` days up to `end` vs the same dates in each base year."""
    s = daily.copy()
    s.index = pd.to_datetime(s.index)
    start = end - timedelta(days=days - 1)
    now = float(s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))].sum()) + extra
    sample = []
    for y in range(C.BASE_YEARS[0], C.BASE_YEARS[1] + 1):
        try:
            e = end.replace(year=y)
        except ValueError:
            e = end.replace(year=y, day=28)
        b = e - timedelta(days=days - 1)
        sample.append(float(s[(s.index >= pd.Timestamp(b)) & (s.index <= pd.Timestamp(e))].sum()))
    a = np.array(sample)
    return {"value": now, "median": float(np.median(a)), "p10": float(np.quantile(a, .1)),
            "p90": float(np.quantile(a, .9)), "max": float(a.max()), "percentile": stats.percentile_of(now, a),
            "status": stats.window_status(now, a), "start": start, "end": end, "sample": sample}


# ------------------------------------------------------------------ convenience
def year_range() -> tuple[int, int]:
    s = summary()
    return int(s["first_month"][:4]), int(s["last_month"][:4])


def seasons_for(key: tuple, t: pd.DataFrame | None = None) -> dict:
    if key[0] in ("country", "adm1", "adm2") and t is None:
        s = csv("seasons.csv")
        name = C.COUNTRY if key[0] == "country" else key[1]
        r = s[(s["area_level"] == key[0]) & (s["area_name"] == name)]
        if len(r):
            r = r.iloc[0]
            months_ = [int(x) for x in str(r["season_months"]).split()] if isinstance(r["season_months"], str) else []
            return {"start": int(r["season_start"]) if pd.notna(r["season_start"]) else None,
                    "peak": int(r["season_peak"]) if pd.notna(r["season_peak"]) else None,
                    "end": int(r["season_end"]) if pd.notna(r["season_end"]) else None,
                    "two_seasons": r["two_seasons"] == "yes",
                    "second_peak": int(r["second_peak"]) if pd.notna(r["second_peak"]) else None,
                    "season_months": months_}
    t = t if t is not None else area_monthly(key)
    return stats.seasons(stats.month_normals(t, "harmonized"))


def normals_for(t: pd.DataFrame) -> pd.DataFrame:
    return stats.month_normals(t, "harmonized")


def trend_for(t: pd.DataFrame) -> dict:
    return stats.trend(t, "harmonized")
