import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import base64
import requests
import os

# 1. إعداد الصفحة والـ Theme
st.set_page_config(page_title="DSQUARES INSIGHTS HUB", layout="wide")

DS_BLUE = "#0055A4"
DS_LIGHT_BLUE = "#00AEEF"

# --- دالة قراءة اللوجو برابط مباشر لضمان الظهور 100% ---
@st.cache_data
def get_remote_image(file_name):
    # الرابط المباشر لصورك من الـ Repository بتاعك
    raw_url = f"https://raw.githubusercontent.com/mohamedshawky-svg/gdp-dashboard/main/{file_name}"
    try:
        response = requests.get(raw_url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode()
        return None
    except: return None

full_logo_64 = get_remote_image("logo_icon.png")
icon_inner_64 = get_remote_image("Small_Logo.png")

# CSS المطور (كامل بكل تفاصيله)
st.markdown(f"""
    <style>
    span[data-baseweb="tag"] {{ background-color: {DS_BLUE} !important; }}
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
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important; text-align: center; 
    }}
    .stDataFrame {{ background-color: white !important; border-radius: 10px; }}
    [data-testid="stElementToolbar"] {{ display: none; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; padding: 10px 20px;
    }}
    .stTabs [aria-selected="true"] {{ background-color: {DS_BLUE} !important; color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# 2. تحميل البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
@st.cache_data(ttl=2)
def load_all_data():
    try:
        f = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407", dtype=str).fillna("N/A")
        s = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0", dtype=str).fillna("0")
        q = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747", dtype=str).fillna("0")
        
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
EXCLUDE = ['N/A', 'Dropped Call', '0', 'Other', 'n', 'N', ' ', '']

# --- شاشة الدخول ---
password = st.sidebar.text_input("Enter Password", type="password")
if not password or (password not in ["admin123", "ds2024"]):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if full_logo_64:
            st.markdown(f'<div style="text-align:center; margin-top:50px;"><img src="data:image/png;base64,{full_logo_64}" width="400"/></div>', unsafe_allow_html=True)
    st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)
    st.stop()

# --- محتوى الداشبورد ---
if df_f is not None:
    if icon_inner_64:
        st.markdown(f'<div class="header-container"><img src="data:image/png;base64,{icon_inner_64}" width="32"/><span class="main-title">DSQUARES INSIGHTS HUB</span></div>', unsafe_allow_html=True)

    # الفلاتر الجانبية (FF)
    st.sidebar.divider()
    min_d, max_d = min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])
    dr = st.sidebar.date_input("🗓️ Select Date Range", [min_d, max_d])
    ff = df_f[(df_f['Full_Date_Obj'] >= dr[0]) & (df_f['Full_Date_Obj'] <= dr[1])] if len(dr)==2 else df_f
    
    # فلترة Inbound بناء على شهور التاريخ المختار
    sel_months = pd.to_datetime(ff['Full_Date_Obj']).dt.strftime('%b').unique()
    fs = df_s[df_s['Month'].isin(sel_months)]

    f_merch = st.sidebar.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_proj = st.sidebar.multiselect("🏢 Project", sorted(ff['Project'].unique()))
    f_type = st.sidebar.multiselect("🎫 Ticket type", sorted(ff['Ticket type'].unique()))
    
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]
    if f_type: ff = ff[ff['Ticket type'].isin(f_type)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]: # Overview
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        inbound_val = int(to_n(fs['Offered']).sum()) if not fs.empty else int(to_n(df_s['Offered']).sum())
        k2.metric("Total Inbound", f"{inbound_val:,}")
        k3.metric("Total WhatsApp", f"{len(ff[ff['Type'].str.contains('App', case=False, na=False)]):,}")
        k4.metric("Avg Quality", "96.6%")
        
        st.divider()
        st.subheader("🗓️ Volume Trend (Top 20 Peak Days)")
        daily = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        peak = daily.nlargest(20, 'Total').sort_values('Full_Date_Obj')
        st.plotly_chart(px.bar(peak, x=peak['Full_Date_Obj'].astype(str), y='Total', text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(ff[~ff['Merchant'].isin(EXCLUDE)]['Merchant'].value_counts().head(10), title="1. Top Merchants", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Project'].isin(EXCLUDE)]['Project'].value_counts().head(10), title="3. Top Projects", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Ticket subtype'].isin(EXCLUDE)]['Ticket subtype'].value_counts().head(10), title="5. Top Sub-types", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Action taken'].isin(EXCLUDE)]['Action taken'].value_counts().head(10), title="7. Top Actions Taken", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        with c2:
            br_col = next((c for c in ff.columns if 'branch' in c.lower()), "Branch User Name")
            st.plotly_chart(px.bar(ff[~ff[br_col].isin(EXCLUDE)][br_col].value_counts().head(10), title="2. Top Branches", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)
            st.plotly_chart(px.pie(ff, names='Ticket type', title="4. Ticket Type Distribution"), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Call Microtype'].isin(EXCLUDE)]['Call Microtype'].value_counts().head(10), title="6. Top Microtypes", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)

    with tabs[1]: # WhatsApp
        st.subheader("💬 WhatsApp MoM SLA Analysis")
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        m_list = ff.sort_values('Month_Num')['Month_Name'].unique()
        if len(m_list) > 0:
            cols = st.columns(4)
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Name'] == m]
                ot = len(m_data[m_data[wa_col].str.contains('On-Time', case=False, na=False)])
                lt = len(m_data[m_data[wa_col].str.contains('Late', case=False, na=False)])
                perc = (ot / (ot + lt) * 100) if (ot + lt) > 0 else 0
                with cols[i % 4]:
                    st.markdown(f'<div class="wa-card"><h5 style="color:{DS_LIGHT_BLUE}">{m}</h5><h2 style="margin:10px 0;">{perc:.1f}%</h2><p>✅ {ot} | ❌ {lt}</p></div>', unsafe_allow_html=True)

    with tabs[2]: # Inbound
        st.subheader("📈 Inbound SLA Summary")
        st.plotly_chart(px.bar(fs, x='Month', y=to_n(fs['PCA %']), title="PCA % Performance", text_auto='.1f', color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        st.dataframe(fs, use_container_width=True, hide_index=True)

    with tabs[3]: # Quality
        st.subheader("🏆 Quality Board")
        plot_df = df_q[df_q['Agent Name'] != 'Total'].copy()
        fig_q = px.bar(plot_df, x='Agent Name', y=[to_n(plot_df['EC %']), to_n(plot_df['BC %'])], barmode='group', title="Agent Performance", text_auto='.1f', color_discrete_sequence=[DS_BLUE, DS_LIGHT_BLUE])
        new_names = {'wide_variable_0':'EC%', 'wide_variable_1':'BC%'}
        fig_q.for_each_trace(lambda t: t.update(name = new_names.get(t.name, t.name)))
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(df_q, use_container_width=True, hide_index=True)

    with tabs[4]: # Explorer
        search = st.text_input("🔍 Search Anything...", "")
        exp_df = ff[ff.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else ff
        st.dataframe(exp_df, use_container_width=True, hide_index=True)
