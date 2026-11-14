"""Step 1: read every FIRMS CSV and bring them into one table with the same columns."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config as C

OUT_COLS = ["date", "time", "hhmm", "lat", "lon", "satellite", "sensor", "source", "confidence",
            "conf_raw", "frp", "daynight", "type", "bright_1", "bright_2", "scan", "track", "version", "file"]


def _source_of(path: Path, version: str) -> str:
    name = path.name.lower()
    if "nrt" in name or "NRT" in str(version):
        return "nrt"
    if name.startswith("fire_archive"):
        return "archive"
    return "yearly"


def _unify_conf(raw: pd.Series, sensor: str) -> pd.Series:
    if sensor == "MODIS":
        v = pd.to_numeric(raw, errors="coerce")
        return pd.Series(np.select([v < C.MODIS_CONF_LOW, v >= C.MODIS_CONF_HIGH], ["low", "high"], "nominal"),
                         index=raw.index)
    m = raw.astype(str).str.strip().str.lower().str[0].map({"l": "low", "n": "nominal", "h": "high"})
    return m.fillna("nominal")


def read_file(path: Path, sensor: str) -> pd.DataFrame:
    d = pd.read_csv(path, dtype={"acq_time": str, "version": str, "satellite": str, "confidence": str})
    d = d.rename(columns={"brightness": "bright_1", "bright_ti4": "bright_1",
                          "bright_t31": "bright_2", "bright_ti5": "bright_2"})
    out = pd.DataFrame(index=d.index)
    out["date"] = pd.to_datetime(d["acq_date"]).dt.normalize()
    hhmm = d["acq_time"].astype(str).str.strip().str.zfill(4)
    out["hhmm"] = hhmm.astype(int)
    out["time"] = hhmm.str[:2] + ":" + hhmm.str[2:]
    out["lat"] = d["latitude"].astype(float)
    out["lon"] = d["longitude"].astype(float)
    sat = d["satellite"].astype(str).str.strip()
    out["satellite"] = sat.map(C.SATELLITE_CODES)
    unknown = sorted(set(sat[out["satellite"].isna()]))
    if unknown:
        raise ValueError(f"Unknown satellite codes {unknown} in {path.name}: add them to config.SATELLITE_CODES")
    out["sensor"] = sensor
    version = d.get("version", pd.Series("", index=d.index)).astype(str)
    out["version"] = version
    out["source"] = [_source_of(path, v) for v in version]
    out["conf_raw"] = d["confidence"].astype(str)
    out["confidence"] = _unify_conf(d["confidence"], sensor)
    out["frp"] = pd.to_numeric(d.get("frp"), errors="coerce")
    out["daynight"] = d.get("daynight", pd.Series("D", index=d.index)).astype(str).str.upper().str[0]
    out["type"] = pd.to_numeric(d["type"], errors="coerce") if "type" in d else np.nan
    for c in ["bright_1", "bright_2", "scan", "track"]:
        out[c] = pd.to_numeric(d.get(c), errors="coerce")
    out["file"] = f"{path.parent.name}/{path.name}"
    return out[OUT_COLS]


def load_all(verbose: bool = True) -> pd.DataFrame:
    frames = []
    report = []
    for folder, sensor in C.SENSOR_FOLDERS.items():
        for path in sorted((C.DATA / folder).glob("*.csv")):
            df = read_file(path, sensor)
            frames.append(df)
            raw = pd.read_csv(path, usecols=["satellite", "instrument"], dtype=str)
            report.append((path.name, len(df), df["date"].min().date(), df["date"].max().date(),
                           sorted(raw["satellite"].unique()), sorted(raw["instrument"].unique()),
                           df["source"].iloc[0] if len(df) else "-"))
    if verbose:
        print("  files read:")
        for r in report:
            print(f"    {r[0]:<38} {r[1]:>6} rows  {r[2]} .. {r[3]}  sat={r[4]} instr={r[5]} source={r[6]}")
    return pd.concat(frames, ignore_index=True)
