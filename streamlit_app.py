import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import base64
import os

# 1. إعداد الصفحة والـ Theme (تنسيق السطور الأصلي)
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

# أسامي اللوجوهات المعتمدة (تأكد من وجودها في GitHub بنفس الاسم)
FULL_LOGO = "logo_icon.png"  
ICON_INNER = "Small_Logo.png" 

full_logo_64 = get_image_base64(FULL_LOGO)
icon_inner_64 = get_image_base64(ICON_INNER)

# CSS المطور (نفس كودك وتنسيقك)
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
    .stDataFrame, div[data-testid="stTable"] {{
        background-color: white !important; color: {DS_BLUE} !important; border-radius: 10px;
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

# ✅ التطهير النهائي (كل اللي قولت نشيله)
EXCLUDE = ['N/A', 'Dropped Call', 'Call Dropped', 'Dropped call', 'Out Of Our Scope', 'Out of our scope', 'Out Of Scope', 'Other', 'other', 'na', 'n.a', 'n', 'N', ' ', '']

# --- 🔐 شاشة الدخول ---
st.sidebar.title("🔐 Access Control")
password = st.sidebar.text_input("Enter Password", type="password")

if not password or (password not in ["admin123", "ds2024"]):
    st.write("")
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if full_logo_64:
            st.markdown(f'<div style="text-align:center; margin-top:50px;"><img src="data:image/png;base64,{full_logo_64}" style="width:100%; max-width:400px;"/></div>', unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='text-align:center; color:{DS_BLUE}; margin-top:50px;'>DSQUARES</h1>", unsafe_allow_html=True)
    st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)
    if password: st.sidebar.error("Wrong Password!")
    st.stop()

# --- محتوى الداشبورد ---
if df_f is not None:
    # اللوجو والعنوان الداخلي
    if icon_inner_64:
        st.markdown(f"""
            <div class="header-container">
                <img src="data:image/png;base64,{icon_inner_64}" width="32" style="margin-bottom: -5px;"/>
                <span class="main-title">DSQUARES INSIGHTS HUB</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)

    # Sidebar Filters
    st.sidebar.divider()
    min_d, max_d = min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])
    dr = st.sidebar.date_input("🗓 Select Date Range", [min_d, max_d])
    ff = df_f if not (isinstance(dr, (list, tuple)) and len(dr) == 2) else df_f[(df_f['Full_Date_Obj'] >= dr[0]) & (df_f['Full_Date_Obj'] <= dr[1])]
    
    br_col = next((c for c in ff.columns if 'branch' in c.lower()), "Branch User Name")
    f_merch = st.sidebar.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_branch = st.sidebar.multiselect("📍 Branch", sorted(ff[br_col].unique()))
    f_proj = st.sidebar.multiselect("🏢 Project", sorted(ff['Project'].unique()))
    f_type = st.sidebar.multiselect("🎫 Ticket type", sorted(ff['Ticket type'].unique()))
    f_action = st.sidebar.multiselect("🎬 Action Taken", sorted(ff['Action taken'].unique()))
    
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_branch: ff = ff[ff[br_col].isin(f_branch)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]
    if f_type: ff = ff[ff['Ticket type'].isin(f_type)]
    if f_action: ff = ff[ff['Action taken'].isin(f_action)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]:
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
        st.subheader("🗓 Volume Trend per Microtype")
        daily_vol = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        peak_days = daily_vol.nlargest(20, 'Total').sort_values('Full_Date_Obj')
        
        fig_v = px.bar(peak_days, x=peak_days['Full_Date_Obj'].astype(str), y='Total', text_auto=True, color_discrete_sequence=[DS_BLUE])
        fig_v.update_xaxes(type='category', title=None)
        st.plotly_chart(fig_v, use_container_width=True)

        st.divider()
        # ✅ رسم الـ 7 Charts كاملة مع الـ EXCLUDE
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(ff[~ff['Merchant'].isin(EXCLUDE)]['Merchant'].value_counts().head(10), title="1. Top Merchants", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Project'].isin(EXCLUDE)]['Project'].value_counts().head(10), title="3. Top Projects", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Ticket subtype'].isin(EXCLUDE)]['Ticket subtype'].value_counts().head(10), title="5. Top Sub-types", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Action taken'].isin(EXCLUDE)]['Action taken'].value_counts().head(10), title="7. Top Actions Taken", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(ff[~ff[br_col].isin(EXCLUDE)][br_col].value_counts().head(10), title="2. Top Branches", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)
            st.plotly_chart(px.pie(ff[~ff['Ticket type'].isin(EXCLUDE)], names='Ticket type', title="4. Ticket Type Distribution"), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Call Microtype'].isin(EXCLUDE)]['Call Microtype'].value_counts().head(10), title="6. Top Microtypes", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)

    with tabs[1]: # WhatsApp
        st.subheader("💬 WhatsApp MoM SLA Analysis")
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        m_list = ff.sort_values('Month_Num')['Month_Name'].unique()
        if len(m_list) > 0:
            cols = st.columns(4)
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Name'] == m]
                ot, lt = len(m_data[m_data[wa_col].str.contains('On-Time', case=False, na=False)]), len(m_data[m_data[wa_col].str.contains('Late', case=False, na=False)])
                perc = (ot / (ot + lt) * 100) if (ot + lt) > 0 else 0
                with cols[i % 4]:
                    st.markdown(f'<div class="wa-card"><h5>{m}</h5><h2>{perc:.1f}%</h2><p>✅ {ot} | ❌ {lt}</p></div>', unsafe_allow_html=True)
    
    with tabs[3]: # Quality Board
        st.subheader("🏆 Quality Board")
        clean_q = df_q[df_q['Agent Name'] != 'Total'].copy()
        plot_df = clean_q.copy()
        plot_df['EC%'] = to_n(plot_df['EC %'])
        plot_df['BC%'] = to_n(plot_df['BC %'])
        fig_q = px.bar(plot_df, x='Agent Name', y=['EC%', 'BC%'], barmode='group', title="Agent Comparison", text_auto='.1f', color_discrete_sequence=[DS_BLUE, DS_LIGHT_BLUE], labels={'value': 'Percentage %', 'variable': 'Metric'})
        fig_q.update_layout(legend_title_text='Results')
        st.plotly_chart(fig_q, use_container_width=True)
