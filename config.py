"""VATRA settings: every number and path the code uses lives here.

Change the country by changing COUNTRY, the boundary files and the FIRMS folders.
Nothing else in the code names Albania directly.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------- area
COUNTRY = "Albania"
COUNTRY_SQ = "Shqipëria"
COUNTRY_ISO3 = "ALB"
APP_URL = "https://vatra-albania.streamlit.app"
REPO_URL = "https://github.com/violazeneli31/vatra-albania-fire-calendar"
ORCID_URL = "https://orcid.org/0009-0000-2815-6398"
DOI_URL = "https://doi.org/10.5281/zenodo.24231762"       # dataset (Zenodo)
CODE_DOI_URL = "https://doi.org/10.5281/zenodo.24231571"  # software release v1.0 (Zenodo)
VIDEO_URL = ""        # fill in after the YouTube upload
REPORT_URL = "https://doi.org/10.5281/zenodo.24232403"    # technical report (Zenodo)

# ---------------------------------------------------------------- paths
DATA = ROOT / "data"
OUT = ROOT / "outputs"
ASSETS = ROOT / "assets"
CONTENT = ROOT / "content"
GAME = ROOT / "game"
FONTS = ASSETS / "fonts"

SENSOR_FOLDERS = {          # folder -> sensor family
    "modis": "MODIS",
    "viirs_snpp": "VIIRS",
    "viirs_noaa20": "VIIRS",
    "viirs_noaa21": "VIIRS",
}
BOUNDARY_FILES = {
    "adm0": DATA / "boundaries" / "geoBoundaries-ALB-ADM0.geojson",
    "adm1": DATA / "boundaries" / "geoBoundaries-ALB-ADM1.geojson",
    "adm2": DATA / "boundaries" / "geoBoundaries-ALB-ADM2.geojson",
    "adm1_simple": DATA / "boundaries" / "geoBoundaries-ALB-ADM1_simplified.geojson",
    "adm2_simple": DATA / "boundaries" / "geoBoundaries-ALB-ADM2_simplified.geojson",
    "adm0_simple": DATA / "boundaries" / "geoBoundaries-ALB-ADM0_simplified.geojson",
}
EFFIS_FILE = DATA / "effis" / "effis_burnt_areas_albania_2000-2026.geojson"

# ---------------------------------------------------------------- satellites
# The codes inside FIRMS files differ between yearly files and request files
# ("N" vs "SNPP", "N20", "N21"). build.py prints the codes it finds.
SATELLITE_CODES = {
    "Terra": "Terra", "T": "Terra",
    "Aqua": "Aqua", "A": "Aqua",
    "N": "S-NPP", "SNPP": "S-NPP", "NPP": "S-NPP", "Suomi NPP": "S-NPP",
    "N20": "NOAA-20", "1": "NOAA-20", "J1": "NOAA-20", "NOAA-20": "NOAA-20",
    "N21": "NOAA-21", "J2": "NOAA-21", "NOAA-21": "NOAA-21",
}
MODIS_SATS = ["Terra", "Aqua"]
VIIRS_SATS = ["S-NPP", "NOAA-20", "NOAA-21"]
ALL_SATS = MODIS_SATS + VIIRS_SATS
SAT_SHORT = {"Terra": "T", "Aqua": "A", "S-NPP": "SN", "NOAA-20": "N20", "NOAA-21": "N21"}

# ---------------------------------------------------------------- method
GRID_DEG = 0.01                    # ~1 km cells for fire cell-days
FIRST_FULL_MODIS = (2002, 7)       # Aqua starts mid-2002: before this month only Terra
BASE_YEARS = (2003, 2025)          # "normal" = 2003-2025
TREND_YEARS = (2003, 2025)
FIRE_SEASON_MONTHS = [5, 6, 7, 8, 9, 10]   # May-Oct = fire season for calibration
TERRA_RATIO_YEARS = (2003, 2011)   # years used for the Terra-only scaling
VIIRS_START = {"S-NPP": "2012-01-20", "NOAA-20": "2018-04-01", "NOAA-21": "2023-03-01"}
CAL_TRAIN_YEARS = (2012, 2019)     # validation: fit on these ...
CAL_TEST_YEARS = (2020, 2025)      # ... test on these
N21_TRAIN_YEARS = (2023, 2024)     # NOAA-21 has a shorter history
N21_TEST_YEARS = (2025, 2025)
COUNTY_MIN_MONTHS = 24             # county gets its own adjustment only with >= 24 months ...
COUNTY_MIN_CELLDAYS = 5            # ... with >= 5 cell-days
COUNTY_SHRINK_K = 24               # shrinkage: weight = n / (n + K)
PRED_INTERVAL_Z = 1.645            # 90 % prediction interval
STATIC_MIN_DAYS = 3                # type-2 cells seen on >= 3 days -> static source mask
SEASON_THRESHOLD = 0.25            # months above 25 % of the peak median = fire season
TWO_SEASON_DIP = 0.60              # dip < 60 % of the smaller peak -> two seasons
EVENT_MAX_GAP_DAYS = 1
EVENT_MIN_CELLDAYS = 3
HERITAGE_RADIUS_KM = 5
MODIS_CONF_LOW = 30                # MODIS confidence < 30 = low, 30-79 nominal, >= 80 high
MODIS_CONF_HIGH = 80

# ---------------------------------------------------------------- app
MAP_POINT_CAP = 15000
API_CACHE_SECONDS = 3 * 3600
API_TIMEOUT = 10
FIRMS_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{date}"
FIRMS_API_SOURCES = {"MODIS_NRT": "MODIS", "VIIRS_NOAA20_NRT": "NOAA-20", "VIIRS_NOAA21_NRT": "NOAA-21"}
# bounding box (W, S, E, N) is computed from ADM0 by build.py and saved in summary.json;
# this is only the fallback.
BBOX_FALLBACK = (19.2, 39.6, 21.1, 42.7)

# ---------------------------------------------------------------- colours
RAMP = ["#FBF1DC", "#F1CC7A", "#E08A3C", "#B83A2A", "#7A1420", "#2A0B0E"]
ANOM = ["#2E5A87", "#F7F3EC", "#A61E26"]
RED, RED_DARK = "#A61E26", "#C2333B"
GOLD = "#C9A24A"
BLACK = "#161212"
BLUE = "#2E5A87"

# ---------------------------------------------------------------- boundaries for counties / municipalities
# geoBoundaries ADM2 for Albania holds the 37 older districts, not the 61 municipalities (bashki)
# created in 2015, so VATRA uses the OCHA COD-AB 2019 boundaries for counties (ADM1) and
# municipalities (ADM2). geoBoundaries ADM0 is still used to clip detections to the country.
OCHA_FILES = {
    "adm1": DATA / "boundaries" / "ocha-ALB-ADM1-2019.geojson",
    "adm2": DATA / "boundaries" / "ocha-ALB-ADM2-2019.geojson",
}
# Clean municipality names (the source file has some genitive forms and two labels swapped).
MUNICIPALITY_NAMES = {
    "AL0101": "Berat", "AL0102": "Kuçovë", "AL0103": "Poliçan", "AL0104": "Skrapar", "AL0105": "Ura Vajgurore",
    "AL0201": "Bulqizë", "AL0202": "Dibër", "AL0203": "Klos", "AL0204": "Mat",
    "AL0301": "Durrës", "AL0302": "Krujë", "AL0303": "Shijak",
    "AL0401": "Belsh", "AL0402": "Cërrik", "AL0403": "Elbasan", "AL0404": "Gramsh", "AL0405": "Librazhd",
    "AL0406": "Peqin", "AL0407": "Prrenjas",
    "AL0501": "Divjakë", "AL0502": "Fier", "AL0503": "Lushnjë", "AL0504": "Mallakastër", "AL0505": "Patos",
    "AL0506": "Roskovec",
    "AL0601": "Dropull", "AL0602": "Gjirokastër", "AL0603": "Këlcyrë", "AL0604": "Libohovë", "AL0605": "Memaliaj",
    "AL0606": "Përmet", "AL0607": "Tepelenë",
    "AL0701": "Devoll", "AL0702": "Kolonjë", "AL0703": "Korçë", "AL0704": "Maliq", "AL0705": "Pogradec",
    "AL0706": "Pustec",
    "AL0801": "Has", "AL0802": "Kukës", "AL0803": "Tropojë",
    "AL0901": "Kurbin", "AL0902": "Lezhë", "AL0903": "Mirditë",
    "AL1001": "Fushë-Arrëz", "AL1002": "Malësi e Madhe", "AL1003": "Pukë", "AL1004": "Shkodër", "AL1005": "Vau i Dejës",
    "AL1101": "Kamëz", "AL1102": "Kavajë", "AL1103": "Rrogozhinë", "AL1104": "Vorë", "AL1105": "Tiranë",
    "AL1201": "Delvinë", "AL1202": "Finiq", "AL1203": "Himarë", "AL1204": "Konispol", "AL1205": "Sarandë",
    "AL1206": "Selenicë", "AL1207": "Vlorë",
}
# Counties in a fixed order (north to south) with an id used in URLs and content files.
COUNTIES = [
    ("shkoder", "Shkodër"), ("kukes", "Kukës"), ("lezhe", "Lezhë"), ("diber", "Dibër"),
    ("durres", "Durrës"), ("tirane", "Tiranë"), ("elbasan", "Elbasan"), ("fier", "Fier"),
    ("berat", "Berat"), ("korce", "Korçë"), ("gjirokaster", "Gjirokastër"), ("vlore", "Vlorë"),
]
