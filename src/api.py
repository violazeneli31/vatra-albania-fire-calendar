"""Latest days from the NASA FIRMS area API (after the files end). Cached for 3 hours, 10-second timeout.

The MAP_KEY is read from Streamlit Secrets first, then from .env. It is never printed or shown.
If there is no key or the API fails, the app keeps working and says "latest days unavailable".
"""
from __future__ import annotations

import io
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

import config as C


def _key() -> str | None:
    try:
        k = st.secrets.get("FIRMS_MAP_KEY")
        if k:
            return str(k).strip()
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv(C.ROOT / ".env")
    except Exception:
        pass
    k = os.environ.get("FIRMS_MAP_KEY", "").strip()
    return k if k and k != "paste_key_here" else None


def _bbox() -> str:
    from src import data
    b = data.summary().get("bbox") or C.BBOX_FALLBACK
    w, s, e, n = b
    return f"{w - .05:.2f},{s - .05:.2f},{e + .05:.2f},{n + .05:.2f}"


@st.cache_data(ttl=C.API_CACHE_SECONDS, show_spinner=False)
def _fetch(start: str, today: str) -> tuple[pd.DataFrame, str]:
    """Download detections from `start` to `today` (both ISO dates). Returns (rows, status)."""
    import requests
    key = _key()
    if not key:
        return pd.DataFrame(), "no_key"
    d0, d1 = date.fromisoformat(start), date.fromisoformat(today)
    if d0 > d1:
        return pd.DataFrame(), "up_to_date"
    frames, errors = [], 0
    for source, sat in C.FIRMS_API_SOURCES.items():
        cur = d0
        while cur <= d1:
            days = min(10, (d1 - cur).days + 1)
            url = C.FIRMS_API.format(key=key, source=source, bbox=_bbox(), days=days, date=cur.isoformat())
            try:
                r = requests.get(url, timeout=C.API_TIMEOUT)
                if r.status_code != 200 or r.text.lstrip().lower().startswith(("invalid", "error", "<")):
                    errors += 1
                elif r.text.strip():
                    df = pd.read_csv(io.StringIO(r.text), dtype={"acq_time": str, "confidence": str, "satellite": str})
                    if len(df):
                        df["sat_name"] = sat
                        frames.append(df)
            except Exception:
                errors += 1
            cur += timedelta(days=days)
    if not frames:
        return pd.DataFrame(), ("error" if errors else "ok_empty")
    return pd.concat(frames, ignore_index=True), ("partial" if errors else "ok")


def _normalise(raw: pd.DataFrame) -> pd.DataFrame:
    from src import data
    from src.grid import cell_index
    d = pd.DataFrame()
    d["date"] = pd.to_datetime(raw["acq_date"]).dt.normalize()
    hhmm = raw["acq_time"].astype(str).str.zfill(4)
    d["time"] = hhmm.str[:2] + ":" + hhmm.str[2:]
    d["lat"], d["lon"] = raw["latitude"].astype(float), raw["longitude"].astype(float)
    d["satellite"] = raw["sat_name"]
    d["sensor"] = np.where(d["satellite"] == "MODIS", "MODIS", "VIIRS")
    d.loc[d["satellite"] == "MODIS", "satellite"] = raw.loc[d["satellite"] == "MODIS", "satellite"].map(
        {"T": "Terra", "A": "Aqua", "Terra": "Terra", "Aqua": "Aqua"}).fillna("MODIS")
    conf = raw["confidence"].astype(str).str.lower()
    num = pd.to_numeric(conf, errors="coerce")
    d["confidence"] = np.where(num.notna(), np.where(num < C.MODIS_CONF_LOW, "low", np.where(num >= C.MODIS_CONF_HIGH, "high", "nominal")),
                               conf.str[0].map({"l": "low", "n": "nominal", "h": "high"}).fillna("nominal"))
    d["frp"] = pd.to_numeric(raw.get("frp"), errors="coerce")
    d["daynight"] = raw.get("daynight", "D")
    d["source"] = "api"
    # clip to the country and attach county / municipality
    import shapely
    inside = shapely.contains_xy(data.country_shape(), d["lon"].to_numpy(), d["lat"].to_numpy())
    d = d[inside].copy()
    adm1, adm2 = [], []
    for lon, lat in zip(d["lon"], d["lat"]):
        hit = ("", "")
        for name, county, prep, _ in data.municipality_shapes():
            if prep.contains(shapely.Point(lon, lat)):
                hit = (county, name)
                break
        adm1.append(hit[0])
        adm2.append(hit[1])
    d["adm1"], d["adm2"] = adm1, adm2
    i, j = cell_index(d["lat"], d["lon"])
    d["cell_id"] = [f"{a}_{b}" for a, b in zip(i, j)]
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    return d.reset_index(drop=True)


def latest() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(detections, cell-days with weights, info) for the days after the files end."""
    return _latest(date.today().isoformat())


@st.cache_data(ttl=C.API_CACHE_SECONDS, show_spinner=False)
def _latest(today_iso: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    from src import data
    end = data.data_end()
    today = date.fromisoformat(today_iso)
    info = {"status": "up_to_date", "end": None, "files_end": end}
    raw, status = _fetch((end + timedelta(days=1)).isoformat(), today.isoformat())
    info["status"] = status
    if raw is None or len(raw) == 0:
        return pd.DataFrame(), pd.DataFrame(), info
    try:
        det = _normalise(raw)
    except Exception:
        info["status"] = "error"
        return pd.DataFrame(), pd.DataFrame(), info
    det = det[det["date"].dt.date > end]
    if len(det) == 0:
        info["end"] = today if status in ("ok", "ok_empty") else None
        return det, pd.DataFrame(), info
    calib = data.js("calibration.json")
    rw = {int(k): v for k, v in calib.get("recent_weight_by_month", {}).items()}
    g = det.groupby(["date", "cell_id", "satellite"], as_index=False).agg(
        lat=("lat", "first"), lon=("lon", "first"), sensor=("sensor", "first"), adm1=("adm1", "first"),
        adm2=("adm2", "first"), max_frp=("frp", "max"), n_det=("lat", "size"),
        low_only=("confidence", lambda s: (s == "low").all()), dn=("daynight", lambda s: "B" if s.nunique() > 1 else s.iloc[0]))
    g["year"], g["month"] = g["date"].dt.year, g["date"].dt.month
    g["weight"] = np.where(g["sensor"] == "VIIRS", g["month"].map(rw).fillna(np.nanmedian(list(rw.values())) if rw else 0.4), 0.0)
    info["end"] = today if status in ("ok", "ok_empty") else det["date"].max().date()
    return det, g, info


def latest_info() -> dict:
    try:
        return latest()[2]
    except Exception:
        return {"status": "error", "end": None}
