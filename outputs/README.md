# VATRA outputs: data dictionary

Made by `python build.py` from the files in `data/`. Area: Albania. Records: 15 Nov 2000 – 7 Nov 2026.
CSV files are UTF-8 with BOM (Excel shows ë and ç correctly); `.parquet` files hold the same tables for the app.
Dates are `YYYY-MM-DD`; times are UTC.

**Dataset DOI:** https://doi.org/10.5281/zenodo.24231762 · code: https://doi.org/10.5281/zenodo.24231571 · report: https://doi.org/10.5281/zenodo.24232403

**Licence:** derived data CC BY 4.0 (credit "VATRA, Viola Zeneli, 2026" and the sources below). Source data keep their
own terms: NASA FIRMS (open, please cite), EFFIS (© European Union, reuse with acknowledgement), geoBoundaries (CC BY 4.0),
OCHA COD-AB (CC BY-IGO).

FIRMS dataset DOIs: MODIS C6.1 NRT 10.5067/FIRMS/MODIS/MCD14DL.NRT.0061 · MODIS archive MCD14ML 10.5067/FIRMS/MODIS/MCD14ML · VIIRS S-NPP 10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002 · VIIRS NOAA-20 10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002 · VIIRS NOAA-21 10.5067/VIIRS/VJ214IMG_NRT.002.

**For publishing:** `build.py` also copies the shareable files (the CSV tables, `calibration.json`, `validation.json` and this
README) into `outputs/dataset_to_publish/`. Upload that folder's files as the dataset; the other files here are copies the app uses.

## Main unit: the fire cell-day

A **fire cell-day** is one ~1 km grid cell (0.01° × 0.01°) with at least one detection on one day by one satellite.
The **harmonized** value is in **MODIS-equivalent units** (Terra cell-days + Aqua cell-days):
2000–2011 = MODIS; from 2012 = the mean of the VIIRS satellites, each converted with
`log(MODIS + 1) = a + b · log(VIIRS + 1)` (fitted per satellite and season on monthly totals).
Low-confidence detections are left out by default.

## Files

| File | What |
|---|---|
| `fires_clean.parquet/.csv` | Every detection after cleaning |
| `celldays_harmonized.parquet/.csv` | One row per cell per day per satellite, with its harmonized weight |
| `monthly_harmonized.parquet/.csv` | Main table: per area (country, 12 counties, 61 municipalities) and month |
| `seasons.csv` | Fire season per area |
| `anomalies.csv` | Months above/below normal or extreme (no Terra-only months) |
| `trends.csv` | Mann–Kendall + Sen's slope per area, 2003–2025 |
| `events.csv`, `events.parquet` | Fire Events Catalogue |
| `effis_comparison.csv` | Harmonized activity vs EFFIS burnt area, per year and month, country and counties |
| `heritage_nearby.csv` | Fire cell-days within 5 km of each heritage site / park, per year |
| `calibration.json` | Fit parameters per satellite and season, Terra-only ratios, county adjustments |
| `validation.json`, `validation_series.csv`, `validation_chart.png` | Validation numbers, monthly predicted vs real, chart |
| `headline.json`, `stories_en.json`, `stories_sq.json` | Headline finding and data stories (made by templates from the numbers) |
| `boundaries_adm0/1/2.geojson` | Simplified borders for the app map |
| `effis_burnt_areas.geojson` | Simplified EFFIS perimeters for the map layer |
| `areas.json` | List of areas with centre, bounds and size (km²) |
| `summary.json` | Data dates per satellite, totals, cleaning counts, colour-ramp check, package versions |

## Columns

**fires_clean** – `date`, `time` (UTC, HH:MM), `hhmm`, `lat`, `lon`, `satellite` (Terra, Aqua, S-NPP, NOAA-20, NOAA-21),
`sensor` (MODIS/VIIRS), `source` (yearly / archive / nrt), `confidence` (low / nominal / high; MODIS <30 low, 30–79 nominal,
≥80 high), `frp` (fire radiative power, MW), `daynight` (D/N), `adm1` (county), `adm2` (municipality), `cell_id`
(row_col of the 0.01° grid), `year`, `month`.

