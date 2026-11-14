"""The frame around every page: CSS (both themes), header band, zigzag, footer, loading screen, cards."""
from __future__ import annotations

import base64
import json
from functools import lru_cache
from html import escape

import streamlit as st

import config as C
from src import motifs
from src.i18n import t
from src.theme import STATUS_COLORS, colors

FONTS_CSS = "https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Inter:wght@400;500;600;700&display=swap"


@lru_cache(maxsize=8)
def img_uri(name: str) -> str:
    p = C.ASSETS / name
    if not p.exists():
        return ""
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def theme() -> str:
    return st.session_state.get("theme", "light")


def lang() -> str:
    return st.session_state.get("lang", "en")


def html(s: str):
    """HTML snippet that keeps inline SVG (st.html sanitizes SVG away)."""
    st.markdown(s, unsafe_allow_html=True)


def html_in(container, s: str):
    container.markdown(s, unsafe_allow_html=True)


# ------------------------------------------------------------------ CSS
def inject_css():
    th = theme()
    c = colors(th)
    dia = motifs.diamonds_uri(c["red"], c["black"] if th == "light" else c["gold"])
    zz = motifs.zigzag_uri(c["gold"])
    photo = img_uri("viola_circle_dark.png" if th == "dark" else "viola_circle_light.png")
    sc = STATUS_COLORS[th]
    badge_css = "".join(f".v-b-{k}{{background:{v[0]};color:{v[1]}}}" for k, v in sc.items())
    css = f"""
<style>
@import url('{FONTS_CSS}');
:root{{--page:{c['page']};--card:{c['card']};--card2:{c['card2']};--text:{c['text']};--muted:{c['muted']};
 --red:{c['red']};--red2:{c['red2']};--gold:{c['gold']};--black:{c['black']};--line:{c['line']};--blue:{c['blue']};
 --input:{c['input']};--diamonds:{dia};--zigzag:{zz};
 --shadow:{'0 1px 3px rgba(60,30,20,.08),0 4px 14px rgba(60,30,20,.06)' if th == 'light' else '0 1px 3px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3)'};}}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{{background:var(--page)!important;color:var(--text);}}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp select,
.stMarkdown, [data-testid="stMarkdownContainer"]{{font-family:Inter,Arial,sans-serif;}}
[data-testid="stIconMaterial"], .material-symbols-rounded{{font-family:"Material Symbols Rounded"!important;}}
.stApp h1,.stApp h2,.v-cinzel{{font-family:Cinzel,Georgia,serif!important;letter-spacing:.02em;color:var(--red);}}
.stApp h1{{font-size:2rem;font-weight:700;padding:.2rem 0 .3rem}}
.stApp h2{{font-size:1.45rem;font-weight:700;padding:.8rem 0 .3rem}}
.stApp h3{{font-family:Inter,Arial,sans-serif!important;font-size:1.05rem;font-weight:700;color:var(--text);padding:.3rem 0 .2rem}}
.stApp p,.stApp li,.stApp label,.stApp span{{color:var(--text);}}
a{{color:var(--red)}}
:focus-visible{{outline:3px solid var(--gold)!important;outline-offset:2px}}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .v-muted{{color:var(--muted)!important}}
/* top navigation (Streamlit header) in red */
header[data-testid="stHeader"]{{background:var(--red)!important;height:3.2rem;box-shadow:none}}
[data-testid="stTopNav"]{{margin-left:.2rem}}
[data-testid="stTopNavLink"]{{border-radius:8px}}
[data-testid="stTopNavLink"] p,[data-testid="stTopNavSection"] p{{color:#fff!important;font-weight:500;font-size:.95rem}}
[data-testid="stTopNavLink"]:hover,[data-testid="stTopNavSection"]:hover{{background:rgba(255,255,255,.14)!important}}
[data-testid="stTopNavLink"][aria-current="page"]{{background:rgba(255,255,255,.22)!important;box-shadow:inset 0 -2px 0 var(--gold)}}
[data-testid="stTopNavSection"] svg,[data-testid="stHeader"] svg{{fill:#fff!important;color:#fff!important}}
#MainMenu,[data-testid="stMainMenu"],[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"],
[data-testid="stDecoration"],[data-testid="stStatusWidget"] .stDeployButton{{display:none!important}}
[data-testid="stSidebarCollapsedControl"] svg,[data-testid="stExpandSidebarButton"] svg,[data-testid="stExpandSidebarButton"] span{{fill:#fff!important;color:#fff!important}}
.block-container, [data-testid="stMainBlockContainer"]{{max-width:1400px;padding:3.2rem 1.25rem 1rem!important;}}
/* header band under the nav */
.st-key-vatra_header{{background:var(--red);margin:-1rem -1.25rem 1.1rem;width:calc(100% + 2.5rem)!important;max-width:none!important;box-sizing:border-box;padding:1.45rem 1.25rem 1.35rem;gap:.2rem;box-shadow:0 0 0 100vmax var(--red);clip-path:inset(0 -100vmax -14px -100vmax);overflow:visible;position:relative}}
.st-key-vatra_header:after{{content:"";position:absolute;left:-100vmax;right:-100vmax;bottom:-10px;height:10px;background:var(--zigzag) repeat-x;background-size:20px 10px}}
.st-key-vatra_header div{{overflow:visible!important}}
[data-testid="stMain"]{{overflow-x:hidden!important}}
.st-key-vatra_header [data-testid="stColumn"]{{padding:3px 0}}
[data-testid="stMain"] .st-key-vatra_header [data-testid="stHorizontalBlock"]{{flex-wrap:nowrap!important;justify-content:flex-end;gap:.5rem!important}}
[data-testid="stMain"] .st-key-vatra_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{flex:0 0 auto!important;width:auto!important;min-width:0!important}}
[data-testid="stMain"] .st-key-vatra_header [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{{flex:1 1 auto!important;min-width:0!important}}
.stApp .st-key-vatra_header button{{line-height:1.25!important;height:2.25rem!important;min-height:2.25rem!important;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center}}
.stApp .st-key-vatra_header button p{{margin:0!important;line-height:1.25!important}}
.st-key-vatra_header [data-testid="stMarkdownContainer"] p{{margin:0}}
.stApp .v-white,.stApp .v-white *{{color:#fff!important}}
.st-key-vatra_header p,.st-key-vatra_header span,.st-key-vatra_header label{{color:#fff!important}}
.stApp .st-key-vatra_header button[data-variant="segmented_control"]{{background:rgba(255,255,255,.15)!important;border-color:rgba(255,255,255,.3)!important;padding:0 .8rem}}
.stApp .st-key-vatra_header button[data-variant="segmented_control"] p{{color:#fff!important;font-weight:700}}
.stApp .st-key-vatra_header button[data-variant="segmented_control"][data-selected="true"]{{background:#fff!important}}
.stApp .st-key-vatra_header button[data-variant="segmented_control"][data-selected="true"] p{{color:var(--red)!important}}
.stApp .st-key-vatra_header .st-key-theme_btn button{{background:rgba(255,255,255,.15)!important;border:1px solid rgba(255,255,255,.3)!important;border-radius:999px!important;width:2.25rem;padding:0}}
.stApp .st-key-vatra_header .st-key-theme_btn button p{{color:#fff!important;font-size:1.1rem}}
.stApp .st-key-kids_link a{{border:0;border-radius:999px;padding:0 .95rem;height:2.25rem;box-sizing:border-box;display:inline-flex;align-items:center;line-height:1.25;background:linear-gradient(90deg,#FFD166,#F4A259,#7BD389)!important}}
.stApp .st-key-kids_link a p{{margin:0!important;line-height:1.25!important}}
.stApp .st-key-kids_link a p,.stApp .st-key-kids_link a span{{color:#3a1500!important;font-weight:800}}

.v-logo{{display:flex;align-items:center;gap:10px;color:#fff;text-decoration:none}}
.v-logo .n{{font-family:Cinzel,Georgia,serif;font-weight:700;font-size:1.65rem;letter-spacing:.08em;color:#fff;line-height:1}}
.v-logo .tg{{font-size:.78rem;opacity:.92;color:#fff;line-height:1.25}}
/* filter bar */
.st-key-filterbar{{background:var(--card);border:1px solid var(--line);border-top:0;border-radius:0 0 14px 14px;margin:-.25rem 0 .8rem;width:100%!important;box-sizing:border-box;padding:.6rem 1rem .35rem;gap:.25rem}}
.st-key-filterbar button p,.st-key-filterbar [data-baseweb="select"] div{{white-space:nowrap}}
.v-summary{{font-size:.82rem;color:var(--muted);padding:.05rem 0 .2rem}}
/* cards: same height in a row, space between rows */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-card"]),
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-dcard"]){{align-items:stretch!important;margin-bottom:.5rem}}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > [class*="st-key-card"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > [class*="st-key-dcard"]){{height:100%}}
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-card"]),
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-dcard"]){{flex:1 1 auto;display:flex;flex-direction:column}}
[data-testid="stLayoutWrapper"] > [class*="st-key-card"],[data-testid="stLayoutWrapper"] > [class*="st-key-dcard"]{{flex:1 1 auto}}
[class*="st-key-dcard_reg_"] > [data-testid="stElementContainer"]:last-child{{margin-top:auto}}
.st-key-cal_btn [data-testid="stPageLink"] a{{display:inline-flex;align-items:center;gap:.35rem;background:var(--red);border-radius:10px;padding:.45rem 1rem;box-shadow:var(--shadow);transition:filter .15s}}
.st-key-cal_btn [data-testid="stPageLink"] a:hover{{filter:brightness(1.12)}}
.st-key-cal_btn [data-testid="stPageLink"] a p,.st-key-cal_btn [data-testid="stPageLink"] a span{{color:#fff!important;font-weight:700}}
.v-facts{{display:flex;gap:12px;margin-top:14px;margin-bottom:1.6rem;flex-wrap:wrap}}
.v-facts>div{{flex:1 1 0;min-width:120px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}}
.v-facts b{{display:block;font-size:1.35rem;color:var(--red);line-height:1.2}} .v-facts span{{font-size:.78rem;color:var(--muted)}}
.v-nowrow{{display:grid;grid-template-columns:1.15fr 2fr;gap:16px;align-items:stretch;margin:6px 0 18px}}
.v-nowrow>.v-card{{margin:0}} .v-tiles{{grid-auto-rows:1fr;height:100%}} .v-tiles .v-card{{height:100%;box-sizing:border-box}}
/* cards */
.v-card,[class*="st-key-card"],[class*="st-key-dcard"]{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:16px;position:relative}}
.v-dia,[class*="st-key-dcard"]{{padding-top:24px!important}}
.v-dia:before,[class*="st-key-dcard"]:before{{content:"";position:absolute;left:14px;right:14px;top:7px;height:8px;background-image:var(--diamonds);background-size:16px 8px;background-repeat:repeat-x;opacity:.9}}
.v-card h3{{margin:.1rem 0 .4rem;padding:0}}
.v-tile .big{{font-size:1.75rem;font-weight:700;line-height:1.15;color:var(--text)}}
.v-tile .lbl{{font-size:.74rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}}
.v-tile .sub{{font-size:.8rem;color:var(--muted)}}
.v-badge{{display:inline-block;border-radius:999px;padding:3px 10px;font-size:.8rem;font-weight:700}}
{badge_css}
.v-headline{{border:2px solid var(--gold);border-radius:12px;padding:12px 14px;background:linear-gradient(0deg,rgba(201,162,74,.10),rgba(201,162,74,.03))}}
.v-headline .k{{font-size:.75rem;color:var(--gold);font-weight:700;letter-spacing:.08em}}
.v-small{{font-size:.84rem}} .v-src{{font-size:.74rem;color:var(--muted)}} .v-src a{{color:var(--muted)}}
.v-kicker{{font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}}
.v-row{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.v-grid{{display:grid;gap:14px;margin-bottom:1rem}} .v-card{{margin-bottom:1rem}}
.v-grid .v-card,.v-nowrow .v-card,.v-nowrow .v-grid,.v-tiles{{margin-bottom:0}} .v-g2{{grid-template-columns:1fr 1fr}} .v-g3{{grid-template-columns:repeat(3,1fr)}} .v-g4{{grid-template-columns:repeat(4,1fr)}}
.v-answer{{border-left:3px solid var(--gold);background:var(--page);border-radius:8px;padding:10px;margin:6px 0}}
.v-band{{height:10px;background-image:var(--diamonds);background-size:16px 8px;background-repeat:repeat-x;background-position:center;opacity:.9}}
.st-key-vfooter{{border-top:1px solid var(--line);background:var(--card);margin:1.2rem 0 -1rem;padding:16px 0 30px;gap:.35rem;text-align:center;box-shadow:0 0 0 100vmax var(--card);clip-path:inset(0 -100vmax -100vmax -100vmax)}}
.st-key-vfooter [data-testid="stElementContainer"]{{width:100%!important}}
.v-footer{{font-size:.82rem;color:var(--muted);text-align:center;line-height:1.5;padding:0 90px;margin-bottom:1rem}}
.st-key-vfooter [data-testid="stPageLink"]{{display:flex;justify-content:center}}
.st-key-vfooter [data-testid="stPageLink"] a{{justify-content:center}}
.v-footer a{{color:var(--red)}}
.v-legend{{display:flex;align-items:center;gap:8px;font-size:.8rem;color:var(--muted);flex-wrap:wrap}}
.v-legend .bar{{height:10px;width:170px;border-radius:5px}}
.v-tl{{position:relative;padding-left:34px}} .v-tl:before{{content:"";position:absolute;left:13px;top:4px;bottom:4px;width:2px;background:var(--gold)}}
.v-tl .ev{{position:relative;margin:0 0 14px}} .v-tl .ev svg{{position:absolute;left:-34px;top:0}}
.v-dl{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);gap:10px}}
table.v-t{{border-collapse:collapse;width:100%;font-size:.86rem}} table.v-t th{{text-align:left;border-bottom:2px solid var(--gold);padding:6px;background:var(--card2)}}
table.v-t td{{border-bottom:1px solid var(--line);padding:6px;color:var(--text)}}
.vatra-spin{{animation:vspin 6s linear infinite}} @keyframes vspin{{to{{transform:rotate(360deg)}}}}

/* widgets in both themes */
[data-baseweb="select"]>div,[data-baseweb="input"]>div,[data-baseweb="base-input"],.stTextInput input,.stNumberInput input,
.stDateInput input,[data-testid="stTextArea"] textarea{{background:var(--input)!important;color:var(--text)!important;-webkit-text-fill-color:var(--text)!important;border-color:var(--line)!important}}
[data-baseweb="select"] span,[data-baseweb="select"] div{{color:var(--text)}}
.stApp [data-baseweb="select"],.stApp [data-baseweb="select"] div,.stApp .stDateInput div,.stApp .stNumberInput div[data-baseweb],.stApp .stTextInput div[data-baseweb]{{background-color:var(--input)!important}}
.stApp .stNumberInput button{{background:var(--card2)!important;color:var(--text)!important}}
[data-baseweb="popover"]>div,[data-baseweb="menu"],[role="listbox"],ul[role="listbox"] li{{background:var(--card)!important;color:var(--text)!important}}
[data-baseweb="calendar"],[data-baseweb="calendar"] div,[data-baseweb="calendar"] button{{background-color:var(--card)!important;color:var(--text)!important}}
[data-testid="stPopoverBody"],[role="dialog"],[data-testid="stDialog"] > div > div{{background:var(--card)!important;color:var(--text)!important;border:1px solid var(--line)}}
[data-testid="stPopoverBody"]{{max-width:min(420px,96vw)}}
[data-testid="stPopoverBody"] [class*="st-key-gq_"] button{{justify-content:flex-start;text-align:left;border-radius:999px!important}}
.stButton button,.stDownloadButton button,[data-testid="stPopover"] button,[data-testid="stPageLink"] a{{border-radius:10px}}
[data-testid="stBaseButton-secondary"],[data-testid="stPopover"] button,button[data-variant="segmented_control"],button[data-variant="pills"]{{background:var(--card)!important;color:var(--text)!important;border-color:var(--line)!important}}
[data-testid="stBaseButton-secondary"] p,button[data-variant="segmented_control"] p,button[data-variant="pills"] p,[data-testid="stPopover"] button p{{color:var(--text)!important}}
[data-testid="stBaseButton-primary"],button[data-variant="segmented_control"][data-selected="true"],button[data-variant="pills"][data-selected="true"]{{background:var(--red)!important;border-color:var(--red)!important}}
[data-testid="stBaseButton-primary"] p,button[data-variant="segmented_control"][data-selected="true"] p,button[data-variant="pills"][data-selected="true"] p{{color:#fff!important}}
[data-testid="stBaseButton-secondary"]:hover,button[data-variant="pills"]:hover,button[data-variant="segmented_control"]:hover{{border-color:var(--gold)!important}}
[data-testid="stBaseButton-tertiary"] p{{color:var(--red)!important;text-decoration:underline}}
button[role="tab"] p,button[role="tab"] span,button[role="tab"] div{{color:var(--muted)!important;font-weight:600}} button[role="tab"][aria-selected="true"] p,button[role="tab"][aria-selected="true"] span,button[role="tab"][aria-selected="true"] div{{color:var(--red)!important}}
[data-baseweb="tab-highlight"]{{background:var(--red)!important}} [data-baseweb="tab-border"]{{background:var(--line)!important}}
[data-testid="stExpander"] details{{border-color:var(--line)!important;background:var(--card)}}
[data-testid="stExpander"] summary p{{color:var(--text)!important}}
[data-testid="stPageLink"] a p{{color:var(--red)!important;font-weight:600}}
[data-testid="stToast"]{{background:var(--black)!important}} [data-testid="stToast"] p{{color:#fff!important}}
[data-testid="stAlert"] p{{color:inherit}}
[data-testid="stSlider"] [role="slider"]{{background:var(--red)!important}}
[data-testid="stCheckbox"] span{{border-color:var(--muted)}}
iframe[title="streamlit_folium.st_folium"]{{border-radius:12px}}
/* Viola button */
.st-key-viola_fab{{position:fixed!important;right:18px;bottom:18px;z-index:9990;width:auto!important;align-items:center}}
.stApp .st-key-viola_fab [data-testid="stPopover"] button{{width:74px!important;height:74px!important;
  border-radius:50%!important;border:3px solid var(--gold)!important;background:url('{photo}') center/cover no-repeat, var(--card)!important;
  box-shadow:0 4px 14px rgba(0,0,0,.28);padding:0!important;min-height:0}}
.st-key-viola_fab [data-testid="stPopover"] button p,.st-key-viola_fab [data-testid="stPopover"] button svg,
.st-key-viola_fab [data-testid="stPopover"] button [data-testid="stIconMaterial"]{{opacity:0!important;}}
.st-key-viola_fab:after{{content:"Viola  AI";white-space:pre;display:block;margin:2px auto 0;text-align:center;background:var(--card);border:1px solid var(--line);
  border-radius:999px;font-size:11.5px;font-weight:700;padding:1px 10px;color:var(--text);font-family:Inter,Arial,sans-serif}}
.v-ai{{display:inline-block;background:#5F5F5F;color:#fff!important;font-size:10px;font-weight:700;border-radius:999px;padding:1px 6px;margin-left:4px;vertical-align:middle;letter-spacing:.03em}}
.v-ring{{border:2px solid var(--gold);border-radius:50%}}
@media (max-width:1000px){{.v-nowrow{{grid-template-columns:1fr}} .v-g4{{grid-template-columns:repeat(2,1fr)}} .v-g3{{grid-template-columns:repeat(2,1fr)}}}}
/* medium windows (tablet, narrow laptop window): content columns wrap to 2 per row instead of squeezing */
@media (min-width:761px) and (max-width:1100px){{
  [data-testid="stMain"] [data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important}}
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{flex:1 1 calc(50% - 1rem)!important;min-width:calc(50% - 1rem)!important}}
  .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{flex:0 0 auto!important;min-width:0!important;width:auto!important}}
  .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{{flex:1 1 100%!important}}
  .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has([data-testid="stButtonGroup"]){{min-width:330px!important}}
  .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has([data-testid="stPopover"]){{min-width:130px!important}}
}}
/* phones: one column per row */
@media (max-width:760px){{
  [data-testid="stMain"] [data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important}}
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{flex:1 1 100%!important;min-width:100%!important}}
  .st-key-fb_row1 [data-testid="stHorizontalBlock"]{{gap:.45rem!important}}
  .st-key-fb_row1 [data-testid="stColumn"]:nth-child(1){{flex:1 1 calc(58% - .45rem)!important;min-width:0!important}}
  .st-key-fb_row1 [data-testid="stColumn"]:nth-child(2){{flex:1 1 calc(42% - .45rem)!important;min-width:0!important}}
  .st-key-filterbar{{padding:.5rem .7rem .3rem!important}}
  .st-key-filterbar [data-testid="stVerticalBlock"]{{gap:.45rem}}
}}
@media (max-width:760px){{
  .stApp .st-key-kids_link a{{padding:.2rem .5rem}} .stApp .st-key-kids_link a p{{font-size:0!important}} .stApp .st-key-kids_link a p:after{{content:'Kids';font-size:.8rem}}
  [data-testid="stMain"] .st-key-vatra_header [data-testid="stHorizontalBlock"]{{gap:.3rem!important}}
  .v-logo svg{{width:28px;height:28px}} .v-logo .n{{font-size:1.1rem!important}} .stApp h1{{font-size:1.55rem!important;word-break:break-word}}
  .stApp .st-key-vatra_header button[data-variant="segmented_control"]{{padding:0 .45rem;min-height:1.8rem}}
  .stApp .st-key-vatra_header .st-key-theme_btn button{{width:1.9rem;min-height:1.8rem}}
  .v-g2,.v-g3{{grid-template-columns:1fr}} .v-g4{{grid-template-columns:1fr 1fr}}
  .stApp h1{{font-size:1.5rem}} .v-logo .tg{{display:none}} .v-logo .n{{font-size:1.35rem}}
  iframe[title="streamlit_folium.st_folium"]{{height:420px!important}}
  [data-testid="stPopoverBody"]{{max-width:96vw;width:96vw}}
  .st-key-filterbar button[data-variant="segmented_control"]{{padding:0 .55rem!important}}
  .st-key-filterbar button[data-variant="segmented_control"] p{{font-size:.82rem!important}}
  .v-facts{{gap:8px}} .v-facts>div{{min-width:0;padding:8px}} .v-facts b{{font-size:1.1rem}} .v-facts span{{font-size:.7rem;line-height:1.25;display:block}}
  .st-key-fb_row2 [data-testid="stHorizontalBlock"]{{flex-wrap:wrap!important;gap:.5rem}}
  [data-testid="stMain"] .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{min-width:0!important;width:auto!important;flex:0 0 auto!important}}
  [data-testid="stMain"] .st-key-fb_row2 [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{{flex:1 1 100%!important}}
  .st-key-fb_row2 [data-testid="stColumn"]:last-child{{display:none}}
  .v-askhint{{text-align:left!important;margin-top:-.6rem}}
  .st-key-viola_fab{{right:10px;bottom:10px}}
  .st-key-viola_fab [data-testid="stPopover"] button{{width:60px!important;height:60px!important}}
}}
</style>"""
    st.html(css)


