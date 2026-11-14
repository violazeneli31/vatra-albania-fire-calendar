"""Steps 5-10: Terra-only scaling, MODIS-VIIRS calibration, harmonized record, cell-day weights, validation.

Units: "fire cell-days, MODIS-equivalent" = Terra cell-days + Aqua cell-days. VIIRS satellites are
converted to that scale with log(MODIS + 1) = a + b * log(VIIRS + 1), fitted on monthly totals in the
years when both sensors fly, separately per VIIRS satellite and per season.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as ss

import config as C


def season_of(month) -> np.ndarray:
    return np.where(np.isin(np.asarray(month), C.FIRE_SEASON_MONTHS), "fire", "off")


def month_table(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    ms = pd.period_range(start.to_period("M"), end.to_period("M"), freq="M")
    t = pd.DataFrame({"period": ms})
    t["year"] = t["period"].dt.year
    t["month"] = t["period"].dt.month
    t["season"] = season_of(t["month"])
    t["start"] = t["period"].dt.start_time
    t["end"] = t["period"].dt.end_time.dt.normalize()
    return t


def sat_availability(cd: pd.DataFrame, months: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Which satellites cover each month (first date <= start+10 d and last date >= end-10 d).

    The last month in the data is partial: satellites that still deliver data close to the
    end of the record count as available.
    """
    first = cd.groupby("satellite")["date"].min()
    last = cd.groupby("satellite")["date"].max()
    for s, d in C.VIIRS_START.items():
        if s in first:
            first[s] = max(first[s], pd.Timestamp(d))
    global_last = last.max()
    av = pd.DataFrame(index=months.index)
    for s in C.ALL_SATS:
        if s not in first:
            av[s] = False
            continue
        ok_start = first[s] <= months["start"] + pd.Timedelta(days=10)
        ok_end = (last[s] >= months["end"] - pd.Timedelta(days=10)) | (last[s] >= global_last - pd.Timedelta(days=5))
        av[s] = (ok_start & ok_end).to_numpy()
    av["partial"] = (months["end"] > global_last).to_numpy()
    span = {s: [str(first[s].date()), str(last[s].date())] for s in first.index}
    return av, {"satellite_span": span, "data_end": str(global_last.date())}


