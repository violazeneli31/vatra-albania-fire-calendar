"""VATRA build: run once on your computer (python build.py). Writes everything the app needs to outputs/.

Steps (see the "How it works" page and outputs/README.md):
 1 load all FIRMS files      5 harmonize (Terra-only fix, calibration, weights)
 2 clean (duplicates, false  6 monthly tables, normals, anomalies, seasons, trends
   alarms)                   7 validation, EFFIS check, Fire Events Catalogue
 3 clip to the country       8 data stories + headline finding
 4 fire cell-days            9 boundaries, summary, data dictionary
"""
from __future__ import annotations

import json
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from importlib import metadata

import numpy as np
import pandas as pd

import config as C
from src import clean, effis, events, grid, harmonize, load, stats, stories

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


def step(msg):
    print(f"\n== {msg}", flush=True)


def jdump(obj, path):
    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else round(float(o), 6)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, (pd.Timestamp, datetime)):
            return o.isoformat()[:10]
        if isinstance(o, set):
            return sorted(o)
        raise TypeError(type(o))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=conv)


def write_csv(df: pd.DataFrame, path):
    """UTF-8 with BOM so Excel shows ë and ç correctly."""
    df.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")


def area_monthly(cd, fires, months, abm, sd_log, ratio, level, name, harm=None):
    """Monthly table for one area. harm: precomputed harmonized series (country/adm1) or None (sum of weights)."""
    base = months[["year", "month"]].copy()
    c = cd[~cd["low_only"]]
    f = fires[fires["confidence"] != "low"]
    if level == "adm1":
        c, f = c[c["adm1"] == name], f[f["adm1"] == name]
    elif level == "adm2":
        c, f = c[c["adm2"] == name], f[f["adm2"] == name]
    rm = f[f["sensor"] == "MODIS"].groupby(["year", "month"]).size().rename("raw_modis")
    rv = f[f["sensor"] == "VIIRS"].groupby(["year", "month"]).size().rename("raw_viirs")
    cm = c[c["sensor"] == "MODIS"].groupby(["year", "month"]).size().rename("raw_modis_cd")
    cv = c[c["sensor"] == "VIIRS"].groupby(["year", "month"]).size().rename("raw_viirs_cd")
    w = c.groupby(["year", "month"])["weight"].sum().rename("hw")
    frp = c.groupby(["year", "month"])["max_frp"].sum().rename("frp_sum")
    t = base.set_index(["year", "month"]).join([rm, rv, cm, cv, w, frp]).fillna(0).reset_index()
    t["harmonized"] = harm if harm is not None else t["hw"]
    t = t.drop(columns="hw")
    t["harmonized"] = t["harmonized"].astype(float)
    a = abm.reset_index(drop=True)
    H = t["harmonized"].to_numpy()
    sd = np.nan_to_num(sd_log)
    rs = np.array([ratio[s]["ratio"] for s in a["season"]])
    rmin = np.array([ratio[s]["min"] for s in a["season"]])
    rmax = np.array([ratio[s]["max"] for s in a["season"]])
    t["low"] = np.where(a["use_viirs"], np.clip((H + 1) * np.exp(-C.PRED_INTERVAL_Z * sd) - 1, 0, None),
                        np.where(a["terra_only"], H * rmin / rs, H))
    t["high"] = np.where(a["use_viirs"], (H + 1) * np.exp(C.PRED_INTERVAL_Z * sd) - 1,
                         np.where(a["terra_only"], H * rmax / rs, H))
    t["terra_only_flag"] = a["terra_only"].to_numpy()
    t["partial_flag"] = a["partial"].to_numpy()
    t["viirs_satellites"] = a["viirs_n"].to_numpy()
    t["source_sensor"] = np.where(a["use_viirs"], "VIIRS (calibrated)", np.where(a["terra_only"], "MODIS Terra (scaled)", "MODIS"))
    t = stats.add_anomalies(t, "harmonized")
    t.insert(0, "area_level", level)
    t.insert(1, "area_name", name)
    return t


