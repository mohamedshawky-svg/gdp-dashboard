import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import base64
import os

# 1. إعداد الصفحة والـ Theme (السطور كاملة بالتنسيق الأصلي)
st.set_page_config(page_title="DSQUARES INSIGHTS HUB", layout="wide")

DS_BLUE = "#0055A4"
DS_LIGHT_BLUE = "#00AEEF"

def get_image_base64(path):
    try:
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        return None
    except:
        return None

# ✅ الأسماء اللي إنت صلحتا في الـ Codespace
FULL_LOGO = "logo_big.png"    
ICON_INNER = "logo_small.png" 

full_logo_64 = get_image_base64(FULL_LOGO)
icon_inner_64 = get_image_base64(ICON_INNER)

# CSS المطور (🔵 تم إعادة اللون الكحلي Navy للجداول والخطوط)
st.markdown(f"""
    <style>
    span[data-baseweb="tag"] {{
        background-color: {DS_BLUE} !important;
    }}
    .main-title {{ 
        color: {DS_BLUE}; font-weight: 900; font-size: 38px !important; 
        text-align: center; margin: 0; font-family: 'Arial Black', sans-serif;
    }}
    .header-container {{
        display: flex; align-items: center; justify-content: center;
        margin-top: 10px; margin-bottom: 30px; gap: 12px;
    }}
    [data-testid="stMetricValue"] {{ font-size: 30px; color: {DS_BLUE} !important; font-weight: bold; }}
    .stMetric, .wa-card {{
        background-color: white !important; padding: 20px !important; border-radius: 12px !important;
        border: 1px solid #e0e0e0 !important; border-top: 6px solid {DS_BLUE} !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
        text-align: center;
    }}
    /* 🔵 تثبيت اللون الكحلي لكل النصوص والجداول */
    .stDataFrame, div[data-testid="stTable"], [data-testid="stText"], .stMarkdown p {{
        color: {DS_BLUE} !important;
    }}
    .stDataFrame [data-testid="stTable"] td, .stDataFrame [data-testid="stTable"] th {{
        color: {DS_BLUE} !important;
    }}
    [data-testid="stElementToolbar"] {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

# 2. تحميل البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
URL_F = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407"
URL_S = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0"
URL_Q = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747"

@st.cache_data(ttl=2)
def load_all_data():
    try:
        f = pd.read_csv(URL_F, dtype=str).fillna("N/A")
        s = pd.read_csv(URL_S, dtype=str).fillna("0")
        q = pd.read_csv(URL_Q, dtype=str).fillna("0")
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

# القائمة المحظورة لتنظيف الداتا
EXCLUDE = ['N/A', 'Dropped Call', 'Call Dropped', '0', 'Other', 'na', ' ', '']

# --- 🔐 شاشة الدخول ---
st.sidebar.title("🔐 Access Control")
password = st.sidebar.text_input("Enter Password", type="password")

if not password or (password not in ["admin123", "ds2024"]):
    st.write("")
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if full_logo_64:
            st.markdown(f'<div style="text-align:center; margin-top:50px;"><img src="data:image/png;base64,{full_logo_64}" width="400"/></div>', unsafe_allow_html=True)
    st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)
    st.stop()

# --- محتوى الداشبورد ---
if df_f is not None:
    # الهيدر الداخلي (اللوجو الصغير + الاسم)
    if icon_inner_64:
        st.markdown(f"""
            <div class="header-container">
                <img src="data:image/png;base64,{icon_inner_64}" width="32" style="margin-bottom: -5px;"/>
                <span class="main-title">DSQUARES INSIGHTS HUB</span>
            </div>
            """, unsafe_allow_html=True)

    # Sidebar Filters
    st.sidebar.divider()
    min_d, max_d = min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])
    dr = st.sidebar.date_input("🗓 Select Date Range", [min_d, max_d])
    ff = df_f[(df_f['Full_Date_Obj'] >= dr[0]) & (df_f['Full_Date_Obj'] <= dr[1])] if len(dr)==2 else df_f
    
    f_merch = st.sidebar.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_proj = st.sidebar.multiselect("🏢 Project", sorted(ff['Project'].unique()))
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]: # 🏠 Overview
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        
        # ✅ قراءة الـ Total Inbound من عمود P
        inb_val = 0
        if 'Total Inbound' in ff.columns:
            inb_val = int(to_n(ff['Total Inbound']).max())
        k2.metric("Total Inbound", f"{inb_val:,}")
        
        k3.metric("Total WhatsApp", f"{len(ff[ff['Type'].str.contains('App', case=False, na=False)]):,}")
        k4.metric("Avg Quality", "96.6%")
        
        st.divider()
        daily_vol = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        fig_v = px.bar(daily_vol.nlargest(20, 'Total').sort_values('Full_Date_Obj'), x='Full_Date_Obj', y='Total', text_auto=True, title="🗓 Volume Trend (Peak Days)", color_discrete_sequence=[DS_BLUE])
        fig_v.update_xaxes(type='category', title=None)
        st.plotly_chart(fig_v, use_container_width=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(ff[~ff['Merchant'].isin(EXCLUDE)]['Merchant'].value_counts().head(10), title="1. Top Merchants", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Project'].isin(EXCLUDE)]['Project'].value_counts().head(10), title="3. Top Projects", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Ticket subtype'].isin(EXCLUDE)]['Ticket subtype'].value_counts().head(10), title="5. Top Sub-types", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        with c2:
            br_col = next((c for c in ff.columns if 'branch' in c.lower()), "Branch User Name")
            st.plotly_chart(px.bar(ff[~ff[br_col].isin(EXCLUDE)][br_col].value_counts().head(10), title="2. Top Branches", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)
            st.plotly_chart(px.pie(ff[~ff['Ticket type'].isin(EXCLUDE)], names='Ticket type', title="4. Ticket Type Distribution"), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Call Microtype'].isin(EXCLUDE)]['Call Microtype'].value_counts().head(10), title="6. Top Microtypes", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)

    with tabs[1]: # 💬 WhatsApp
        st.subheader("💬 WhatsApp MoM SLA Analysis")
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        m_list = ff.sort_values('Month_Num')['Month_Name'].unique()
        if len(m_list) > 0:
            cols = st.columns(4)
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Name'] == m]
                ot, lt = len(m_data[m_data[wa_col].str.contains('On-Time', na=False)]), len(m_data[m_data[wa_col].str.contains('Late', na=False)])
                perc = (ot / (ot + lt) * 100) if (ot + lt) > 0 else 0
                with cols[i % 4]:
                    st.markdown(f'<div class="wa-card"><h5>{m}</h5><h2>{perc:.1f}%</h2><p>✅ {ot} | ❌ {lt}</p></div>', unsafe_allow_html=True)

    with tabs[2]: # 📈 Inbound
        st.subheader("📈 Inbound SLA Summary")
        st.plotly_chart(px.bar(df_s, x='Month', y=to_n(df_s['PCA %']), title="PCA % Performance", text_auto='.1f', color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        st.dataframe(df_s, use_container_width=True, hide_index=True)

    with tabs[3]: # 🏆 Quality Board
        st.subheader("🏆 Quality Board")
        # ✅ مسح أي صفوف وهمية (أصفار أو Total)
        clean_q = df_q[(df_q['Agent Name'] != 'Total') & (df_q['Agent Name'] != '0') & (to_n(df_q['Total Calls']) > 0)].copy()
        clean_q['EC%'] = to_n(clean_q['EC %'])
        clean_q['BC%'] = to_n(clean_q['BC %'])
        
        fig_q = px.bar(clean_q, x='Agent Name', y=['EC%', 'BC%'], barmode='group', title="Agent Comparison", text_auto='.1f', color_discrete_sequence=[DS_BLUE, DS_LIGHT_BLUE])
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(clean_q, use_container_width=True, hide_index=True)

    with tabs[4]: # 🎫 Explorer
        st.subheader("🎫 Ticket Explorer")
        search = st.text_input("🔍 Search Anything...", "")
        exp_df = ff[ff.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else ff
        st.dataframe(exp_df, use_container_width=True, hide_index=True)