def counts(cd: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Non-low-confidence cell-days per month per satellite (columns = satellites)."""
    d = cd[~cd["low_only"]]
    c = d.groupby(by + ["year", "month", "satellite"]).size().unstack("satellite", fill_value=0)
    for s in C.ALL_SATS:
        if s not in c:
            c[s] = 0
    return c[C.ALL_SATS].reset_index()


# ------------------------------------------------------------------ Terra-only scaling
def terra_ratio(nat: pd.DataFrame) -> dict:
    y0, y1 = C.TERRA_RATIO_YEARS
    d = nat[(nat["year"] >= y0) & (nat["year"] <= y1)].copy()
    d["season"] = season_of(d["month"])
    out = {}
    for se, g in d.groupby("season"):
        t, a = g["Terra"].sum(), g["Aqua"].sum()
        per_year = g.groupby("year")[["Terra", "Aqua"]].sum()
        per_year = per_year[per_year["Terra"] > 0]
        r_y = ((per_year["Terra"] + per_year["Aqua"]) / per_year["Terra"]).to_numpy()
        out[se] = {"ratio": float((t + a) / t) if t > 0 else 2.0,
                   "min": float(r_y.min()) if len(r_y) else 1.5, "max": float(r_y.max()) if len(r_y) else 2.5,
                   "terra_celldays": int(t), "aqua_celldays": int(a)}
    return out


def is_terra_only(year, month):
    y, m = C.FIRST_FULL_MODIS
    return (np.asarray(year) * 100 + np.asarray(month)) < (y * 100 + m)


# ------------------------------------------------------------------ calibration
def fit_line(x, y) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 4 or np.ptp(x) == 0:
        a = float(np.mean(y - x)) if len(x) else 0.0
        b = 1.0
    else:
        b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    sd = float(np.std(resid, ddof=2)) if len(x) > 2 else 0.5
    smear = float(np.mean(np.exp(resid))) if len(x) else 1.0
    r2 = float(1 - np.sum(resid ** 2) / np.sum((y - y.mean()) ** 2)) if len(x) > 2 and np.var(y) > 0 else None
    return {"a": float(a), "b": float(b), "sd": sd, "smear": smear, "n": int(len(x)), "r2": r2}


def predict(fit: dict, v, adj: float = 0.0) -> np.ndarray:
    v = np.asarray(v, float)
    p = fit["smear"] * np.exp(fit["a"] + adj + fit["b"] * np.log1p(v)) - 1.0
    return np.clip(p, 0, None)


def calibrate(nat: pd.DataFrame, av: pd.DataFrame, months: pd.DataFrame, years=None, sats=None) -> dict:
    """Fit per VIIRS satellite and season on months where MODIS and that satellite both fly."""
    df = nat.merge(months[["year", "month", "season"]], on=["year", "month"])
    df["M"] = df["Terra"] + df["Aqua"]
    out = {}
    for s in (sats or C.VIIRS_SATS):
        sel = df.merge(av_frame(av, months, s), on=["year", "month"])
        sel = sel[sel["avail"] & sel["modis_ok"] & ~sel["partial"]]
        if years:
            sel = sel[(sel["year"] >= years[0]) & (sel["year"] <= years[1])]
        out[s] = {}
        for se in ["fire", "off"]:
            g = sel[sel["season"] == se]
            f = fit_line(np.log1p(g[s]), np.log1p(g["M"]))
            f["months"] = [int(g["year"].min()) if len(g) else None, int(g["year"].max()) if len(g) else None]
            out[s][se] = f
    return out


def av_frame(av: pd.DataFrame, months: pd.DataFrame, s: str) -> pd.DataFrame:
    return pd.DataFrame({"year": months["year"].to_numpy(), "month": months["month"].to_numpy(),
                         "avail": av[s].to_numpy(), "modis_ok": (av["Terra"] & av["Aqua"]).to_numpy(),
                         "partial": av["partial"].to_numpy()})


def combine(viirs_counts: pd.DataFrame, avail: pd.DataFrame, cal: dict, adj: dict | None = None,
            sats=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mean of calibrated available VIIRS satellites (MODIS-equivalent), with the log-scale sd and count."""
    sats = sats or C.VIIRS_SATS
    se = season_of(viirs_counts["month"])
    preds, sds, n = np.zeros(len(viirs_counts)), np.zeros(len(viirs_counts)), np.zeros(len(viirs_counts))
    for s in sats:
        if s not in cal:
            continue
        on = avail[s].to_numpy()
        for season in ["fire", "off"]:
            m = on & (se == season)
            if not m.any():
                continue
            f = cal[s][season]
            preds[m] += predict(f, viirs_counts.loc[m, s].to_numpy(), (adj or {}).get(s, 0.0))
            sds[m] += f["sd"]
            n[m] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, preds / np.maximum(n, 1), np.nan)
        sd = np.where(n > 0, sds / np.maximum(n, 1), np.nan)
    vsum = viirs_counts[[s for s in sats]].sum(axis=1).to_numpy()
    mean = np.where((n > 0) & (vsum == 0), 0.0, mean)
    return mean, sd, n


