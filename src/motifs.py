"""SVG motifs: sun rosette, zigzag, diamond chain, cross-stitch, spiral, 12 landmark icons,
the satellites Mo and Vee, and the embroidery calendar. Drawn folk motifs only (no emblems)."""
from __future__ import annotations

import base64
import math
from html import escape
from urllib.parse import quote

import numpy as np

GOLD, RED, BLACK = "#C9A24A", "#A61E26", "#161212"


def rosette(r: float = 50, col: str = GOLD, col2: str = RED) -> str:
    """Sun rosette inspired by Illyrian jewellery (SVG group content, centred on 0,0)."""
    s = [f'<circle r="{r:.1f}" fill="none" stroke="{col}" stroke-width="{r * .08:.1f}"/>']
    for i in range(12):
        a = i * math.pi / 6
        p = lambda rr, aa: f"{rr * math.cos(aa):.1f} {rr * math.sin(aa):.1f}"
        s.append(f'<path d="M0 0 L{p(r * .85, a - .22)} Q{p(r * .98, a)} {p(r * .85, a + .22)} Z" '
                 f'fill="{col if i % 2 else col2}" opacity="{1 if i % 2 else .85}"/>')
    s.append(f'<circle r="{r * .32:.1f}" fill="{col2}" stroke="{col}" stroke-width="{r * .06:.1f}"/>')
    s.append(f'<path d="M0 {-r * .18:.1f} A{r * .18:.1f} {r * .18:.1f} 0 1 1 {-r * .12:.1f} {r * .1:.1f}" fill="none" '
             f'stroke="{col}" stroke-width="{r * .05:.1f}"/>')
    return "".join(s)


def rosette_svg(size: int = 40, col: str = GOLD, col2: str = RED, spin: bool = False, ring: bool = False,
                label: str | None = None) -> str:
    extra = '<circle r="56" fill="none" stroke="#C9A24A" stroke-width="3" stroke-dasharray="6 5"/>' if ring else ""
    txt = (f'<text y="14" text-anchor="middle" font-size="40" font-family="Cinzel, Georgia, serif" fill="#fff" '
           f'font-weight="700">{escape(label)}</text>') if label else ""
    cls = ' class="vatra-spin"' if spin else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="-60 -60 120 120"{cls} '
            f'role="img" aria-label="sun rosette">{extra}{rosette(44 if ring else 52, col, col2)}{txt}</svg>')


def svg_data_uri(svg: str) -> str:
    if 'xmlns=' not in svg:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def diamonds_uri(c1: str = RED, c2: str = BLACK) -> str:
    s = (f"<svg xmlns='http://www.w3.org/2000/svg' width='16' height='8'><path d='M8 0 L16 4 L8 8 L0 4 Z' fill='{c1}'/>"
         f"<path d='M8 2 L12 4 L8 6 L4 4 Z' fill='{c2}'/></svg>")
    return f'url("data:image/svg+xml,{quote(s)}")'


def zigzag_uri(col: str = GOLD) -> str:
    s = f"<svg xmlns='http://www.w3.org/2000/svg' width='20' height='10'><path d='M0 0 L20 0 L10 9 Z' fill='{col}'/></svg>"
    return f'url("data:image/svg+xml,{quote(s)}")'


def zigzag_svg(width: int = 400, col: str = GOLD) -> str:
    p = "".join(f'<path d="M{x} 0 L{x + 10} 0 L{x + 5} 9 Z" fill="{col}"/>' for x in range(0, width, 10))
    return f'<svg viewBox="0 0 {width} 10" preserveAspectRatio="none" width="100%" height="10">{p}</svg>'


def cross_stitch_row(n: int = 8, w: int = 120) -> str:
    step = w / n
    p = "".join(f'<path d="M{6 + i * step:.1f} 6 l10 14 M{16 + i * step:.1f} 6 l-10 14" stroke="{BLACK if i % 2 else RED}" '
                f'stroke-width="3" stroke-linecap="round"/>' for i in range(n))
    return f'<svg viewBox="0 0 {w} 26" width="100%">{p}</svg>'


def spiral(size: int = 14, col: str = GOLD) -> str:
    pts = []
    for k in range(60):
        a = k * 0.32
        r = 0.8 + k * 0.11
        pts.append(f"{7 + r * math.cos(a):.2f},{7 + r * math.sin(a):.2f}")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 14 14"><polyline points="{" ".join(pts)}" fill="none" '
            f'stroke="{col}" stroke-width="1.4" stroke-linecap="round"/></svg>')