def validation_chart(series: pd.DataFrame, nat: pd.DataFrame, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8), dpi=150)
    fig.patch.set_facecolor("#FAF7F2")
    for a in ax:
        a.set_facecolor("#FFFBF4")
        for s in a.spines.values():
            s.set_color("#E4DACB")
    for split, col, mk in [("train", C.GOLD, "o"), ("test", C.RED, "D")]:
        d = series[series["split"] == split]
        ax[0].scatter(d["real_modis"] + 1, d["predicted"] + 1, s=18, c=col, marker=mk, alpha=.8,
                      label=f"{split} ({'fit' if split == 'train' else 'not used for fitting'})")
    mx = max(series["real_modis"].max(), series["predicted"].max()) + 2
    ax[0].plot([1, mx], [1, mx], color="#6E6560", lw=1, ls="--")
    ax[0].set_xscale("log"); ax[0].set_yscale("log")
    ax[0].set_xlabel("Real MODIS fire cell-days per month (+1)")
    ax[0].set_ylabel("VIIRS converted to MODIS scale (+1)")
    ax[0].set_title("Predicted vs real, monthly, Albania", color=C.RED, fontweight="bold")
    ax[0].legend(frameon=False, fontsize=9)
    yr = nat.groupby("year")[["raw_modis", "raw_viirs", "harmonized"]].sum()
    yr = yr.loc[2001:2025]
    ax[1].plot(yr.index, yr["raw_modis"] + yr["raw_viirs"], color="#8C8178", lw=2, ls="--", label="Raw hotspots (all satellites)")
    ax[1].plot(yr.index, yr["harmonized"], color=C.RED, lw=2.6, label="VATRA harmonized (cell-days, MODIS-equivalent)")
    ax[1].axvline(2012, color=C.GOLD, lw=1.5, ls=":")
    ax[1].text(2012.2, ax[1].get_ylim()[1] * 0.92, "VIIRS starts", color="#8a6a1e", fontsize=9)
    ax[1].set_yscale("log")
    ax[1].set_title("The 2012 jump: raw counts vs harmonized record", color=C.RED, fontweight="bold")
    ax[1].legend(frameon=False, fontsize=9, loc="upper left")
    fig.text(0.01, 0.01, "VATRA · data: NASA FIRMS (MODIS C6.1, VIIRS 375 m)", fontsize=8, color="#6E6560")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_boundaries(out):
    from src.clean import load_admin
    adm0, adm1, adm2 = load_admin()
    a1 = adm1.copy()
    a1["geometry"] = a1.simplify(0.004, preserve_topology=True)
    a1["name"] = a1["adm1"]
    a1["id"] = a1["adm1"].map({v: k for k, v in C.COUNTIES})
    a1[["id", "name", "geometry"]].to_file(out / "boundaries_adm1.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)
    a2 = adm2.copy()
    a2["geometry"] = a2.simplify(0.003, preserve_topology=True)
    a2 = a2.rename(columns={"adm2": "name", "adm1": "county", "adm2_code": "code"})
    a2[["code", "name", "county", "geometry"]].to_file(out / "boundaries_adm2.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)
    a0 = adm0.copy()
    a0["geometry"] = a0.simplify(0.01, preserve_topology=True)
    a0[["geometry"]].to_file(out / "boundaries_adm0.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)
    # area list: centroid + bounds for map zoom and pickers
    rows = [{"level": "country", "name": C.COUNTRY, "county": "", "lat": float(adm0.geometry.iloc[0].representative_point().y),
             "lon": float(adm0.geometry.iloc[0].representative_point().x), "bounds": list(map(float, adm0.total_bounds))}]
    for _, r in adm1.iterrows():
        p = r.geometry.representative_point()
        rows.append({"level": "adm1", "name": r["adm1"], "county": r["adm1"], "lat": p.y, "lon": p.x,
                     "bounds": list(map(float, r.geometry.bounds)), "area_km2": None})
    for _, r in adm2.iterrows():
        p = r.geometry.representative_point()
        rows.append({"level": "adm2", "name": r["adm2"], "county": r["adm1"], "lat": p.y, "lon": p.x,
                     "bounds": list(map(float, r.geometry.bounds))})
    areas = pd.DataFrame(rows)
    a_eq = adm2.to_crs(6933)
    km2 = dict(zip(adm2["adm2"], (a_eq.area / 1e6).round(1)))
    c_eq = adm1.to_crs(6933)
    km2.update(dict(zip(adm1["adm1"], (c_eq.area / 1e6).round(1))))
    km2[C.COUNTRY] = float((adm0.to_crs(6933).area / 1e6).round(1).iloc[0])
    areas["area_km2"] = areas["name"].map(km2)
    jdump(areas.to_dict(orient="records"), out / "areas.json")
    return [round(float(x), 3) for x in adm0.total_bounds]


def write_effis_layer(e, out):
    g = e[["id", "initialdate", "finaldate", "area_ha", "county", "municipality", "map_source", "geometry"]].copy()
    g["geometry"] = g.simplify(0.0015, preserve_topology=True)
    g["initialdate"] = g["initialdate"].dt.strftime("%Y-%m-%d")
    g["finaldate"] = g["finaldate"].dt.strftime("%Y-%m-%d")
    g["year"] = pd.to_datetime(g["initialdate"]).dt.year
    g.to_file(out / "effis_burnt_areas.geojson", driver="GeoJSON", COORDINATE_PRECISION=4)


def package_versions():
    out = {"python": platform.python_version()}
    for p in ["streamlit", "pandas", "numpy", "geopandas", "shapely", "plotly", "folium", "pymannkendall",
              "scipy", "fpdf2", "matplotlib", "pyarrow", "pyproj"]:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pass
    return out


def main():
    t0 = time.time()
    out = C.OUT
    out.mkdir(exist_ok=True)

    step("1 Load all FIRMS files")
    raw = load.load_all()
    print(f"  {len(raw):,} rows")

    step("2-3 Clean and clip to the country")
    fires, clean_info = clean.clean(raw)
    print("  detections per satellite per year (after cleaning):")
    print(fires.groupby(["year", "satellite"]).size().unstack(fill_value=0).to_string())

    step("4 Fire cell-days")
    cd = grid.to_celldays(fires)
    print(f"  {len(cd):,} cell-days (cell x day x satellite)")

    step("5 Harmonize")
    cd, natm, cty, calib, abm = harmonize.harmonize(cd)
    months = harmonize.month_table(cd["date"].min(), cd["date"].max())
    ratio = calib["terra_only_ratio"]
    sd_log = natm["sd_log"].to_numpy()

    step("6 Monthly tables, normals, anomalies")
    sites = pd.read_csv(C.CONTENT / "heritage_sites.csv")
    tables = [area_monthly(cd, fires, months, abm, sd_log, ratio, "country", C.COUNTRY, natm["harmonized"].to_numpy())]
    for county in sorted(cd["adm1"].dropna().unique()):
        h = cty[cty["adm1"] == county].sort_values(["year", "month"])["harmonized"].to_numpy()
        tables.append(area_monthly(cd, fires, months, abm, sd_log, ratio, "adm1", county, h))
    mun_county = fires.groupby("adm2")["adm1"].agg(lambda s: s.mode().iloc[0]).to_dict()
    for mun in sorted(C.MUNICIPALITY_NAMES.values()):
        tables.append(area_monthly(cd, fires, months, abm, sd_log, ratio, "adm2", mun))
    monthly = pd.concat(tables, ignore_index=True)
    monthly["parent"] = np.where(monthly["area_level"] == "adm2", monthly["area_name"].map(mun_county),
                                 np.where(monthly["area_level"] == "adm1", C.COUNTRY, ""))
    nat = monthly[monthly["area_level"] == "country"]
    # sanity: counties and municipalities add up to the country
    s_c = monthly[monthly["area_level"] == "adm1"]["harmonized"].sum()
    s_m = monthly[monthly["area_level"] == "adm2"]["harmonized"].sum()
    print(f"  harmonized total: country {nat['harmonized'].sum():,.1f} | counties {s_c:,.1f} | municipalities {s_m:,.1f}")

    seasons_rows, trend_rows = [], []
    for (lvl, name), g in monthly.groupby(["area_level", "area_name"], sort=False):
        n = stats.month_normals(g, "harmonized")
        s = stats.seasons(n)
        seasons_rows.append({"area_level": lvl, "area_name": name, "season_start": s["start"], "season_peak": s["peak"],
                             "season_end": s["end"], "two_seasons": "yes" if s["two_seasons"] else "no",
                             "second_peak": s["second_peak"], "season_months": " ".join(map(str, s["season_months"])),
                             "peak_median": float(n["median"].max()), "yearly_median": float(
                                 g[(g.year >= C.BASE_YEARS[0]) & (g.year <= C.BASE_YEARS[1])].groupby("year")["harmonized"].sum().median())})
        tr = stats.trend(g, "harmonized")
        trend_rows.append({"area_level": lvl, "area_name": name, "years": tr["years"], "sens_slope_per_year": tr["slope"],
                           "pct_per_year": tr["pct_per_year"], "mk_p_value": tr["p"], "direction": tr["direction"],
                           "intercept": tr["intercept"]})
    seasons = pd.DataFrame(seasons_rows)
    trends = pd.DataFrame(trend_rows)
    anomalies = monthly[monthly["status"].isin(["above", "below", "extreme"]) & ~monthly["terra_only_flag"]][
        ["area_level", "area_name", "year", "month", "harmonized", "median", "p10", "p90", "anomaly", "anomaly_pct", "z_log", "status"]]
    print(f"  national seasons: {seasons.iloc[0].to_dict()}")
    print(f"  national trend: {trends.iloc[0].to_dict()}")

    step("7a Validation")
    val, series = harmonize.validate(cd, natm, cty[["adm1", "year", "month"] + C.ALL_SATS], abm)
    for k in ["train", "test"]:
        m = val["national"][k]
        print(f"  national {k}: n={m['n']} MAE={m['mae']:.2f} RMSE={m['rmse']:.2f} bias={m['bias_pct']:+.1f}% "
              f"Pearson={m['pearson']:.3f} Spearman={m['spearman']:.3f}")
    print(f"  NOAA-21 test: {val['noaa21']['test']}")
    print(f"  counties (median of 12): {val['counties']['median']}")
    validation_chart(series, nat, out / "validation_chart.png")
    series.to_csv(out / "validation_series.csv", index=False)

    step("7b Fire Events Catalogue")
    ev, ev_id = events.build_events(cd, sites)
    cd["event_id"] = ev_id.to_numpy()
    print(f"  {len(ev):,} events with >= {C.EVENT_MIN_CELLDAYS} cell-days; largest: "
          f"{ev.nlargest(3, 'cell_days')[['start', 'municipality', 'days', 'cell_days']].to_dict(orient='records')}")

    step("7c EFFIS check")
    e = effis.load_effis()
    eff_table, eff_sum, ev = effis.compare(e, monthly, cd, ev)
    print(f"  EFFIS fires {eff_sum['effis_fires']}, yearly r = {eff_sum['national'].get('yearly_pearson')}, "
          f"Spearman = {eff_sum['national'].get('yearly_spearman')}, cell-days inside perimeters {eff_sum['share_celldays_inside']:.1%}")
    val["effis"] = {k: v for k, v in eff_sum.items() if k != "counties"}
    write_effis_layer(e, out)

    step("8 Headline and data stories")
    cty_tot = monthly[(monthly["area_level"] == "adm1") & (monthly["year"] <= C.BASE_YEARS[1])].groupby("area_name")["harmonized"].sum()
    normals_nat = stats.month_normals(nat, "harmonized")
    tr_nat = stats.trend(nat, "harmonized")
    hl = stories.headline(nat, tr_nat, cty_tot, normals_nat)
    hl["validation"] = {"test_pearson": val["national"]["test"]["pearson"], "test_spearman": val["national"]["test"]["spearman"],
                        "test_bias_pct": val["national"]["test"]["bias_pct"], "test_mae": val["national"]["test"]["mae"]}
    print("  " + hl["text_en"])
    ys = stories.year_stories(nat, monthly[monthly["area_level"] == "adm1"], ev)
    es = stories.event_stories(ev, monthly, 50)
    jdump({"headline": hl["text_en"], "years": ys["en"], "events": es["en"]}, out / "stories_en.json")
    jdump({"headline": hl["text_sq"], "years": ys["sq"], "events": es["sq"]}, out / "stories_sq.json")
    jdump(hl, out / "headline.json")

    step("9 Heritage, boundaries, files")
    hn = events.heritage_nearby(cd, sites)
    write_csv(hn, out / "heritage_nearby.csv")
    bbox = write_boundaries(out)

    fires_out = fires[["date", "time", "hhmm", "lat", "lon", "satellite", "sensor", "source", "confidence", "frp", "daynight",
                       "adm1", "adm2", "cell_id", "year", "month"]].copy()
    fires_out["frp"] = fires_out["frp"].round(2)
    fires_out.to_parquet(out / "fires_clean.parquet", index=False, compression="zstd")
    write_csv(fires_out.drop(columns=["hhmm", "year", "month"]), out / "fires_clean.csv")
    cd_out = cd[["date", "cell_id", "lat", "lon", "satellite", "sensor", "weight", "max_frp", "n_det", "adm1", "adm2",
                 "low_only", "dn", "event_id", "year", "month"]].copy()
    cd_out["max_frp"] = cd_out["max_frp"].round(2)
    cd_out.to_parquet(out / "celldays_harmonized.parquet", index=False, compression="zstd")
    write_csv(cd_out.drop(columns=["year", "month"]), out / "celldays_harmonized.csv")
    mcols = ["area_level", "area_name", "parent", "year", "month", "raw_modis", "raw_viirs", "raw_modis_cd", "raw_viirs_cd",
             "harmonized", "low", "high", "median", "p10", "p90", "max", "anomaly", "anomaly_pct", "z_log", "status",
             "terra_only_flag", "partial_flag", "viirs_satellites", "source_sensor", "frp_sum"]
    mo = monthly[mcols].copy()
    for c in ["harmonized", "low", "high", "median", "p10", "p90", "max", "anomaly", "frp_sum"]:
        mo[c] = mo[c].astype(float).round(2)
    mo["anomaly_pct"] = mo["anomaly_pct"].round(1)
    mo["z_log"] = mo["z_log"].astype(float).round(3)
    for c in ["raw_modis", "raw_viirs", "raw_modis_cd", "raw_viirs_cd"]:
        mo[c] = mo[c].astype(int)
    mo.to_parquet(out / "monthly_harmonized.parquet", index=False, compression="zstd")
    write_csv(mo, out / "monthly_harmonized.csv")
    write_csv(seasons, out / "seasons.csv")
    write_csv(anomalies.round(3), out / "anomalies.csv")
    ev_out = ev.copy()
    ev.to_parquet(out / "events.parquet", index=False)
    write_csv(ev_out, out / "events.csv")
    write_csv(trends, out / "trends.csv")
    write_csv(eff_table, out / "effis_comparison.csv")
    jdump(calib, out / "calibration.json")
    jdump(val, out / "validation.json")

    last = cd.groupby("satellite")["date"].max().dt.strftime("%Y-%m-%d").to_dict()
    first = cd.groupby("satellite")["date"].min().dt.strftime("%Y-%m-%d").to_dict()
    summary = {
        "country": C.COUNTRY, "bbox": bbox, "build_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "build_seconds": round(time.time() - t0, 1), "first_date_per_satellite": first, "last_date_per_satellite": last,
        "data_end": calib["data_end"], "detections_clean": int(len(fires)), "detections_by_sensor": fires["sensor"].value_counts().to_dict(),
        "celldays": int(len(cd)), "events": int(len(ev)), "harmonized_total": float(nat["harmonized"].sum()),
        "base_years": list(C.BASE_YEARS), "cleaning": clean_info, "packages": package_versions(),
        "first_month": f"{int(months['year'].iloc[0])}-{int(months['month'].iloc[0]):02d}",
        "last_month": f"{int(months['year'].iloc[-1])}-{int(months['month'].iloc[-1]):02d}",
    }
    try:
        from src.theme import check_ramp
        summary["colour_ramp_check"] = check_ramp()
        print("  colour ramp, CIELAB lightness falls at every step:",
              {k: v["monotonic"] for k, v in summary["colour_ramp_check"].items()})
    except Exception as e:  # colorspacious is only in requirements-build.txt
        print("  colour ramp check skipped:", e)
    jdump(summary, out / "summary.json")
    publish_folder(out)
    size = sum(p.stat().st_size for p in out.glob("*") if p.is_file()) / 1e6
    print(f"\nDone in {time.time() - t0:.0f} s. outputs/ = {size:.1f} MB")
    if size > 50:
        print("WARNING: outputs/ is larger than 50 MB")


PUBLISH = ["monthly_harmonized.csv", "celldays_harmonized.csv", "fires_clean.csv", "events.csv", "anomalies.csv",
           "seasons.csv", "trends.csv", "effis_comparison.csv", "heritage_nearby.csv", "calibration.json",
           "validation.json", "validation_series.csv", "README.md"]


def publish_folder(out):
    """Copy the files meant for publishing (Zenodo dataset record) into outputs/dataset_to_publish/."""
    import shutil
    dst = out / "dataset_to_publish"
    dst.mkdir(exist_ok=True)
    for name in PUBLISH:
        if (out / name).exists():
            shutil.copy2(out / name, dst / name)
    print(f"  dataset_to_publish/: {len(PUBLISH)} files")


if __name__ == "__main__":
    sys.exit(main())