# ------------------------------------------------------------------ the whole step
def county_adjustments(cty: pd.DataFrame, avail_by_ym: pd.DataFrame, cal: dict, years=None) -> dict:
    """Intercept shift per county and satellite, shrunk towards the national fit: n/(n+K) * mean residual."""
    out = {}
    for county, g in cty.groupby("adm1"):
        g = g.merge(avail_by_ym, on=["year", "month"])
        if years:
            g = g[(g["year"] >= years[0]) & (g["year"] <= years[1])]
        M = g["Terra"] + g["Aqua"]
        active = int((M >= C.COUNTY_MIN_CELLDAYS).sum())
        out[county] = {"eligible": active >= C.COUNTY_MIN_MONTHS, "active_months": active}
        for s in C.VIIRS_SATS:
            sel = g[g[s + "_av"] & g["modis_ok"] & ~g["partial"] & ((M + g[s]) > 0)]
            if not out[county]["eligible"] or len(sel) == 0:
                out[county][s] = 0.0
                continue
            Ms = sel["Terra"] + sel["Aqua"]
            res = []
            for season in ["fire", "off"]:
                q = sel[season_of(sel["month"]) == season]
                if len(q) == 0:
                    continue
                f = cal[s][season]
                pred = np.log(f["smear"]) + f["a"] + f["b"] * np.log1p(q[s].to_numpy())
                res.append(np.log1p((q["Terra"] + q["Aqua"]).to_numpy()) - pred)
            r = np.concatenate(res) if res else np.array([])
            nn = len(r)
            out[county][s] = float(nn / (nn + C.COUNTY_SHRINK_K) * r.mean()) if nn else 0.0
            out[county][s + "_n"] = nn
    return out


def avail_by_month(av: pd.DataFrame, months: pd.DataFrame) -> pd.DataFrame:
    t = pd.DataFrame({"year": months["year"].to_numpy(), "month": months["month"].to_numpy()})
    for s in C.ALL_SATS:
        t[s + "_av"] = av[s].to_numpy()
    t["modis_ok"] = (av["Terra"] & av["Aqua"]).to_numpy()
    t["partial"] = av["partial"].to_numpy()
    t["viirs_n"] = av[C.VIIRS_SATS].sum(axis=1).to_numpy()
    return t


