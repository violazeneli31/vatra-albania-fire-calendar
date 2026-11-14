"""Normals, anomalies, seasons, trend and early-warning statistics.

Used by build.py and by the app (for custom areas), so it needs only numpy/pandas/scipy/pymannkendall.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import config as C

STATUS_ORDER = ["below", "normal", "above", "extreme"]


def month_normals(monthly: pd.DataFrame, value: str = "harmonized") -> pd.DataFrame:
    """Per calendar month over the base years: median, P10, P90, max, mean/sd of log(v+1).

    `monthly` needs columns year, month and `value`. Missing months count as 0 inside the base period.
    """
    y0, y1 = C.BASE_YEARS
    base = monthly[(monthly["year"] >= y0) & (monthly["year"] <= y1)]
    full = pd.MultiIndex.from_product([range(y0, y1 + 1), range(1, 13)], names=["year", "month"])
    s = base.set_index(["year", "month"])[value].groupby(level=[0, 1]).sum().reindex(full, fill_value=0.0)
    g = s.groupby(level="month")
    lg = np.log1p(s).groupby(level="month")
    out = pd.DataFrame({
        "median": g.median(), "p10": g.quantile(0.10), "p90": g.quantile(0.90), "max": g.max(),
        "mean": g.mean(), "log_mean": lg.mean(), "log_sd": lg.std(ddof=1),
    })
    out.index.name = "month"
    return out.reset_index()


def classify(value: float, med: float, p10: float, p90: float, vmax: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if vmax > 0 and value >= vmax and value > 0:
        return "extreme"
    if value >= p90 and value > med:
        return "above"
    if med > 0 and value <= p10:
        return "below"
    return "normal"


def add_anomalies(monthly: pd.DataFrame, value: str = "harmonized", normals: pd.DataFrame | None = None) -> pd.DataFrame:
    n = month_normals(monthly, value) if normals is None else normals
    m = monthly.merge(n, on="month", how="left")
    m["anomaly"] = m[value] - m["median"]
    m["anomaly_pct"] = np.where(m["median"] > 0, 100 * (m[value] - m["median"]) / m["median"], np.nan)
    m["z_log"] = np.where(m["log_sd"] > 0, (np.log1p(m[value]) - m["log_mean"]) / m["log_sd"], 0.0)
    m["status"] = [classify(v, a, b, c, d) for v, a, b, c, d in
                   zip(m[value], m["median"], m["p10"], m["p90"], m["max"])]
    return m


def seasons(normals: pd.DataFrame) -> dict:
    """Fire season from the median profile; two seasons only with a clear dip between two peaks."""
    med = normals.sort_values("month")["median"].to_numpy(dtype=float)
    if med.max() <= 0:
        med = normals.sort_values("month")["mean"].to_numpy(dtype=float)
    if med.max() <= 0:
        return {"start": None, "peak": None, "end": None, "two_seasons": False,
                "second_peak": None, "season_months": []}
    peak = int(med.argmax())
    thr = C.SEASON_THRESHOLD * med[peak]
    above = med >= thr
    # contiguous (circular) run of months above the threshold that contains the peak
    start = peak
    while above[(start - 1) % 12] and (start - 1) % 12 != peak:
        start = (start - 1) % 12
    end = peak
    while above[(end + 1) % 12] and (end + 1) % 12 != start:
        end = (end + 1) % 12
    run = [(start + k) % 12 for k in range(((end - start) % 12) + 1)]
    # second peak: local maximum (circular) at least 2 months from the main peak
    second, dip_ok = None, False
    cands = [m for m in range(12) if med[m] >= med[(m - 1) % 12] and med[m] >= med[(m + 1) % 12]
             and min((m - peak) % 12, (peak - m) % 12) >= 2 and med[m] >= thr and med[m] > 0]
    if cands:
        m2 = max(cands, key=lambda m: med[m])
        fwd = [(peak + k) % 12 for k in range(1, (m2 - peak) % 12)]
        bwd = [(m2 + k) % 12 for k in range(1, (peak - m2) % 12)]
        path = fwd if len(fwd) <= len(bwd) else bwd
        if path:
            dip = min(med[p] for p in path)
            if dip < C.TWO_SEASON_DIP * min(med[peak], med[m2]):
                second, dip_ok = m2, True
    return {"start": start + 1, "peak": peak + 1, "end": end + 1, "two_seasons": bool(dip_ok),
            "second_peak": (second + 1) if second is not None else None,
            "season_months": [m + 1 for m in run]}


def yearly_totals(monthly: pd.DataFrame, value: str = "harmonized") -> pd.Series:
    return monthly.groupby("year")[value].sum()


def trend(monthly: pd.DataFrame, value: str = "harmonized") -> dict:
    y0, y1 = C.TREND_YEARS
    yt = yearly_totals(monthly, value).reindex(range(y0, y1 + 1), fill_value=0.0)
    out = {"years": f"{y0}-{y1}", "slope": None, "p": None, "direction": "none", "pct_per_year": None,
           "intercept": None, "n": int(len(yt))}
    if yt.sum() <= 0 or len(yt) < 8:
        return out
    try:
        import pymannkendall as mk
        r = mk.original_test(yt.to_numpy())
        slope, p, intercept = float(r.slope), float(r.p), float(r.intercept)
    except Exception:  # fallback: Kendall tau + Theil-Sen from scipy
        from scipy import stats as ss
        x = np.arange(len(yt))
        tau = ss.kendalltau(x, yt.to_numpy())
        ts = ss.theilslopes(yt.to_numpy(), x)
        slope, p, intercept = float(ts[0]), float(tau.pvalue), float(ts[1])
    med = float(np.median(yt))
    direction = "none"
    if p < 0.05:
        direction = "up" if slope > 0 else "down"
    out.update({"slope": slope, "p": p, "intercept": intercept, "direction": direction,
                "pct_per_year": (100 * slope / med) if med > 0 else None, "median_year": med})
    return out


def percentile_of(value: float, sample) -> float:
    a = np.asarray(sample, dtype=float)
    if len(a) == 0:
        return float("nan")
    return float(100.0 * (np.sum(a < value) + 0.5 * np.sum(a == value)) / len(a))


def window_status(value: float, sample) -> str:
    a = np.asarray(sample, dtype=float)
    if len(a) == 0:
        return "normal"
    return classify(value, float(np.median(a)), float(np.quantile(a, 0.10)),
                    float(np.quantile(a, 0.90)), float(a.max()))
