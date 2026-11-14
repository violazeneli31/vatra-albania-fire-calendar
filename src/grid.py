"""Step 4: the ~1 km grid used for fire cell-days."""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C


def cell_index(lat, lon):
    """Integer grid row/column of each point (0.01 degree cells)."""
    i = np.floor(np.asarray(lat, dtype=float) / C.GRID_DEG + 1e-9).astype(int)
    j = np.floor(np.asarray(lon, dtype=float) / C.GRID_DEG + 1e-9).astype(int)
    return i, j


def cell_id(i, j) -> pd.Series:
    return pd.Series(i).astype(str) + "_" + pd.Series(j).astype(str)


def cell_center(i, j):
    return (np.asarray(i) + 0.5) * C.GRID_DEG, (np.asarray(j) + 0.5) * C.GRID_DEG


def add_cells(df: pd.DataFrame) -> pd.DataFrame:
    i, j = cell_index(df["lat"].values, df["lon"].values)
    df = df.copy()
    df["ci"], df["cj"] = i, j
    df["cell_id"] = cell_id(i, j).values
    return df


def to_celldays(fires: pd.DataFrame) -> pd.DataFrame:
    """One row per cell per day per satellite.

    A VIIRS satellite often sees one fire as several small 375 m pixels; counting
    each ~1 km cell once per day per satellite removes most of that difference.
    """
    g = fires.groupby(["date", "cell_id", "satellite"], sort=False)
    cd = g.agg(ci=("ci", "first"), cj=("cj", "first"), sensor=("sensor", "first"),
               n_det=("lat", "size"), max_frp=("frp", "max"),
               adm1=("adm1", "first"), adm2=("adm2", "first"),
               conf_best=("conf_rank", "max"), has_d=("is_day", "max"), has_n=("is_night", "max"),
               source=("source", "first")).reset_index()
    cd["low_only"] = cd["conf_best"] == 0
    cd["dn"] = np.where(cd["has_d"] & cd["has_n"], "B", np.where(cd["has_d"], "D", "N"))
    cd = cd.drop(columns=["conf_best", "has_d", "has_n"])
    lat, lon = cell_center(cd["ci"], cd["cj"])
    cd["lat"], cd["lon"] = np.round(lat, 3), np.round(lon, 3)
    cd["year"] = cd["date"].dt.year
    cd["month"] = cd["date"].dt.month
    return cd