def harmonize(cd: pd.DataFrame, verbose: bool = True):
    """Returns (cd with weights, national monthly, county monthly, calibration dict, availability)."""
    months = month_table(cd["date"].min(), cd["date"].max())
    av, span = sat_availability(cd, months)
    abm = avail_by_month(av, months)
    abm["use_viirs"] = abm["viirs_n"] > 0
    abm["terra_only"] = is_terra_only(abm["year"], abm["month"])
    abm["season"] = season_of(abm["month"])

    nat = months[["year", "month"]].merge(counts(cd, []), on=["year", "month"], how="left").fillna(0)
    ratio = terra_ratio(nat)
    cal = calibrate(nat, av, months)

    # ---- national harmonized series
    vc = nat.copy()
    av_cols = pd.DataFrame({s: abm[s + "_av"].to_numpy() for s in C.ALL_SATS})
    h_v, sd_v, n_v = combine(vc, av_cols, cal)
    M = (nat["Terra"] + nat["Aqua"]).to_numpy(float)
    r_season = np.array([ratio[s]["ratio"] for s in abm["season"]])
    rmin = np.array([ratio[s]["min"] for s in abm["season"]])
    rmax = np.array([ratio[s]["max"] for s in abm["season"]])
    terra = nat["Terra"].to_numpy(float)
    H = np.where(abm["use_viirs"], h_v, np.where(abm["terra_only"], terra * r_season, M))
    low = np.where(abm["use_viirs"], np.clip((H + 1) * np.exp(-C.PRED_INTERVAL_Z * np.nan_to_num(sd_v)) - 1, 0, None),
                   np.where(abm["terra_only"], terra * rmin, M))
    high = np.where(abm["use_viirs"], (H + 1) * np.exp(C.PRED_INTERVAL_Z * np.nan_to_num(sd_v)) - 1,
                    np.where(abm["terra_only"], terra * rmax, M))
    natm = nat.assign(harmonized=H, low=low, high=high, use_viirs=abm["use_viirs"].to_numpy(),
                      terra_only=abm["terra_only"].to_numpy(), partial=abm["partial"].to_numpy(),
                      viirs_n=abm["viirs_n"].to_numpy(), sd_log=sd_v)

    # ---- counties: own prediction (national fit + shrunk adjustment), then scaled to add up to the national total
    cty = counts(cd, ["adm1"])
    full = pd.MultiIndex.from_product([sorted(cd["adm1"].dropna().unique()), range(len(months))],
                                      names=["adm1", "k"]).to_frame(index=False)
    full["year"] = months["year"].to_numpy()[full["k"]]
    full["month"] = months["month"].to_numpy()[full["k"]]
    cty = full.drop(columns="k").merge(cty, on=["adm1", "year", "month"], how="left").fillna(0)
    adj = county_adjustments(cty, abm, cal)
    cty = cty.merge(abm, on=["year", "month"], how="left")
    pred = np.zeros(len(cty))
    for county, idx in cty.groupby("adm1").groups.items():
        sub = cty.loc[idx]
        a = {s: adj[county].get(s, 0.0) for s in C.VIIRS_SATS}
        p, _, _ = combine(sub, pd.DataFrame({s: sub[s + "_av"].to_numpy() for s in C.ALL_SATS}), cal, a)
        pred[np.asarray(idx)] = np.nan_to_num(p)
    cty["pred"] = pred
    cty["vsum"] = sum(cty[s] * cty[s + "_av"].astype(int) for s in C.VIIRS_SATS)
    tot = cty.groupby(["year", "month"])[["pred", "vsum"]].transform("sum")
    nat_h = cty[["year", "month"]].merge(natm[["year", "month", "harmonized", "low", "high"]],
                                         on=["year", "month"], how="left")
    share = np.where(tot["pred"] > 0, cty["pred"] / tot["pred"].replace(0, np.nan),
                     np.where(tot["vsum"] > 0, cty["vsum"] / tot["vsum"].replace(0, np.nan), 0.0))
    share = np.nan_to_num(share)
    Mc = (cty["Terra"] + cty["Aqua"]).to_numpy(float)
    rs = np.array([ratio[s]["ratio"] for s in cty["season"]])
    cty["harmonized"] = np.where(cty["use_viirs"], nat_h["harmonized"].to_numpy() * share,
                                 np.where(cty["terra_only"], cty["Terra"] * rs, Mc))

    # ---- weights for every cell-day (so any custom area = sum of weights)
    cd = cd.copy()
    cd = cd.merge(abm[["year", "month", "use_viirs", "terra_only", "season"]], on=["year", "month"], how="left")
    cw = cty[["adm1", "year", "month", "harmonized", "vsum"]].copy()
    cw["w_cty"] = np.where(cw["vsum"] > 0, cw["harmonized"] / cw["vsum"].replace(0, np.nan), np.nan)
    nv = natm[["year", "month", "harmonized"]].copy()
    nv["vsum"] = sum(nat[s].to_numpy() * abm[s + "_av"].to_numpy().astype(int) for s in C.VIIRS_SATS)
    nv["w_nat"] = np.where(nv["vsum"] > 0, nv["harmonized"] / nv["vsum"].replace(0, np.nan), np.nan)
    cd = cd.merge(cw[["adm1", "year", "month", "w_cty"]], on=["adm1", "year", "month"], how="left")
    cd = cd.merge(nv[["year", "month", "w_nat"]], on=["year", "month"], how="left")
    glob = {se: float(np.nanmedian(nv.loc[season_of(nv["month"]) == se, "w_nat"])) for se in ["fire", "off"]}
    is_v = cd["sensor"] == "VIIRS"
    wv = cd["w_cty"].fillna(cd["w_nat"]).fillna(cd["season"].map(glob))
    wm = np.where(cd["terra_only"], cd["season"].map({k: v["ratio"] for k, v in ratio.items()}), 1.0)
    cd["weight"] = np.where(cd["use_viirs"], np.where(is_v, wv, 0.0), np.where(is_v, 0.0, wm))
    # a satellite that is not "available" in a month (partial coverage) must not add weight there
    av_long = abm.melt(id_vars=["year", "month"], value_vars=[s + "_av" for s in C.VIIRS_SATS],
                       var_name="satellite", value_name="sat_av")
    av_long["satellite"] = av_long["satellite"].str[:-3]
    cd = cd.merge(av_long, on=["year", "month", "satellite"], how="left")
    cd.loc[is_v & cd["use_viirs"] & ~cd["sat_av"].fillna(False).astype(bool), "weight"] = 0.0
    cd["weight"] = cd["weight"].astype(float).round(5)
    cd = cd.drop(columns=["w_cty", "w_nat", "use_viirs", "terra_only", "season", "sat_av"])

    # recent weights for API cell-days (latest days): median national weight per calendar month, last 3 years
    nvr = nv[(nv["year"] >= nv["year"].max() - 3)].dropna(subset=["w_nat"])
    recent_w = {int(m): float(g["w_nat"].median()) for m, g in nvr.groupby("month")}

    calib = {"units": "fire cell-days, MODIS-equivalent (Terra + Aqua cell-days)",
             "formula": "log(MODIS+1) = a + b*log(VIIRS+1); prediction = smear*exp(a+adj+b*log(VIIRS+1)) - 1",
             "grid_deg": C.GRID_DEG, "seasons": {"fire": C.FIRE_SEASON_MONTHS,
                                                  "off": [m for m in range(1, 13) if m not in C.FIRE_SEASON_MONTHS]},
             "national": cal, "terra_only_ratio": ratio, "county_adjustment": adj,
             "county_rule": {"min_months": C.COUNTY_MIN_MONTHS, "min_celldays": C.COUNTY_MIN_CELLDAYS,
                             "shrink_K": C.COUNTY_SHRINK_K},
             "recent_weight_by_month": recent_w, "global_weight_by_season": glob,
             "prediction_interval": f"{int(round(2 * ss.norm.cdf(C.PRED_INTERVAL_Z) * 100 - 100))} %",
             **span}
    if verbose:
        for s, d in cal.items():
            for se, f in d.items():
                print(f"    {s:8} {se:4}: a={f['a']:+.3f} b={f['b']:.3f} sd={f['sd']:.3f} n={f['n']} R2={f['r2']}")
        print(f"    Terra-only ratio: { {k: round(v['ratio'], 3) for k, v in ratio.items()} }")
    return cd, natm, cty, calib, abm


