"""PDF report for any area and dates (fpdf2, A4, EN or SQ) and the kids' activity sheet. Made only on click, cached."""
from __future__ import annotations

import io
import math
from datetime import date
from functools import lru_cache

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from fpdf import FPDF  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

import config as C  # noqa: E402
from src import data, motifs, stats  # noqa: E402
from src.i18n import fdate, month, months, num, pct, status_label, t  # noqa: E402

CREAM, CARD, TEXT, MUTED, LINE = "#FAF7F2", "#FFFBF4", "#1E1816", "#6E6560", "#E4DACB"
CMAP = LinearSegmentedColormap.from_list("vatra", C.RAMP)


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=1)
def fonts() -> dict:
    """Inter + Cinzel from assets/fonts; DejaVu (shipped with matplotlib) as a safe fallback."""
    mpl = font_manager.findfont("DejaVu Sans")
    mplb = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))
    f = {"reg": C.FONTS / "Inter-Regular.ttf", "bold": C.FONTS / "Inter-Bold.ttf", "title": C.FONTS / "Cinzel-Bold.ttf"}
    out = {k: (str(v) if v.exists() else (mplb if k != "reg" else mpl)) for k, v in f.items()}
    for p in [out["reg"], out["bold"], out["title"]]:
        try:
            font_manager.fontManager.addfont(p)
        except Exception:
            pass
    return out


def _mpl_family():
    return "Inter" if (C.FONTS / "Inter-Regular.ttf").exists() else "DejaVu Sans"


