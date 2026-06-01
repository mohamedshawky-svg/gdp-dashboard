import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import os
import hmac
import time
import io
import concurrent.futures
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="Support Analysis Dashboard", layout="wide", initial_sidebar_state="expanded")
pd.set_option("styler.render.max_elements", 1200000)

DS_BLUE, DS_NAVY, DS_LIGHT = "#0055A4", "#002147", "#00AEEF"

BLACK_LIST = ['', 'n/a', 'n.a', 'n', 'dropped call', 'call dropped', 'out of our scope', 'other', '0', 'na', ' ', 'N', 'none', 'nan', 'N/A', '0.0', 'NaN', 'None', 'n/m', 'N/M', "what's app"]

SHORT_NAMES = {"Not Done": "Solved", "This Number Belongs To An Inactive Wallet": "Inactive Wallet",
    "Escalated- Tech Support": "Esc-Tech", "Escalated- Field Team": "Esc-FO",
    "Escalated- Management Team": "Esc-MGT", "Escalated- Sys.Set-Up": "Esc-Sys",
    "Escalated- Monitoring Team": "Esc-M&C", "Escalated- Product Team": "Esc-PR",
    "Escalated- CCubed Team": "Esc-CCubed", "Escalated- Data Team": "Esc-Data",
    "Escalated- Fraud Team": "Esc-Fraud", "Escalated- YGG/Like Card": "Esc-YGG",
    "Escalated- PS Team": "Esc-PS", "Escalated- PM Team": "Esc-PM", "Escalated- AM Team": "Esc-AM",
    "Escalated- Merchant": "Esc - Merchant",
    "Connection Problem or Invalid MMI Code": "Connection Problem",
    "Mismatch (Coupon Number & CST MSISDN)": "Mismatch"}

PROJECT_RENAME = {"Red Ramadan": "VF Red Ramadan"}

PASSWORD_PROJECTS = {
    "vodafone123": ["Red", "Red DOM", "Redrebalance (HHT)", "VF Enterprise Packs", "Sherkety", "Red Ramadan", "VF Red Ramadan", "VF Mass Retail", "VF Marketplace", "VF Cash Deals"],
    "nbe123": ["Alahly Points"], "Alex123": ["Alex Bank"], "cib123": ["CIB Bonus"], "wdc123": ["Wadi Degla"],
    "bm123": ["Bank Misr"], "Exxon123": ["Exxon Mobil"], "Mashreq123": ["El Mashreq Bank"],
    "Agricole123": ["Credit Agricole"], "FAB123": ["FAB"], "NBK123": ["NBK"], "WE123": ["WE"],
    "QNB123": ["QNB"], "Jotun123": ["Jotun"], "Mazaya123": ["Mazaya"], "Sky Logistics123": ["Sky Logistics"]}

PROJECT_LOGO_MAP = {"wdc123": "log-WD.png", "Alex123": "logo_Ab.png", "bm123": "logo_BM.png", "cib123": "logo_CIB.png",
    "Agricole123": "logo_CA.png", "Exxon123": "logo_EM.png", "FAB123": "logo_FAB.png", "Jotun123": "logo_Jotun.png",
    "Mashreq123": "logo_MB.png", "Mazaya123": "logo_MAZ.png", "nbe123": "logo_NBE.png", "NBK123": "logo_NBK.png",
    "QNB123": "logo_QNB.png", "Sky Logistics123": "logo_SL.png", "vodafone123": "logo_RED.png", "WE123": "logo_WE.png"}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_TTL_SECONDS = 900
APP_TIMEZONE = ZoneInfo("Africa/Cairo")
DEFAULT_ADMIN_KEY = "admin123"
DEFAULT_USER_KEY = "dsq123"

def get_setting(name, default=None):
    if name in os.environ: return os.environ[name]
    try: return st.secrets.get(name, default)
    except: return default

ADMIN_ACCESS_KEY = get_setting("ADMIN_ACCESS_KEY", DEFAULT_ADMIN_KEY)
USER_ACCESS_KEY = get_setting("USER_ACCESS_KEY", DEFAULT_USER_KEY)
SPREADSHEET_ID = get_setting("GOOGLE_SHEET_ID", "1f3L3zsB9u_kje2QezsL5qWKeg0vfbVDK8u42Q_gaio8")

SHEET_GIDS = {
    "merchant_support": 471895160,
    "client_support": 1950888044,
    "quality_board": 10002,
    "agent_perf": 1306770575,
    "inbound_sla": 1713632809,
    "redemption": 17439532
}

def is_valid_key(inp, exp):
    if not inp or not exp: return False
    return hmac.compare_digest(str(inp), str(exp))