# ------------------------------------------------------------------ validation
def _metrics(pred, real) -> dict:
    pred, real = np.asarray(pred, float), np.asarray(real, float)
    ok = ~(np.isnan(pred) | np.isnan(real))
    pred, real = pred[ok], real[ok]
    if len(pred) < 3:
        return {"n": int(len(pred))}
    out = {"n": int(len(pred)), "mae": float(np.mean(np.abs(pred - real))),
           "rmse": float(np.sqrt(np.mean((pred - real) ** 2))),
           "bias_pct": float(100 * (pred.sum() - real.sum()) / real.sum()) if real.sum() > 0 else None,
           "mean_real": float(real.mean())}
    out["pearson"] = float(ss.pearsonr(pred, real)[0]) if np.std(pred) > 0 and np.std(real) > 0 else None
    out["spearman"] = float(ss.spearmanr(pred, real)[0]) if np.std(pred) > 0 and np.std(real) > 0 else None
    out["pearson_log"] = float(ss.pearsonr(np.log1p(pred), np.log1p(real))[0]) if np.std(pred) > 0 else None
    return out


def validate(cd: pd.DataFrame, natm: pd.DataFrame, cty_counts: pd.DataFrame, abm: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    months = month_table(cd["date"].min(), cd["date"].max())
    av, _ = sat_availability(cd, months)
    nat = natm[["year", "month"] + C.ALL_SATS].copy()
    tr, te = C.CAL_TRAIN_YEARS, C.CAL_TEST_YEARS
    sats = ["S-NPP", "NOAA-20"]
    cal_tr = calibrate(nat, av, months, years=tr, sats=sats)
    av_cols = pd.DataFrame({s: abm[s + "_av"].to_numpy() for s in C.ALL_SATS})
    pred, _, n = combine(nat, av_cols, cal_tr, sats=sats)
    real = (nat["Terra"] + nat["Aqua"]).to_numpy(float)
    ok = (n > 0) & abm["modis_ok"].to_numpy() & ~abm["partial"].to_numpy()
    yr = nat["year"].to_numpy()
    test = ok & (yr >= te[0]) & (yr <= te[1])
    train = ok & (yr >= tr[0]) & (yr <= tr[1])
    series = pd.DataFrame({"year": yr, "month": nat["month"], "real_modis": real, "predicted": pred,
                           "raw_viirs_sum": nat[C.VIIRS_SATS].sum(axis=1), "split": np.where(test, "test", np.where(train, "train", ""))})
    series = series[series["split"] != ""]
    res = {"national": {"train": _metrics(pred[train], real[train]), "test": _metrics(pred[test], real[test]),
                        "fit_years": list(tr), "test_years": list(te), "satellites": sats,
                        "calibration_train": cal_tr}}
    # NOAA-21: shorter split
    cal21 = calibrate(nat, av, months, years=C.N21_TRAIN_YEARS, sats=["NOAA-21"])
    p21, _, n21 = combine(nat, av_cols, cal21, sats=["NOAA-21"])
    t21 = (n21 > 0) & abm["modis_ok"].to_numpy() & ~abm["partial"].to_numpy() & (yr >= C.N21_TEST_YEARS[0]) & (yr <= C.N21_TEST_YEARS[1])
    res["noaa21"] = {"test": _metrics(p21[t21], real[t21]), "fit_years": list(C.N21_TRAIN_YEARS),
                     "test_years": list(C.N21_TEST_YEARS)}
    # counties: national train fit + county adjustment from train years
    cty_counts = cty_counts[["adm1", "year", "month"] + C.ALL_SATS]
    adj_tr = county_adjustments(cty_counts, abm, cal_tr, years=tr)
    parts = []
    for county, g in cty_counts.groupby("adm1"):
        g = g.merge(abm, on=["year", "month"], how="left")
        a = {s: adj_tr[county].get(s, 0.0) for s in sats}
        p, _, nn = combine(g, pd.DataFrame({s: g[s + "_av"].to_numpy() for s in C.ALL_SATS}), cal_tr, a, sats=sats)
        parts.append(pd.DataFrame({"adm1": county, "year": g["year"].to_numpy(), "month": g["month"].to_numpy(),
                                   "p": np.nan_to_num(p), "nn": nn, "real": (g["Terra"] + g["Aqua"]).to_numpy(float),
                                   "vsum": g[sats].sum(axis=1).to_numpy(float),
                                   "ok": (g["modis_ok"] & ~g["partial"]).to_numpy()}))
    allc = pd.concat(parts, ignore_index=True)
    natp = pd.DataFrame({"year": yr, "month": nat["month"].to_numpy(), "natp": np.nan_to_num(pred)})
    allc = allc.merge(natp, on=["year", "month"], how="left")
    tot = allc.groupby(["year", "month"])[["p", "vsum"]].transform("sum")
    share = np.where(tot["p"] > 0, allc["p"] / tot["p"].replace(0, np.nan),
                     np.where(tot["vsum"] > 0, allc["vsum"] / tot["vsum"].replace(0, np.nan), 0.0))
    allc["pred"] = np.nan_to_num(share) * allc["natp"]
    rows = []
    for county, g in allc.groupby("adm1"):
        sel = (g["nn"] > 0) & g["ok"] & (g["year"] >= te[0]) & (g["year"] <= te[1])
        m = _metrics(g.loc[sel, "pred"], g.loc[sel, "real"])
        m["county"] = county
        rows.append(m)
    cm = pd.DataFrame(rows)
    res["counties"] = {"median": {k: (float(cm[k].median()) if k in cm and cm[k].notna().any() else None)
                                  for k in ["mae", "rmse", "bias_pct", "pearson", "spearman"]},
                       "per_county": cm.to_dict(orient="records")}
    # the 2012 jump: raw detections vs harmonized
    res["notes"] = ("Test years are not used for fitting. Terra and Aqua orbits drifted in recent years "
                    "(earlier overpass times), which can lower MODIS counts and make test-year errors larger.")
    return res, series