class Doc(FPDF):
    def __init__(self, lang="en", orientation="P", fmt="A4", footer_text=""):
        super().__init__(orientation=orientation, unit="mm", format=fmt)
        fo = fonts()
        self.add_font("Inter", "", fo["reg"])
        self.add_font("Inter", "B", fo["bold"])
        self.add_font("Cinzel", "", fo["title"])
        self.lang = lang
        self.footer_text = footer_text
        self.set_auto_page_break(True, margin=18)
        self.set_margins(14, 14, 14)

    def header(self):
        self.set_fill_color(*_rgb(CREAM))
        self.rect(0, 0, self.w, self.h, "F")

    def footer(self):
        y = self.h - 12
        x = 14
        while x < self.w - 14:  # diamond chain
            self.set_fill_color(*_rgb(C.RED))
            self.polygon([(x + 3, y - 1.6), (x + 6, y), (x + 3, y + 1.6), (x, y)], style="F")
            self.set_fill_color(*_rgb(C.BLACK))
            self.polygon([(x + 3, y - .7), (x + 4.3, y), (x + 3, y + .7), (x + 1.7, y)], style="F")
            x += 6.5
        self.set_y(-9)
        self.set_font("Inter", "", 7.5)
        self.set_text_color(*_rgb(MUTED))
        self.cell(0, 4, f"{self.footer_text}   ·   {self.page_no()}/{{nb}}", align="C")

    # helpers
    def band(self, title: str, sub: str, icon_svg: str | None = None):
        self.set_fill_color(*_rgb(C.RED))
        self.rect(0, 0, self.w, 30, "F")
        x = 0
        self.set_fill_color(*_rgb(C.GOLD))
        while x < self.w:
            self.polygon([(x, 30), (x + 5, 30), (x + 2.5, 34)], style="F")
            x += 5
        try:
            self.image(io.BytesIO(motifs.rosette_svg(60, C.GOLD, "#FFFFFF").encode()), x=12, y=5, w=20, h=20)
        except Exception:
            pass
        self.set_xy(35, 6)
        self.set_font("Cinzel", "", 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "VATRA")
        self.set_xy(35, 16)
        self.set_font("Inter", "", 9)
        self.cell(0, 5, "Albania's Fire Calendar · Kalendari i Zjarreve")
        if icon_svg:
            try:
                self.image(io.BytesIO(icon_svg.encode()), x=self.w - 34, y=4, w=22, h=22)
            except Exception:
                pass
        self.set_xy(14, 40)
        self.set_text_color(*_rgb(C.RED))
        self.set_font("Cinzel", "", 18)
        self.multi_cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_rgb(MUTED))
        self.set_font("Inter", "", 10)
        self.multi_cell(0, 5, sub, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def h2(self, text):
        if self.get_y() > self.h - 60:
            self.add_page()
        self.ln(3)
        self.set_font("Cinzel", "", 13)
        self.set_text_color(*_rgb(C.RED))
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_rgb(C.GOLD))
        self.set_line_width(.6)
        self.line(14, self.get_y(), 60, self.get_y())
        self.ln(2)

    def para(self, text, size=9.5, color=TEXT, bold=False):
        self.set_font("Inter", "B" if bold else "", size)
        self.set_text_color(*_rgb(color))
        self.multi_cell(0, size * .5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def section(self, title, fig, w=None):
        """Heading + chart kept together on one page."""
        from PIL import Image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=170, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        iw, ih = Image.open(buf).size
        buf.seek(0)
        w = w or (self.w - 28)
        h = w * ih / iw
        if self.get_y() + h + 16 > self.h - 20:
            self.add_page()
        self.h2(title)
        self.image(buf, x=14 + ((self.w - 28) - w) / 2, w=w, h=h)
        self.ln(2)

    def fig(self, fig, w=None, x=None):
        from PIL import Image
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=170, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        iw, ih = Image.open(buf).size
        buf.seek(0)
        w = w or (self.w - 28)
        h = w * ih / iw
        if self.get_y() + h > self.h - 20:
            self.add_page()
        self.image(buf, x=x if x is not None else 14 + ((self.w - 28) - w) / 2, w=w, h=h)
        self.ln(2)

    def boxes(self, items):
        """Key numbers in cards: list of (label, value, sub)."""
        n = len(items)
        gap = 3
        w = (self.w - 28 - gap * (n - 1)) / n
        y = self.get_y()
        for i, (lab, val, sub) in enumerate(items):
            x = 14 + i * (w + gap)
            self.set_fill_color(*_rgb(CARD))
            self.set_draw_color(*_rgb(LINE))
            self.rect(x, y, w, 22, "DF", round_corners=True, corner_radius=2.5)
            self.set_xy(x + 2.5, y + 2)
            self.set_font("Inter", "", 6.8)
            self.set_text_color(*_rgb(MUTED))
            self.multi_cell(w - 5, 3, lab.upper(), new_x="LMARGIN", new_y="NEXT")
            self.set_xy(x + 2.5, y + 9)
            self.set_font("Inter", "B", 13)
            self.set_text_color(*_rgb(TEXT))
            self.cell(w - 5, 6, val)
            self.set_xy(x + 2.5, y + 16)
            self.set_font("Inter", "", 7)
            self.set_text_color(*_rgb(MUTED))
            self.cell(w - 5, 4, sub)
        self.set_y(y + 25)

    def table(self, head, rows, widths):
        self.set_font("Inter", "B", 8.5)
        self.set_fill_color(*_rgb("#F3ECE0"))
        self.set_text_color(*_rgb(TEXT))
        for h, w in zip(head, widths):
            self.cell(w, 6, h, border="B", fill=True)
        self.ln()
        self.set_font("Inter", "", 8.5)
        for r in rows:
            if self.get_y() > self.h - 25:
                self.add_page()
            for v, w in zip(r, widths):
                self.cell(w, 5.5, str(v), border="B")
            self.ln()
        self.ln(2)


def _style(ax, fig):
    fam = _mpl_family()
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CARD)
    for s in ax.spines.values():
        s.set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=8)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily(fam)
    ax.grid(color="#EDE4D6", lw=.6)
    ax.set_axisbelow(True)