def get_img_64(path):
    try:
        full = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
        if os.path.exists(full):
            with open(full, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None
    return None

logo_big = get_img_64("logo_big.png")
logo_sm = get_img_64("logo_small.png")

ACCESS_CONFIG_FILE = os.path.join(BASE_DIR, "access_config.json")
CUSTOM_LOGO_DIR = os.path.join(BASE_DIR, "custom_logos")

def load_access_config():
    try:
        if os.path.exists(ACCESS_CONFIG_FILE):
            with open(ACCESS_CONFIG_FILE, encoding='utf-8') as f: return json.load(f)
    except: pass
    return {}

def save_access_config(data):
    os.makedirs(os.path.dirname(ACCESS_CONFIG_FILE), exist_ok=True)
    with open(ACCESS_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

os.makedirs(CUSTOM_LOGO_DIR, exist_ok=True)

def get_dynamic_passwords():
    cfg = load_access_config()
    return {k: v['projects'] for k, v in cfg.items() if v.get('projects')}

def get_dynamic_logo_map():
    cfg = load_access_config()
    return {k: v['logo'] for k, v in cfg.items() if v.get('logo')}

def get_dynamic_vf_map():
    cfg = load_access_config()
    return {k: v.get('is_vodafone', False) for k, v in cfg.items()}

def to_n(s):
    return pd.to_numeric(s.astype(str).str.replace('%', '').str.replace(',', ''), errors='coerce').fillna(0)

def clean_st(df, col):
    if col not in df.columns: return df
    t = df.copy()
    t[col] = t[col].astype(str).str.strip()
    mask = ((t[col] != "") & (t[col].str.lower() != "nan") & (t[col].str.lower() != "none") & (~t[col].str.lower().isin([x.lower() for x in BLACK_LIST])))
    return t[mask]

def get_top_safe(df, col):
    t = clean_st(df, col)
    return t[col].mode()[0] if not t.empty else "N/A"

def smart_analysis(df_filtered, df_base, filter_context):
    if df_filtered.empty: return [("No data for this filter", "gray")]
    lines = []
    share = (len(df_filtered) / len(df_base) * 100) if len(df_base) > 0 else 0
    lines.append((f"{share:.1f}% of all tickets", DS_NAVY))
    if 'Month_Num' in df_filtered.columns:
        monthly_num = df_filtered.groupby('Month_Num').size().reset_index(name='count').sort_values('count', ascending=False)
        if not monthly_num.empty:
            peak_label, peak_val = str(monthly_num.iloc[0]['Month_Num']), int(monthly_num.iloc[0]['count'])
            lines.append((f"Peak: {peak_label} ({peak_val:,} tickets)", "#00873d"))
    return lines

def build_card_html(card_id, title, value_str, analysis_lines, delay, border_color):
    analysis_html = ""
    divider_html = ""
    if analysis_lines:
        divider_html = '<div class="sc-divider"></div>'
        for i, (text, color) in enumerate(analysis_lines):
            analysis_html += f'<div class="sc-insight" style="color:{color};animation-delay:{i*0.06:.2f}s;">{text}</div>'
    raw_num = value_str.replace(',', '').replace('%', '').strip()
    has_pct = '%' in value_str
    data_attrs = ""
    try:
        float(raw_num)
        data_attrs = f'data-target="{raw_num}" data-suffix="{"%" if has_pct else ""}"'
    except: pass
    return f'''<div class="sc-card" id="{card_id}" style="animation-delay:{delay:.2f}s; --top-color:{border_color};">
        <div class="sc-header"><span class="sc-label-txt">{title}</span></div>
        <div class="sc-value-txt" {data_attrs}>{value_str}</div>{divider_html}<div class="sc-analysis-wrap">{analysis_html}</div></div>'''

def render_scorecards_row(cards):
    cards_html = "".join(build_card_html(c.get("id", f"sc_{i}"), c["title"], c["value_str"], c.get("analysis_lines") or [], i * 0.09, c.get("border_color", DS_NAVY)) for i, c in enumerate(cards))
    has_analysis = any(c.get("analysis_lines") for c in cards)
    card_height = 200 if has_analysis else 165
    import time as _t; _ts = int(_t.time()*1000)
    full_html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><!-- {_ts} -->
    <link href="https://fonts.googleapis.com/css2?family=Sora:wght@700;900&family=DM+Sans:wght@500;700&display=swap" rel="stylesheet">
    <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    html,body{{background:transparent;font-family:'DM Sans',sans-serif;overflow:visible!important;height:auto!important;}}
    .sc-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;padding:4px 2px 10px;overflow:visible;}}
    .sc-card{{background:linear-gradient(145deg,#ffffff,#f0f5ff);border:1px solid rgba(0,33,71,.08);border-top:4px solid var(--top-color,{DS_NAVY});border-radius:18px;box-shadow:0 4px 16px rgba(0,33,71,.08),0 12px 32px rgba(0,33,71,.10);padding:18px 20px;position:relative;overflow:visible;cursor:default;animation:slideUp .55s cubic-bezier(.18,.89,.32,1.28) forwards;transition:transform .28s ease,box-shadow .28s ease,border-top-color .25s ease,background .2s ease;}}
    .sc-card::before{{content:'';position:absolute;inset:0;border-radius:18px;background:linear-gradient(135deg,rgba(255,255,255,.7),rgba(240,245,255,.3));pointer-events:none;z-index:0;}}
    .sc-card:hover{{transform:translateY(-8px) scale(1.01);box-shadow:0 14px 28px rgba(0,33,71,.13),0 28px 52px rgba(0,33,71,.14),0 0 0 1.5px rgba(0,174,239,.25);border-top-color:{DS_LIGHT}!important;background:linear-gradient(145deg,#ffffff,#e8f2ff);}}
    @keyframes slideUp{{0%{{opacity:0;transform:translateY(20px) scale(.94);}}65%{{opacity:1;transform:translateY(-5px) scale(1.01);}}100%{{opacity:1;transform:translateY(0) scale(1);}}}}
    .sc-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px;position:relative;z-index:1;}}
    .sc-label-txt{{font-size:9px;font-weight:800;color:#aaa;text-transform:uppercase;letter-spacing:1px;}}
    .sc-value-txt{{font-family:'Sora',sans-serif;font-size:36px;font-weight:900;color:{DS_NAVY};line-height:1.05;margin-bottom:5px;animation:popIn .55s cubic-bezier(.18,.89,.32,1.28) forwards;position:relative;z-index:1;}}
    @keyframes popIn{{0%{{opacity:0;transform:scale(.75);}}70%{{opacity:1;transform:scale(1.05);}}100%{{opacity:1;transform:scale(1);}}}}
    .sc-divider{{height:1px;background:linear-gradient(90deg,{DS_LIGHT}66,transparent);margin:9px 0 7px;position:relative;z-index:1;}}
    .sc-insight{{font-size:10px;font-weight:700;margin:3px 0;line-height:1.4;animation:fadeSlide .4s ease both;position:relative;z-index:1;}}
    @keyframes fadeSlide{{from{{opacity:0;transform:translateX(-6px);}}to{{opacity:1;transform:translateX(0);}}}}
    </style></head><body><div class="sc-row">{cards_html}</div>
    <script>function runCountUp(){{document.querySelectorAll('.sc-value-txt[data-target]').forEach(function(el){{if(el.dataset.animated) return;el.dataset.animated='1';var target=parseFloat(el.dataset.target);var suffix=el.dataset.suffix||'';var isFloat=el.dataset.target.indexOf('.')>-1;var steps=50,dur=800,step=target/steps,cur=0;var iv=setInterval(function(){{cur=Math.min(cur+step,target);el.textContent=isFloat?cur.toFixed(1)+suffix:Math.round(cur).toLocaleString()+suffix;if(cur>=target)clearInterval(iv);}},dur/steps);}});}}setTimeout(runCountUp,400);new MutationObserver(function(){{setTimeout(runCountUp,300);}}).observe(document.body,{{childList:true,subtree:true}});</script></body></html>'''
    components.html(full_html, height=card_height + 20, scrolling=False)

st.markdown(f'''<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;900&family=DM+Sans:wght@400;500;600;700&display=swap');
*{{box-sizing:border-box;}}
.main .block-container{{padding-top:.4rem;background:linear-gradient(160deg,#f0f4ff 0%,#f8faff 60%,#eef6ff 100%)!important;min-height:100vh;}}
[data-testid="stHeader"]{{background:rgba(0,0,0,0)!important;visibility:visible!important;}}
[data-testid="stSidebarHeader"],[data-testid="stSidebarCollapsedControl"]{{overflow:hidden!important;}}
[data-testid="stSidebarHeader"] *:not(button),[data-testid="stSidebarCollapsedControl"] *:not(button){{font-size:0!important;color:transparent!important;visibility:hidden!important;line-height:0!important;}}
[data-testid="stSidebarHeader"] button,[data-testid="stSidebarCollapsedControl"] button,button[title*="sidebar" i],button[aria-label*="sidebar" i],button[aria-expanded]{{width:36px!important;height:36px!important;border-radius:50%!important;background:rgba(255,255,255,0.13)!important;border:1.5px solid rgba(255,255,255,0.30)!important;box-shadow:0 4px 16px rgba(0,33,71,.22)!important;color:transparent!important;font-size:0!important;transition:background .2s ease,transform .2s ease,box-shadow .2s ease!important;position:relative!important;overflow:hidden!important;display:flex!important;align-items:center!important;justify-content:center!important;cursor:pointer!important;padding:0!important;}}
[data-testid="stSidebarHeader"] button:hover,[data-testid="stSidebarCollapsedControl"] button:hover,button[title*="sidebar" i]:hover,button[aria-label*="sidebar" i]:hover,button[aria-expanded]:hover{{background:rgba(0,174,239,0.28)!important;transform:translateY(-1px) scale(1.06)!important;box-shadow:0 8px 22px rgba(0,33,71,.30)!important;}}
[data-testid="stSidebarHeader"] button svg,[data-testid="stSidebarCollapsedControl"] button svg,button[title*="sidebar" i] svg,button[aria-label*="sidebar" i] svg,button[aria-expanded] svg{{display:none!important;visibility:hidden!important;}}
[data-testid="stSidebarHeader"] button::after,[data-testid="stSidebarCollapsedControl"] button::after,button[title*="sidebar" i]::after,button[aria-label*="sidebar" i]::after,button[aria-expanded]::after{{content:""!important;display:block!important;width:8px!important;height:8px!important;border-left:2.5px solid #ffffff!important;border-bottom:2.5px solid #ffffff!important;transform:rotate(45deg) translate(2px,-1px)!important;border-radius:1px!important;transition:transform .25s ease!important;visibility:visible!important;opacity:1!important;}}
[data-testid="stSidebarCollapsedControl"] button::after,button[aria-expanded="false"]::after{{transform:rotate(225deg) translate(-1px,2px)!important;}}
/* ── SIDEBAR BACKGROUND ── */
[data-testid="stSidebar"]>div:first-child{{background:linear-gradient(180deg,#00AEEF 0%,#0077cc 25%,#0055A4 50%,#002d6b 75%,#001225 100%)!important;padding:0!important;overflow-y:auto!important;overflow-x:hidden!important;box-shadow:4px 0 30px rgba(0,0,0,.45)!important;}}

/* ── SIDEBAR: ALL TEXT WHITE ── */
[data-testid="stSidebar"] label{{color:#ffffff!important;font-weight:800!important;font-size:12px!important;letter-spacing:.3px!important;font-family:'DM Sans',sans-serif!important;text-shadow:0 1px 4px rgba(0,0,0,.25)!important;}}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] .stMarkdown p{{color:rgba(255,255,255,.65)!important;font-size:9px!important;font-weight:800!important;text-transform:uppercase!important;letter-spacing:1.6px!important;padding-left:2px!important;text-shadow:0 1px 3px rgba(0,0,0,.2)!important;}}
[data-testid="stSidebar"] small,[data-testid="stSidebar"] .caption{{color:rgba(255,255,255,.45)!important;font-size:10px!important;}}
[data-testid="stSidebar"] [data-baseweb="select"] span,[data-testid="stSidebar"] [data-baseweb="input"] span,[data-testid="stSidebar"] .stSelectbox span,[data-testid="stSidebar"] .stMultiSelect span,[data-testid="stSidebar"] .stDateInput span{{color:rgba(255,255,255,.88)!important;font-family:'DM Sans',sans-serif!important;font-weight:600!important;font-size:12px!important;}}

/* ── SIDEBAR: SELECTBOX / MULTISELECT ── */
[data-testid="stSidebar"] div[data-baseweb="select"]>div{{background:rgba(255,255,255,.15)!important;border:1px solid rgba(255,255,255,.30)!important;border-radius:10px!important;transition:all .25s ease!important;min-height:38px!important;box-shadow:0 2px 6px rgba(0,0,0,.12)!important;}}
[data-testid="stSidebar"] div[data-baseweb="select"]>div:hover{{border-color:rgba(255,255,255,.55)!important;background:rgba(255,255,255,.22)!important;box-shadow:0 0 0 2px rgba(255,255,255,.15)!important;}}
[data-testid="stSidebar"] div[data-baseweb="select"]>div *{{color:rgba(255,255,255,.92)!important;}}
[data-testid="stSidebar"] div[data-baseweb="select"] svg{{fill:rgba(255,255,255,.6)!important;}}
[data-testid="stSidebar"] [data-baseweb="menu"]{{background:#001e42!important;border:1px solid rgba(0,174,239,.3)!important;border-radius:10px!important;box-shadow:0 8px 24px rgba(0,0,0,.4)!important;}}
[data-testid="stSidebar"] [data-baseweb="menu"] li{{color:rgba(255,255,255,.88)!important;background:transparent!important;}}
[data-testid="stSidebar"] [data-baseweb="menu"] li:hover{{background:rgba(0,174,239,.18)!important;color:white!important;}}
[data-testid="stSidebar"] [data-baseweb="menu"] li[aria-selected="true"]{{background:rgba(0,174,239,.25)!important;color:white!important;}}

/* ── SIDEBAR: SELECTED TAGS ── */
[data-testid="stSidebar"] span[data-baseweb="tag"]{{background:linear-gradient(135deg,rgba(0,174,239,.40),rgba(0,85,164,.40))!important;border-radius:6px!important;font-size:11px!important;padding:2px 8px!important;border:1px solid rgba(0,174,239,.40)!important;color:white!important;font-weight:700!important;}}
[data-testid="stSidebar"] span[data-baseweb="tag"] span{{color:white!important;}}
[data-testid="stSidebar"] span[data-baseweb="tag"] button,[data-testid="stSidebar"] span[data-baseweb="tag"] svg{{color:rgba(255,255,255,.7)!important;fill:rgba(255,255,255,.7)!important;}}

/* ── SIDEBAR: DATE INPUT ── */
[data-testid="stSidebar"] [data-testid="stDateInput"]{{border-radius:10px!important;min-height:38px!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] div[data-baseweb="input"]{{background:rgba(255,255,255,.09)!important;border:1px solid rgba(255,255,255,.18)!important;border-radius:10px!important;min-height:38px!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] div[data-baseweb="input"]:hover{{border-color:rgba(0,174,239,.6)!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] input{{background:transparent!important;color:white!important;border:none!important;font-size:13px!important;min-height:36px!important;font-weight:600!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] input::placeholder{{color:rgba(255,255,255,.45)!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] input::-webkit-calendar-picker-indicator{{filter:invert(1)!important;cursor:pointer!important;opacity:.7!important;}}
[data-testid="stSidebar"] [data-testid="stDateInput"] svg{{fill:rgba(255,255,255,.6)!important;}}

/* ── SIDEBAR: TEXT INPUT (search boxes) ── */
[data-testid="stSidebar"] div[data-baseweb="input"]{{background:rgba(255,255,255,.09)!important;border:1px solid rgba(255,255,255,.18)!important;border-radius:10px!important;min-height:38px!important;}}
[data-testid="stSidebar"] div[data-baseweb="input"]:hover{{border-color:rgba(0,174,239,.6)!important;}}
[data-testid="stSidebar"] div[data-baseweb="input"] input{{background:transparent!important;color:white!important;border:none!important;font-size:13px!important;font-weight:600!important;}}
[data-testid="stSidebar"] div[data-baseweb="input"] input::placeholder{{color:rgba(255,255,255,.40)!important;}}
[data-testid="stSidebar"] .st-bp,[data-testid="stSidebar"] .st-cx{{background:transparent!important;}}

/* ── SIDEBAR: BUTTONS ── */
[data-testid="stSidebar"] .stButton>button{{background:rgba(255,255,255,.15)!important;color:#ffffff!important;border:1px solid rgba(255,255,255,.35)!important;border-radius:10px!important;font-weight:800!important;font-size:12px!important;transition:all .25s ease!important;width:100%!important;padding:8px 12px!important;letter-spacing:.4px!important;text-shadow:0 1px 4px rgba(0,0,0,.3)!important;box-shadow:0 2px 8px rgba(0,0,0,.15)!important;}}
[data-testid="stSidebar"] .stButton>button:hover{{background:rgba(255,255,255,.25)!important;border-color:rgba(255,255,255,.60)!important;transform:translateY(-2px)!important;box-shadow:0 6px 18px rgba(0,0,0,.30)!important;color:white!important;}}
[data-testid="stSidebar"] .stButton:last-of-type>button{{background:rgba(180,30,30,.30)!important;border-color:rgba(255,120,120,.50)!important;color:#ffcccc!important;font-weight:800!important;text-shadow:0 1px 4px rgba(0,0,0,.3)!important;}}
[data-testid="stSidebar"] .stButton:last-of-type>button:hover{{background:rgba(200,30,30,.45)!important;border-color:rgba(255,120,120,.70)!important;color:#ffdddd!important;}}

/* ── SIDEBAR: DIVIDER ── */
[data-testid="stSidebar"] hr{{border:none!important;border-top:1px solid rgba(255,255,255,.08)!important;margin:10px 16px!important;}}

/* ── SIDEBAR: RADIO & CHECKBOX ── */
[data-testid="stSidebar"] [data-testid="stRadio"] label,[data-testid="stSidebar"] [data-testid="stCheckbox"] label{{color:rgba(255,255,255,.88)!important;}}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] div{{border-color:rgba(255,255,255,.3)!important;}}

/* ── SIDEBAR: SELECTBOX DISABLED STATE ── */
[data-testid="stSidebar"] div[data-baseweb="select"][aria-disabled="true"]>div{{opacity:.45!important;cursor:not-allowed!important;}}

/* ── TABS ── */
[data-testid="stTabs"] [role="tablist"]{{background:rgba(255,255,255,.7)!important;backdrop-filter:blur(12px)!important;border-radius:16px!important;padding:5px 6px!important;box-shadow:0 2px 12px rgba(0,33,71,.10)!important;border:1px solid rgba(0,33,71,.08)!important;margin-bottom:16px!important;gap:4px!important;}}
[data-testid="stTabs"] button[role="tab"]{{border-radius:11px!important;font-weight:700!important;font-size:12px!important;color:{DS_NAVY}!important;transition:all .22s ease!important;padding:7px 14px!important;}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{{background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE})!important;color:white!important;box-shadow:0 4px 14px rgba(0,33,71,.28)!important;}}
[data-testid="stTabs"] button[role="tab"]:hover:not([aria-selected="true"]){{background:rgba(0,33,71,.08)!important;transform:translateY(-1px)!important;}}

/* ── LIVE BADGE ── */
.live-badge{{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(135deg,rgba(0,200,80,.12),rgba(0,200,80,.06));border:1px solid rgba(0,200,80,.40);border-radius:20px;padding:3px 12px;font-size:11px;font-weight:700;color:#006b30;box-shadow:0 2px 8px rgba(0,200,80,.15);}}
.live-dot{{width:8px;height:8px;background:radial-gradient(circle,#00ff66,#00cc55);border-radius:50%;animation:pulse 1.5s infinite;flex-shrink:0;}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 rgba(0,204,85,.6);}}50%{{box-shadow:0 0 0 6px rgba(0,204,85,0);}}}}

/* ── FILTER BADGES ── */
.filter-badge{{background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE});color:white;border-radius:8px;padding:3px 12px;font-size:11px;font-weight:700;display:inline-block;margin:2px 3px;box-shadow:0 2px 8px rgba(0,33,71,.20);}}

/* ── DASHBOARD HEADER ── */
.dashboard-header{{text-align:center;margin-bottom:10px;padding:12px 0 6px;}}
.dashboard-header h2{{color:{DS_NAVY};font-weight:900;font-size:24px;margin-top:4px;font-family:'Sora',sans-serif;letter-spacing:-.3px;background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}

/* ── DATAFRAME ── */
[data-testid="stTable"] td,[data-testid="stDataFrame"] td,[data-testid="stDataFrame"] div,[data-testid="stTable"] th{{color:{DS_NAVY}!important;font-weight:700!important;font-size:13px!important;}}
[data-testid="stDataFrame"]>div:first-child{{display:none!important}}
[data-testid="stDataFrame"]{{border-radius:14px!important;overflow:hidden!important;box-shadow:0 4px 20px rgba(0,33,71,.08)!important;border:1px solid rgba(0,33,71,.07)!important;}}

/* ── PAGE TITLE ── */
.page-title-header{{color:{DS_NAVY};font-weight:900;font-size:24px;text-align:center;margin-bottom:18px;padding:14px;font-family:'Sora',sans-serif;background:linear-gradient(135deg,rgba(0,33,71,.04),rgba(0,85,164,.06));border-radius:16px;border:1px solid rgba(0,33,71,.07);letter-spacing:-.2px;}}

/* ── WA / OVERALL CARDS ── */
.wa-card,.overall-card{{background:linear-gradient(145deg,#ffffff,#f5f8ff)!important;border-top:5px solid {DS_NAVY}!important;border-radius:16px!important;box-shadow:0 6px 24px rgba(0,33,71,.10),0 2px 8px rgba(0,33,71,.06)!important;padding:20px!important;transition:all .3s cubic-bezier(.18,.89,.32,1.28)!important;border:1px solid rgba(0,33,71,.06)!important;}}
.wa-card:hover,.overall-card:hover{{transform:translateY(-8px) scale(1.01)!important;box-shadow:0 20px 40px rgba(0,33,71,.16),0 4px 12px rgba(0,33,71,.08)!important;border-top:5px solid {DS_LIGHT}!important;}}
.wa-card h5{{color:{DS_NAVY}!important;font-weight:900;font-size:15px;margin-bottom:6px;font-family:'Sora',sans-serif;}}
.wa-card .perc{{color:{DS_BLUE}!important;font-weight:900;font-size:28px;font-family:'Sora',sans-serif;}}

/* ── SLIDESHOW ── */
.slideshow-banner{{background:linear-gradient(135deg,{DS_NAVY} 0%,{DS_BLUE} 50%,{DS_LIGHT} 100%);color:white;text-align:center;padding:9px 16px;border-radius:12px;font-size:12px;font-weight:700;margin-bottom:10px;box-shadow:0 4px 16px rgba(0,33,71,.25);letter-spacing:.3px;}}
.slide-tab{{display:inline-block;padding:3px 14px;border-radius:20px;font-size:11px;font-weight:800;background:rgba(255,255,255,.10);color:rgba(255,255,255,.55);transition:all .3s;border:1px solid transparent;}}
.slide-tab-active{{background:rgba(0,174,239,.30);color:#fff;box-shadow:0 0 14px rgba(0,174,239,.45);border-color:rgba(0,174,239,.4);}}
button[kind="primary"]{{background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE})!important;border-color:{DS_NAVY}!important;color:#fff!important;box-shadow:0 4px 14px rgba(0,33,71,.25)!important;}}
button[kind="secondary"]{{color:{DS_NAVY}!important;border-color:rgba(0,33,71,.25)!important;background:rgba(0,33,71,.04)!important;}}

/* ── SLIDE SCORECARDS ── */
.slide-scorecard-wrap{{display:flex;justify-content:center;gap:14px;margin-bottom:10px;flex-wrap:wrap;}}
.slide-scorecard{{background:linear-gradient(145deg,#ffffff,#f0f5ff);border-top:3px solid {DS_NAVY};border-radius:12px;box-shadow:0 4px 14px rgba(0,33,71,.10);padding:8px 18px;text-align:center;min-width:110px;border:1px solid rgba(0,33,71,.06);}}
.slide-scorecard .sc-label{{color:#888;font-size:9px;font-weight:700;text-transform:uppercase;margin-bottom:3px;letter-spacing:.8px;}}
.slide-scorecard .sc-value{{color:{DS_NAVY};font-size:22px;font-weight:900;margin:0;font-family:'Sora',sans-serif;}}

/* ── MOM GRID ── */
.mom-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;}}
@media(max-width:900px){{.mom-grid{{grid-template-columns:repeat(2,1fr);}}}}

/* ── DS TAB BUTTONS ── */
.ds-tab-btn{{background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE});color:white!important;border:none;border-radius:12px;padding:10px 26px;font-weight:700;font-size:13px;cursor:pointer;transition:all .22s;margin:0 4px;box-shadow:0 4px 14px rgba(0,33,71,.20);}}
.ds-tab-btn:hover{{background:linear-gradient(135deg,{DS_BLUE},{DS_LIGHT});transform:translateY(-2px);box-shadow:0 8px 22px rgba(0,33,71,.28);}}
.ds-tab-btn.active{{background:linear-gradient(135deg,{DS_LIGHT},{DS_BLUE});box-shadow:0 0 0 2.5px {DS_NAVY},0 6px 18px rgba(0,174,239,.30);}}

/* ── M-CARDS (Redemption) ── */
.mcard{{background:linear-gradient(145deg,#ffffff,#f2f6ff);border-radius:16px;padding:18px 16px;border:1px solid rgba(0,33,71,.07);box-shadow:0 4px 16px rgba(0,33,71,.08);transition:all .28s cubic-bezier(.18,.89,.32,1.28);border-top:4px solid var(--c,{DS_NAVY});}}
.mcard:hover{{transform:translateY(-6px) scale(1.01);box-shadow:0 12px 32px rgba(0,33,71,.14);}}
.mcard .ml{{font-size:9px;font-weight:800;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}}
.mcard .mv{{font-size:30px;font-weight:900;color:{DS_NAVY};font-family:'Sora',sans-serif;}}

/* ── TABLES ── */
.modern-table{{border-collapse:collapse;width:100%;font-size:12px;border-radius:12px;overflow:hidden;}}
.modern-table th{{background:linear-gradient(135deg,{DS_NAVY},{DS_BLUE});color:white;padding:10px 12px;text-align:left;font-weight:400;letter-spacing:.3px;}}
.modern-table td{{padding:7px 12px;border-bottom:1px solid rgba(0,33,71,.06);font-weight:600;color:{DS_NAVY};transition:background .15s;}}
.modern-table tr:hover td{{background:rgba(0,85,164,.04);}}
</style>''', unsafe_allow_html=True)

if 'auth_role' not in st.session_state: st.session_state.auth_role = None
if 'active_ov_tab' not in st.session_state: st.session_state.active_ov_tab = "Merchant Support"

if not st.session_state.auth_role:
    st.markdown(f'''<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;700;900&family=DM+Sans:wght@400;500;700&display=swap');
    .main .block-container{{max-width:100%!important;padding:0!important;}}
    [data-testid="stHeader"]{{display:none!important;}}
    [data-testid="stAppViewContainer"]{{
        background:#000e20!important;
        position:relative;overflow:hidden!important;
        min-height:100vh!important;
    }}
    /* ── MESH BACKGROUND ── */
    .lp-bg{{
        position:fixed;top:0;left:0;width:100%;height:100%;
        background:
            radial-gradient(ellipse 80% 60% at 20% 10%, rgba(0,174,239,.18) 0%, transparent 60%),
            radial-gradient(ellipse 60% 80% at 80% 80%, rgba(0,55,130,.25) 0%, transparent 55%),
            radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,33,71,.40) 0%, transparent 70%),
            linear-gradient(160deg,#000e20 0%,#001535 40%,#001f50 70%,#000e20 100%);
        z-index:0;pointer-events:none;
    }}
    /* ── GRID LINES ── */
    .lp-grid{{
        position:fixed;top:0;left:0;width:100%;height:100%;
        background-image:
            linear-gradient(rgba(0,174,239,.04) 1px,transparent 1px),
            linear-gradient(90deg,rgba(0,174,239,.04) 1px,transparent 1px);
        background-size:60px 60px;
        z-index:0;pointer-events:none;
        mask-image:radial-gradient(ellipse 70% 70% at 50% 50%,black 30%,transparent 100%);
    }}
    /* ── ANIMATED ORBS ── */
    .lp-orb{{position:fixed;border-radius:50%;filter:blur(80px);pointer-events:none;z-index:0;animation:orbFloat ease-in-out infinite alternate;}}
    .lp-orb1{{width:500px;height:500px;background:radial-gradient(circle,rgba(0,174,239,.12),transparent 70%);top:-10%;left:-5%;animation-duration:12s;}}
    .lp-orb2{{width:400px;height:400px;background:radial-gradient(circle,rgba(0,85,164,.15),transparent 70%);bottom:-10%;right:-5%;animation-duration:16s;animation-delay:-4s;}}
    .lp-orb3{{width:300px;height:300px;background:radial-gradient(circle,rgba(0,140,200,.08),transparent 70%);top:40%;left:60%;animation-duration:10s;animation-delay:-8s;}}
    @keyframes orbFloat{{0%{{transform:translate(0,0) scale(1);}}100%{{transform:translate(30px,-20px) scale(1.1);}}}}
    /* ── PARTICLES ── */
    .lp-particles{{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;}}
    .lp-p{{position:absolute;border-radius:50%;animation:pFloat linear infinite;}}
    @keyframes pFloat{{0%{{transform:translateY(105vh) rotate(0deg);opacity:0;}}5%{{opacity:1;}}90%{{opacity:.4;}}100%{{transform:translateY(-5vh) rotate(360deg);opacity:0;}}}}
    /* ── MAIN LAYOUT ── */
    .lp-wrap{{
        position:relative;z-index:2;
        display:flex;flex-direction:column;align-items:center;
        justify-content:center;min-height:auto;padding-top:8vh;padding-bottom:4vh;gap:0;
        padding:20px;font-family:'DM Sans',sans-serif;
    }}
    /* ── TOP BADGE ── */
    .lp-badge{{
        display:inline-flex;align-items:center;gap:6px;
        background:rgba(0,174,239,.12);border:1px solid rgba(0,174,239,.25);
        border-radius:20px;padding:4px 14px;margin-bottom:28px;
        font-size:10px;font-weight:700;color:rgba(0,174,239,.9);
        letter-spacing:1.5px;text-transform:uppercase;
        animation:fadeDown .6s ease both;
    }}
    .lp-badge-dot{{width:6px;height:6px;background:#00AEEF;border-radius:50%;animation:pulse2 2s infinite;}}
    @keyframes pulse2{{0%,100%{{box-shadow:0 0 0 0 rgba(0,174,239,.5);}}50%{{box-shadow:0 0 0 5px rgba(0,174,239,0);}}}}
    @keyframes fadeDown{{from{{opacity:0;transform:translateY(-12px);}}to{{opacity:1;transform:translateY(0);}}}}
    /* ── LOGO ── */
    .lp-logo{{margin-bottom:10px;animation:fadeDown .7s .1s ease both;}}
    .lp-logo img{{width:160px;max-width:70vw;filter:drop-shadow(0 8px 24px rgba(0,174,239,.3)) brightness(1.1);}}
    /* ── TITLE ── */
    .lp-title{{
        font-family:'Sora',sans-serif;font-size:26px;font-weight:900;
        color:#ffffff;letter-spacing:-.5px;margin:0 0 6px;
        animation:fadeDown .7s .2s ease both;
        text-shadow:0 0 40px rgba(0,174,239,.2);
    }}
    .lp-sub{{
        font-size:11px;font-weight:500;color:rgba(255,255,255,.35);
        letter-spacing:2.5px;text-transform:uppercase;margin-bottom:36px;
        animation:fadeDown .7s .3s ease both;
    }}
    /* ── GLASS CARD ── */
    .lp-card{{
        width:220px;margin:0 auto;
        background:linear-gradient(145deg,rgba(255,255,255,.07),rgba(255,255,255,.03));
        border:1px solid rgba(255,255,255,.10);
        border-radius:20px;padding:18px 20px 16px;
        backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);
        box-shadow:0 32px 64px rgba(0,0,0,.4),0 0 0 1px rgba(255,255,255,.04) inset,0 1px 0 rgba(255,255,255,.08) inset;
        animation:cardIn .8s .4s cubic-bezier(.18,.89,.32,1.28) both;
        position:relative;overflow:hidden;
    }}
    .lp-card::before{{
        content:'';position:absolute;top:0;left:0;right:0;height:1px;
        background:linear-gradient(90deg,transparent,rgba(0,174,239,.5),transparent);
    }}
    @keyframes cardIn{{0%{{opacity:0;transform:translateY(24px) scale(.95);}}100%{{opacity:1;transform:translateY(0) scale(1);}}}}
    /* ── CARD HEADER ── */
    .lp-card-icon{{font-size:11px;margin-bottom:0;display:block;text-align:center;}}
    .lp-card-title{{font-family:'Sora',sans-serif;font-size:6px;font-weight:900;color:rgba(255,255,255,.35);letter-spacing:1px;text-transform:uppercase;text-align:center;margin:0 auto;display:table;}}
    /* ── INPUT INSIDE CARD ── */
    .lp-card [data-testid="stTextInput"]{{min-width:0!important;width:100%!important;margin:0!important;}}
    .lp-card [data-testid="stTextInput"]>div{{min-width:0!important;width:100%!important;}}
    .lp-card [data-baseweb="input"]{{
        border-radius:10px!important;
        border:1px solid rgba(255,255,255,.12)!important;
        background:rgba(255,255,255,.06)!important;
        height:42px!important;font-size:13px!important;
        width:100%!important;transition:all .3s ease!important;
    }}
    .lp-card [data-baseweb="input"]:hover{{background:rgba(255,255,255,.09)!important;border-color:rgba(255,255,255,.20)!important;}}
    .lp-card [data-baseweb="input"] input{{color:#fff!important;font-weight:600!important;font-size:13px!important;text-align:center!important;letter-spacing:3px!important;}}
    .lp-card [data-baseweb="input"] input::placeholder{{color:rgba(255,255,255,.25)!important;letter-spacing:1px!important;font-weight:400!important;font-size:12px!important;}}
    .lp-card [data-baseweb="input"]:focus-within{{
        border-color:rgba(0,174,239,.6)!important;
        background:rgba(0,174,239,.07)!important;
        box-shadow:0 0 0 3px rgba(0,174,239,.12),0 0 20px rgba(0,174,239,.08)!important;
    }}
    .lp-card [data-testid="stAlert"]{{background:rgba(255,60,60,.08)!important;border:1px solid rgba(255,60,60,.18)!important;border-radius:8px!important;color:rgba(255,180,180,.9)!important;font-size:11px!important;padding:7px 10px!important;margin-top:10px!important;}}
    /* ── HINT TEXT ── */
    .lp-hint{{font-size:8px;color:rgba(255,255,255,.18);text-align:center;margin-top:10px;letter-spacing:1px;text-transform:uppercase;}}
    /* ── FOOTER ── */
    .lp-footer{{margin-top:12px;font-size:9px;color:rgba(255,255,255,.12);letter-spacing:2px;text-transform:uppercase;text-align:center;}}
    </style>''', unsafe_allow_html=True)

    img_html = f'<img src="data:image/png;base64,{logo_big}" alt="Dsquares"/>' if logo_big else "<span style='font-family:Sora,sans-serif;font-size:32px;font-weight:900;color:#fff;'>Dsquares</span>"
    st.markdown(f'''
    <div class="lp-bg"></div>
    <div class="lp-grid"></div>
    <div class="lp-orb lp-orb1"></div>
    <div class="lp-orb lp-orb2"></div>
    <div class="lp-orb lp-orb3"></div>
    <div class="lp-particles">
        <div class="lp-p" style="left:8%;width:2px;height:2px;background:rgba(0,174,239,.4);animation-duration:14s;animation-delay:0s;"></div>
        <div class="lp-p" style="left:22%;width:3px;height:3px;background:rgba(255,255,255,.2);animation-duration:20s;animation-delay:4s;"></div>
        <div class="lp-p" style="left:38%;width:2px;height:2px;background:rgba(0,174,239,.3);animation-duration:16s;animation-delay:2s;"></div>
        <div class="lp-p" style="left:55%;width:2px;height:2px;background:rgba(255,255,255,.15);animation-duration:22s;animation-delay:7s;"></div>
        <div class="lp-p" style="left:70%;width:3px;height:3px;background:rgba(0,140,200,.35);animation-duration:18s;animation-delay:1s;"></div>
        <div class="lp-p" style="left:85%;width:2px;height:2px;background:rgba(255,255,255,.2);animation-duration:15s;animation-delay:9s;"></div>
        <div class="lp-p" style="left:92%;width:2px;height:2px;background:rgba(0,174,239,.25);animation-duration:19s;animation-delay:5s;"></div>
    </div>
    <div class="lp-wrap">
        <div class="lp-badge"><div class="lp-badge-dot"></div>Live System</div>
        <div class="lp-logo">{img_html}</div>
        <div class="lp-title">Support Analysis Dashboard</div>
        <div class="lp-sub">Dsquares &nbsp;&bull;&nbsp; 2026</div>
    </div>''', unsafe_allow_html=True)

    _, c2, _ = st.columns([2.2, 1, 2.2])
    with c2:
        st.markdown('<div class="lp-card"><span class="lp-card-icon">🔐</span><div class="lp-card-title">Enter Access Key</div>', unsafe_allow_html=True)
        pwd = st.text_input("KEY", type="password", placeholder="••••••••", label_visibility="collapsed")
        st.markdown('</div><div class="lp-footer">Dsquares &copy; 2026 &nbsp;·&nbsp; Confidential</div>', unsafe_allow_html=True)
    if is_valid_key(pwd, ADMIN_ACCESS_KEY): st.session_state.auth_role = "admin"; st.rerun()
    elif is_valid_key(pwd, USER_ACCESS_KEY): st.session_state.auth_role = "user"; st.rerun()
    _dyn_pwds = get_dynamic_passwords()
    _full_pwd_map = {**PASSWORD_PROJECTS, **_dyn_pwds}
    if pwd in _full_pwd_map:
        st.session_state.auth_role = "client"
        st.session_state.client_projects = _full_pwd_map[pwd]
        _dyn_vf = get_dynamic_vf_map()
        st.session_state.is_vodafone = _dyn_vf.get(pwd, False) or (pwd == "vodafone123")
        _dyn_logos = get_dynamic_logo_map()
        _full_logo_map = {**PROJECT_LOGO_MAP, **_dyn_logos}
        logo_file = _full_logo_map.get(pwd)
        st.session_state.client_logo_file = logo_file
        st.session_state.client_logo = get_img_64(logo_file) if logo_file else None
        st.rerun()
    elif pwd: st.error("Invalid access key")
    st.stop()

S_ID = SPREADSHEET_ID

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_all_data():
    base = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv"
    gid_keys = ['merchant_support', 'client_support', 'quality_board', 'agent_perf', 'inbound_sla', 'redemption']
    try:
        def load_csv(gid_key):
            return pd.read_csv(f"{base}&gid={SHEET_GIDS[gid_key]}", dtype=str).dropna(axis=1, how='all').fillna("")
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futs = {pool.submit(load_csv, k): k for k in gid_keys}
            for f in concurrent.futures.as_completed(futs):
                results[futs[f]] = f.result()
        df_merchant, df_client = results['merchant_support'], results['client_support']
        df_qual, df_agent = results['quality_board'], results['agent_perf']
        df_sla, df_red = results['inbound_sla'], results['redemption']
        df_all = pd.concat([df_merchant, df_client], ignore_index=True)
        df_merchant = df_merchant[df_merchant.iloc[:, 0].astype(str).str.strip() != ""].copy()
        df_client = df_client[df_client.iloc[:, 0].astype(str).str.strip() != ""].copy()
        df_all = df_all[df_all.iloc[:, 0].astype(str).str.strip() != ""].copy()
        for old, new in SHORT_NAMES.items():
            df_merchant = df_merchant.replace(old, new)
            df_client = df_client.replace(old, new)
            df_all = df_all.replace(old, new)
        for d in [df_merchant, df_client, df_all]:
            d_col = next((c for c in d.columns if any(k in c.lower() for k in ['created', 'date'])), d.columns[0])
            d['D_Obj'] = pd.to_datetime(d[d_col], errors='coerce').dt.date
            d['Month_Name'] = pd.to_datetime(d[d_col], errors='coerce').dt.strftime('%b')
            d['Month_Num'] = pd.to_datetime(d[d_col], errors='coerce').dt.to_period('M')
        df_qual = df_qual[df_qual.iloc[:, 0].astype(str).str.strip() != ""].copy() if not df_qual.empty else pd.DataFrame()
        df_agent = df_agent[df_agent.iloc[:, 0].astype(str).str.strip() != ""].copy() if not df_agent.empty else pd.DataFrame()
        df_sla = df_sla[df_sla.iloc[:, 0].astype(str).str.strip() != ""].copy() if not df_sla.empty else pd.DataFrame()
        df_red = df_red[df_red.iloc[:, 0].astype(str).str.strip() != ""].copy() if not df_red.empty else pd.DataFrame()
        return df_merchant, df_client, df_all, df_qual, df_agent, df_sla, df_red, datetime.now(APP_TIMEZONE)
    except Exception as exc:
        st.session_state.load_error = str(exc)
        return None, None, None, None, None, None, None, None

with st.spinner("Loading dashboard data..."):
    res = load_all_data()
if res[0] is None:
    st.error("Data source unavailable."); st.stop()

df_merchant, df_client, df_all, df_qual, df_agent, df_sla, df_red, last_updated = res

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def load_quality_raw():
    base = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid={SHEET_GIDS['quality_board']}"
    try:
        raw = pd.read_csv(base, dtype=str, header=None).fillna("")
        return raw
    except: return pd.DataFrame()

_raw_q = load_quality_raw()
_agent_summary_rows = []
_top_errors = {"EC": [], "BC": [], "NC": []}
_per_agent_errors = []
if not _raw_q.empty:
    for i in range(len(_raw_q)):
        r = _raw_q.iloc[i].tolist()
        if r[1] == "Agent Name" and r[2] == "Total Volume":
            for j in range(i + 1, len(_raw_q)):
                nr = _raw_q.iloc[j].tolist()
                if nr[1] and nr[2] and str(nr[2]).replace(".","").isdigit():
                    _agent_summary_rows.append({"Agent": nr[1], "Volume": nr[2], "Avg EC%": nr[3], "Avg BC%": nr[4], "Overall Avg": nr[5]})
                else: break
        if r[1] == "Top EC Errors":
            for j in range(i + 1, len(_raw_q)):
                nr = _raw_q.iloc[j].tolist()
                if nr[1] and str(nr[2]).replace(".","").isdigit():
                    _top_errors["EC"].append({"Error": nr[1], "Count": nr[2]})
                    if nr[5] and str(nr[6]).replace(".","").isdigit(): _top_errors["BC"].append({"Error": nr[5], "Count": nr[6]})
                    if nr[9] and len(nr) > 10 and str(nr[10]).replace(".","").isdigit(): _top_errors["NC"].append({"Error": nr[9], "Count": nr[10]})
                else: break
        if r[1] == "Agent" and r[2] == "EC Error":
            for j in range(i + 1, len(_raw_q)):
                nr = _raw_q.iloc[j].tolist()
                if nr[1] and nr[2] and str(nr[3]).replace(".","").isdigit():
                    _per_agent_errors.append({"Agent": nr[1], "Type": "EC", "Error": nr[2], "Count": nr[3]})
                    if nr[5] and nr[6] and len(nr) > 7 and str(nr[7]).replace(".","").isdigit():
                        _per_agent_errors.append({"Agent": nr[5], "Type": "BC", "Error": nr[6], "Count": nr[7]})
                    if nr[9] and nr[10] and len(nr) > 11 and str(nr[11]).replace(".","").isdigit():
                        _per_agent_errors.append({"Agent": nr[9], "Type": "NC", "Error": nr[10], "Count": nr[11]})
                else: break
for d in [df_merchant, df_client, df_all]:
    if not d.empty and 'Closed time' in d.columns:
        d['Ticket_Status'] = pd.to_datetime(d['Closed time'], errors='coerce').notna().map({True: 'Closed', False: 'Open'})
    if not d.empty and 'Project' in d.columns:
        d['Project'] = d['Project'].replace(PROJECT_RENAME)

if 'last_row_count' not in st.session_state: st.session_state.last_row_count = len(df_all)
now_str = last_updated.strftime("%d %b %Y %H:%M") if last_updated else ""
logo_html = f'<img src="data:image/png;base64,{logo_sm}" width="34">' if logo_sm else ""

st.markdown(f'<div class="dashboard-header">{logo_html}<h2>Support Analysis Dashboard</h2>'
    f'<div style="display:flex;justify-content:center;align-items:center;gap:10px;margin-top:5px;flex-wrap:wrap;">'
    f'<span class="live-badge"><span class="live-dot"></span> LIVE</span>'
    f'<span style="font-size:11px;color:gray;">Last updated: {now_str} | Auto</span></div></div>', unsafe_allow_html=True)

for k, v in [('slideshow_active', False), ('slide_index', 0), ('click_filter_col', None), ('click_filter_val', None), ('client_projects', None), ('client_logo', None), ('auto_refresh_mins', 0), ('client_tab_idx', 0)]:
    if k not in st.session_state: st.session_state[k] = v
for k in ['drill_down_date_Merchant_Support', 'drill_down_date_Client_Support', 'drill_down_tab', '_last_drill_nav']:
    if k not in st.session_state: st.session_state[k] = None

if st.session_state.get("client_projects"):
    st.markdown('''<style>
    /* Client mode: light sidebar */
    [data-testid="stSidebar"]>div:first-child{background:linear-gradient(175deg,#f0f5ff 0%,#e8f0fb 50%,#ddeaff 100%)!important;box-shadow:4px 0 24px rgba(0,33,71,.12)!important;}
    [data-testid="stSidebar"] label{color:#002147!important;font-weight:700!important;}
    [data-testid="stSidebar"] [data-baseweb="select"] span,[data-testid="stSidebar"] [data-baseweb="input"] span,[data-testid="stSidebar"] .stSelectbox span,[data-testid="stSidebar"] .stMultiSelect span,[data-testid="stSidebar"] .stDateInput span{color:#002147!important;}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] .stMarkdown p,[data-testid="stSidebar"] .stMarkdown div{color:rgba(0,33,71,.45)!important;font-size:9px!important;text-transform:uppercase!important;letter-spacing:1.4px!important;}
    [data-testid="stSidebar"] div[data-baseweb="select"]>div{background:rgba(255,255,255,.80)!important;border:1px solid rgba(0,33,71,.15)!important;border-radius:10px!important;min-height:38px!important;}
    [data-testid="stSidebar"] div[data-baseweb="select"]>div:hover{border-color:rgba(0,85,164,.40)!important;background:white!important;box-shadow:0 0 0 2px rgba(0,85,164,.10)!important;}
    [data-testid="stSidebar"] div[data-baseweb="select"]>div *{color:#002147!important;}
    [data-testid="stSidebar"] div[data-baseweb="select"] svg{fill:#002147!important;opacity:.5!important;}
    [data-testid="stSidebar"] span[data-baseweb="tag"]{background:rgba(0,85,164,.15)!important;border:1px solid rgba(0,85,164,.25)!important;border-radius:6px!important;padding:2px 8px!important;color:#002147!important;font-weight:700!important;font-size:11px!important;}
    [data-testid="stSidebar"] span[data-baseweb="tag"] *{color:#002147!important;}
    [data-testid="stSidebar"] hr{border:none!important;border-top:1px solid rgba(0,33,71,.10)!important;margin:10px 16px!important;}
    [data-testid="stSidebar"] .stButton>button{background:rgba(0,33,71,.08)!important;color:#002147!important;border:1px solid rgba(0,33,71,.15)!important;border-radius:10px!important;font-weight:700!important;font-size:12px!important;width:100%!important;padding:8px 12px!important;}
    [data-testid="stSidebar"] .stButton>button:hover{background:rgba(0,33,71,.14)!important;border-color:rgba(0,85,164,.35)!important;transform:translateY(-1px)!important;box-shadow:0 4px 12px rgba(0,33,71,.10)!important;color:#002147!important;}
    [data-testid="stSidebar"] .stButton:last-of-type>button{background:rgba(200,50,50,.08)!important;border-color:rgba(200,50,50,.20)!important;color:#CC0000!important;}
    [data-testid="stSidebar"] .stButton:last-of-type>button:hover{background:rgba(200,50,50,.16)!important;border-color:rgba(200,50,50,.35)!important;color:#aa0000!important;}
    [data-testid="stSidebar"] [data-testid="stDateInput"] div[data-baseweb="input"]{background:rgba(255,255,255,.80)!important;border:1px solid rgba(0,33,71,.15)!important;border-radius:10px!important;min-height:38px!important;}
    [data-testid="stSidebar"] [data-testid="stDateInput"] div[data-baseweb="input"]:hover{border-color:rgba(0,85,164,.40)!important;}
    [data-testid="stSidebar"] [data-testid="stDateInput"] input{color:#002147!important;background:transparent!important;border:none!important;font-size:13px!important;font-weight:600!important;}
    [data-testid="stSidebar"] [data-testid="stDateInput"] input::placeholder{color:rgba(0,33,71,.40)!important;}
    [data-testid="stSidebar"] [data-testid="stDateInput"] input::-webkit-calendar-picker-indicator{filter:none!important;cursor:pointer!important;opacity:.6!important;}
    [data-testid="stSidebar"] div[data-baseweb="input"]{background:rgba(255,255,255,.80)!important;border:1px solid rgba(0,33,71,.15)!important;border-radius:10px!important;min-height:38px!important;}
    [data-testid="stSidebar"] div[data-baseweb="input"] input{color:#002147!important;background:transparent!important;border:none!important;font-size:13px!important;font-weight:600!important;}
    [data-testid="stSidebar"] div[data-baseweb="input"] input::placeholder{color:rgba(0,33,71,.40)!important;}
    </style>''', unsafe_allow_html=True)

with st.sidebar:
    if st.session_state.get("client_projects"):
        if st.session_state.get("client_logo_file"):
            lp = os.path.join(BASE_DIR, st.session_state.client_logo_file)
            if os.path.exists(lp):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2: st.image(Image.open(lp), width=130)
    else:
        if logo_big:
            c1, c2, c3 = st.columns([1, 5, 1])
            with c2: st.image(os.path.join(BASE_DIR, "logo_big.png"), width=200)
    st.markdown('<div style="display:flex;align-items:center;justify-content:center;gap:8px;padding:6px 16px;border-bottom:1px solid rgba(255,255,255,.06);border-top:1px solid rgba(255,255,255,.06);margin-bottom:2px;background:rgba(255,255,255,.03);">'
        '<span style="width:6px;height:6px;background:#00e676;border-radius:50%;box-shadow:0 0 6px rgba(0,230,118,.5);flex-shrink:0;"></span>'
        '<span style="font-size:9px!important;font-weight:700!important;color:rgba(255,255,255,.5);letter-spacing:.8px!important;">LIVE &nbsp;·&nbsp; Auto</span></div>', unsafe_allow_html=True)
    st.markdown('<div style="padding:8px 16px 2px 18px;font-size:9px;font-weight:700;color:rgba(255,255,255,.35);text-transform:uppercase;letter-spacing:1.6px;">FILTERS</div>', unsafe_allow_html=True)
    date_mode = st.selectbox("📅 Date filter", ["Custom range", "All time"], index=0, key="date_mode_key")
    show_all = date_mode == "All time"
    dr = st.date_input("🗓 Date Range", [min(df_all['D_Obj']), max(df_all['D_Obj'])], key="dr_key", disabled=show_all)
    ff_base = df_all.copy()
    if not show_all and len(dr) == 2:
        ff_base = ff_base[(ff_base['D_Obj'] >= dr[0]) & (ff_base['D_Obj'] <= dr[1])]
    if st.session_state.get("client_projects"):
        ff_base = ff_base[ff_base['Project'].astype(str).isin(st.session_state.client_projects)]
    f_merch = st.multiselect("🏪 Merchant", sorted(ff_base['Merchant'].unique()) if 'Merchant' in ff_base.columns else [])
    if st.session_state.get("client_projects") and not st.session_state.get("is_vodafone"):
        f_proj = []
    else:
        f_proj = st.multiselect("🏢 Project", sorted(ff_base['Project'].unique()) if 'Project' in ff_base.columns else [])
    f_branch = []
    if not st.session_state.get("client_projects"):
        f_branch = st.multiselect("📍 Branch", sorted(ff_base['Branch User Name'].unique()) if 'Branch User Name' in ff_base.columns else [])
    f_type = st.multiselect("🎫 Ticket type", sorted(ff_base['Ticket type'].unique()) if 'Ticket type' in ff_base.columns else [])
    f_act = st.multiselect("🎬 Action taken", sorted(ff_base['Action taken'].unique()) if 'Action taken' in ff_base.columns else [])
    if st.session_state.get("client_projects"):
        f_status = []
    else:
        f_status = st.multiselect("🎫 Ticket Status", options=["Open", "Closed"], default=[])
    ff = ff_base.copy()
    if f_merch and 'Merchant' in ff.columns: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_proj and 'Project' in ff.columns: ff = ff[ff['Project'].isin(f_proj)]
    if f_branch and 'Branch User Name' in ff.columns: ff = ff[ff['Branch User Name'].isin(f_branch)]
    if f_type and 'Ticket type' in ff.columns: ff = ff[ff['Ticket type'].isin(f_type)]
    if f_act and 'Action taken' in ff.columns: ff = ff[ff['Action taken'].isin(f_act)]
    if f_status and 'Ticket_Status' in ff.columns: ff = ff[ff['Ticket_Status'].isin(f_status)]
    active_filters = {}
    if f_merch: active_filters['Merchant'] = ", ".join(f_merch)
    if f_proj: active_filters['Project'] = ", ".join(f_proj)
    if f_branch: active_filters['Branch'] = ", ".join(f_branch)
    if f_type: active_filters['Ticket type'] = ", ".join(f_type)
    if f_act: active_filters['Action'] = ", ".join(f_act)
    if f_status: active_filters['Status'] = ", ".join(f_status)
    if not show_all and len(dr) == 2 and (dr[0] != min(df_all['D_Obj']) or dr[1] != max(df_all['D_Obj'])):
        active_filters['Date'] = f"{dr[0]} → {dr[1]}"
    if st.session_state.click_filter_col and st.session_state.click_filter_val:
        col_cf, val_cf = st.session_state.click_filter_col, st.session_state.click_filter_val
        if col_cf in df_merchant.columns: df_merchant = df_merchant[df_merchant[col_cf] == val_cf]
        if col_cf in df_client.columns: df_client = df_client[df_client[col_cf] == val_cf]
        if col_cf in ff.columns: ff = ff[ff[col_cf] == val_cf]
        active_filters[col_cf] = val_cf
        st.info(f"🔍 {col_cf}: **{val_cf}**")
        if st.button("Clear Chart Filter", use_container_width=True): st.session_state.click_filter_col = None; st.session_state.click_filter_val = None; st.rerun()
    st.divider()
    if st.button("🔄 Refresh Data Now", use_container_width=True): st.cache_data.clear(); st.rerun()
    slide_label = "⏹ Stop Slideshow" if st.session_state.slideshow_active else "▶️ Start Slideshow"
    if st.button(slide_label, use_container_width=True): st.session_state.slideshow_active = not st.session_state.slideshow_active; st.session_state.slide_index = 0; st.rerun()
    if st.session_state.auth_role == "admin":
        mgmt_on = st.session_state.get("show_access_mgmt", False)
        mgmt_label = "⏹ Close Mgmt" if mgmt_on else "🔐 Access Management"
        if st.button(mgmt_label, use_container_width=True):
            st.session_state.show_access_mgmt = not mgmt_on
            st.rerun()
    st.divider()
    if st.button("🚪 Log Out", use_container_width=True): st.session_state.auth_role = None; st.rerun()

ff_drill = ff.copy()

CHART_PALETTE = ["#002147", "#0055A4", "#00AEEF", "#0077cc", "#003d82", "#00c6ff", "#1a3a6b", "#4a90d9"]
CHART_BG = "rgba(248,251,255,0)"

def _style_bar_fig(fig, color):
    n = len(fig.data[0].x) if fig.data and hasattr(fig.data[0], 'x') and fig.data[0].x is not None else 8
    palette = [color] * n if n <= 1 else [
        f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},{0.55 + 0.45*(i/(max(n-1,1))):.2f})"
        for i in range(n)
    ]
    fig.update_traces(
        marker_color=palette,
        marker_line_width=0,
        marker_cornerradius=6,
        textfont=dict(family="Sora, DM Sans, sans-serif", size=11, color="#002147", weight=700),
        textposition='outside',
        cliponaxis=False,
        hovertemplate=fig.data[0].hovertemplate if fig.data[0].hovertemplate else "%{x}<br><b>%{y:,}</b><extra></extra>",
    )
    fig.update_layout(
        xaxis_type='category',
        yaxis_title="",
        xaxis_title="",
        title_font=dict(family="Sora, sans-serif", size=14, color="#002147", weight=700),
        title_x=0,
        bargap=0.28,
        margin=dict(t=46, b=8, l=4, r=8),
        plot_bgcolor=CHART_BG,
        paper_bgcolor=CHART_BG,
        font=dict(family="DM Sans, sans-serif", color="#002147"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11, weight=600), tickangle=-28),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,33,71,.07)", gridwidth=1, zeroline=False, tickfont=dict(size=10)),
        hoverlabel=dict(bgcolor="#001e42", font_size=12, font_family="DM Sans", font_color="white", bordercolor="#00AEEF"),
        showlegend=False,
    )
    return fig

def clickable_bar(df_plot, x_col, y_col, title, color, filter_col, key_name, customdata=None, hovertemplate=None):
    fig = px.bar(df_plot, x=x_col, y=y_col, title=title, text=y_col, color_discrete_sequence=[color], labels={y_col: "Total", x_col: ""})
    if customdata is not None and hovertemplate: fig.update_traces(customdata=customdata, hovertemplate=hovertemplate)
    fig = _style_bar_fig(fig, color)
    ev = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=key_name)
    if ev and ev.selection and ev.selection.get("points"):
        pt = ev.selection["points"][0]; cv = pt.get("x") or pt.get("label")
        if cv and isinstance(cv, str): st.session_state.click_filter_col = filter_col; st.session_state.click_filter_val = str(cv); st.rerun()

def mksb(df, x, y, title, color):
    f = px.bar(df, x=x, y=y, title=title, text=y, color_discrete_sequence=[color], labels={y:'Total', x:''})
    f = _style_bar_fig(f, color)
    return f

def ms(df, x, y, title, color, fc, kn, cd=None, ht=None):
    return clickable_bar(df, x, y, title, color, fc, kn, customdata=cd, hovertemplate=ht)

PIE_COLORS = ["#002147","#0055A4","#00AEEF","#0077cc","#4a90d9","#003d82","#00c6ff","#1a3a6b","#66b2e8","#0094d4"]

def _style_pie(fig):
    fig.update_traces(
        textinfo='percent+label',
        textfont=dict(family="DM Sans, sans-serif", size=11, color="white"),
        marker=dict(colors=PIE_COLORS, line=dict(color='white', width=2.5)),
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent:.1%}<extra></extra>",
        pull=[0.03]*20,
        rotation=30,
    )
    fig.update_layout(
        title_font=dict(family="Sora, sans-serif", size=14, color="#002147", weight=700),
        title_x=0,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color="#002147"),
        legend=dict(orientation="v", font=dict(size=11, family="DM Sans"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=46, b=10, l=10, r=10),
        hoverlabel=dict(bgcolor="#001e42", font_size=12, font_family="DM Sans", font_color="white", bordercolor="#00AEEF"),
    )
    return fig

def render_team_overview(data_df, show_branches=True, show_redemption=True, drill_tab="Merchant Support", client_mode=False):
    cfc = st.session_state.click_filter_col
    cfv = st.session_state.click_filter_val
    if cfc and cfv and cfc in data_df.columns:
        data_df = data_df[data_df[cfc] == cfv]
    inbound_all = data_df[data_df['Type'].str.contains('Inbound|Call', case=False, na=False)] if 'Type' in data_df.columns else data_df
    wa_all = data_df[data_df['Type'].str.contains('WhatsApp|App', case=False, na=False)] if 'Type' in data_df.columns else pd.DataFrame()
    inbound_base = ff_base[ff_base['Type'].str.contains('Inbound|Call', case=False, na=False)] if not ff_base.empty else inbound_all
    wa_base = ff_base[ff_base['Type'].str.contains('WhatsApp|App', case=False, na=False)] if not ff_base.empty else wa_all
    has_filter = bool(active_filters)
    analysis_total = smart_analysis(data_df, ff_base if not ff_base.empty else data_df, active_filters) if has_filter else []
    analysis_inbound = smart_analysis(inbound_all, inbound_base, active_filters) if has_filter else []
    analysis_wa = smart_analysis(wa_all, wa_base, active_filters) if has_filter else []
    t_m = get_top_safe(data_df, 'Merchant'); t_p = get_top_safe(data_df, 'Project')
    t_b = get_top_safe(data_df, 'Branch User Name'); t_t = get_top_safe(data_df, 'Ticket type')

    if active_filters:
        badges = "".join([f'<span class="filter-badge"> {k}: {v}</span>' for k, v in active_filters.items()])
        st.markdown(f'<div style="margin:0 0 8px;">{badges}</div>', unsafe_allow_html=True)

    # ── SLIDESHOW ──
    if st.session_state.slideshow_active:
        ff_drill_s = data_df.copy()
        daily_s = data_df.groupby('D_Obj').size().reset_index(name='Total')
        peak_s = daily_s.nlargest(20, 'Total').sort_values('D_Obj')
        peak_s['Date_Str'] = peak_s['D_Obj'].astype(str)
        hp_s = []
        for d in peak_s['D_Obj']:
            rows = data_df[data_df['D_Obj'] == d].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
            lines = [f"• {r['Call Microtype']}: {r['n']}" for _, r in rows.iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]
            hp_s.append("<br>".join(lines))
        fig_v_s = px.bar(peak_s, x='Date_Str', y='Total', title=" Volume Trend (Peak Days)", color_discrete_sequence=[DS_NAVY], text='Total')
        fig_v_s.update_traces(customdata=hp_s, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        fig_v_s.update_layout(xaxis=dict(type='category', showgrid=False, tickangle=-28, tickfont=dict(size=11)), yaxis_title='', bargap=0.22, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans, sans-serif', color='#002147'), yaxis=dict(showgrid=True, gridcolor='rgba(0,33,71,.07)', zeroline=False), margin=dict(t=46,b=8,l=4,r=8), hoverlabel=dict(bgcolor='#001e42', font_size=12, font_color='white', bordercolor='#00AEEF'), title_font=dict(family='Sora, sans-serif', size=14, color='#002147'))
        fig_v_s.update_traces(marker_cornerradius=5, marker_line_width=0, textfont=dict(family='Sora, sans-serif', size=11, weight=700))
        m_a = clean_st(data_df, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        br_a = clean_st(data_df, 'Branch User Name').groupby('Branch User Name').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        p_a = clean_st(data_df, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Project' in data_df.columns else pd.DataFrame()
        su_a = clean_st(data_df, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Ticket subtype' in data_df.columns else pd.DataFrame()
        mi_a = clean_st(data_df, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Call Microtype' in data_df.columns else pd.DataFrame()
        ac_a = clean_st(data_df, 'Action taken')['Action taken'].value_counts().head(10).reset_index() if 'Action taken' in data_df.columns else pd.DataFrame()
        if not ac_a.empty: ac_a.columns = ['Action taken', 'Count']
        tt_a = clean_st(data_df, 'Ticket type')
        slides_data = [
            ("📊 Volume Trend (Peak Days)", fig_v_s),
            ("🏪 1. Top 10 Merchants", mksb(m_a, 'Merchant', 'c', "🏪 1. Top 10 Merchants", DS_NAVY) if not m_a.empty else None),
            ("📍 2. Top 10 Branches", mksb(br_a, 'Branch User Name', 'c', "📍 2. Top 10 Branches", DS_LIGHT) if not br_a.empty else None),
        ]
        if p_a is not None and not p_a.empty: slides_data.append(("🏢 3. Top 10 Projects", mksb(p_a, 'Project', 'c', "🏢 3. Top 10 Projects", DS_NAVY)))
        if tt_a is not None and not tt_a.empty:
            fp = px.pie(tt_a, names='Ticket type', title="🎫 4. Ticket Type Share", hole=0.3); fp = _style_pie(fp)
            slides_data.append(("🎫 4. Ticket Type Share", fp))
        if su_a is not None and not su_a.empty: slides_data.append(("🏷️ 5. Top 10 Subtypes", mksb(su_a, 'Ticket subtype', 'c', "🏷️ 5. Top 10 Subtypes", DS_NAVY)))
        if mi_a is not None and not mi_a.empty: slides_data.append(("🔬 6. Top 10 Microtypes", mksb(mi_a, 'Call Microtype', 'c', "🔬 6. Top 10 Microtypes", DS_LIGHT)))
        abt_s = (data_df[~data_df['Action taken'].astype(str).str.lower().isin([x.lower() for x in BLACK_LIST])].groupby(['Ticket_Status', 'Action taken']).size().reset_index(name='n').sort_values('n', ascending=False)) if 'Ticket_Status' in data_df.columns and 'Action taken' in data_df.columns else pd.DataFrame()
        if not abt_s.empty:
            def bhs_s(s): r2 = abt_s[abt_s['Ticket_Status'] == s].head(6); return "<br>".join([f"• {x['Action taken']}: {x['n']}" for _, x in r2.iterrows()]) if not r2.empty else "No actions"
            sc_s = data_df['Ticket_Status'].value_counts().reset_index(); sc_s.columns = ['Ticket_Status', 'Count']
            sc_s['h'] = sc_s['Ticket_Status'].apply(bhs_s)
            fig_st_s = px.pie(sc_s, names='Ticket_Status', values='Count', title=" Live Ticket Status", hole=0.4, color='Ticket_Status', color_discrete_map={"Closed": DS_NAVY, "Open": "#FF4B4B"})
            fig_st_s.update_traces(customdata=sc_s['h'], hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent:.2%}<br><br><b>Top Actions:</b><br>%{customdata}<extra></extra>", textinfo='percent+label', texttemplate='%{label}: %{percent:.2%}', textfont=dict(family="DM Sans, sans-serif", size=12), marker=dict(line=dict(color="white", width=3)), pull=[0.04, 0])
            fig_st_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title_font=dict(family="Sora, sans-serif", size=14, color="#002147"), hoverlabel=dict(bgcolor="#001e42", font_size=12, font_color="white", bordercolor="#00AEEF"), margin=dict(t=46,b=10,l=10,r=10))
            slides_data.append(("🎫 Live Ticket Status", fig_st_s))
        if not ac_a.empty: slides_data.append(("🎬 7. Key Actions Taken", mksb(ac_a, 'Action taken', 'Count', "🎬 7. Key Actions Taken", DS_NAVY)))
        slides_data = [(t, f) for t, f in slides_data if f is not None]
        SLIDE_DUR = 15
        ci = st.session_state.slide_index % len(slides_data)
        st_title, sf = slides_data[ci]
        st.markdown(f'<div class="slideshow-banner"> Slideshow &nbsp;|&nbsp; {ci + 1}/{len(slides_data)} &nbsp;|&nbsp; {SLIDE_DUR}s</div>', unsafe_allow_html=True)
        if client_mode is True:
            rs_val_sl = "N/A"
            if 'Resolution status' in data_df.columns: rs_val_sl = f"{len(data_df[data_df['Resolution status'].astype(str).str.contains('Within|Resolved', case=False, na=False)]):,}"
            urgent_val_sl = "N/A"
            if 'Priority' in data_df.columns: urgent_val_sl = f"{len(data_df[data_df['Priority'].astype(str).str.contains('Urgent|High', case=False, na=False)]):,}"
            st.markdown(f"""<div class="slide-scorecard-wrap">
                <div class="slide-scorecard"><div class="sc-label">Total</div><div class="sc-value">{len(data_df):,}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Resolution</div><div class="sc-value">{rs_val_sl}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Urgent</div><div class="sc-value">{urgent_val_sl}</div></div>
            </div>""", unsafe_allow_html=True)
        elif client_mode == "client":
            top_merchant_sl = get_top_safe(data_df, 'Merchant') or "—"
            top_ticket_type_sl = get_top_safe(data_df, 'Ticket type') or "—"
            st.markdown(f"""<div class="slide-scorecard-wrap">
                <div class="slide-scorecard"><div class="sc-label">Total</div><div class="sc-value">{len(data_df):,}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Top Merchant</div><div class="sc-value" style="font-size:16px;">{top_merchant_sl}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Top Type</div><div class="sc-value" style="font-size:16px;">{top_ticket_type_sl}</div></div>
            </div>""", unsafe_allow_html=True)
        else:
            red_val_sl = "N/A"
            if show_redemption and df_red is not None and not df_red.empty and 'Total Redemption Amount' in df_red.columns:
                try: red_val_sl = f"{pd.to_numeric(df_red['Total Redemption Amount'].astype(str).str.replace(',','').str.replace('EGP','').str.strip(), errors='coerce').iloc[0]:,.0f}"
                except: pass
            st.markdown(f"""<div class="slide-scorecard-wrap">
                <div class="slide-scorecard"><div class="sc-label">Total</div><div class="sc-value">{len(data_df):,}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Inbound</div><div class="sc-value">{len(inbound_all):,}</div></div>
                <div class="slide-scorecard"><div class="sc-label">WhatsApp</div><div class="sc-value">{len(wa_all):,}</div></div>
                <div class="slide-scorecard"><div class="sc-label">Redemption</div><div class="sc-value" style="font-size:16px;">{red_val_sl}</div></div>
            </div>""", unsafe_allow_html=True)
        _, cc, _ = st.columns([0.5, 9, 0.5])
        with cc: st.plotly_chart(sf, use_container_width=True)
        pb = st.progress(0); sh = st.empty()
        for i in range(SLIDE_DUR):
            if not st.session_state.slideshow_active: break
            pb.progress((i + 1) / SLIDE_DUR)
            sh.markdown(f'<p style="text-align:center;color:gray;font-size:11px;"> {SLIDE_DUR - i - 1}s...</p>', unsafe_allow_html=True)
            time.sleep(1)
        if st.session_state.slideshow_active:
            st.session_state.slide_index = (ci + 1) % len(slides_data); st.rerun()

    # ── NORMAL MODE ──
    else:
        if client_mode == "client":
            top_merchant = get_top_safe(data_df, 'Merchant') or "—"
            top_ticket_type = get_top_safe(data_df, 'Ticket type') or "—"
            render_scorecards_row([
                {"id": "sc_tc", "title": "📋 Total Tickets", "value_str": f"{len(data_df):,}", "analysis_lines": analysis_total, "border_color": "#002147"},
                {"id": "sc_tm", "title": "🏪 Top Merchant", "value_str": str(top_merchant), "analysis_lines": [], "border_color": "#0055A4"},
                {"id": "sc_tt", "title": "🎫 Top Ticket Type", "value_str": str(top_ticket_type), "analysis_lines": [], "border_color": "#00A3E0"},
            ])
        elif client_mode is True:
            rs_val = "N/A"
            if 'Resolution status' in data_df.columns:
                rs_count = len(data_df[data_df['Resolution status'].astype(str).str.contains('Within|Resolved', case=False, na=False)])
                rs_val = f"{rs_count:,}"
            urgent_val = "N/A"
            if 'Priority' in data_df.columns:
                urgent_count = len(data_df[data_df['Priority'].astype(str).str.contains('Urgent|High', case=False, na=False)])
                urgent_val = f"{urgent_count:,}"
            render_scorecards_row([
                {"id": "sc_tot", "title": "📋 Total Tickets", "value_str": f"{len(data_df):,}", "analysis_lines": analysis_total, "border_color": "#002147"},
                {"id": "sc_rs", "title": "🔧 Resolution Status", "value_str": rs_val, "analysis_lines": [], "border_color": "#0055A4"},
                {"id": "sc_urg", "title": "🚨 Urgent Alert", "value_str": urgent_val, "analysis_lines": [], "border_color": "#FF4B4B"},
            ])
        else:
            red_val = "N/A"
            if show_redemption and df_red is not None and not df_red.empty and 'Total Redemption Amount' in df_red.columns:
                try: red_val = f"{pd.to_numeric(df_red['Total Redemption Amount'].astype(str).str.replace(',','').str.replace('EGP','').str.strip(), errors='coerce').iloc[0]:,.0f}"
                except: pass
            render_scorecards_row([
                {"id": "sc_tot", "title": "📋 Total Tickets", "value_str": f"{len(data_df):,}", "analysis_lines": analysis_total, "border_color": "#002147"},
                {"id": "sc_in", "title": "📞 Inbound Calls", "value_str": f"{len(inbound_all):,}", "analysis_lines": analysis_inbound, "border_color": "#0055A4"},
                {"id": "sc_wa", "title": "💬 WhatsApp", "value_str": f"{len(wa_all):,}", "analysis_lines": analysis_wa, "border_color": "#00AEEF"},
                {"id": "sc_rd", "title": "💰 Total Redemption Value", "value_str": red_val, "analysis_lines": [], "border_color": "#00c06a"},
            ])

        if client_mode != "client":
            daily = data_df.groupby('D_Obj').size().reset_index(name='Total')
            peak = daily.nlargest(20, 'Total').sort_values('D_Obj')
            peak['Date_Str'] = peak['D_Obj'].astype(str)
            h_peak = []
            if 'Call Microtype' in data_df.columns:
                for d in peak['D_Obj']:
                    rows = data_df[data_df['D_Obj'] == d].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
                    lines = [f"• {r['Call Microtype']}: {r['n']}" for _, r in rows.iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]
                    h_peak.append("<br>".join(lines))
            fig_v = px.bar(peak, x='Date_Str', y='Total', title="📊 Volume Trend (Peak Days)", color_discrete_sequence=[DS_NAVY], text='Total')
            if h_peak: fig_v.update_traces(customdata=h_peak, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
            fig_v.update_layout(xaxis=dict(type='category', showgrid=False, tickangle=-28, tickfont=dict(size=11)), yaxis_title='', bargap=0.22, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans, sans-serif', color='#002147'), yaxis=dict(showgrid=True, gridcolor='rgba(0,33,71,.07)', zeroline=False), margin=dict(t=46,b=8,l=4,r=8), hoverlabel=dict(bgcolor='#001e42', font_size=12, font_color='white', bordercolor='#00AEEF'), title_font=dict(family='Sora, sans-serif', size=14, color='#002147'))
            fig_v.update_traces(marker_cornerradius=5, marker_line_width=0, textfont=dict(family='Sora, sans-serif', size=11, weight=700))
            st.plotly_chart(fig_v, use_container_width=True, key=f"bar_vol_{drill_tab.replace(' ', '_')}")

            drill_d = st.selectbox("📅 Drill down by Peak Day:", ["All Data"] + sorted(peak['Date_Str'].tolist()), key=f"drill_{drill_tab.replace(' ', '_')}")
            ff_drill = data_df.copy() if drill_d == "All Data" else data_df[data_df['D_Obj'].astype(str) == drill_d]
            if drill_d != "All Data":
                st.session_state[f"drill_down_date_{drill_tab.replace(' ', '_')}"] = drill_d
                st.session_state.drill_down_tab = drill_tab
                esc_dt = drill_tab.replace("'", "\\'")
                components.html(f"""<script>(function(){{
var c=function(){{
var ex=Array.from(window.parent.document.querySelectorAll('[role=\"tab\"]'))
  .find(function(t){{return (t.innerText||'').includes('Ticket Explorer');}});
if(ex&&ex.getAttribute('aria-selected')!=='true'){{ex.click();}}
setTimeout(function(){{
var last=Array.from(window.parent.document.querySelectorAll('[role=\"tab\"]'))
  .filter(function(t){{return (t.innerText||'').includes('{esc_dt}');}});
if(last.length)last[last.length-1].click();
}},500);}};
if(document.readyState==='complete')c();else window.addEventListener('load',c);
}})();</script>""", height=0)

            st.divider()
            st.markdown("### 🎫 Tickets Live Status Summary")
            abt = (ff_drill[~ff_drill['Action taken'].astype(str).str.lower().isin([x.lower() for x in BLACK_LIST])].groupby(['Ticket_Status', 'Action taken']).size().reset_index(name='n').sort_values('n', ascending=False)) if 'Ticket_Status' in ff_drill.columns and 'Action taken' in ff_drill.columns else pd.DataFrame()
            if not abt.empty:
                def bh(status):
                    r2 = abt[abt['Ticket_Status'] == status].head(6)
                    return "<br>".join([f"• {x['Action taken']}: {x['n']}" for _, x in r2.iterrows()]) if not r2.empty else "No actions"
                sc = ff_drill['Ticket_Status'].value_counts().reset_index(); sc.columns = ['Ticket_Status', 'Count']
                sc['ht'] = sc['Ticket_Status'].apply(bh)
                _, pc, _ = st.columns([1, 2, 1])
                with pc:
                    fig_st = px.pie(sc, names='Ticket_Status', values='Count', title="🎫 Live Ticket Status", hole=0.4, color='Ticket_Status', color_discrete_map={"Closed": DS_NAVY, "Open": "#FF4B4B"})
                    fig_st.update_traces(customdata=sc['ht'], hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent:.2%}<br><br><b>Top Actions:</b><br>%{customdata}<extra></extra>", textinfo='percent+label', texttemplate='%{label}: %{percent:.2%}', textfont=dict(family="DM Sans, sans-serif", size=12), marker_line=dict(color="white", width=3), pull=[0.04, 0])
                    fig_st.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title_font=dict(family="Sora, sans-serif", size=14, color="#002147"), hoverlabel=dict(bgcolor="#001e42", font_size=12, font_color="white", bordercolor="#00AEEF"), margin=dict(t=46,b=10,l=10,r=10))
                    pe = st.plotly_chart(fig_st, use_container_width=True, on_select="rerun", selection_mode="points", key=f"pie_st_{drill_tab.replace(' ', '_')}")
                    if pe and pe.selection and pe.selection.get("points"):
                        cs = pe.selection["points"][0].get("label")
                        if cs in ["Open", "Closed"]: st.session_state.click_filter_col = "Ticket_Status"; st.session_state.click_filter_val = cs; st.rerun()

            st.divider()
        else:
            drill_d = "All Data"
            ff_drill = data_df.copy()
        if client_mode == "client":
            is_vf = st.session_state.get("is_vodafone")
            ca, cb = st.columns(2)
            with ca:
                if 'Merchant' in ff_drill.columns:
                    m_agg = clean_st(ff_drill, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not m_agg.empty and 'Call Microtype' in ff_drill.columns:
                        m_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Merchant'] == m].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for m in m_agg['Merchant']]
                        ms(m_agg, 'Merchant', 'c', "🏪 Top Merchant", DS_NAVY, 'Merchant', f"bar_m_{drill_tab.replace(' ', '_')}", cd=m_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
            with cb:
                if 'District' in ff_drill.columns:
                    di_agg = clean_st(ff_drill, 'District').groupby('District').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not di_agg.empty:
                        if 'Merchant' in ff_drill.columns:
                            di_h = ["<br>".join([f"• {r['Merchant']}: {r['n']}" for _, r in ff_drill[ff_drill['District'] == d].groupby('Merchant').size().reset_index(name='n').sort_values('n', ascending=False).head(6).iterrows()]) for d in di_agg['District']]
                            ms(di_agg, 'District', 'c', "📍 Top 10 Branches", DS_LIGHT, 'District', f"bar_di_{drill_tab.replace(' ', '_')}", cd=di_h, ht="Total: %{y}<br><b>Top Merchants:</b><br>%{customdata}<extra></extra>")
                        else:
                            ms(di_agg, 'District', 'c', "📍 Top 10 Branches", DS_LIGHT, 'District', f"bar_di_{drill_tab.replace(' ', '_')}")
            if is_vf and 'Project' in ff_drill.columns:
                cc, cd = st.columns(2)
                with cc:
                    p_agg = clean_st(ff_drill, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not p_agg.empty and 'Call Microtype' in ff_drill.columns:
                        p_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Project'] == p].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for p in p_agg['Project']]
                        ms(p_agg, 'Project', 'c', "🏢 Top Projects", DS_NAVY, 'Project', f"bar_p_{drill_tab.replace(' ', '_')}", cd=p_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with cd:
                    if 'Ticket type' in ff_drill.columns:
                        tt_df = clean_st(ff_drill, 'Ticket type')
                        if not tt_df.empty:
                            fig4 = _style_pie(px.pie(tt_df, names='Ticket type', title="🎫 Ticket Type", hole=0.3))
                            st.plotly_chart(fig4, use_container_width=True)
                ce, cf = st.columns(2)
                with ce:
                    if 'Ticket subtype' in ff_drill.columns:
                        su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not su_agg.empty and 'Ticket type' in ff_drill.columns:
                            su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype'] == s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
                            ms(su_agg, 'Ticket subtype', 'c', "🏷️ Top Subtypes", DS_NAVY, 'Ticket subtype', f"bar_su_{drill_tab.replace(' ', '_')}", cd=su_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with cf:
                    if 'Call Microtype' in ff_drill.columns:
                        mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not mi_agg.empty and 'Ticket subtype' in ff_drill.columns:
                            mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype'] == m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
                            ms(mi_agg, 'Call Microtype', 'c', "🔬 Top Microtypes", DS_LIGHT, 'Call Microtype', f"bar_mi_{drill_tab.replace(' ', '_')}", cd=mi_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                cg_ = st.columns(1)
                with cg_[0]:
                    if 'Action taken' in ff_drill.columns:
                        act_df = clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10).reset_index()
                        act_df.columns = ['Action taken', 'Count']
                        ms(act_df, 'Action taken', 'Count', "🎬 Action Taken", DS_NAVY, 'Action taken', f"bar_act_{drill_tab.replace(' ', '_')}")
            else:
                cc, cd = st.columns(2)
                with cc:
                    if 'Ticket type' in ff_drill.columns:
                        tt_df = clean_st(ff_drill, 'Ticket type')
                        if not tt_df.empty:
                            fig4 = _style_pie(px.pie(tt_df, names='Ticket type', title="🎫 Ticket Type", hole=0.3))
                            st.plotly_chart(fig4, use_container_width=True)
                with cd:
                    if 'Ticket subtype' in ff_drill.columns:
                        su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not su_agg.empty and 'Ticket type' in ff_drill.columns:
                            su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype'] == s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
                            ms(su_agg, 'Ticket subtype', 'c', "🏷️ Top Subtypes", DS_NAVY, 'Ticket subtype', f"bar_su_{drill_tab.replace(' ', '_')}", cd=su_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                ce, cf = st.columns(2)
                with ce:
                    if 'Call Microtype' in ff_drill.columns:
                        mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not mi_agg.empty and 'Ticket subtype' in ff_drill.columns:
                            mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype'] == m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
                            ms(mi_agg, 'Call Microtype', 'c', "🔬 Top Microtypes", DS_LIGHT, 'Call Microtype', f"bar_mi_{drill_tab.replace(' ', '_')}", cd=mi_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with cf:
                    if 'Action taken' in ff_drill.columns:
                        act_df = clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10).reset_index()
                        act_df.columns = ['Action taken', 'Count']
                        ms(act_df, 'Action taken', 'Count', "🎬 Action Taken", DS_NAVY, 'Action taken', f"bar_act_{drill_tab.replace(' ', '_')}")
        elif client_mode:
            c1, c2 = st.columns(2)
            with c1:
                if 'Merchant' in ff_drill.columns:
                    m_agg = clean_st(ff_drill, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not m_agg.empty and 'Call Microtype' in ff_drill.columns:
                        m_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Merchant'] == m].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for m in m_agg['Merchant']]
                        ms(m_agg, 'Merchant', 'c', "🏪 1. Top 10 Merchants — click to filter", DS_NAVY, 'Merchant', f"bar_m_{drill_tab.replace(' ', '_')}", cd=m_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
            with c2:
                if 'District' in ff_drill.columns:
                    br_agg = clean_st(ff_drill, 'District').groupby('District').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not br_agg.empty:
                        if 'Merchant' in ff_drill.columns:
                            br_h = ["<br>".join([f"• {r['Merchant']}: {r['n']}" for _, r in ff_drill[ff_drill['District'] == b].groupby('Merchant').size().reset_index(name='n').sort_values('n', ascending=False).head(6).iterrows()]) for b in br_agg['District']]
                        elif 'Call Microtype' in ff_drill.columns:
                            br_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['District'] == b].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for b in br_agg['District']]
                        else:
                            br_h = ["" for _ in br_agg['District']]
                        ms(br_agg, 'District', 'c', "📍 2. Top 10 Branches — click to filter", DS_LIGHT, 'District', f"bar_br_{drill_tab.replace(' ', '_')}", cd=br_h, ht="Total: %{y}<br><b>Top Merchants:</b><br>%{customdata}<extra></extra>")
            is_vf = st.session_state.get("is_vodafone")
            if is_vf and 'Project' in ff_drill.columns:
                c3, c4 = st.columns(2)
                with c3:
                    p_agg = clean_st(ff_drill, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not p_agg.empty and 'Call Microtype' in ff_drill.columns:
                        p_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Project'] == p].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for p in p_agg['Project']]
                        ms(p_agg, 'Project', 'c', "🏢 3. Top 10 Projects — click to filter", DS_NAVY, 'Project', f"bar_p_{drill_tab.replace(' ', '_')}", cd=p_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with c4:
                    if 'Ticket type' in ff_drill.columns:
                        tt_df = clean_st(ff_drill, 'Ticket type')
                        if not tt_df.empty:
                            fig4 = _style_pie(px.pie(tt_df, names='Ticket type', title="🎫 4. Ticket Type Share", hole=0.3))
                            st.plotly_chart(fig4, use_container_width=True)
                c5, c6 = st.columns(2)
                with c5:
                    if 'Ticket subtype' in ff_drill.columns:
                        su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not su_agg.empty and 'Ticket type' in ff_drill.columns:
                            su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype'] == s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
                            ms(su_agg, 'Ticket subtype', 'c', "🏷️ 5. Top 10 Subtypes — click to filter", DS_NAVY, 'Ticket subtype', f"bar_su_{drill_tab.replace(' ', '_')}", cd=su_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with c6:
                    if 'Call Microtype' in ff_drill.columns:
                        mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not mi_agg.empty and 'Ticket subtype' in ff_drill.columns:
                            mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype'] == m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
                            ms(mi_agg, 'Call Microtype', 'c', "🔬 6. Top 10 Microtypes — click to filter", DS_LIGHT, 'Call Microtype', f"bar_mi_{drill_tab.replace(' ', '_')}", cd=mi_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                c7_ = st.columns(1)
                with c7_[0]:
                    if 'Action taken' in ff_drill.columns:
                        act_df = clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10).reset_index()
                        act_df.columns = ['Action taken', 'Count']
                        ms(act_df, 'Action taken', 'Count', "🎬 7. Key Actions Taken — click to filter", DS_NAVY, 'Action taken', f"bar_act_{drill_tab.replace(' ', '_')}")
            else:
                c3, c4 = st.columns(2)
                with c3:
                    if 'Project' in ff_drill.columns:
                        p_agg = clean_st(ff_drill, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not p_agg.empty and 'Call Microtype' in ff_drill.columns:
                            p_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Project'] == p].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for p in p_agg['Project']]
                            ms(p_agg, 'Project', 'c', "🏢 3. Top 10 Projects — click to filter", DS_NAVY, 'Project', f"bar_p_{drill_tab.replace(' ', '_')}", cd=p_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with c4:
                    if 'Ticket type' in ff_drill.columns:
                        tt_df = clean_st(ff_drill, 'Ticket type')
                        if not tt_df.empty:
                            fig4 = _style_pie(px.pie(tt_df, names='Ticket type', title="🎫 4. Ticket Type Share", hole=0.3))
                            st.plotly_chart(fig4, use_container_width=True)
                c5, c6 = st.columns(2)
                with c5:
                    if 'Ticket subtype' in ff_drill.columns:
                        su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not su_agg.empty and 'Ticket type' in ff_drill.columns:
                            su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype'] == s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
                            ms(su_agg, 'Ticket subtype', 'c', "🏷️ 5. Top 10 Subtypes — click to filter", DS_NAVY, 'Ticket subtype', f"bar_su_{drill_tab.replace(' ', '_')}", cd=su_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                with c6:
                    if 'Call Microtype' in ff_drill.columns:
                        mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                        if not mi_agg.empty and 'Ticket subtype' in ff_drill.columns:
                            mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype'] == m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
                            ms(mi_agg, 'Call Microtype', 'c', "🔬 6. Top 10 Microtypes — click to filter", DS_LIGHT, 'Call Microtype', f"bar_mi_{drill_tab.replace(' ', '_')}", cd=mi_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                c7_ = st.columns(1)
                with c7_[0]:
                    if 'Action taken' in ff_drill.columns:
                        act_df = clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10).reset_index()
                        act_df.columns = ['Action taken', 'Count']
                        ms(act_df, 'Action taken', 'Count', "🎬 7. Key Actions Taken — click to filter", DS_NAVY, 'Action taken', f"bar_act_{drill_tab.replace(' ', '_')}")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if 'Merchant' in ff_drill.columns:
                    m_agg = clean_st(ff_drill, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not m_agg.empty and 'Call Microtype' in ff_drill.columns:
                        m_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Merchant'] == m].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for m in m_agg['Merchant']]
                        ms(m_agg, 'Merchant', 'c', "🏪 1. Top 10 Merchants — click to filter", DS_NAVY, 'Merchant', f"bar_m_{drill_tab.replace(' ', '_')}", cd=m_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                if 'Project' in ff_drill.columns:
                    p_agg = clean_st(ff_drill, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not p_agg.empty and 'Call Microtype' in ff_drill.columns:
                        p_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Project'] == p].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for p in p_agg['Project']]
                        ms(p_agg, 'Project', 'c', "🏢 3. Top 10 Projects — click to filter", DS_NAVY, 'Project', f"bar_p_{drill_tab.replace(' ', '_')}", cd=p_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                if 'Ticket subtype' in ff_drill.columns:
                    su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not su_agg.empty and 'Ticket type' in ff_drill.columns:
                        su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype'] == s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
                        ms(su_agg, 'Ticket subtype', 'c', "🏷️ 5. Top 10 Subtypes — click to filter", DS_NAVY, 'Ticket subtype', f"bar_su_{drill_tab.replace(' ', '_')}", cd=su_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
            with c2:
                if show_branches and 'Branch User Name' in ff_drill.columns:
                    br_agg = clean_st(ff_drill, 'Branch User Name').groupby('Branch User Name').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not br_agg.empty and 'Merchant' in ff_drill.columns:
                        br_h = ["<br>".join([f"• {r['Merchant']}: {r['n']}" for _, r in ff_drill[ff_drill['Branch User Name'] == b].groupby('Merchant').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for b in br_agg['Branch User Name']]
                        ms(br_agg, 'Branch User Name', 'c', "📍 2. Top 10 Branches — click to filter", DS_LIGHT, 'Branch User Name', f"bar_br_{drill_tab.replace(' ', '_')}", cd=br_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")
                if 'Ticket type' in ff_drill.columns:
                    tt_df = clean_st(ff_drill, 'Ticket type')
                    if not tt_df.empty:
                        fig4 = _style_pie(px.pie(tt_df, names='Ticket type', title="🎫 4. Ticket Type Share", hole=0.3))
                        st.plotly_chart(fig4, use_container_width=True)
                if 'Call Microtype' in ff_drill.columns:
                    mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not mi_agg.empty and 'Ticket subtype' in ff_drill.columns:
                        mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype'] == m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
                        ms(mi_agg, 'Call Microtype', 'c', "🔬 6. Top 10 Microtypes — click to filter", DS_LIGHT, 'Call Microtype', f"bar_mi_{drill_tab.replace(' ', '_')}", cd=mi_h, ht="Total: %{y}<br><br>%{customdata}<extra></extra>")

        if client_mode is False and 'Action taken' in ff_drill.columns:
            st.divider()
            act_df = clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10).reset_index()
            act_df.columns = ['Action taken', 'Count']
            ms(act_df, 'Action taken', 'Count', "🎬 7. Key Actions Taken — click to filter", DS_NAVY, 'Action taken', f"bar_act_{drill_tab.replace(' ', '_')}")

if st.session_state.get("client_projects"):
    proj_list = st.session_state.client_projects
    proj_data = ff.copy()
    merchant_ids = set(df_merchant['Ticket ID'].astype(str))
    client_ids = set(df_client['Ticket ID'].astype(str))
    proj_merchant = proj_data[proj_data['Ticket ID'].astype(str).isin(merchant_ids)]
    proj_client = proj_data[proj_data['Ticket ID'].astype(str).isin(client_ids)]

    if st.session_state.slideshow_active:
        combined_slides = []
        merchant_slide_count = 0
        unique_proj_count = proj_data['Project'].nunique() if 'Project' in proj_data.columns else 0
        for ddf, pfx in [(proj_merchant, "🏪 Merchant"), (proj_client, "🤝 Client")]:
            if ddf.empty: continue
            start_len = len(combined_slides)
            m_a = clean_st(ddf, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
            if not m_a.empty: combined_slides.append(("🏪 Top Merchant", mksb(m_a, 'Merchant', 'c', "🏪 Top Merchant", DS_NAVY)))
            br_a = clean_st(ddf, 'District').groupby('District').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'District' in ddf.columns else pd.DataFrame()
            if not br_a.empty: combined_slides.append(("📍 Top Branches", mksb(br_a, 'District', 'c', "📍 Top Branches", DS_LIGHT)))
            if unique_proj_count > 1:
                p_a = clean_st(ddf, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Project' in ddf.columns else pd.DataFrame()
                if not p_a.empty: combined_slides.append(("🏢 Top Projects", mksb(p_a, 'Project', 'c', "🏢 Top Projects", DS_NAVY)))
            tt_a = clean_st(ddf, 'Ticket type')
            if not tt_a.empty:
                fp = px.pie(tt_a, names='Ticket type', title="🎫 Ticket Type", hole=0.3)
                fp = _style_pie(fp)
                combined_slides.append(("🎫 Ticket Type", fp))
            su_a = clean_st(ddf, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Ticket subtype' in ddf.columns else pd.DataFrame()
            if not su_a.empty: combined_slides.append(("🏷️ Top Subtypes", mksb(su_a, 'Ticket subtype', 'c', "🏷️ Top Subtypes", DS_NAVY)))
            mi_a = clean_st(ddf, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Call Microtype' in ddf.columns else pd.DataFrame()
            if not mi_a.empty: combined_slides.append(("🔬 Top Microtypes", mksb(mi_a, 'Call Microtype', 'c', "🔬 Top Microtypes", DS_LIGHT)))
            ac_a = clean_st(ddf, 'Action taken')['Action taken'].value_counts().head(10).reset_index() if 'Action taken' in ddf.columns else pd.DataFrame()
            if not ac_a.empty:
                ac_a.columns = ['Action taken', 'Count']
                combined_slides.append(("🎬 Action Taken", mksb(ac_a, 'Action taken', 'Count', "🎬 Action Taken", DS_NAVY)))
            if pfx == "🏪 Merchant":
                merchant_slide_count = len(combined_slides) - start_len
        combined_slides = [(t, f) for t, f in combined_slides if f is not None]
        SLIDE_DUR = 15
        ci = st.session_state.slide_index % len(combined_slides)
        st_title, sf = combined_slides[ci]
        is_merchant_slide = ci < merchant_slide_count
        st.session_state.client_tab_idx = 0 if is_merchant_slide else 1
        tab_labels = ["🏪 Merchant Support", "🤝 Client Support"]
        act_tab = st.session_state.client_tab_idx
        st.markdown(f'<div class="slideshow-banner"><span style="display:flex;gap:10px;align-items:center;justify-content:center;">'
                    f'<span class="slide-tab {"slide-tab-active" if act_tab==0 else ""}">🏪 Merchant</span>'
                    f'<span class="slide-tab {"slide-tab-active" if act_tab==1 else ""}">🤝 Client</span>'
                    f'</span> &nbsp;|&nbsp; {ci+1}/{len(combined_slides)} &nbsp;|&nbsp; {SLIDE_DUR}s</div>', unsafe_allow_html=True)
        _, cc, _ = st.columns([0.5, 9, 0.5])
        with cc: st.plotly_chart(sf, use_container_width=True)
        pb = st.progress(0); sh = st.empty()
        for i in range(SLIDE_DUR):
            if not st.session_state.slideshow_active: break
            pb.progress((i + 1) / SLIDE_DUR)
            sh.markdown(f'<p style="text-align:center;color:gray;font-size:11px;">⏱ {SLIDE_DUR - i - 1}s...</p>', unsafe_allow_html=True)
            time.sleep(1)
        if st.session_state.slideshow_active:
            st.session_state.slide_index = (ci + 1) % len(combined_slides)
            st.rerun()
        st.stop()

    if "client_tab_idx" not in st.session_state:
        st.session_state.client_tab_idx = 0
    ctc1, ctc2 = st.columns(2)
    with ctc1:
        if st.button("🏪 Merchant Support", key="ctab0", use_container_width=True,
                     type="primary" if st.session_state.client_tab_idx == 0 else "secondary"):
            st.session_state.client_tab_idx = 0; st.rerun()
    with ctc2:
        if st.button("🤝 Client Support", key="ctab1", use_container_width=True,
                     type="primary" if st.session_state.client_tab_idx == 1 else "secondary"):
            st.session_state.client_tab_idx = 1; st.rerun()
    if st.session_state.client_tab_idx == 0:
        render_team_overview(proj_merchant, show_branches=False, show_redemption=False, drill_tab="Merchant Support", client_mode="client")
    else:
        render_team_overview(proj_client, show_branches=False, show_redemption=False, drill_tab="Client Support", client_mode="client")
    st.stop()

TAB_EMOJI = {"Overview": "🏠", "Quality Board": "🏆", "WhatsApp MOM": "💬", "Inbound SLA": "📈", "Redemption Tracker": "💰", "Ticket Explorer": "🎫"}
if st.session_state.auth_role == "admin":
    admin_tabs_list = [f"{TAB_EMOJI.get(t,t)} {t}" for t in ["Overview", "Quality Board", "WhatsApp MOM", "Inbound SLA", "Redemption Tracker", "Ticket Explorer"]]
else:
    admin_tabs_list = [f"{TAB_EMOJI.get(t,t)} {t}" for t in ["Overview", "Ticket Explorer"]]

tabs = st.tabs(admin_tabs_list)

def ti(name): return admin_tabs_list.index(f"{TAB_EMOJI.get(name,name)} {name}")

if st.session_state.get("show_access_mgmt") and st.session_state.auth_role == "admin":
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.show_access_mgmt = False
            st.rerun()
    st.markdown("<div class='page-title-header'>🔐 Access Management</div>", unsafe_allow_html=True)
    _acc_cfg = load_access_config()

    with st.expander("➕ Add New Access", expanded=False):
        with st.form("add_access_form", clear_on_submit=True):
            new_pwd = st.text_input("Password", placeholder="e.g. newclient123")
            all_projects = sorted(df_all['Project'].unique()) if 'Project' in df_all.columns else []
            new_projs = st.multiselect("Projects", all_projects)
            new_is_vf = st.checkbox("Vodafone layout (show Projects chart)")
            new_logo = st.file_uploader("Logo (optional)", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("Add Access", use_container_width=True):
                if not new_pwd or not new_projs:
                    st.error("Password and at least one project required")
                else:
                    err = None
                    if new_pwd in PASSWORD_PROJECTS or new_pwd in _acc_cfg:
                        err = "Password already exists!"
                    if not err:
                        new_entry = {"projects": new_projs, "is_vodafone": new_is_vf, "logo": ""}
                        if new_logo:
                            os.makedirs(CUSTOM_LOGO_DIR, exist_ok=True)
                            ext = os.path.splitext(new_logo.name)[1] or ".png"
                            logo_path = os.path.join("custom_logos", f"{new_pwd}{ext}")
                            full_logo_path = os.path.join(BASE_DIR, logo_path)
                            with open(full_logo_path, "wb") as f: f.write(new_logo.getbuffer())
                            new_entry["logo"] = logo_path
                        _acc_cfg[new_pwd] = new_entry
                        save_access_config(_acc_cfg)
                        st.success(f"Access '{new_pwd}' added! Relogin to apply.")
                        if new_logo: st.rerun()
                    else:
                        st.error(err)

    if _acc_cfg:
        st.markdown("### Current Dynamic Accesses")
        rows = []
        for pwd, info in _acc_cfg.items():
            projs = ", ".join(info.get("projects", []))
            vf = "✅" if info.get("is_vodafone") else "—"
            logo = "✅" if info.get("logo") else "—"
            rows.append({"Password": pwd, "Projects": projs, "Vodafone": vf, "Logo": logo, "_pwd": pwd})
        if rows:
            df_disp = pd.DataFrame(rows).drop(columns=["_pwd"])
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
            for r in rows:
                if st.button(f"🗑 Delete {r['_pwd']}", key=f"del_{r['_pwd']}"):
                    _acc_cfg.pop(r['_pwd'], None)
                    save_access_config(_acc_cfg)
                    st.rerun()
    else:
        st.info("No dynamic accesses yet. Add one above.")
    st.stop()

with tabs[ti("Overview")]:
    if st.session_state.auth_role == "admin":
        if st.session_state.slideshow_active:
            merchant_ids = set(df_merchant['Ticket ID'].astype(str))
            client_ids = set(df_client['Ticket ID'].astype(str))
            ov_merchant = ff[ff['Ticket ID'].astype(str).isin(merchant_ids)]
            ov_client = ff[ff['Ticket ID'].astype(str).isin(client_ids)]
            combined_slides_adm = []
            ms_count = 0
            adm_unique_proj = pd.concat([ov_merchant, ov_client])['Project'].nunique() if 'Project' in pd.concat([ov_merchant, ov_client]).columns else 0
            for ddf, pfx in [(ov_merchant, "🏪 Merchant"), (ov_client, "🤝 Client")]:
                if ddf.empty: continue
                start_len = len(combined_slides_adm)
                ds = ddf.groupby('D_Obj').size().reset_index(name='Total')
                ps = ds.nlargest(20, 'Total').sort_values('D_Obj')
                ps['Date_Str'] = ps['D_Obj'].astype(str)
                hp_v = []
                for d in ps['D_Obj']:
                    rows = ddf[ddf['D_Obj']==d].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
                    lines = [f"• {r['Call Microtype']}: {r['n']}" for _, r in rows.iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]
                    hp_v.append("<br>".join(lines))
                fv = px.bar(ps, x='Date_Str', y='Total', title="📊 Volume Trend", color_discrete_sequence=[DS_NAVY], text='Total')
                fv.update_traces(customdata=hp_v, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
                fv.update_layout(xaxis=dict(type='category', showgrid=False, tickangle=-28, tickfont=dict(size=11)), yaxis_title='', bargap=0.22, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans, sans-serif', color='#002147'), yaxis=dict(showgrid=True, gridcolor='rgba(0,33,71,.07)', zeroline=False), margin=dict(t=46,b=8,l=4,r=8), hoverlabel=dict(bgcolor='#001e42', font_size=12, font_color='white', bordercolor='#00AEEF'), title_font=dict(family='Sora, sans-serif', size=14, color='#002147'))
                fv.update_traces(marker_cornerradius=5, marker_line_width=0, textfont=dict(family='Sora, sans-serif', size=11, weight=700))
                combined_slides_adm.append(("📊 Volume Trend", fv))
                m_a = clean_st(ddf, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                if not m_a.empty: combined_slides_adm.append(("🏪 Top 10 Merchants", mksb(m_a, 'Merchant', 'c', "🏪 Top 10 Merchants", DS_NAVY)))
                if pfx == "🏪 Merchant":
                    br_a = clean_st(ddf, 'Branch User Name').groupby('Branch User Name').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not br_a.empty: combined_slides_adm.append(("📍 Top 10 Branches", mksb(br_a, 'Branch User Name', 'c', "📍 Top 10 Branches", DS_LIGHT)))
                if adm_unique_proj > 1:
                    p_a = clean_st(ddf, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Project' in ddf.columns else pd.DataFrame()
                    if not p_a.empty: combined_slides_adm.append(("🏢 Top 10 Projects", mksb(p_a, 'Project', 'c', "🏢 Top 10 Projects", DS_NAVY)))
                tt_a = clean_st(ddf, 'Ticket type')
                if not tt_a.empty:
                    fp = px.pie(tt_a, names='Ticket type', title="🎫 Ticket Type Share", hole=0.3)
                    fp = _style_pie(fp)
                    combined_slides_adm.append(("🎫 Ticket Type Share", fp))
                su_a = clean_st(ddf, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Ticket subtype' in ddf.columns else pd.DataFrame()
                if not su_a.empty: combined_slides_adm.append(("🏷️ Top 10 Subtypes", mksb(su_a, 'Ticket subtype', 'c', "🏷️ Top 10 Subtypes", DS_NAVY)))
                mi_a = clean_st(ddf, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Call Microtype' in ddf.columns else pd.DataFrame()
                if not mi_a.empty: combined_slides_adm.append(("🔬 Top 10 Microtypes", mksb(mi_a, 'Call Microtype', 'c', "🔬 Top 10 Microtypes", DS_LIGHT)))
                ac_a = clean_st(ddf, 'Action taken')['Action taken'].value_counts().head(10).reset_index() if 'Action taken' in ddf.columns else pd.DataFrame()
                if not ac_a.empty:
                    ac_a.columns = ['Action taken', 'Count']
                    combined_slides_adm.append(("🎬 Key Actions Taken", mksb(ac_a, 'Action taken', 'Count', "🎬 Key Actions Taken", DS_NAVY)))
                abt_s = (ddf[~ddf['Action taken'].astype(str).str.lower().isin([x.lower() for x in BLACK_LIST])].groupby(['Ticket_Status', 'Action taken']).size().reset_index(name='n').sort_values('n', ascending=False)) if 'Ticket_Status' in ddf.columns and 'Action taken' in ddf.columns else pd.DataFrame()
                if not abt_s.empty:
                    def bhs_s(s): r2 = abt_s[abt_s['Ticket_Status'] == s].head(6); return "<br>".join([f"• {x['Action taken']}: {x['n']}" for _, x in r2.iterrows()]) if not r2.empty else "No actions"
                    sc_s = ddf['Ticket_Status'].value_counts().reset_index(); sc_s.columns = ['Ticket_Status', 'Count']
                    sc_s['h'] = sc_s['Ticket_Status'].apply(bhs_s)
                    fig_st_s = px.pie(sc_s, names='Ticket_Status', values='Count', title="🎫 Live Ticket Status", hole=0.4, color='Ticket_Status', color_discrete_map={"Closed": DS_NAVY, "Open": "#FF4B4B"})
                    fig_st_s.update_traces(customdata=sc_s['h'], hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent:.2%}<br><br><b>Top Actions:</b><br>%{customdata}<extra></extra>", textinfo='percent+label', texttemplate='%{label}: %{percent:.2%}', textfont=dict(family="DM Sans, sans-serif", size=12), marker=dict(line=dict(color="white", width=3)), pull=[0.04, 0])
                    fig_st_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title_font=dict(family="Sora, sans-serif", size=14, color="#002147"), hoverlabel=dict(bgcolor="#001e42", font_size=12, font_color="white", bordercolor="#00AEEF"), margin=dict(t=46,b=10,l=10,r=10))
                    combined_slides_adm.append(("🎫 Live Ticket Status", fig_st_s))
                if pfx == "🏪 Merchant":
                    ms_count = len(combined_slides_adm) - start_len
            combined_slides_adm = [(t, f) for t, f in combined_slides_adm if f is not None]
            if combined_slides_adm:
                SLIDE_DUR = 15
                ci = st.session_state.slide_index % len(combined_slides_adm)
                st_title, sf = combined_slides_adm[ci]
                is_merchant = ci < ms_count
                st.session_state.client_tab_idx = 0 if is_merchant else 1
                act_tab = st.session_state.client_tab_idx
                st.markdown(f'<div class="slideshow-banner"><span style="display:flex;gap:10px;align-items:center;justify-content:center;">'
                            f'<span class="slide-tab {"slide-tab-active" if act_tab==0 else ""}">🏪 Merchant</span>'
                            f'<span class="slide-tab {"slide-tab-active" if act_tab==1 else ""}">🤝 Client</span>'
                            f'</span> &nbsp;|&nbsp; {ci+1}/{len(combined_slides_adm)} &nbsp;|&nbsp; {SLIDE_DUR}s</div>', unsafe_allow_html=True)
                _, cc, _ = st.columns([0.5, 9, 0.5])
                with cc: st.plotly_chart(sf, use_container_width=True)
                pb = st.progress(0); sh = st.empty()
                for i in range(SLIDE_DUR):
                    if not st.session_state.slideshow_active: break
                    pb.progress((i+1)/SLIDE_DUR)
                    sh.markdown(f'<p style="text-align:center;color:gray;font-size:11px;">⏱ {SLIDE_DUR-i-1}s...</p>', unsafe_allow_html=True)
                    time.sleep(1)
                if st.session_state.slideshow_active:
                    st.session_state.slide_index = (ci+1) % len(combined_slides_adm)
                    st.rerun()
            st.stop()
        ov_tabs = st.tabs(["🏪 Merchant Support", "🤝 Client Support"])
        with ov_tabs[0]:
            merchant_ids = set(df_merchant['Ticket ID'].astype(str))
            ff_merchant = ff[ff['Ticket ID'].astype(str).isin(merchant_ids)]
            render_team_overview(ff_merchant, show_branches=True, show_redemption=True, drill_tab="Merchant Support")
        with ov_tabs[1]:
            client_ids = set(df_client['Ticket ID'].astype(str))
            ff_client = ff[ff['Ticket ID'].astype(str).isin(client_ids)]
            render_team_overview(ff_client, show_branches=False, show_redemption=False, drill_tab="Client Support", client_mode=True)
    else:
        if st.session_state.slideshow_active:
            merchant_ids = set(df_merchant['Ticket ID'].astype(str))
            client_ids = set(df_client['Ticket ID'].astype(str))
            ov_merchant = ff[ff['Ticket ID'].astype(str).isin(merchant_ids)]
            ov_client = ff[ff['Ticket ID'].astype(str).isin(client_ids)]
            combined_slides_adm = []
            ms_count = 0
            adm_unique_proj = pd.concat([ov_merchant, ov_client])['Project'].nunique() if 'Project' in pd.concat([ov_merchant, ov_client]).columns else 0
            for ddf, pfx in [(ov_merchant, "🏪 Merchant"), (ov_client, "🤝 Client")]:
                if ddf.empty: continue
                start_len = len(combined_slides_adm)
                ds = ddf.groupby('D_Obj').size().reset_index(name='Total')
                ps = ds.nlargest(20, 'Total').sort_values('D_Obj')
                ps['Date_Str'] = ps['D_Obj'].astype(str)
                hp_v = []
                for d in ps['D_Obj']:
                    rows = ddf[ddf['D_Obj']==d].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5)
                    lines = [f"• {r['Call Microtype']}: {r['n']}" for _, r in rows.iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]
                    hp_v.append("<br>".join(lines))
                fv = px.bar(ps, x='Date_Str', y='Total', title="📊 Volume Trend", color_discrete_sequence=[DS_NAVY], text='Total')
                fv.update_traces(customdata=hp_v, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
                fv.update_layout(xaxis=dict(type='category', showgrid=False, tickangle=-28, tickfont=dict(size=11)), yaxis_title='', bargap=0.22, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='DM Sans, sans-serif', color='#002147'), yaxis=dict(showgrid=True, gridcolor='rgba(0,33,71,.07)', zeroline=False), margin=dict(t=46,b=8,l=4,r=8), hoverlabel=dict(bgcolor='#001e42', font_size=12, font_color='white', bordercolor='#00AEEF'), title_font=dict(family='Sora, sans-serif', size=14, color='#002147'))
                fv.update_traces(marker_cornerradius=5, marker_line_width=0, textfont=dict(family='Sora, sans-serif', size=11, weight=700))
                combined_slides_adm.append(("📊 Volume Trend", fv))
                m_a = clean_st(ddf, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                if not m_a.empty: combined_slides_adm.append(("🏪 Top 10 Merchants", mksb(m_a, 'Merchant', 'c', "🏪 Top 10 Merchants", DS_NAVY)))
                if pfx == "🏪 Merchant":
                    br_a = clean_st(ddf, 'Branch User Name').groupby('Branch User Name').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
                    if not br_a.empty: combined_slides_adm.append(("📍 Top 10 Branches", mksb(br_a, 'Branch User Name', 'c', "📍 Top 10 Branches", DS_LIGHT)))
                if adm_unique_proj > 1:
                    p_a = clean_st(ddf, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Project' in ddf.columns else pd.DataFrame()
                    if not p_a.empty: combined_slides_adm.append(("🏢 Top 10 Projects", mksb(p_a, 'Project', 'c', "🏢 Top 10 Projects", DS_NAVY)))
                tt_a = clean_st(ddf, 'Ticket type')
                if not tt_a.empty:
                    fp = px.pie(tt_a, names='Ticket type', title="🎫 Ticket Type Share", hole=0.3)
                    fp = _style_pie(fp)
                    combined_slides_adm.append(("🎫 Ticket Type Share", fp))
                su_a = clean_st(ddf, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Ticket subtype' in ddf.columns else pd.DataFrame()
                if not su_a.empty: combined_slides_adm.append(("🏷️ Top 10 Subtypes", mksb(su_a, 'Ticket subtype', 'c', "🏷️ Top 10 Subtypes", DS_NAVY)))
                mi_a = clean_st(ddf, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10) if 'Call Microtype' in ddf.columns else pd.DataFrame()
                if not mi_a.empty: combined_slides_adm.append(("🔬 Top 10 Microtypes", mksb(mi_a, 'Call Microtype', 'c', "🔬 Top 10 Microtypes", DS_LIGHT)))
                ac_a = clean_st(ddf, 'Action taken')['Action taken'].value_counts().head(10).reset_index() if 'Action taken' in ddf.columns else pd.DataFrame()
                if not ac_a.empty:
                    ac_a.columns = ['Action taken', 'Count']
                    combined_slides_adm.append(("🎬 Key Actions Taken", mksb(ac_a, 'Action taken', 'Count', "🎬 Key Actions Taken", DS_NAVY)))
                abt_s = (ddf[~ddf['Action taken'].astype(str).str.lower().isin([x.lower() for x in BLACK_LIST])].groupby(['Ticket_Status', 'Action taken']).size().reset_index(name='n').sort_values('n', ascending=False)) if 'Ticket_Status' in ddf.columns and 'Action taken' in ddf.columns else pd.DataFrame()
                if not abt_s.empty:
                    def bhs_s(s): r2 = abt_s[abt_s['Ticket_Status'] == s].head(6); return "<br>".join([f"• {x['Action taken']}: {x['n']}" for _, x in r2.iterrows()]) if not r2.empty else "No actions"
                    sc_s = ddf['Ticket_Status'].value_counts().reset_index(); sc_s.columns = ['Ticket_Status', 'Count']
                    sc_s['h'] = sc_s['Ticket_Status'].apply(bhs_s)
                    fig_st_s = px.pie(sc_s, names='Ticket_Status', values='Count', title="🎫 Live Ticket Status", hole=0.4, color='Ticket_Status', color_discrete_map={"Closed": DS_NAVY, "Open": "#FF4B4B"})
                    fig_st_s.update_traces(customdata=sc_s['h'], hovertemplate="<b>%{label}</b><br>%{value}<br>%{percent:.2%}<br><br><b>Top Actions:</b><br>%{customdata}<extra></extra>", textinfo='percent+label', texttemplate='%{label}: %{percent:.2%}', textfont=dict(family="DM Sans, sans-serif", size=12), marker=dict(line=dict(color="white", width=3)), pull=[0.04, 0])
                    fig_st_s.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title_font=dict(family="Sora, sans-serif", size=14, color="#002147"), hoverlabel=dict(bgcolor="#001e42", font_size=12, font_color="white", bordercolor="#00AEEF"), margin=dict(t=46,b=10,l=10,r=10))
                    combined_slides_adm.append(("🎫 Live Ticket Status", fig_st_s))
                if pfx == "🏪 Merchant":
                    ms_count = len(combined_slides_adm) - start_len
            combined_slides_adm = [(t, f) for t, f in combined_slides_adm if f is not None]
            if combined_slides_adm:
                SLIDE_DUR = 15
                ci = st.session_state.slide_index % len(combined_slides_adm)
                st_title, sf = combined_slides_adm[ci]
                is_merchant = ci < ms_count
                st.session_state.client_tab_idx = 0 if is_merchant else 1
                act_tab = st.session_state.client_tab_idx
                st.markdown(f'<div class="slideshow-banner"><span style="display:flex;gap:10px;align-items:center;justify-content:center;">'
                            f'<span class="slide-tab {"slide-tab-active" if act_tab==0 else ""}">🏪 Merchant</span>'
                            f'<span class="slide-tab {"slide-tab-active" if act_tab==1 else ""}">🤝 Client</span>'
                            f'</span> &nbsp;|&nbsp; {ci+1}/{len(combined_slides_adm)} &nbsp;|&nbsp; {SLIDE_DUR}s</div>', unsafe_allow_html=True)
                _, cc, _ = st.columns([0.5, 9, 0.5])
                with cc: st.plotly_chart(sf, use_container_width=True)
                pb = st.progress(0); sh = st.empty()
                for i in range(SLIDE_DUR):
                    if not st.session_state.slideshow_active: break
                    pb.progress((i+1)/SLIDE_DUR)
                    sh.markdown(f'<p style="text-align:center;color:gray;font-size:11px;">⏱ {SLIDE_DUR-i-1}s...</p>', unsafe_allow_html=True)
                    time.sleep(1)
                if st.session_state.slideshow_active:
                    st.session_state.slide_index = (ci+1) % len(combined_slides_adm)
                    st.rerun()
            st.stop()
        ov_tabs = st.tabs(["🏪 Merchant Support", "🤝 Client Support"])
        with ov_tabs[0]:
            merchant_ids = set(df_merchant['Ticket ID'].astype(str))
            ff_merchant = ff[ff['Ticket ID'].astype(str).isin(merchant_ids)]
            render_team_overview(ff_merchant, show_branches=True, show_redemption=True, drill_tab="Merchant Support")
        with ov_tabs[1]:
            client_ids = set(df_client['Ticket ID'].astype(str))
            ff_client = ff[ff['Ticket ID'].astype(str).isin(client_ids)]
            render_team_overview(ff_client, show_branches=False, show_redemption=False, drill_tab="Client Support", client_mode=True)

if st.session_state.auth_role == "admin":
    with tabs[ti("Quality Board")]:
        st.markdown("<div class='page-title-header'>🏆 Agent Quality Board</div>", unsafe_allow_html=True)
        if df_agent is not None and not df_agent.empty:
            ec_vals = to_n(df_agent['EC%']) if 'EC%' in df_agent.columns else pd.Series(dtype=float)
            bc_vals = to_n(df_agent['BC%']) if 'BC%' in df_agent.columns else pd.Series(dtype=float)
            avg_ec = f"{ec_vals.mean():.1f}%" if not ec_vals.empty else "N/A"
            avg_bc = f"{bc_vals.mean():.1f}%" if not bc_vals.empty else "N/A"
            total_vol = len(df_agent)
            if 'Queue' in df_agent.columns:
                wa_vol = len(df_agent[df_agent['Queue'].str.contains('WhatsApp', case=False, na=False)])
                call_vol = len(df_agent[df_agent['Queue'].str.contains('Call', case=False, na=False)])
            else: wa_vol = call_vol = 0
            st.markdown(f'''<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px;">
                <div class="mcard" style="--c:{DS_NAVY};"><div class="ml">Avg EC%</div><div class="mv">{avg_ec}</div></div>
                <div class="mcard" style="--c:{DS_BLUE};"><div class="ml">Avg BC%</div><div class="mv">{avg_bc}</div></div>
                <div class="mcard" style="--c:{DS_LIGHT};"><div class="ml">Total Volume</div><div class="mv">{total_vol:,}</div></div>
                <div class="mcard" style="--c:#00c06a;"><div class="ml">WA / Calls</div><div class="mv" style="font-size:18px;">{wa_vol} / {call_vol}</div></div>
            </div>''', unsafe_allow_html=True)
            agent_cols = df_agent.columns.tolist()
            name_col = agent_cols[0]
            ec_col = 'EC%' if 'EC%' in agent_cols else next((c for c in agent_cols if c.upper() == 'EC'), None)
            bc_col = 'BC%' if 'BC%' in agent_cols else next((c for c in agent_cols if c.upper() == 'BC'), None)
            if ec_col and bc_col:
                cq = df_agent.copy()
                cq['EC_num'] = to_n(cq[ec_col]); cq['BC_num'] = to_n(cq[bc_col])
                cq_agg = cq.groupby(name_col, as_index=False)[['EC_num', 'BC_num']].mean()
                melt_vars, melt_labels = ['EC_num', 'BC_num'], {'EC_num': 'EC%', 'BC_num': 'BC%'}
                dp = cq_agg.melt(id_vars=[name_col], value_vars=melt_vars, var_name='Metric', value_name='Score')
                dp['Metric'] = dp['Metric'].map(melt_labels)
                fq = px.bar(dp, x=name_col, y='Score', color='Metric', barmode='group', text='Score',
                            color_discrete_sequence=[DS_NAVY, DS_LIGHT],
                            labels={'Score': 'Score %', name_col: ''})
                fq.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fq.update_layout(xaxis_type='category', bargap=0.15, bargroupgap=0.05, yaxis_range=[0, 115], yaxis_title="Score %")
                st.plotly_chart(fq, use_container_width=True)
        else:
            st.warning("No agent performance data available")

        st.divider()
        st.markdown("#### 📊 Error Analysis")
        if _agent_summary_rows:
            st.markdown("##### 📋 Agent Summary")
            sdf = pd.DataFrame(_agent_summary_rows)
            sdf.rename(columns={'Agent': '🧑‍💼 Agent', 'Volume': '📊 Volume', 'Avg EC%': '📈 Avg EC%', 'Avg BC%': '📉 Avg BC%', 'Overall Avg': '🎯 Overall Avg'}, inplace=True)
            st.dataframe(sdf.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
            st.divider()
        ec, bc, nc = st.columns(3)
        for etype, col_obj in [("EC", ec), ("BC", bc), ("NC", nc)]:
            with col_obj:
                st.markdown(f"**📈 Top {etype} Errors**")
                if _top_errors.get(etype):
                    edf = pd.DataFrame(_top_errors[etype])
                    edf.rename(columns={'Error': '❌ Error', 'Count': '🔢 Count'}, inplace=True)
                    st.dataframe(edf.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
                else: st.info(f"No {etype} errors found")
        if _per_agent_errors:
            st.divider()
            st.markdown("##### 👤 Per-Agent Error Breakdown")
            pdf = pd.DataFrame(_per_agent_errors)
            pdf = pdf[pdf['Type'].isin(['EC', 'BC', 'NC'])]
            pdf.rename(columns={'Agent': '🧑‍💼 Agent', 'Type': '📂 Type', 'Error': '❌ Error', 'Count': '🔢 Count'}, inplace=True)
            agent_filter = st.selectbox("👤 Filter by Agent", ["All"] + sorted(pdf['🧑‍💼 Agent'].unique()), key="qe_agent")
            type_filter = st.selectbox("🏷️ Filter by Error Type", ["All", "EC", "BC", "NC"], key="qe_type")
            fpdf = pdf.copy()
            if agent_filter != "All": fpdf = fpdf[fpdf['🧑‍💼 Agent'] == agent_filter]
            if type_filter != "All": fpdf = fpdf[fpdf['📂 Type'] == type_filter]
            st.dataframe(fpdf.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)

    with tabs[ti("WhatsApp MOM")]:
        st.markdown("<div class='page-title-header'>💬 WhatsApp MOM SLA Analysis</div>", unsafe_allow_html=True)
        wa_df = df_merchant[df_merchant['WhatsApp SLA Status'].astype(str).str.strip() != ""].copy() if 'df_merchant' in dir() and df_merchant is not None and 'WhatsApp SLA Status' in df_merchant.columns else pd.DataFrame()
        if wa_df.empty:
            st.warning("No WhatsApp SLA data available")
        else:
            sla_col = 'WhatsApp SLA Status'
            ot_t = len(wa_df[wa_df[sla_col].astype(str).str.contains('On-Time|On Time', case=False, na=False)])
            lt_t = len(wa_df[wa_df[sla_col].astype(str).str.contains('Late', case=False, na=False)])
            ov_p = (ot_t / len(wa_df) * 100) if len(wa_df) > 0 else 0
            asym = ""; acol = "#00873d"; tico = "Achieved"; tcol = "#00873d"
            if ov_p >= 95: asym = "▲"; acol = "#00873d"; tico = "Achieved"; tcol = "#00873d"
            else: asym = "▼"; acol = "#CC0000"; tico = "Below Target"; tcol = "#CC0000"
            st.markdown(f'''<div class="overall-card" style="text-align:center;">
                <p style="margin:0 0 4px;font-weight:900;color:{DS_NAVY};font-size:14px;letter-spacing:1px;font-family:Sora,sans-serif;">💬 OVERALL ON-TIME RESPONSE</p>
                <p style="color:{DS_LIGHT};font-size:46px;font-weight:900;margin:2px 0 6px;font-family:Sora,sans-serif;">{ov_p:.1f}%</p>
                <p style="font-weight:800;font-size:16px;margin:0;">
                    <span style="color:{acol};font-size:20px;">{asym}</span>&nbsp;
                    <span style="color:green;"> Target: 95%</span>&nbsp;—&nbsp;
                    <span style="color:{tcol};">{tico}</span>
                </p></div>''', unsafe_allow_html=True)
            st.divider()
            if 'Month_Name' in wa_df.columns:
                ml = wa_df.sort_values('D_Obj')['Month_Name'].unique()
                cols = st.columns(4)
                for i, m in enumerate(ml):
                    md = wa_df[wa_df['Month_Name'] == m]
                    if sla_col:
                        ot = len(md[md[sla_col].astype(str).str.contains('On-Time|On Time', case=False, na=False)])
                        lt = len(md[md[sla_col].astype(str).str.contains('Late', case=False, na=False)])
                    else:
                        ot, lt = len(md), 0
                    prc = (ot / len(md) * 100) if len(md) > 0 else 0
                    with cols[i % 4]:
                        st.markdown(f'<div class="wa-card"><h5>📅 {m}</h5><div class="perc">{prc:.1f}%</div>'
                                    f'<p style="color:green;font-weight:700;margin:3px 0;">✅ On-Time: {ot}</p>'
                                    f'<p style="color:#CC0000;font-weight:700;margin:3px 0;">❌ Late: {lt}</p></div>', unsafe_allow_html=True)

    with tabs[ti("Inbound SLA")]:
        st.markdown("<div class='page-title-header'>📈 Inbound SLA Performance</div>", unsafe_allow_html=True)
        if df_sla is not None and not df_sla.empty:
            sla_cols = df_sla.columns.tolist()
            pca_col = next((c for c in sla_cols if 'pca' in c.lower() or 'PCA' in c), None)
            if pca_col:
                pca_s = to_n(df_sla[pca_col]); ap = pca_s[pca_s > 0]; opa = ap.mean() if not ap.empty else 0
                ps = "▲"; pc2 = "#00873d"; pt = "Achieved"; ptc = "#00873d"
                if opa < 95: ps = "▼"; pc2 = "#CC0000"; pt = "Below Target"; ptc = "#CC0000"
                st.markdown(f'''<div class="overall-card" style="text-align:center;margin-bottom:20px;">
                    <p style="margin:0 0 8px;font-weight:900;color:{DS_NAVY};font-size:11px;letter-spacing:2px;font-family:Sora,sans-serif;text-transform:uppercase;opacity:.7;">📊 OVERALL PCA% ACHIEVEMENT (AVG)</p>
                    <p style="color:{DS_BLUE};font-size:52px;font-weight:900;margin:2px 0 10px;font-family:Sora,sans-serif;">{opa:.1f}%</p>
                    <p style="font-weight:800;font-size:16px;margin:0;color:{DS_NAVY};">
                        <span style="color:{pc2};font-size:22px;">{ps}</span>&nbsp;
                        Target: 95% &mdash; <span style="color:{ptc};font-weight:900;">{pt}</span>
                    </p></div>''', unsafe_allow_html=True)
                st.divider()
                month_col = next((c for c in sla_cols if 'month' in c.lower() or 'Month' in c), sla_cols[0])
                df_sla[pca_col] = to_n(df_sla[pca_col]).fillna(0).round(1)
                fig_sla = px.bar(df_sla, x=month_col, y=pca_col, title="📊 Monthly PCA% Achievement", color_discrete_sequence=[DS_NAVY], labels={pca_col: 'PCA %', month_col: ''})
                fig_sla.update_traces(text=df_sla[pca_col].apply(lambda v: f'{v:.1f}%'), textposition='outside', hovertemplate='%{x}<br>PCA: <b>%{y:.1f}%</b><extra></extra>', marker_cornerradius=6, marker_line_width=0, textfont=dict(family="Sora, sans-serif", size=12, color="#002147", weight=700))
                fig_sla.update_layout(yaxis_title="PCA %", xaxis_type='category', bargap=0.28, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans, sans-serif", color="#002147"), yaxis=dict(showgrid=True, gridcolor="rgba(0,33,71,.07)"), xaxis=dict(showgrid=False), margin=dict(t=46,b=8,l=4,r=8), hoverlabel=dict(bgcolor="#001e42", font_size=12, font_color="white", bordercolor="#00AEEF"))
                st.plotly_chart(fig_sla, use_container_width=True)
                sla_disp = df_sla.rename(columns={month_col: f'📅 {month_col}', pca_col: f'📊 {pca_col}'})
                sla_disp[f'📊 {pca_col}'] = sla_disp[f'📊 {pca_col}'].round(1)
                st.dataframe(sla_disp.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}).format({f'📊 {pca_col}': '{:.1f}'}), use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_sla.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
        else: st.warning("No SLA data available")

    with tabs[ti("Redemption Tracker")]:
        st.markdown("<div class='page-title-header'>💰 Redemption Tracker</div>", unsafe_allow_html=True)
        if df_red is not None and not df_red.empty:
            total_txn = "N/A"; top_agent = "N/A"; total_val = "N/A"
            red_cols = df_red.columns.tolist()
            if 'Total Transactions' in red_cols:
                try: total_txn = f"{int(pd.to_numeric(df_red['Total Transactions'].astype(str).str.replace(',',''), errors='coerce').iloc[0]):,}"
                except: pass
            if 'Top Agent' in red_cols:
                top_agent = str(df_red['Top Agent'].iloc[0]) if len(df_red) > 0 else "N/A"
            if 'Total Redemption Amount' in red_cols:
                try: total_val = f"{pd.to_numeric(df_red['Total Redemption Amount'].astype(str).str.replace(',','').str.replace('EGP','').str.strip(), errors='coerce').iloc[0]:,.0f}"
                except: pass
            st.markdown(f'''<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px;">
                <div class="mcard" style="--c:{DS_NAVY};"><div class="ml">📋 Total Transactions</div><div class="mv">{total_txn}</div></div>
                <div class="mcard" style="--c:{DS_BLUE};"><div class="ml">🏆 Top Agent</div><div class="mv" style="font-size:20px;">{top_agent}</div></div>
                <div class="mcard" style="--c:{DS_LIGHT};"><div class="ml">💰 Total Redemption Amount</div><div class="mv">{total_val}</div></div>
            </div>''', unsafe_allow_html=True)
            exclude_cols = ['Total Transactions', 'Top Agent', 'Total Redemption Amount']
            detail_cols = [c for c in df_red.columns if c not in exclude_cols]
            red_disp = df_red[detail_cols].copy() if detail_cols else df_red.copy()
            name_map = {}
            for old_c in red_disp.columns:
                cl = old_c.lower()
                if 'agent' in cl: name_map[old_c] = '🧑‍💼 Agent'
                elif 'transaction' in cl and 'count' in cl: name_map[old_c] = '📊 Transaction Count'
                elif 'transaction' in cl: name_map[old_c] = '📊 Transaction Count'
                elif 'redemption' in cl and 'value' in cl: name_map[old_c] = '💰 Total Redemption Value'
                elif 'redemption' in cl: name_map[old_c] = '💰 Total Redemption Value'
            red_disp = red_disp.rename(columns=name_map)
            st.dataframe(red_disp.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
        else: st.warning("No Redemption data available")

with tabs[ti("Ticket Explorer")]:
    if st.session_state.auth_role == "admin":
        exp_tabs = st.tabs(["🏪 Merchant Support", "🤝 Client Support"])
        for ei, (exp_name, exp_df_src) in enumerate([("Merchant Support", df_merchant if 'df_merchant' in dir() else ff), ("Client Support", df_client if 'df_client' in dir() else ff)]):
            with exp_tabs[ei]:
                ff_final = ff.copy()
                if not exp_df_src.empty:
                    ff_final = exp_df_src.copy()
                    if not ff_final.empty and 'D_Obj' in ff_final.columns:
                        dd_key = f"drill_down_date_{exp_name.replace(' ', '_')}"
                        if st.session_state.get(dd_key):
                            ff_final = ff_final[ff_final['D_Obj'].astype(str) == st.session_state[dd_key]]
                        if f_merch and 'Merchant' in ff_final.columns: ff_final = ff_final[ff_final['Merchant'].isin(f_merch)]
                        if f_proj and 'Project' in ff_final.columns: ff_final = ff_final[ff_final['Project'].isin(f_proj)]
                        if f_branch and 'Branch User Name' in ff_final.columns: ff_final = ff_final[ff_final['Branch User Name'].isin(f_branch)]
                        if f_type and 'Ticket type' in ff_final.columns: ff_final = ff_final[ff_final['Ticket type'].isin(f_type)]
                        if f_act and 'Action taken' in ff_final.columns: ff_final = ff_final[ff_final['Action taken'].isin(f_act)]
                        if f_status and 'Ticket_Status' in ff_final.columns: ff_final = ff_final[ff_final['Ticket_Status'].isin(f_status)]
                csv_data = ff_final.drop(columns=['D_Obj', 'Month_Name', 'Month_Num', 'Ticket_Status'], errors='ignore').to_csv(index=False).encode('utf-8')
                srch_col, exp_col = st.columns([4, 1])
                with srch_col:
                    search = st.text_input("Search...", "", key=f"search_{ei}")
                with exp_col:
                    st.download_button("📥 Export CSV", data=csv_data, file_name=f"tickets_{exp_name.lower().replace(' ','_')}.csv", mime="text/csv", use_container_width=True)
                if search:
                    ff_final = ff_final[ff_final.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
                st.dataframe(ff_final.drop(columns=['D_Obj', 'Month_Name', 'Month_Num', 'Ticket_Status'], errors='ignore').style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
    else:
        exp_tabs = st.tabs(["🏪 Merchant Support", "🤝 Client Support"])
        for ei, (exp_name, exp_df_src) in enumerate([("Merchant Support", df_merchant if 'df_merchant' in dir() else ff), ("Client Support", df_client if 'df_client' in dir() else ff)]):
            with exp_tabs[ei]:
                ff_final = ff.copy()
                if not exp_df_src.empty:
                    ff_final = exp_df_src.copy()
                    if not ff_final.empty and 'D_Obj' in ff_final.columns:
                        dd_key = f"drill_down_date_{exp_name.replace(' ', '_')}"
                        if st.session_state.get(dd_key):
                            ff_final = ff_final[ff_final['D_Obj'].astype(str) == st.session_state[dd_key]]
                        if f_merch and 'Merchant' in ff_final.columns: ff_final = ff_final[ff_final['Merchant'].isin(f_merch)]
                        if f_proj and 'Project' in ff_final.columns: ff_final = ff_final[ff_final['Project'].isin(f_proj)]
                        if f_branch and 'Branch User Name' in ff_final.columns: ff_final = ff_final[ff_final['Branch User Name'].isin(f_branch)]
                        if f_type and 'Ticket type' in ff_final.columns: ff_final = ff_final[ff_final['Ticket type'].isin(f_type)]
                        if f_act and 'Action taken' in ff_final.columns: ff_final = ff_final[ff_final['Action taken'].isin(f_act)]
                        if f_status and 'Ticket_Status' in ff_final.columns: ff_final = ff_final[ff_final['Ticket_Status'].isin(f_status)]
                csv_data = ff_final.drop(columns=['D_Obj', 'Month_Name', 'Month_Num', 'Ticket_Status'], errors='ignore').to_csv(index=False).encode('utf-8')
                srch_col, exp_col = st.columns([4, 1])
                with srch_col:
                    search = st.text_input("Search...", "", key=f"search_{ei}")
                with exp_col:
                    st.download_button("📥 Export CSV", data=csv_data, file_name=f"tickets_{exp_name.lower().replace(' ','_')}.csv", mime="text/csv", use_container_width=True)
                if search:
                    ff_final = ff_final[ff_final.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
                st.dataframe(ff_final.drop(columns=['D_Obj', 'Month_Name', 'Month_Num', 'Ticket_Status'], errors='ignore').style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)

ar_interval = st.session_state.auto_refresh_mins
if ar_interval > 0:
    components.html(f"<script>setTimeout(function(){{location.reload();}}, {ar_interval * 60 * 1000});</script>", height=0)