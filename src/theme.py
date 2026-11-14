"""Colours, colour ramps, plotly templates and map tiles for light and dark mode."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

import config as C

THEMES = {
    "light": {"page": "#FAF7F2", "card": "#FFFBF4", "card2": "#F3ECE0", "text": "#1E1816", "muted": "#6E6560",
              "red": "#A61E26", "red2": "#8C1820", "gold": "#C9A24A", "black": "#161212", "line": "#E4DACB",
              "blue": "#2E5A87", "grid": "#EDE4D6", "input": "#FFFFFF"},
    "dark": {"page": "#141214", "card": "#201D20", "card2": "#2A262A", "text": "#F0EAE2", "muted": "#AAA096",
             "red": "#C2333B", "red2": "#A12930", "gold": "#C9A24A", "black": "#000000", "line": "#3A3438",
             "blue": "#6F9CCB", "grid": "#2F2A2E", "input": "#2A262A"},
}

RAMP = C.RAMP
ANOM = C.ANOM
STATUS_COLORS = {
    "light": {"below": ("#DCE6F2", "#1F3F63"), "normal": ("#EFE9DE", "#4A433D"),
              "above": ("#F6D6D3", "#7A1420"), "extreme": ("#161212", "#FFFFFF")},
    "dark": {"below": ("#20334A", "#C9DAEE"), "normal": ("#3A3438", "#EEEEEE"),
             "above": ("#4A1A1E", "#F6C9C5"), "extreme": ("#000000", "#FFFFFF")},
}
TILES = {
    # CARTO tiles now ask for an API key, so the light map uses Esri's free Light Gray Canvas
    "light": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
              "Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors"),
    "dark": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
             "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"),
}


def colors(theme: str) -> dict:
    return THEMES.get(theme, THEMES["light"])


def ramp_scale(ramp=None):
    ramp = ramp or RAMP
    n = len(ramp) - 1
    return [[i / n, c] for i, c in enumerate(ramp)]


def anom_scale():
    return [[0, ANOM[0]], [0.5, ANOM[1]], [1, ANOM[2]]]


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(c1, c2, t):
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ramp_color(t: float, ramp=None) -> str:
    ramp = ramp or RAMP
    t = max(0.0, min(1.0, float(t)))
    p = t * (len(ramp) - 1)
    i = min(int(p), len(ramp) - 2)
    return lerp(ramp[i], ramp[i + 1], p - i)


def _template(theme: str) -> go.layout.Template:
    c = colors(theme)
    return go.layout.Template(layout=dict(
        font=dict(family="Inter, Arial, sans-serif", color=c["text"], size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[c["red"], c["gold"], c["blue"], c["muted"], "#E08A3C", "#7A1420"],
        xaxis=dict(automargin=True, gridcolor=c["grid"], linecolor=c["line"], zerolinecolor=c["line"], tickfont=dict(color=c["muted"])),
        yaxis=dict(automargin=True, gridcolor=c["grid"], linecolor=c["line"], zerolinecolor=c["line"], tickfont=dict(color=c["muted"])),
        hoverlabel=dict(bgcolor=c["black"] if theme == "light" else "#2A262A", font=dict(color="#FFFFFF", family="Inter")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=c["text"]), orientation="h", y=1.08, x=0),
        margin=dict(l=48, r=12, t=34, b=36),
        title=dict(font=dict(family="Cinzel, Georgia, serif", color=c["red"], size=16)),
    ))


pio.templates["vatra_light"] = _template("light")
pio.templates["vatra_dark"] = _template("dark")


def template(theme: str) -> str:
    return "vatra_dark" if theme == "dark" else "vatra_light"


def check_ramp(ramp=None) -> dict:
    """Colour-blind check (build/tests only): CIELAB lightness must fall at every step,
    also under deuteranopia and protanopia simulation. Needs colorspacious."""
    from colorspacious import cspace_convert
    ramp = ramp or RAMP
    rgb = [tuple(v / 255 for v in hex_to_rgb(h)) for h in ramp]
    res = {}
    for name, space in [("normal", "sRGB1"),
                        ("deuteranopia", {"name": "sRGB1+CVD", "cvd_type": "deuteranomaly", "severity": 100}),
                        ("protanopia", {"name": "sRGB1+CVD", "cvd_type": "protanomaly", "severity": 100})]:
        L = []
        for c in rgb:
            sim = cspace_convert(c, space, "sRGB1") if name != "normal" else c
            L.append(float(cspace_convert(sim, "sRGB1", "CIELab")[0]))
        res[name] = {"L": [round(x, 1) for x in L], "monotonic": all(L[i] > L[i + 1] for i in range(len(L) - 1))}
    return res
