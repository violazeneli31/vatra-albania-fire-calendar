"""Step 18: Fire Events Catalogue.

Cell-days that touch (8 neighbours, or the same cell) on days at most EVENT_MAX_GAP_DAYS apart
belong to the same event (union-find). Events with >= EVENT_MIN_CELLDAYS distinct cell-days are kept.
The size is the number of fire cell-days, not burnt area.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C


class DSU:
    def __init__(self, n):
        self.p = np.arange(n)

    def find(self, x):
        p = self.p
        root = x
        while p[root] != root:
            root = p[root]
        while p[x] != root:
            p[x], x = root, p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.p[rb] = ra
            else:
                self.p[ra] = rb


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def nearest_site(lat, lon, sites: pd.DataFrame):
    if sites is None or len(sites) == 0:
        return [""] * len(lat), np.full(len(lat), np.nan)
    d = haversine_km(np.asarray(lat)[:, None], np.asarray(lon)[:, None],
                     sites["lat"].to_numpy()[None, :], sites["lon"].to_numpy()[None, :])
    k = d.argmin(axis=1)
    return sites["name_en"].to_numpy()[k], d[np.arange(len(k)), k]


def build_events(cd: pd.DataFrame, sites: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Returns (events table, event_id per cell-day row of `cd` (or -1))."""
    use = cd[~cd["low_only"]]
    u = use.groupby(["ci", "cj", "date"], as_index=False).agg(n=("satellite", "size"))
    u["day"] = (u["date"] - pd.Timestamp("2000-01-01")).dt.days.astype(int)
    key = {(a, b, d): k for k, (a, b, d) in enumerate(zip(u["ci"], u["cj"], u["day"]))}
    dsu = DSU(len(u))
    gaps = range(0, C.EVENT_MAX_GAP_DAYS + 1)
    for k, (a, b, d) in enumerate(zip(u["ci"].to_numpy(), u["cj"].to_numpy(), u["day"].to_numpy())):
        for g in gaps:
            for da in (-1, 0, 1):
                for db in (-1, 0, 1):
                    if g == 0 and (da, db) >= (0, 0):
                        continue  # same day: look only at "earlier" neighbours to avoid double work
                    j = key.get((a + da, b + db, d - g))
                    if j is not None:
                        dsu.union(k, j)
    root = np.array([dsu.find(k) for k in range(len(u))])
    u["root"] = root
    size = u.groupby("root")["day"].transform("size")
    u = u[size >= C.EVENT_MIN_CELLDAYS]
    # number events by start date
    order = u.groupby("root")["date"].min().sort_values()
    ids = {r: i + 1 for i, r in enumerate(order.index)}
    u["event_id"] = u["root"].map(ids)
    m = cd.merge(u[["ci", "cj", "date", "event_id"]], on=["ci", "cj", "date"], how="left")
    ev_rows = m[m["event_id"].notna() & ~m["low_only"]]
    g = ev_rows.groupby("event_id")
    ev = pd.DataFrame({
        "start": g["date"].min(), "end": g["date"].max(),
        "cell_days": u.groupby("event_id").size(),
        "detections": g["n_det"].sum(),
        "harmonized_weight": g["weight"].sum().round(2),
        "max_frp": g["max_frp"].max().round(1),
        "lat": g["lat"].mean().round(4), "lon": g["lon"].mean().round(4),
        "county": g["adm1"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        "municipality": g["adm2"].agg(lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        "satellites": g["satellite"].agg(lambda s: ", ".join(sorted(set(s)))),
    })
    ev["days"] = (ev["end"] - ev["start"]).dt.days + 1
    ev = ev.reset_index()
    ev["event_id"] = ev["event_id"].astype(int)
    if sites is not None and len(sites):
        n, d = nearest_site(ev["lat"], ev["lon"], sites)
        ev["nearest_site"], ev["site_km"] = n, np.round(d, 1)
    else:
        ev["nearest_site"], ev["site_km"] = "", np.nan
    ev["year"] = ev["start"].dt.year
    ev["month"] = ev["start"].dt.month
    cols = ["event_id", "start", "end", "days", "cell_days", "detections", "harmonized_weight", "max_frp",
            "lat", "lon", "county", "municipality", "nearest_site", "site_km", "satellites", "year", "month"]
    return ev[cols].sort_values("event_id").reset_index(drop=True), m["event_id"].fillna(-1).astype(int)


def heritage_nearby(cd: pd.DataFrame, sites: pd.DataFrame) -> pd.DataFrame:
    """Fire cell-days (non-low, unique cell-date) within HERITAGE_RADIUS_KM of each site, per year."""
    u = cd[~cd["low_only"]].drop_duplicates(["cell_id", "date"])
    rows = []
    for _, s in sites.iterrows():
        d = haversine_km(u["lat"].to_numpy(), u["lon"].to_numpy(), s["lat"], s["lon"])
        near = u[d <= C.HERITAGE_RADIUS_KM]
        per_year = near.groupby("year").size()
        for y, n in per_year.items():
            rows.append({"site_id": s["site_id"], "name_en": s["name_en"], "type": s["type"], "year": int(y),
                         "fire_celldays_5km": int(n)})
    out = pd.DataFrame(rows, columns=["site_id", "name_en", "type", "year", "fire_celldays_5km"])
    return out
