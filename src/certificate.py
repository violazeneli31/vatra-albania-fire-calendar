"""Backup certificate (same design as the one drawn inside the game), PNG (Pillow) + A4 PDF (fpdf2).
Only used if the game frame blocks downloads. The name is never stored."""
from __future__ import annotations

import io
import math
import re
import unicodedata
from datetime import date

from PIL import Image, ImageDraw, ImageFont

import config as C
from src.i18n import ddmmyyyy
from src.report import fonts

W, H = 2480, 1754
NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿĀ-žËëÇç' \-]{1,30}$")
TEXT = {
    "en": ("Fire Detective", "This certifies that",
           ["completed VATRA Kids: Sky Twins and learned how satellites", "help protect Albania's forests."], "Date"),
    "sq": ("Detektiv i Zjarreve", "Vërtetohet që",
           ["përfundoi VATRA Kids: Sky Twins dhe mësoi si satelitët", "ndihmojnë në mbrojtjen e pyjeve të Shqipërisë."], "Data"),
}
CREDIT = "VATRA · Albania's Fire Calendar · made by Viola Zeneli · NASA Space Apps Challenge 2026 project"


def valid(name: str | None) -> bool:
    return bool(name) and bool(NAME_RE.match(name.strip())) and len(name.strip()) <= 30


def filename(name: str, ext: str) -> str:
    s = unicodedata.normalize("NFD", name.strip())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Za-z0-9-]+", "_", s).strip("_")
    return f"VATRA_Certificate_{s}.{ext}"


def _f(kind, size):
    return ImageFont.truetype(fonts()[kind], size)


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rosette(d, cx, cy, r):
    for i in range(12):
        a = i * math.pi / 6
        pts = [(cx, cy)]
        for k in range(9):
            aa = a - .26 + k * .065
            rr = r * math.sin(math.pi * k / 8) ** .5
            pts.append((cx + rr * math.cos(aa), cy + rr * math.sin(aa)))
        d.polygon(pts, fill=_hex(C.GOLD if i % 2 else C.RED))
    d.ellipse([cx - r * .3, cy - r * .3, cx + r * .3, cy + r * .3], fill=_hex(C.GOLD))
    d.ellipse([cx - r * .14, cy - r * .14, cx + r * .14, cy + r * .14], fill=_hex(C.RED))


def _sat(d, cx, cy, s, mo=True):
    for sx in (-1, 1):
        x0 = cx + sx * 38 * s
        d.rectangle([x0 - 18 * s, cy - 12 * s, x0 + 18 * s, cy + 12 * s], fill=_hex(C.GOLD), outline=_hex("#7a5a12"), width=3)
    d.ellipse([cx - 22 * s, cy - 22 * s, cx + 22 * s, cy + 22 * s], fill=_hex("#E9EDF2" if mo else "#FFE7EE"), outline=_hex("#1E1816"), width=4)
    if mo:
        for ex in (-8, 8):
            d.ellipse([cx + (ex - 7) * s, cy - 10 * s, cx + (ex + 7) * s, cy + 4 * s], fill="white", outline=_hex("#1E1816"), width=5)
            d.ellipse([cx + (ex - 2.5) * s, cy - 5.5 * s, cx + (ex + 2.5) * s, cy - .5 * s], fill=_hex("#1E1816"))
    else:
        for ex in (-8, 8):
            pts = []
            for k in range(10):
                rr = 6 * s if k % 2 == 0 else 2.6 * s
                a = -math.pi / 2 + k * math.pi / 5
                pts.append((cx + ex * s + rr * math.cos(a), cy - 3 * s + rr * math.sin(a)))
            d.polygon(pts, fill=_hex("#F4A259"))
    d.arc([cx - 7 * s, cy + 2 * s, cx + 7 * s, cy + 14 * s], 20, 160, fill=_hex("#1E1816"), width=5)