def ch_calendar(tt, y0, y1, lang, embroidery=False):
    plt.rcParams["font.family"] = _mpl_family()
    years = list(range(y0, y1 + 1))
    g = tt.pivot(index="year", columns="month", values="harmonized").reindex(index=years, columns=range(1, 13))
    fig, ax = plt.subplots(figsize=(7.4, max(2.2, .2 * len(years) + .9)))
    _style(ax, fig)
    ax.grid(False)
    if embroidery:
        from src.motifs import stitch_classes, STITCH_COLORS
        k, _ = stitch_classes(g.to_numpy())
        ax.set_facecolor("#F6EEDD")
        for r in range(len(years)):
            for m in range(12):
                kk = k[r, m]
                if kk > 0:
                    s = .12 + kk * .055
                    ax.plot([m - s, m + s], [r - s, r + s], color=STITCH_COLORS[kk], lw=.5 + kk * .45, solid_capstyle="round")
                    ax.plot([m - s, m + s], [r + s, r - s], color=STITCH_COLORS[kk], lw=.5 + kk * .45, solid_capstyle="round")
        ax.set_xlim(-.6, 11.6)
        ax.set_ylim(len(years) - .5, -.5)
    else:
        z = np.log1p(g.to_numpy())
        im = ax.imshow(np.ma.masked_invalid(z), cmap=CMAP, aspect="auto", vmin=0, vmax=np.nanmax(z) if np.isfinite(np.nanmax(z)) else 1)
        cb = fig.colorbar(im, ax=ax, fraction=.025, pad=.01)
        vmax = np.nanmax(g.to_numpy()) if np.isfinite(np.nanmax(g.to_numpy())) else 1
        ticks = [v for v in [0, 1, 5, 20, 100, 500, 2000] if v <= vmax * 1.05]
        cb.set_ticks([math.log1p(v) for v in ticks])
        cb.set_ticklabels([num(v, lang) for v in ticks])
        cb.ax.tick_params(labelsize=7, colors=MUTED)
        cb.outline.set_edgecolor(LINE)
    ax.set_xticks(range(12))
    ax.set_xticklabels(months(lang), fontsize=7.5)
    step = 1 if len(years) <= 14 else 2
    ax.set_yticks(range(0, len(years), step))
    ax.set_yticklabels(years[::step], fontsize=7.5)
    ax.xaxis.tick_top()
    return fig


def ch_profile(tt, year_sel, lang):
    plt.rcParams["font.family"] = _mpl_family()
    n = stats.month_normals(tt, "harmonized")
    fig, ax = plt.subplots(figsize=(7.4, 2.6))
    _style(ax, fig)
    x = np.arange(12)
    ax.fill_between(x, n["p10"], n["p90"], color=C.GOLD, alpha=.28, lw=0, label=t("normal_range", lang))
    ax.plot(x, n["median"], color=C.GOLD, lw=2.4, label=t("median_base", lang))
    if year_sel:
        v = tt[tt["year"] == year_sel].set_index("month").reindex(range(1, 13))["harmonized"]
        ax.plot(x, v, color=C.RED, lw=2, marker="o", ms=3, label=str(year_sel))
    ax.set_xticks(x)
    ax.set_xticklabels(months(lang))
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    return fig


def ch_yearly(tt, tr, lang):
    plt.rcParams["font.family"] = _mpl_family()
    yrs = list(range(2001, C.BASE_YEARS[1] + 1))
    raw = tt.groupby("year")[["raw_modis", "raw_viirs"]].sum().sum(axis=1).reindex(yrs, fill_value=0)
    h = tt.groupby("year")["harmonized"].sum().reindex(yrs, fill_value=0)
    fig, ax = plt.subplots(figsize=(7.4, 2.6))
    _style(ax, fig)
    ax.bar(yrs, h, color=[CMAP(.25 + .65 * math.sqrt(v / max(h.max(), 1))) for v in h], label=t("vatra_harmonized", lang))
    ax.plot(yrs, raw, color=MUTED, lw=1.6, ls="--", label=t("raw_all", lang))
    if tr.get("slope") is not None:
        ty = list(range(C.TREND_YEARS[0], C.TREND_YEARS[1] + 1))
        ax.plot(ty, tr["intercept"] + tr["slope"] * np.arange(len(ty)), color=C.BLUE, lw=2, label=t("sens_slope", lang))
    ax.axvline(2011.5, color=C.GOLD, ls=":", lw=1.4)
    ax.set_yscale("symlog", linthresh=10)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=3)
    return fig