# ------------------------------------------------------------------ 12 landmark line icons
_ICONS = {
    "castle": 'M6 40 V18 h6 v-6 h6 v6 h12 v-6 h6 v6 h6 V40 Z M20 40 v-9 a4 4 0 0 1 8 0 v9 M10 24 h4 M34 24 h4',
    "memorial": 'M8 40 h32 M12 40 V20 L24 10 L36 20 V40 M17 40 V24 h14 V40 M24 4 v6',
    "mountains": 'M3 40 L17 16 L24 26 L31 12 L45 40 Z M27 19 l4 -7 4 7',
    "peak": 'M2 40 L24 6 L46 40 Z M17 17 l7 4 7 -4 M10 40 L24 24 L36 40',
    "theatre": 'M4 38 A20 20 0 0 1 44 38 M10 38 A14 14 0 0 1 38 38 M16 38 A8 8 0 0 1 32 38 M4 38 H44',
    "tower": 'M18 42 V14 h12 V42 M16 14 h16 M19 14 l5 -9 5 9 M22 22 a2 2 0 1 0 4 0 a2 2 0 1 0 -4 0 M12 42 h24',
    "walls": 'M3 40 V22 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 v-4 h5 v4 h2 V40 Z M20 40 v-8 a4 4 0 0 1 8 0 v8',
    "columns": 'M6 12 L24 4 L42 12 Z M8 15 H40 M11 15 V38 M19 15 V38 M29 15 V38 M37 15 V38 M6 41 H42',
    "houses": 'M4 40 V26 L14 20 L24 26 V40 M24 40 V20 L34 14 L44 20 V40 M8 30 h4 M16 30 h4 M8 35 h4 M16 35 h4 M28 25 h4 M36 25 h4 M28 31 h4 M36 31 h4',
    "cathedral": 'M8 42 V22 h32 V42 M16 22 a8 8 0 0 1 16 0 M24 14 V6 M21 9 h6 M20 42 v-8 a4 4 0 0 1 8 0 v8',
    "roofs": 'M4 42 V28 L14 18 L24 28 V42 M24 42 V26 L34 16 L44 26 V42 M10 34 h8 M30 32 h8 M14 18 v-4 M34 16 v-4',
    "pine": 'M24 4 L12 20 h6 L8 32 h10 L6 42 h36 L30 32 h10 L30 20 h6 Z M24 42 v4',
}
COUNTY_ICON = {"Shkodër": "castle", "Lezhë": "memorial", "Kukës": "mountains", "Dibër": "peak", "Durrës": "theatre",
               "Tiranë": "tower", "Elbasan": "walls", "Fier": "columns", "Berat": "houses", "Korçë": "cathedral",
               "Gjirokastër": "roofs", "Vlorë": "pine"}