def image(name: str, lang: str = "en", when: date | None = None) -> Image.Image:
    title, cert, body, dlab = TEXT.get(lang, TEXT["en"])
    img = Image.new("RGB", (W, H), _hex("#FAF4E6"))
    d = ImageDraw.Draw(img)
    for i in range(0, W, 14):
        for j in range(0, H, 14):
            d.rectangle([i, j, i + 1, j + 1], fill=_hex("#EADCC0"))
    # diamond border
    for k in range((W - 120) // 60):
        for cy in (80, H - 80):
            cx = 90 + k * 60 + 30
            d.polygon([(cx, cy - 26), (cx + 30, cy), (cx, cy + 26), (cx - 30, cy)], fill=_hex(C.RED))
            d.polygon([(cx, cy - 12), (cx + 14, cy), (cx, cy + 12), (cx - 14, cy)], fill=_hex(C.BLACK))
    for k in range((H - 120) // 60):
        for cx in (80, W - 80):
            cy = 90 + k * 60 + 30
            d.polygon([(cx, cy - 26), (cx + 30, cy), (cx, cy + 26), (cx - 30, cy)], fill=_hex(C.RED))
            d.polygon([(cx, cy - 12), (cx + 14, cy), (cx, cy + 12), (cx - 14, cy)], fill=_hex(C.BLACK))
    d.rectangle([140, 140, W - 140, H - 140], outline=_hex(C.GOLD), width=6)
    for p in [(80, 80), (W - 80, 80), (80, H - 80), (W - 80, H - 80)]:
        _rosette(d, *p, 56)
    _rosette(d, W // 2, 320, 130)
    d.text((W / 2, 560), title, font=_f("title", 150), fill=_hex(C.RED), anchor="ms")
    d.text((W / 2, 690), cert, font=_f("reg", 50), fill=_hex("#6E6560"), anchor="ms")
    fs = 170
    while _f("title", fs).getlength(name) > W - 900 and fs > 70:
        fs -= 8
    d.text((W / 2, 900), name, font=_f("title", fs), fill=_hex(C.BLACK), anchor="ms")
    d.line([(W / 2 - 700, 950), (W / 2 + 700, 950)], fill=_hex(C.GOLD), width=5)
    for i, ln in enumerate(body):
        d.text((W / 2, 1070 + i * 76), ln, font=_f("reg", 54), fill=_hex("#1E1816"), anchor="ms")
    for i in range(5):  # five gold stars
        cx, cy, r = W / 2 - 260 + i * 130, 1300, 48
        pts = [(cx + (r if k % 2 == 0 else r * .42) * math.cos(-math.pi / 2 + k * math.pi / 5),
                cy + (r if k % 2 == 0 else r * .42) * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=_hex(C.GOLD))
    _sat(d, 510, 1320, 4.2, True)
    _sat(d, W - 510, 1320, 4.2, False)
    when = when or date.today()
    d.text((W / 2, 1430), f"{dlab}: {ddmmyyyy(when)}", font=_f("reg", 44), fill=_hex("#6E6560"), anchor="ms")
    for x in range(300, W - 300, 40):
        d.polygon([(x, 1490), (x + 40, 1490), (x + 20, 1520)], fill=_hex(C.GOLD))
    d.text((W / 2, 1585), CREDIT, font=_f("reg", 36), fill=_hex("#6E6560"), anchor="ms")
    return img


def png(name: str, lang: str = "en") -> bytes:
    buf = io.BytesIO()
    image(name.strip(), lang).save(buf, "PNG", optimize=True)
    return buf.getvalue()


def pdf(name: str, lang: str = "en") -> bytes:
    from fpdf import FPDF
    buf = io.BytesIO()
    image(name.strip(), lang).save(buf, "JPEG", quality=92)
    buf.seek(0)
    doc = FPDF(orientation="L", unit="mm", format="A4")
    doc.set_auto_page_break(False)
    doc.add_page()
    doc.image(buf, x=0, y=0, w=297, h=210)
    return bytes(doc.output())