**celldays_harmonized** – `date`, `cell_id`, `lat`/`lon` (cell centre), `satellite`, `sensor`, `weight` (harmonized
contribution of this cell-day, MODIS-equivalent; 0 for MODIS from 2012 and for a VIIRS satellite in a month it does not fully
cover), `max_frp` (MW), `n_det` (detections in the cell that day), `adm1`, `adm2`, `low_only` (true = only low-confidence
detections), `dn` (D, N or B = both), `event_id` (−1 = not in an event).
The sum of `weight` over any area and month is that area's harmonized value.

**monthly_harmonized** – `area_level` (country / adm1 / adm2), `area_name`, `parent` (county of a municipality), `year`,
`month`, `raw_modis` and `raw_viirs` (raw detections, not harmonized), `raw_modis_cd` and `raw_viirs_cd` (raw cell-days),
`harmonized` (fire cell-days, MODIS-equivalent), `low`/`high` (90 % prediction interval), `median`, `p10`, `p90`, `max`
(normal for this calendar month over 2003–2025), `anomaly` (harmonized − median), `anomaly_pct`, `z_log` (z-score of
log(value+1), extra information only), `status` (below ≤ P10 when the median > 0; above ≥ P90; extreme ≥ the 2003–2025 maximum;
else normal), `terra_only_flag` (estimated from Terra only), `partial_flag` (month not finished in the data),
`viirs_satellites` (VIIRS satellites used), `source_sensor`, `frp_sum` (sum of daily max FRP of cell-days, MW).

**seasons** – `season_start`, `season_peak`, `season_end` (month numbers; months above 25 % of the peak median),
`two_seasons` (yes only with two peaks and a dip below 60 % of the smaller one), `second_peak`, `season_months`,
`peak_median`, `yearly_median`.

**trends** – `sens_slope_per_year` (cell-days per year), `pct_per_year` (slope / median year), `mk_p_value`,
`direction` (up / down when p < 0.05, else none), `intercept` (for year index 0 = 2003).

**events** – cell-days that touch (8 neighbours or same cell) on days at most 1 day apart are one event; kept with ≥ 3
cell-days. `event_id`, `start`, `end`, `days`, `cell_days` (size: not burnt area), `detections`, `harmonized_weight`,
`max_frp`, `lat`/`lon` (centre), `county`, `municipality`, `nearest_site`, `site_km`, `satellites`, `year`, `month`,
`effis_match` (yes if a cell-day lies inside an EFFIS perimeter within ±5 days), `effis_area_ha`.

**effis_comparison** – `area_level`, `area_name`, `period` (year/month), `year`, `month`, `harmonized`, `effis_area_ha`, `effis_fires`.

## Cleaning (counts from this build)

- 109,382 rows read from 61 CSV files; 32 exact duplicates removed; per satellite, archive data are used up to their last date and
  near-real-time data only after it.
- 3,344 detections of type 2 (static land source) or 3 (offshore) removed; 236 near-real-time detections removed in 8
  cells where archive type-2 detections occurred on ≥ 3 days (NRT files have no type column).
- 719 detections outside Albania removed (geoBoundaries ADM0); 105,051 detections kept (6,399 low confidence, hidden by default).

## Validation (from `validation.json`)

Fit on 2012–2019, test on 2020–2025, national monthly cell-days (S-NPP + NOAA-20):

| | MAE | RMSE | Bias | Pearson r | Spearman ρ |
|---|---|---|---|---|---|
| Fit (95 months) | 8.6 | 25.9 | +5.8 % | 0.998 | 0.94 |
| **Test (72 months)** | **9.8** | **21.9** | **−10.6 %** | **0.986** | **0.96** |
| 12 counties, test (median) | 1.4 | 3.5 | −18 % | 0.95 | 0.75 |

NOAA-21 (fit 2023–2024, test 2025): Pearson r 0.99. The negative test bias is consistent with the orbit drift of Terra
and Aqua in recent years (lower MODIS counts). County counts are small, so their percentages vary a lot.

EFFIS (2001–2025, yearly): Pearson r 0.86, Spearman ρ 0.94. 25 % of fire cell-days lie inside an EFFIS perimeter (±5 days);
94 % of the 50 biggest events match an EFFIS fire. EFFIS maps mainly fires of about 30 ha or larger, and part of its
perimeters come from MODIS, so it is not fully independent.

## Limitations

Hotspots are satellite detections, not confirmed fires; clouds and smoke can hide fires. Terra-only months are estimates.
Recent MODIS orbit drift changes overpass times. Latest days in the app come from the FIRMS API with an approximate weight
(median national weight of the same month in the last years). Not an official warning service.
