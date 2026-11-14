"""Step 11: check the harmonized record against EFFIS burnt areas (build only: uses geopandas).

Caveats: EFFIS maps mainly fires of about 30 ha or larger, and part of its perimeters come from
MODIS (map_source = modis / mcd64), so it is not a fully independent check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as ss

import config as C

WINDOW_DAYS = 5


def load_effis():
    import geopandas as gpd
    from src.clean import load_admin
    e = gpd.read_file(C.EFFIS_FILE).to_crs(4326)
    e["initialdate"] = pd.to_datetime(e["initialdate"], utc=True, format="mixed").dt.tz_localize(None).dt.normalize()
    e["finaldate"] = pd.to_datetime(e["finaldate"], utc=True, format="mixed").dt.tz_localize(None).dt.normalize()
    e["finaldate"] = e["finaldate"].fillna(e["initialdate"])
    adm0, adm1, adm2 = load_admin()
    e = e[e.intersects(adm0.geometry.iloc[0])].copy()
    cent = e.copy()
    cent["geometry"] = e.representative_point()
    j = gpd.sjoin(cent, adm2[["adm1", "adm2", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    e["county"] = j["adm1"]
    e["municipality"] = j["adm2"]
    e["year"] = e["initialdate"].dt.year
    e["month"] = e["initialdate"].dt.month
    e["independent"] = ~e["map_source"].astype(str).str.contains("modis|mcd64", case=False)
    return e


def match_points(e, df: pd.DataFrame, date_col: str = "date") -> pd.Series:
    """For each row of df (lat, lon, date): EFFIS id whose perimeter contains it within +-WINDOW_DAYS, else -1."""
    import geopandas as gpd
    pts = gpd.GeoDataFrame(df[[date_col]].copy(), geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=4326)
    j = gpd.sjoin(pts, e[["id", "initialdate", "finaldate", "area_ha", "geometry"]], how="inner", predicate="within")
    w = pd.Timedelta(days=WINDOW_DAYS)
    ok = (j[date_col] >= j["initialdate"] - w) & (j[date_col] <= j["finaldate"] + w)
    j = j[ok]
    j = j[~j.index.duplicated(keep="first")]
    out = pd.Series(-1, index=df.index, dtype=int)
    out.loc[j.index] = j["id"].astype(int)
    return out


def compare(e, monthly: pd.DataFrame, cd: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Returns (comparison table, summary dict, events with EFFIS match columns)."""
    rows = []
    # yearly + monthly per area (country and counties)
    eff_y_nat = e.groupby("year")["area_ha"].sum()
    eff_m_nat = e.groupby(["year", "month"])["area_ha"].sum()
    areas = [("country", C.COUNTRY, None)] + [("adm1", c, c) for c in sorted(monthly.loc[monthly["area_level"] == "adm1", "area_name"].unique())]
    summary = {"years": None, "national": {}, "counties": {}}
    for level, name, county in areas:
        mm = monthly[(monthly["area_level"] == level) & (monthly["area_name"] == name)]
        ee = e if county is None else e[e["county"] == county]
        hy = mm.groupby("year")["harmonized"].sum()
        ey = ee.groupby("year")["area_ha"].sum()
        years = [y for y in hy.index if 2001 <= y <= 2025]
        for y in years:
            rows.append({"area_level": level, "area_name": name, "period": "year", "year": y, "month": None,
                         "harmonized": round(float(hy.get(y, 0)), 2), "effis_area_ha": round(float(ey.get(y, 0)), 1),
                         "effis_fires": int((ee["year"] == y).sum())})
        hm = mm.set_index(["year", "month"])["harmonized"]
        em = ee.groupby(["year", "month"])["area_ha"].sum()
        sel = [(y, m) for (y, m) in hm.index if 2001 <= y <= 2025]
        for (y, m) in sel:
            rows.append({"area_level": level, "area_name": name, "period": "month", "year": y, "month": m,
                         "harmonized": round(float(hm.get((y, m), 0)), 2), "effis_area_ha": round(float(em.get((y, m), 0)), 1),
                         "effis_fires": int(((ee["year"] == y) & (ee["month"] == m)).sum())})
        a = np.array([hy.get(y, 0) for y in years], float)
        b = np.array([ey.get(y, 0) for y in years], float)
        am = np.array([hm.get(k, 0) for k in sel], float)
        bm = np.array([em.get(k, 0) for k in sel], float)
        res = {}
        if len(a) > 3 and a.std() > 0 and b.std() > 0:
            res["yearly_pearson"] = float(ss.pearsonr(a, b)[0])
            res["yearly_spearman"] = float(ss.spearmanr(a, b)[0])
            res["yearly_pearson_log"] = float(ss.pearsonr(np.log1p(a), np.log1p(b))[0])
        if len(am) > 3 and am.std() > 0 and bm.std() > 0:
            res["monthly_spearman"] = float(ss.spearmanr(am, bm)[0])
            res["monthly_pearson_log"] = float(ss.pearsonr(np.log1p(am), np.log1p(bm))[0])
        if county is None:
            summary["national"] = res
            summary["years"] = [min(years), max(years)]
        else:
            summary["counties"][county] = res
    table = pd.DataFrame(rows)

    # share of cell-days inside EFFIS perimeters (date window +- 5 days)
    u = cd[~cd["low_only"]].copy()
    u["effis_id"] = match_points(e, u)
    inside = u["effis_id"] >= 0
    summary["share_celldays_inside"] = float(inside.mean())
    summary["share_by_sensor"] = {s: float(inside[u["sensor"] == s].mean()) for s in ["MODIS", "VIIRS"]}
    fs = u["month"].isin(C.FIRE_SEASON_MONTHS)
    summary["share_fire_season"] = float(inside[fs].mean())
    summary["share_weighted"] = float((u.loc[inside, "weight"].sum()) / u["weight"].sum()) if u["weight"].sum() else None
    summary["effis_fires"] = int(len(e))
    summary["effis_area_ha"] = float(e["area_ha"].sum())
    summary["effis_independent_share"] = float(e["independent"].mean())
    summary["caveat"] = ("EFFIS maps mainly fires of about 30 ha or more; some perimeters are drawn from MODIS "
                         "(map_source modis/mcd64), so EFFIS is not fully independent of the hotspots.")
    # events: EFFIS match if any of its cell-days is inside a perimeter in the date window
    ev = events.copy()
    if "event_id" in u:
        hit = u[inside & (u["event_id"] > 0)].groupby("event_id")["effis_id"].agg(lambda s: sorted(set(s)))
        area = e.set_index("id")["area_ha"]
        ev["effis_match"] = ev["event_id"].map(lambda k: "yes" if k in hit.index else "no")
        ev["effis_area_ha"] = ev["event_id"].map(lambda k: float(area.reindex(hit[k]).sum()) if k in hit.index else np.nan)
        summary["events_matched_share"] = float((ev["effis_match"] == "yes").mean()) if len(ev) else None
        big = ev.nlargest(min(50, len(ev)), "cell_days")
        summary["top50_events_matched_share"] = float((big["effis_match"] == "yes").mean()) if len(big) else None
    return table, summary, ev
