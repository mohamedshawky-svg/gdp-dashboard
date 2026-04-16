import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import base64
import os

# 1. إعداد الصفحة والـ Theme
st.set_page_config(page_title="DSQUARES INSIGHTS HUB", layout="wide")

DS_BLUE = "#0055A4"
DS_LIGHT_BLUE = "#00AEEF"

def get_image_base64(path):
    try:
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        return None
    except: return None

full_logo_64 = get_image_base64("logo_big.png")
icon_inner_64 = get_image_base64("logo_small.png")

# ✅ CSS - التصميم الجديد للكروت (البرواز الكحلي والبروز والخط الواضح)
st.markdown(f"""
    <style>
    /* تنسيق الكروت العامة والـ Metrics */
    [data-testid="stMetric"] {{
        background-color: white !important;
        border-top: 6px solid {DS_BLUE} !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
        padding: 15px !important;
    }}
    
    /* تنسيق كروت الواتساب (المصغرة والمبروزة) */
    .wa-card {{ 
        background-color: white !important; 
        padding: 15px !important; 
        border-radius: 12px !important; 
        border: 1px solid #eee !important;
        border-top: 6px solid {DS_BLUE} !important; 
        box-shadow: 0 12px 24px rgba(0,0,0,0.12) !important; 
        text-align: center;
        margin-bottom: 20px;
    }}
    .wa-card h5 {{ margin-bottom: 5px; color: #444; font-size: 15px; font-weight: bold; }}
    .wa-card h2 {{ margin: 0; color: {DS_BLUE}; font-size: 28px; font-weight: 900; }}
    .wa-card p {{ font-size: 14px; margin-top: 5px; color: #555; font-weight: 600; }}

    .main-title {{ color: {DS_BLUE} !important; font-weight: 900; font-size: 35px !important; text-align: center; }}
    [data-testid="stMetricValue"] {{ font-size: 26px !important; color: {DS_BLUE} !important; font-weight: bold; }}
    [data-testid="stTable"] td, [data-testid="stTable"] th, .stDataFrame div {{ color: {DS_BLUE} !important; }}
    label, p, li {{ color: {DS_BLUE} !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. نظام الدخول والـ Log Out
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.sidebar.title("🔐 Access Control")
    pwd = st.sidebar.text_input("Enter Password", type="password")
    if pwd in ["admin123", "ds2024"]:
        st.session_state.authenticated = True
        st.rerun()
    else:
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            if full_logo_64: st.markdown(f'<div style="text-align:center; margin-top:50px;"><img src="data:image/png;base64,{full_logo_64}" width="400"/></div>', unsafe_allow_html=True)
        st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)
        st.stop()

if st.sidebar.button("🔓 Log Out"):
    st.session_state.authenticated = False
    st.rerun()

# 3. تحميل البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
@st.cache_data(ttl=2)
def load_all_data():
    try:
        f = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407", dtype=str).fillna("N/A")
        s = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0", dtype=str).fillna("0")
        q = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747", dtype=str).fillna("0")
        f = f.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        d_col = next((c for c in f.columns if 'created' in c.lower() or 'date' in c.lower()), f.columns[0])
        f['Full_Date_Obj'] = pd.to_datetime(f[d_col], errors='coerce').dt.date
        f = f.dropna(subset=['Full_Date_Obj'])
        m_map = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
        f['Month_Name'] = pd.to_datetime(f[d_col], errors='coerce').dt.strftime('%b')
        f['Month_Num'] = f['Month_Name'].map(m_map)
        return f, s, q
    except: return None, None, None

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q = load_all_data()

# ✅ تحديث قائمة الـ EXCLUDE لحذف Out of our scope نهائياً
EXCLUDE = ['N/A', 'Dropped Call', 'Call Dropped', 'Dropped call', 'Out Of Our Scope', 'Out Of our scope', 'Out of our scope', 'Other', '0', 'na', 'n/a']

if df_f is not None:
    st.markdown(f'<div class="header-container"><span class="main-title">DSQUARES INSIGHTS HUB</span></div>', unsafe_allow_html=True)
    
    st.sidebar.divider()
    min_d, max_d = min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])
    dr = st.sidebar.date_input("🗓 Select Date Range", [min_d, max_d])
    
    ff = df_f.copy()
    if isinstance(dr, (list, tuple)) and len(dr) == 2:
        ff = ff[(ff['Full_Date_Obj'] >= dr[0]) & (ff['Full_Date_Obj'] <= dr[1])]
    
    # فلترة شاملة للداتا من المستبعدات
    ff = ff[~ff['Merchant'].isin(EXCLUDE)]
    
    # الفلاتر الجانبية
    br_col = next((c for c in ff.columns if 'branch' in c.lower()), "Branch User Name")
    f_merch = st.sidebar.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_branch = st.sidebar.multiselect("📍 Branch", sorted(ff[br_col].unique()))
    
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_branch: ff = ff[ff[br_col].isin(f_branch)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]: # Overview
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        inb_val = int(to_n(ff['Total Inbound']).max()) if 'Total Inbound' in ff.columns else 0
        k2.metric("Total Inbound", f"{inb_val:,}")
        k3.metric("Total WhatsApp", f"{len(ff[ff['Type'].str.contains('App', case=False, na=False)]):,}")
        k4.metric("Avg Quality", "96.6%")
        
        st.divider()
        # Volume Trend
        daily_vol = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        peak_days = daily_vol.nlargest(20, 'Total').sort_values('Full_Date_Obj')
        peak_days['Date_Str'] = peak_days['Full_Date_Obj'].astype(str)
        
        fig_v = px.bar(peak_days, x='Date_Str', y='Total', text_auto=True, title="🗓 Volume Trend (Peak Days)", color_discrete_sequence=[DS_BLUE])
        fig_v.update_xaxes(type='category', title=None)
        st.plotly_chart(fig_v, use_container_width=True)

    with tabs[1]: # WhatsApp MoM
        st.subheader("💬 WhatsApp MoM SLA Analysis")
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        m_list = ff.sort_values('Month_Num')['Month_Name'].unique()
        
        if len(m_list) > 0:
            cols = st.columns(4)
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Name'] == m]
                ot = len(m_data[m_data[wa_col].str.contains('On-Time', na=False, case=False)])
                lt = len(m_data[m_data[wa_col].str.contains('Late', na=False, case=False)])
                perc = (ot / (ot + lt) * 100) if (ot + lt) > 0 else 0
                with cols[i % 4]:
                    st.markdown(f'''
                        <div class="wa-card">
                            <h5>{m}</h5>
                            <h2>{perc:.1f}%</h2>
                            <p>✅ {ot} | ❌ {lt}</p>
                        </div>
                    ''', unsafe_allow_html=True)

    with tabs[3]: # Ticket Explorer
        search = st.text_input("🔍 Search Anything...", "")
        exp_df = ff[ff.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else ff
        st.dataframe(exp_df.style.set_properties(**{'color': DS_BLUE}), use_container_width=True, hide_index=True)