def ch_area_map(key, cd, lang):
    plt.rcParams["font.family"] = _mpl_family()
    fig, ax = plt.subplots(figsize=(3.3, 4.6))
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)
    ax.axis("off")
    for name, lw, col in [("boundaries_adm1.geojson", .5, "#B9AE9C"), ("boundaries_adm0.geojson", 1.2, C.GOLD)]:
        gj = data.geojson(name)
        for f in gj["features"]:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            hl = key[0] == "adm1" and f["properties"].get("name") == key[1]
            for p in polys:
                xs, ys = zip(*p[0])
                ax.plot(xs, ys, color=C.RED if hl else col, lw=2 if hl else lw)
    if key[0] == "adm2":
        for f in data.geojson("boundaries_adm2.geojson")["features"]:
            if f["properties"]["name"] == key[1]:
                g = f["geometry"]
                for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                    xs, ys = zip(*p[0])
                    ax.fill(xs, ys, color=C.RED, alpha=.15)
                    ax.plot(xs, ys, color=C.RED, lw=1.5)
    elif key[0] == "circle":
        th = np.linspace(0, 2 * np.pi, 80)
        ax.plot(key[2] + key[3] / 85 * np.cos(th), key[1] + key[3] / 111 * np.sin(th), color=C.RED, lw=1.5)
    elif key[0] == "polygon":
        xs, ys = zip(*key[1])
        ax.plot(list(xs) + [xs[0]], list(ys) + [ys[0]], color=C.RED, lw=1.5)
    u = cd.drop_duplicates("cell_id")
    if len(u):
        ax.scatter(u["lon"], u["lat"], s=2.5, c="#E08A3C", alpha=.7, lw=0)
    ax.set_aspect(1 / math.cos(math.radians(41.2)))
    return fig


@st.cache_data(show_spinner=False, max_entries=48)
def make_cached(key: tuple, area_name: str, d0: str, d1: str, lang: str, low: bool, dn: str) -> tuple[bytes, str]:
    return make(key, area_name, date.fromisoformat(d0), date.fromisoformat(d1), lang, low, dn)