# ------------------------------------------------------------------ header / footer / loader
def header():
    from src import filters
    with st.container(key="vatra_header"):
        c1, c2, c3, c4 = st.columns([6, 1.35, .55, 1.6], vertical_alignment="center", gap="small")
        with c1:
            html(f'<div class="v-logo">{motifs.rosette_svg(42, C.GOLD, "#FFFFFF")}<div><div class="n">VATRA</div>'
                    f'<div class="tg">Albania\'s Fire Calendar · Kalendari i Zjarreve</div></div></div>')
        with c2:
            st.segmented_control("lang", ["en", "sq"], format_func=lambda x: x.upper(), key="w_lang",
                                 on_change=filters.on_lang, label_visibility="collapsed", required=True)
        with c3:
            st.button("☀" if theme() == "dark" else "☾", key="theme_btn", on_click=filters.toggle_theme,
                      help=t("theme_help"))
        with c4:
            with st.container(key="kids_link"):
                st.page_link(st.session_state["_pages"]["kids"], label=t("for_kids"), icon="🎮")


FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/"


def project_links(video: bool = False) -> list[tuple[str, str, str]]:
    """(label, url, icon) for the project's public places: code, Zenodo DOIs, NASA FIRMS."""
    links = [("GitHub", C.REPO_URL, "💻")]
    if getattr(C, "CODE_DOI_URL", ""):
        links.append((t("software_doi"), C.CODE_DOI_URL, "🧩"))
    if C.DOI_URL:
        links.append((t("dataset_doi"), C.DOI_URL, "📦"))
    if C.REPORT_URL:
        links.append((t("tech_report"), C.REPORT_URL, "📄"))
    if video and C.VIDEO_URL:
        links.append((t("video"), C.VIDEO_URL, "🎬"))
    links.append(("NASA FIRMS", FIRMS_URL, "🛰️"))
    return links