def icon(kind: str, col: str = GOLD, size: int | str = 46, sw: float = 2.2) -> str:
    d = _ICONS.get(kind, _ICONS["castle"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="{size}" height="{size}" role="img" '
            f'aria-label="{kind}"><path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def county_icon(county: str, col: str = GOLD, size=46) -> str:
    return icon(COUNTY_ICON.get(county, "castle"), col, size)


# ------------------------------------------------------------------ the satellites (cartoon, for kids and story)
def satellite(kind: str = "mo", size: int = 150) -> str:
    mo = kind == "mo"
    panels = "".join(
        f'<g transform="translate({s * 38},0)"><rect x="-18" y="-12" width="36" height="24" rx="3" fill="#C9A24A" '
        f'stroke="#7a5a12"/>' + "".join(f'<line x1="{i * 9}" y1="-12" x2="{i * 9}" y2="12" stroke="#7a5a12"/>' for i in (-1, 0, 1))
        + "</g>" for s in (-1, 1))
    eyes = ('<circle cx="-8" cy="-3" r="7" fill="#fff" stroke="#1E1816" stroke-width="2.5"/><circle cx="8" cy="-3" r="7" '
            'fill="#fff" stroke="#1E1816" stroke-width="2.5"/><line x1="-1" y1="-3" x2="1" y2="-3" stroke="#1E1816" '
            'stroke-width="2.5"/><circle cx="-8" cy="-3" r="2.5" fill="#1E1816"/><circle cx="8" cy="-3" r="2.5" fill="#1E1816"/>'
            if mo else
            '<path d="M-8 -9 l2 4 4 .5 -3 3 1 4 -4 -2 -4 2 1 -4 -3 -3 4 -.5z" fill="#F4A259"/>'
            '<path d="M8 -9 l2 4 4 .5 -3 3 1 4 -4 -2 -4 2 1 -4 -3 -3 4 -.5z" fill="#F4A259"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-60 -40 120 80" width="{size}" role="img" '
            f'aria-label="{"Mo (MODIS)" if mo else "Vee (VIIRS)"}"><g>{panels}'
            f'<circle r="22" fill="{"#E9EDF2" if mo else "#FFE7EE"}" stroke="#1E1816" stroke-width="2"/>{eyes}'
            '<path d="M-7 9 Q0 15 7 9" fill="none" stroke="#1E1816" stroke-width="2.2" stroke-linecap="round"/>'
            '<line x1="0" y1="-22" x2="0" y2="-32" stroke="#1E1816" stroke-width="2"/><circle cx="0" cy="-34" r="3" '
            'fill="#EF476F"/></g></svg>')


# ------------------------------------------------------------------ embroidery calendar
STITCH_COLORS = ["", "#D9534F", "#C2333B", "#A61E26", "#6E1218", "#161212"]


def stitch_classes(values: np.ndarray) -> tuple[np.ndarray, list]:
    """5 classes from quantiles of the positive values (0 = empty cloth)."""
    v = np.asarray(values, float)
    pos = v[np.isfinite(v) & (v > 0)]
    if len(pos) == 0:
        return np.zeros_like(v, dtype=int), []
    q = list(np.quantile(pos, [0.2, 0.4, 0.6, 0.8]))
    k = np.zeros(v.shape, dtype=int)
    k[v > 0] = 1
    for i, qq in enumerate(q):
        k[v > qq] = i + 2
    k[~np.isfinite(v)] = -1
    return np.clip(k, -1, 5), q


def embroidery_svg(grid: np.ndarray, years: list[int], month_names: list[str], title: str, subtitle: str,
                   tooltip, terra: np.ndarray | None = None) -> str:
    """grid: years x 12 values (nan = no data). tooltip(y_index, m) -> str."""
    cw, ch, L, T = 52, 22, 74, 80
    W = L + 12 * cw + 40
    H = T + len(years) * ch + 64
    k, q = stitch_classes(grid)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
         f'style="max-width:920px;display:block;margin:auto" role="img" aria-label="{escape(title)}">',
         '<defs><pattern id="cloth" width="6" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="#F6EEDD"/>'
         '<circle cx="3" cy="3" r=".7" fill="#E4D6BA"/></pattern>'
         '<pattern id="dborder" width="20" height="12" patternUnits="userSpaceOnUse"><path d="M10 0 L20 6 L10 12 L0 6 Z" fill="#A61E26"/>'
         '<path d="M10 3 L15 6 L10 9 L5 6 Z" fill="#161212"/></pattern>'
         '<pattern id="dborderv" width="12" height="20" patternUnits="userSpaceOnUse"><path d="M6 0 L12 10 L6 20 L0 10 Z" fill="#A61E26"/>'
         '<path d="M6 5 L9 10 L6 15 L3 10 Z" fill="#161212"/></pattern></defs>',
         f'<rect width="{W}" height="{H}" rx="10" fill="url(#cloth)"/>',
         f'<rect x="8" y="8" width="{W - 16}" height="12" fill="url(#dborder)"/>',
         f'<rect x="8" y="{H - 20}" width="{W - 16}" height="12" fill="url(#dborder)"/>',
         f'<rect x="8" y="22" width="12" height="{H - 44}" fill="url(#dborderv)"/>',
         f'<rect x="{W - 20}" y="22" width="12" height="{H - 44}" fill="url(#dborderv)"/>',
         f'<text x="{W / 2}" y="46" text-anchor="middle" font-size="18" fill="#A61E26" font-weight="700" '
         f'font-family="Cinzel, Georgia, serif">{escape(title)}</text>']
    for i, m in enumerate(month_names):
        s.append(f'<text x="{L + i * cw + cw / 2}" y="{T - 8}" text-anchor="middle" font-size="11" fill="#161212" '
                 f'font-family="Cinzel, Georgia, serif" font-weight="700">{escape(m)}</text>')
        # little "stitched" dashes under the month names
        s.append(f'<path d="M{L + i * cw + 12} {T - 3} h{cw - 24}" stroke="#A61E26" stroke-width="1" stroke-dasharray="2 2"/>')
    for r, y in enumerate(years):
        cy = T + r * ch + ch / 2
        s.append(f'<text x="{L - 10}" y="{cy + 4}" text-anchor="end" font-size="11" fill="#161212" '
                 f'font-family="Cinzel, Georgia, serif">{y}</text>')
        for m in range(12):
            kk = int(k[r, m])
            cx = L + m * cw + cw / 2
            if kk < 0:
                continue
            tip = escape(tooltip(r, m))
            if kk == 0:
                s.append(f'<g><title>{tip}</title><circle cx="{cx}" cy="{cy}" r="1.2" fill="#D9C9A8"/></g>')
                continue
            sz, sw = 3 + kk * 1.6, .8 + kk * .55
            col = STITCH_COLORS[kk]
            s.append(f'<g><title>{tip}</title><rect x="{cx - cw / 2 + 2}" y="{cy - ch / 2 + 1}" width="{cw - 4}" height="{ch - 2}" '
                     f'fill="transparent"/><path d="M{cx - sz:.1f} {cy - sz:.1f} L{cx + sz:.1f} {cy + sz:.1f} M{cx + sz:.1f} '
                     f'{cy - sz:.1f} L{cx - sz:.1f} {cy + sz:.1f}" stroke="{col}" stroke-width="{sw:.2f}" stroke-linecap="round"/></g>')
            if terra is not None and terra[r, m]:
                s.append(f'<text x="{cx + cw / 2 - 8}" y="{cy - 3}" font-size="9" fill="#6E6560">≈</text>')
    s.append(f'<text x="{W / 2}" y="{H - 30}" text-anchor="middle" font-size="11" fill="#6E6560" '
             f'font-family="Inter, Arial, sans-serif">{escape(subtitle)}</text></svg>')
    return "".join(s)


def b64_png(path) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()