def make(key, area_name, d0, d1, lang="en", low=False, dn="both") -> tuple[bytes, str]:
    from src.guide import safe
    tt = data.area_monthly(key, low, dn)
    cd = data.area_celldays(key, low, dn)
    cdr = cd[(cd["date"] >= pd.Timestamp(d0)) & (cd["date"] <= pd.Timestamp(d1))]
    rng = data.in_range(tt, d0, d1)
    tr = stats.trend(tt, "harmonized")
    n = stats.month_normals(tt, "harmonized")
    s = stats.seasons(n)
    hl = data.js("headline.json")
    val = data.js("validation.json")
    county = key[1] if key[0] == "adm1" else data.county_of(key[1]) if key[0] == "adm2" else None
    icon = motifs.county_icon(county, C.RED, 60) if county else None

    pdf = Doc(lang, footer_text=f"VATRA · {area_name} · {fdate(d0, lang)} – {fdate(d1, lang)}")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.band(t("r_title", lang, area=area_name), f"{fdate(d0, lang)} – {fdate(d1, lang)} · {t('r_made', lang, d=fdate(date.today(), lang))}", icon)

    # key numbers + map
    yt = tt[(tt["year"] >= max(d0.year, C.BASE_YEARS[0])) & (tt["year"] <= min(d1.year, C.BASE_YEARS[1]))].groupby("year")["harmonized"].sum()
    wy = (str(int(yt.idxmax())), num(yt.max(), lang)) if len(yt) and yt.max() > 0 else ("–", "")
    mm = int(n.sort_values(["median", "mean"], ascending=False)["month"].iloc[0]) if n["mean"].sum() > 0 else None
    pdf.boxes([(t("unit_celldays", lang), num(rng["harmonized"].sum(), lang), f"{d0.year}–{d1.year}"),
               (t("tile_worst_year", lang), wy[0], wy[1]),
               (t("tile_worst_month", lang), month(mm, lang, True) if mm else "–", ""),
               (t("tile_trend", lang), pct(tr["pct_per_year"], lang, 1) if tr.get("pct_per_year") is not None else "–",
                t("significant", lang) if tr.get("direction") in ("up", "down") else t("not_significant", lang))])
    y_top = pdf.get_y()
    pdf.fig(ch_area_map(key, cdr, lang), w=58, x=14)
    y_after_map = pdf.get_y()
    pdf.set_xy(78, y_top + 2)
    season = (t("r_season", lang, start=month(s["start"], lang, True), end=month(s["end"], lang, True), peak=month(s["peak"], lang, True))
              if s.get("peak") else "")
    lines = [hl["short_" + lang], season, t("r_rawcounts", lang, m=num(rng["raw_modis"].sum(), lang), v=num(rng["raw_viirs"].sum(), lang))]
    for ln_ in lines:
        if not ln_:
            continue
        pdf.set_x(78)
        pdf.set_font("Inter", "", 9)
        pdf.set_text_color(*_rgb(TEXT))
        pdf.multi_cell(pdf.w - 92, 4.6, ln_, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
    pdf.set_y(max(y_after_map, pdf.get_y()))

    y0, y1 = max(d0.year, int(data.summary()["first_month"][:4])), d1.year
    pdf.section(t("r_calendar", lang), ch_calendar(tt, y0, y1, lang))
    pdf.para(t("r_calendar_note", lang), 8, MUTED)
    pdf.section(t("r_embroidery", lang), ch_calendar(tt, y0, y1, lang, embroidery=True), w=120)

    worst = int(yt.idxmax()) if len(yt) and yt.max() > 0 else None
    pdf.section(t("r_profile", lang), ch_profile(tt, worst, lang))
    pdf.section(t("r_yearly", lang), ch_yearly(tt, tr, lang))
    if tr.get("slope") is not None:
        k = {"up": "g_trend_up", "down": "g_trend_down"}.get(tr["direction"], "g_trend_none")
        pdf.para(t(k, lang, area=area_name, pct=pct(tr["pct_per_year"], lang, 1) if tr["pct_per_year"] is not None else "–",
                   p=num(tr["p"], lang, 2), years=tr["years"].replace("-", "–")) + " " + t("trend_caveat", lang), 9)

    # unusual months
    pdf.h2(t("r_unusual", lang))
    un = rng[rng["status"].isin(["above", "extreme", "below"]) & ~rng["terra_only_flag"]].copy()
    un = un.sort_values("z_log", key=lambda s: -s.abs()).head(12).sort_values(["year", "month"])
    if len(un):
        pdf.table([t("month", lang), t("unit_celldays", lang), t("normal_short", lang), "%", t("r_status", lang)],
                  [[f"{month(int(r.month), lang, True)} {int(r.year)}", num(r.harmonized, lang, 1), num(r["median"], lang, 1),
                    pct(r.anomaly_pct, lang) if pd.notna(r.anomaly_pct) else "–", status_label(r.status, lang)] for _, r in un.iterrows()],
                  [45, 35, 30, 25, 47])
    else:
        pdf.para(t("r_none", lang), 9, MUTED)

    # ranking
    col = "adm2" if key[0] != "country" else "adm1"
    rk = cdr.groupby(col, observed=True)["weight"].sum().sort_values(ascending=False).head(10)
    rk = rk[rk > 0]
    if len(rk) > 1:
        pdf.h2(t("r_ranking", lang))
        pdf.table(["#", t("municipality", lang) if col == "adm2" else t("pick_county", lang), t("unit_celldays", lang), "%"],
                  [[i + 1, k_, num(v, lang, 1), num(100 * v / rk.sum(), lang, 1) + "%"] for i, (k_, v) in enumerate(rk.items())],
                  [12, 80, 50, 40])

    # biggest events
    ev = data.events()
    ev = ev[(ev["start"] >= pd.Timestamp(d0)) & (ev["start"] <= pd.Timestamp(d1))]
    if key[0] == "adm1":
        ev = ev[ev["county"] == key[1]]
    elif key[0] == "adm2":
        ev = ev[ev["municipality"] == key[1]]
    elif key[0] in ("circle", "polygon"):
        ev = ev[data.mask(ev, key)]
    ev = ev.nlargest(8, "cell_days")
    if len(ev):
        pdf.h2(t("biggest_events", lang))
        pdf.table([t("r_dates", lang), t("municipality", lang), t("days", lang), t("unit_celldays_short", lang), "FRP max", "EFFIS"],
                  [[f"{fdate(e.start, lang)} – {fdate(e.end, lang, False)}", e.municipality, int(e.days), int(e.cell_days),
                    num(e.max_frp, lang) if pd.notna(e.max_frp) else "–", (num(e.effis_area_ha, lang) + " ha") if e.effis_match == "yes" else "–"]
                   for e in ev.itertuples()], [50, 40, 15, 22, 25, 30])

    # EFFIS check
    pdf.h2(t("effis_title", lang))
    e = val["effis"]
    pdf.para(t("effis_line", lang, r=num(e["national"].get("yearly_pearson"), lang, 2), rho=num(e["national"].get("yearly_spearman"), lang, 2),
               share=num(100 * e["share_celldays_inside"], lang), fs=num(100 * e["share_fire_season"], lang),
               ev=num(100 * (e.get("top50_events_matched_share") or 0), lang)), 9)
    pdf.para(t("effis_caveat", lang, ind=num(100 * e["effis_independent_share"], lang)), 8, MUTED)

    # method, credits, disclaimer
    pdf.h2(t("method_title", lang))
    te = val["national"]["test"]
    for i in range(1, 5):
        pdf.para(f"{i}. {t(f'step{i}_t', lang)}: {t(f'step{i}', lang)}", 8.8)
    pdf.para(t("sensor_note", lang, r=num(te["pearson"], lang, 2), rho=num(te["spearman"], lang, 2), bias=pct(te["bias_pct"], lang),
               mae=num(te["mae"], lang, 1)), 8.5, MUTED)
    pdf.h2(t("credits_title", lang))
    import re
    for k in ["credit_firms", "credit_effis", "credit_gb", "credit_ocha", "credit_fonts", "credit_license"]:
        pdf.para(re.sub(r"<[^>]+>", "", t(k, lang)).replace("&amp;", "&"), 7.5, MUTED)
    pdf.para(t("disclaimer", lang), 8.5, C.RED, bold=True)
    pdf.para(f"{C.APP_URL} · {C.REPO_URL}", 8, MUTED)
    out = bytes(pdf.output())
    fname = f"VATRA_report_{safe(area_name)}_{d0:%Y%m%d}_{d1:%Y%m%d}_{lang}.pdf"
    return out, fname


@st.cache_data(show_spinner=False)
def activity_sheet_cached(lang: str) -> bytes:
    return activity_sheet(lang)


def activity_sheet(lang="en") -> bytes:
    pdf = Doc(lang, footer_text=f"VATRA Kids · {C.APP_URL}")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.band(t("r_sheet_title", lang), t("r_sheet_sub", lang))
    pdf.para(t("r_sheet_intro", lang), 10)
    x0, y0 = 22, pdf.get_y() + 4
    cw, ch = (pdf.w - 44) / 12, 14
    pdf.set_font("Inter", "B", 9)
    pdf.set_text_color(*_rgb(TEXT))
    for i, m in enumerate(months(lang)):
        pdf.set_xy(x0 + i * cw, y0)
        pdf.cell(cw, 6, m, align="C")
    pdf.set_draw_color(*_rgb(C.RED))
    pdf.set_line_width(.4)
    for r in range(5):
        pdf.set_xy(8, y0 + 7 + r * ch + 4)
        pdf.set_font("Inter", "", 8)
        pdf.cell(13, 5, "____")
        for i in range(12):
            pdf.rect(x0 + i * cw, y0 + 7 + r * ch, cw, ch)
    pdf.set_y(y0 + 7 + 5 * ch + 6)
    pdf.para(t("r_sheet_key", lang), 9)
    sw = [("", t("r_none_fire", lang)), (C.RAMP[1], t("r_little", lang)), (C.RAMP[3], t("r_some", lang)), (C.RAMP[5], t("r_lots", lang))]
    y = pdf.get_y()
    for i, (c, lab) in enumerate(sw):
        x = 22 + i * 42
        if c:
            pdf.set_fill_color(*_rgb(c))
            pdf.rect(x, y, 8, 6, "DF")
        else:
            pdf.rect(x, y, 8, 6)
        pdf.set_xy(x + 10, y)
        pdf.set_font("Inter", "", 8.5)
        pdf.cell(30, 6, lab)
    pdf.set_y(y + 12)
    pdf.h2(t("r_tips", lang))
    for k in ["safety_1", "safety_2", "r_tip3"]:
        pdf.para("•  " + t(k, lang), 10)
    pdf.ln(4)
    pdf.para(t("r_sheet_data", lang), 8, MUTED)
    return bytes(pdf.output())
