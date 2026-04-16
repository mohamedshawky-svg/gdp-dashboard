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

# دالة لقراءة الصور من GitHub
def get_image_base64(path):
    try:
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        return None
    except:
        return None

# الأسماء اللي إنت حددتها بالظبط
OUTER_LOGO = "logo_icon.png"  # اللوجو اللي بره
INNER_LOGO = "Small_Logo.png" # اللوجو اللي جوه

full_logo_64 = get_image_base64(OUTER_LOGO)
icon_inner_64 = get_image_base64(INNER_LOGO)

# CSS لتنسيق الألوان والهيدر
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
        box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

# 2. تحميل البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
@st.cache_data(ttl=2)
def load_all_data():
    try:
        f_url = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407"
        s_url = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0"
        q_url = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747"
        f = pd.read_csv(f_url, dtype=str).fillna("N/A")
        s = pd.read_csv(s_url, dtype=str).fillna("0")
        q = pd.read_csv(q_url, dtype=str).fillna("0")
        d_col = next((c for c in f.columns if 'created' in c.lower() or 'date' in c.lower()), f.columns[0])
        f['Full_Date_Obj'] = pd.to_datetime(f[d_col], errors='coerce').dt.date
        f = f.dropna(subset=['Full_Date_Obj'])
        return f, s, q
    except: return None, None, None

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q = load_all_data()
EXCLUDE = ['N/A', 'Dropped Call', 'Call Dropped', 'Dropped call', 'Out Of Our Scope', 'Other', 'n', 'N', ' ', '']

# --- 🔐 شاشة الدخول ---
password = st.sidebar.text_input("Enter Password", type="password")
if not password or (password not in ["admin123", "ds2024"]):
    st.write("")
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if full_logo_64:
            st.markdown(f'<div style="text-align:center; margin-top:50px;"><img src="data:image/png;base64,{full_logo_64}" style="width:100%; max-width:400px;"/></div>', unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='text-align:center; color:{DS_BLUE}'>DSQUARES</h1>", unsafe_allow_html=True)
    st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)
    st.stop()

# --- محتوى الداشبورد ---
if df_f is not None:
    if icon_inner_64:
        st.markdown(f"""
            <div class="header-container">
                <img src="data:image/png;base64,{icon_inner_64}" width="32" style="margin-bottom: -5px;"/>
                <span class="main-title">DSQUARES INSIGHTS HUB</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p class="main-title">DSQUARES INSIGHTS HUB</p>', unsafe_allow_html=True)

    # الفلاتر
    st.sidebar.divider()
    dr = st.sidebar.date_input("🗓️ Select Date Range", [min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])])
    ff = df_f[(df_f['Full_Date_Obj'] >= dr[0]) & (df_f['Full_Date_Obj'] <= dr[1])] if len(dr)==2 else df_f
    
    selected_months = pd.to_datetime(ff['Full_Date_Obj']).dt.strftime('%b').unique()
    fs = df_s[df_s['Month'].isin(selected_months)]

    f_merch = st.sidebar.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_proj = st.sidebar.multiselect("🏢 Project", sorted(ff['Project'].unique()))
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        inbound_val = int(to_n(fs['Offered']).sum()) if not fs.empty else int(to_n(df_s['Offered']).sum())
        k2.metric("Total Inbound", f"{inbound_val:,}")
        k3.metric("Total WhatsApp", f"{len(ff[ff['Type'].str.contains('App', case=False, na=False)]):,}")
        k4.metric("Avg Quality", "96.6%")
        
        st.divider()
        st.subheader("🗓️ Volume Trend per Microtype")
        daily_vol = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        peak_days = daily_vol.nlargest(20, 'Total').sort_values('Full_Date_Obj')
        
        fig_v = px.bar(peak_days, x=peak_days['Full_Date_Obj'].astype(str), y='Total', text_auto=True, color_discrete_sequence=[DS_BLUE])
        st.plotly_chart(fig_v, use_container_width=True)

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
            st.plotly_chart(px.pie(ff[~ff['Ticket type'].isin(EXCLUDE)], names='Ticket type', title="4. Ticket Type Distribution"), use_container_width=True)
            st.plotly_chart(px.bar(ff[~ff['Call Microtype'].isin(EXCLUDE)]['Call Microtype'].value_counts().head(10), title="6. Top Microtypes", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)

    with tabs[3]: # Quality
        st.subheader("🏆 Quality Board")
        clean_q = df_q[to_n(df_q['Total Calls']) > 0].copy()
        plot_df = clean_q[clean_q['Agent Name'] != 'Total'].copy()
        fig_q = px.bar(plot_df, x='Agent Name', y=[to_n(plot_df['EC %']), to_n(plot_df['BC %'])], barmode='group', title="Agent Comparison", text_auto='.1f', color_discrete_sequence=[DS_BLUE, DS_LIGHT_BLUE])
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(clean_q.style.set_properties(**{'background-color': 'white', 'color': DS_BLUE}), use_container_width=True, hide_index=True)

    with tabs[2]: # Inbound
        st.subheader("📈 Inbound SLA Summary")
        st.plotly_chart(px.bar(fs, x='Month', y=to_n(fs['PCA %']), title="PCA % Performance", text_auto='.1f', color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        st.dataframe(fs.style.set_properties(**{'background-color': 'white', 'color': DS_BLUE}), use_container_width=True, hide_index=True)

    with tabs[4]: # Explorer
        search = st.text_input("🔍 Search Anything...", "")
        exp_df = ff[ff.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else ff
        st.dataframe(exp_df.style.set_properties(**{'background-color': 'white', 'color': DS_BLUE}), use_container_width=True, hide_index=True)
else:
    st.error("Data connection failed!")
