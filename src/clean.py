"""Steps 2-3: remove duplicates, false alarms and points outside the country; attach county and municipality.

Uses geopandas, so it only runs inside build.py (the web app never imports it).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
from src import grid


def archive_before_nrt(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per satellite: standard (yearly/archive) rows up to the last standard date, NRT rows only after it.

    Coordinates can differ slightly between archive and NRT versions of the same detection,
    so we cannot match duplicates on lat/lon; cutting by date avoids double counting.
    """
    keep = []
    cut = {}
    for sat, d in df.groupby("satellite"):
        std = d[d["source"] != "nrt"]
        last_std = std["date"].max() if len(std) else pd.Timestamp("1900-01-01")
        cut[sat] = str(last_std.date())
        nrt = d[(d["source"] == "nrt") & (d["date"] > last_std)]
        keep += [std, nrt]
    out = pd.concat(keep, ignore_index=True)
    before = len(out)
    out = out.loc[~pd.DataFrame({"s": out["satellite"], "d": out["date"], "t": out["hhmm"],
                                 "a": out["lat"].round(4), "o": out["lon"].round(4)}).duplicated()]
    out = out.reset_index(drop=True)
    return out, {"last_standard_date": cut, "exact_duplicates_dropped": int(before - len(out))}


def static_mask(df: pd.DataFrame) -> set:
    """Cells where standard files flagged type 2 (static land source) on >= STATIC_MIN_DAYS different days."""
    t2 = df[df["type"] == 2]
    t2 = grid.add_cells(t2)
    days = t2.groupby("cell_id")["date"].nunique()
    return set(days[days >= C.STATIC_MIN_DAYS].index)


def drop_false_alarms(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    mask_cells = static_mask(df)
    n0 = len(df)
    df = df[~df["type"].isin([2, 3])]
    n_type = n0 - len(df)
    df = grid.add_cells(df)
    is_nrt_static = (df["type"].isna()) & (df["cell_id"].isin(mask_cells))
    n_static = int(is_nrt_static.sum())
    df = df[~is_nrt_static].reset_index(drop=True)
    return df, {"type_2_or_3_dropped": int(n_type), "static_mask_cells": len(mask_cells),
                "nrt_in_static_cells_dropped": n_static}


def load_admin():
    import geopandas as gpd
    adm0 = gpd.read_file(C.BOUNDARY_FILES["adm0"]).to_crs(4326)
    adm2 = gpd.read_file(C.OCHA_FILES["adm2"]).to_crs(4326)
    adm2["adm2"] = adm2["ADM2_PCODE"].map(C.MUNICIPALITY_NAMES)
    adm2["adm1"] = adm2["ADM1_SQ"]
    adm2["adm2_code"] = adm2["ADM2_PCODE"]
    adm1 = adm2.dissolve(by="adm1", as_index=False)[["adm1", "geometry"]]
    return adm0, adm1, adm2[["adm2", "adm2_code", "adm1", "geometry"]]


def clip_and_attach(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    import geopandas as gpd
    adm0, adm1, adm2 = load_admin()
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=4326)
    inside = pts.within(adm0.geometry.iloc[0])
    n_out = int((~inside).sum())
    pts = pts[inside].copy()
    j = gpd.sjoin(pts, adm2, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    miss = j["adm2"].isna()
    if miss.any():  # tiny gaps between the two boundary sources: use the nearest municipality
        near = gpd.sjoin_nearest(j.loc[miss, ["geometry"]].to_crs(3857), adm2.to_crs(3857), how="left")
        near = near[~near.index.duplicated(keep="first")]
        j.loc[miss, "adm2"] = near["adm2"]
        j.loc[miss, "adm1"] = near["adm1"]
    out = pd.DataFrame(j.drop(columns=["geometry", "index_right", "adm2_code"], errors="ignore"))
    return out.reset_index(drop=True), {"outside_country_dropped": n_out, "nearest_municipality_used": int(miss.sum())}


def finish(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["conf_rank"] = df["confidence"].map({"low": 0, "nominal": 1, "high": 2}).astype(int)
    df["is_day"] = df["daynight"] == "D"
    df["is_night"] = df["daynight"] == "N"
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return df.sort_values(["date", "hhmm", "satellite"]).reset_index(drop=True)


def clean(df: pd.DataFrame, verbose: bool = True) -> tuple[pd.DataFrame, dict]:
    info = {"rows_loaded": int(len(df))}
    df, a = archive_before_nrt(df)
    info.update(a)
    df, b = drop_false_alarms(df)
    info.update(b)
    df, c = clip_and_attach(df)
    info.update(c)
    df = finish(df)
    info["rows_clean"] = int(len(df))
    info["low_confidence_rows"] = int((df["confidence"] == "low").sum())
    if verbose:
        for k, v in info.items():
            print(f"    {k}: {v}")
    return df, info