def link_buttons(video: bool = False):
    links = project_links(video)
    for col, (lab, url, ic) in zip(st.columns(len(links), gap="small"), links):
        col.link_button(lab, url, icon=ic, use_container_width=True)


def footer():
    html('<div class="v-band" style="margin-top:22px"></div>')
    with st.container(key="vfooter"):
        html(f'<div class="v-footer"><b>Viola Zeneli</b> · Team Viola Fusion · NASA Space Apps Challenge 2026 · '
             f'{escape(t("footer_data"))}<br>' + " · ".join(
                 f'<a href="{escape(u)}" target="_blank" rel="noopener">{escape(lab)}</a>' for lab, u, _ in project_links()) + '</div>')
        if st.session_state.get("_page_id") != "about":
            st.page_link(st.session_state["_pages"]["about"], label=t("credits"), icon="ℹ️")


def loader():
    """Opening screen, shown once per visit (about 3 seconds). Its styles are inline, so it covers the page from the
    very first frame, before the main stylesheet is applied."""
    if st.session_state.get("_loaded"):
        return
    st.session_state["_loaded"] = True
    th = theme()
    c = colors(th)
    zz = motifs.zigzag_uri(c["gold"])
    dia = motifs.diamonds_uri(c["red"], c["black"] if th == "light" else c["gold"])
    css = (
        f".v-loader{{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;justify-content:space-between;"
        f"background:radial-gradient(ellipse at center,{c['card']} 0%,{c['page']} 70%);animation:vfade .7s ease 3.1s forwards;font-family:Inter,Arial,sans-serif}}"
        f".v-ld-band{{height:44px;background:{c['red']};position:relative}}"
        f".v-ld-band:after{{content:'';position:absolute;left:0;right:0;bottom:-10px;height:10px;background:url(\"{zz}\") repeat-x;background-size:20px 10px}}"
        f".v-ld-band.b{{transform:rotate(180deg)}}"
        f".v-ld-in{{display:flex;flex-direction:column;align-items:center;gap:8px;padding:0 20px;text-align:center}}"
        f".v-ld-logo{{animation:vpop .7s ease both}}"
        f".v-ld-name{{font-family:Cinzel,Georgia,serif;font-size:44px;color:{c['red']};font-weight:700;letter-spacing:.14em;line-height:1;animation:vup .7s ease .15s both}}"
        f".v-ld-tag{{font-size:.95rem;color:{c['muted']};animation:vup .7s ease .3s both}}"
        f".v-ld-dia{{width:220px;height:8px;margin:8px 0 6px;background-image:url(\"{dia}\");background-size:16px 8px;background-repeat:repeat-x;animation:vup .7s ease .4s both}}"
        f".v-ld-sl{{font-size:1.15rem;color:{c['text']};font-weight:600;animation:vup .7s ease .55s both}}"
        f".v-ld-sl.sq{{font-weight:400;font-style:italic;color:{c['muted']};animation-delay:.7s}}"
        f".v-ld-bar{{width:min(320px,80vw);height:6px;border-radius:99px;background:{c['line']};overflow:hidden;margin-top:18px}}"
        f".v-ld-bar span{{display:block;height:100%;width:0;border-radius:99px;background:linear-gradient(90deg,{c['gold']},{c['red']});animation:vbar 2.9s ease-in-out .2s forwards}}"
        f".v-ld-txt{{font-size:.78rem;color:{c['muted']};margin-top:2px}}"
        "@keyframes vfade{to{opacity:0;visibility:hidden}} @keyframes vbar{to{width:100%}}"
        "@keyframes vpop{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:none}}"
        "@keyframes vup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    )
    html(f'<style>{css}</style><div class="v-loader"><div class="v-ld-band"></div><div class="v-ld-in">'
         f'<div class="v-ld-logo">{motifs.rosette_svg(132, C.GOLD, C.RED, spin=True, ring=True)}</div>'
         f'<div class="v-ld-name">VATRA</div>'
         f'<div class="v-ld-tag">Albania\'s Fire Calendar · Kalendari i Zjarreve</div>'
         f'<div class="v-ld-dia"></div>'
         f'<div class="v-ld-sl">Watching Albania\'s forests since 2000</div>'
         f'<div class="v-ld-sl sq">Duke ruajtur pyjet e Shqipërisë që nga viti 2000</div>'
         f'<div class="v-ld-bar"><span></span></div>'
         f'<div class="v-ld-txt">Loading 26 years of NASA satellite data · Duke ngarkuar 26 vite të dhëna satelitore</div>'
         f'</div><div class="v-ld-band b"></div></div>')


# ------------------------------------------------------------------ small HTML helpers
def badge(status: str) -> str:
    if not status:
        return ""
    icon = {"below": "▼", "normal": "●", "above": "▲", "extreme": "◆"}.get(status, "")
    return f'<span class="v-badge v-b-{status}">{icon} {escape(t("status_" + status))}</span>'


def tile(label: str, big: str, sub: str = "") -> str:
    return (f'<div class="v-card v-dia v-tile"><div class="lbl">{escape(label)}</div><div class="big">{big}</div>'
            f'<div class="sub">{sub}</div></div>')


def card(inner: str, dia: bool = False, style: str = "") -> str:
    return f'<div class="v-card{" v-dia" if dia else ""}" style="{style}">{inner}</div>'


def src_link(url: str, label: str | None = None) -> str:
    if not url:
        return ""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.replace("www.", "")
    return f'<div class="v-src">{escape(label or t("source"))}: <a href="{escape(url)}" target="_blank" rel="noopener">{escape(host)}</a></div>'


def legend_ramp(anom: bool = False) -> str:
    if anom:
        return (f'<div class="v-legend"><span>{escape(t("legend_below"))}</span><div class="bar" style="background:'
                f'linear-gradient(90deg,{C.ANOM[0]},{C.ANOM[1]},{C.ANOM[2]})"></div><span>{escape(t("legend_above"))}</span></div>')
    return (f'<div class="v-legend"><span>{escape(t("legend_less"))}</span><div class="bar" style="background:'
            f'linear-gradient(90deg,{",".join(C.RAMP)})"></div><span>{escape(t("legend_more"))} · <b>{escape(t("legend_darker"))}</b></span></div>')


def listen(text: str, key: str):
    """English read-aloud with the browser's built-in voice (tap needed on iPhone). Hidden in Albanian.
    The button toggles: Listen -> Stop while speaking -> Listen when done."""
    if lang() != "en" or not text:
        return
    safe = text.replace("\\", " ").replace("`", "'").replace("</", "< /")
    c = colors(theme())
    st.iframe(f"""
<style>html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
#b{{border:1.5px solid {c['red']};background:transparent;color:{c['red']};border-radius:10px;height:34px;padding:0 12px;margin:5px 2px;
 font:600 13px Inter,Arial,sans-serif;line-height:1;cursor:pointer;display:inline-flex;align-items:center;gap:6px;box-sizing:border-box}}
#b.on{{background:{c['red']};color:#fff}}</style>
<button id="b" title="Computer voice (browser text-to-speech)">🔊 Listen</button>
<script>
const txt = {json.dumps(safe)};
const b = document.getElementById('b');
let s = null; try {{ s = window.parent.speechSynthesis || window.speechSynthesis; }} catch(e) {{ s = window.speechSynthesis; }}
function idle() {{ b.classList.remove('on'); b.innerText = '🔊 Listen'; }}
b.onclick = () => {{
  try {{
    if (b.classList.contains('on')) {{ s.cancel(); idle(); return; }}
    s.cancel();
    const u = new SpeechSynthesisUtterance(txt); u.lang = 'en-US'; u.rate = 1;
    u.onend = idle; u.onerror = idle;
    b.classList.add('on'); b.innerText = '⏹ Stop';
    s.speak(u);
  }} catch(e) {{ b.innerText = 'No voice in this browser'; }}
}};
window.addEventListener('pagehide', () => {{ try {{ s.cancel(); }} catch(e) {{}} }});
</script>""", height=46)


def page_title(icon: str, text: str, sub: str | None = None):
    html(f'<h1 style="margin:.2rem 0 0">{icon} {escape(text)}</h1>' +
            (f'<p class="v-muted" style="margin:.1rem 0 .6rem">{sub}</p>' if sub else ""))
