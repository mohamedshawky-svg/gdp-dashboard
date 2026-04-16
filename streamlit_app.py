import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import base64
import os

# 1. إعداد الصفحة والـ Theme
st.set_page_config(page_title="Dsquares Insights HUB", layout="wide")

DS_BLUE = "#0055A4"
DS_LIGHT_BLUE = "#00AEEF"

def get_image_base64(path):
    try:
        if os.path.exists(path):
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        return None
    except: return None

# جلب اللوجوهات المعتمدة
full_logo_64 = get_image_base64("logo_big.png")
icon_inner_64 = get_image_base64("logo_small.png")

# ✅ CSS - التنسيق النهائي (اللون الكحلي للـ Tags والبروز)
st.markdown(f"""
    <style>
    span[data-baseweb="tag"] {{ background-color: {DS_BLUE} !important; border-radius: 4px !important; }}
    [data-testid="stMetric"] {{
        background-color: white !important;
        border-top: 6px solid {DS_BLUE} !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important;
        padding: 20px !important;
    }}
    .wa-card {{ 
        background-color: white !important; padding: 18px !important; border-radius: 12px !important; 
        border: 1px solid #f0f2f6 !important; border-top: 6px solid {DS_BLUE} !important; 
        box-shadow: 0 12px 24px rgba(0,0,0,0.12) !important; text-align: center; margin-bottom: 20px;
    }}
    .wa-card h5 {{ margin-bottom: 5px; color: #444; font-size: 16px; font-weight: bold; }}
    .wa-card h2 {{ margin: 0; color: {DS_BLUE}; font-size: 28px; font-weight: 900; }}
    .wa-card p {{ font-size: 14px; margin-top: 5px; color: #555; font-weight: 700; }}

    .main-title {{ color: {DS_BLUE} !important; font-weight: 900; font-size: 38px !important; text-align: center; margin: 0; }}
    .header-container {{ display: flex; align-items: center; justify-content: center; margin-top: 10px; margin-bottom: 30px; gap: 12px; }}
    
    [data-testid="stMetricValue"] {{ font-size: 30px !important; color: {DS_BLUE} !important; font-weight: bold; }}
    [data-testid="stTable"] td, [data-testid="stTable"] th, .stDataFrame div, .stDataFrame span, p, label {{ 
        color: {DS_BLUE} !important; 
    }}
    [data-testid="stElementToolbar"] {{ display: none; }}
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
        st.markdown('<p class="main-title">Dsquares Insights HUB</p>', unsafe_allow_html=True)
        st.stop()

if st.sidebar.button("🔓 Log Out"):
    st.session_state.authenticated = False
    st.rerun()

# 3. تحميل ومعالجة البيانات
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
EXCLUDE_LOWER = ['n/a', 'n.a', 'dropped call', 'call dropped', 'out of our scope', 'other', '0', 'na', ' ', 'n', 'N']

if df_f is not None:
    if icon_inner_64:
        st.markdown(f'<div class="header-container"><img src="data:image/png;base64,{icon_inner_64}" width="40"/><span class="main-title">Dsquares Insights HUB</span></div>', unsafe_allow_html=True)

    # 4. الفلاتر (الـ 5 فلاتر كاملة)
    st.sidebar.divider()
    min_d, max_d = min(df_f['Full_Date_Obj']), max(df_f['Full_Date_Obj'])
    dr = st.sidebar.date_input("🗓 Select Date Range", [min_d, max_d])
    
    ff = df_f.copy()
    if isinstance(dr, (list, tuple)) and len(dr) == 2:
        ff = ff[(ff['Full_Date_Obj'] >= dr[0]) & (ff['Full_Date_Obj'] <= dr[1])]
    
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

    # دالة الفلترة السريعة
    def clean_df(df, col):
        return df[~df[col].astype(str).str.lower().isin(EXCLUDE_LOWER)]

    tabs = st.tabs(["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with tabs[0]: # 🏠 Overview
        k1, k2, k3, k4 = st.columns(4)
        
        # الحسابات الديناميكية بناءً على عمود Type
        inb_val = len(ff[ff['Type'].str.contains('Inbound', case=False, na=False)])
        wa_val = len(ff[ff['Type'].str.contains('WhatsApp', case=False, na=False)])
        
        k1.metric("Total Tickets", f"{len(ff):,}")
        k2.metric("Total Inbound", f"{inb_val:,}")
        k3.metric("Total WhatsApp", f"{wa_val:,}")
        k4.metric("Avg Quality", "96.6%")
        
        st.divider()
        # Volume Trend
        daily_total = ff.groupby('Full_Date_Obj').size().reset_index(name='Total')
        peak_days = daily_total.nlargest(20, 'Total').sort_values('Full_Date_Obj')
        peak_days['Date_Str'] = peak_days['Full_Date_Obj'].astype(str)
        
        micro_data = ff.groupby(['Full_Date_Obj', 'Call Microtype']).size().reset_index(name='Count')
        micro_data = clean_df(micro_data, 'Call Microtype')
        
        hover_texts = []
        for d in peak_days['Full_Date_Obj']:
            top_m = micro_data[micro_data['Full_Date_Obj'] == d].sort_values('Count', ascending=False).head(5)
            txt = "<br>".join([f"• {r['Call Microtype']}: {r['Count']}" for _, r in top_m.iterrows()])
            hover_texts.append(txt if txt else "No Data")

        fig_v = px.bar(peak_days, x='Date_Str', y='Total', text_auto=True, title="🗓 Volume Trend (Peak Days)", color_discrete_sequence=[DS_BLUE])
        fig_v.update_traces(customdata=hover_texts, hovertemplate="<b>Date: %{x}</b><br>Total: %{y}<br><br><b>Top Microtypes:</b><br>%{customdata}<extra></extra>")
        fig_v.update_xaxes(type='category', title=None, tickangle=45)
        st.plotly_chart(fig_v, use_container_width=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(clean_df(ff, 'Merchant')['Merchant'].value_counts().head(10), title="1. Top Merchants", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(clean_df(ff, 'Project')['Project'].value_counts().head(10), title="3. Top Projects", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(clean_df(ff, 'Ticket subtype')['Ticket subtype'].value_counts().head(10), title="5. Top Sub-types", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
            st.plotly_chart(px.bar(clean_df(ff, 'Action taken')['Action taken'].value_counts().head(10), title="7. Action Taken", text_auto=True, color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(clean_df(ff, br_col)[br_col].value_counts().head(10), title="2. Top Branches", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)
            st.plotly_chart(px.pie(clean_df(ff, 'Ticket type'), names='Ticket type', title="4. Ticket Type Distribution"), use_container_width=True)
            st.plotly_chart(px.bar(clean_df(ff, 'Call Microtype')['Call Microtype'].value_counts().head(10), title="6. Top Microtypes", text_auto=True, color_discrete_sequence=[DS_LIGHT_BLUE]), use_container_width=True)

    with tabs[1]: # 💬 WhatsApp MoM
        st.subheader("💬 WhatsApp MoM SLA Analysis")
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        m_list = ff.sort_values('Month_Num')['Month_Name'].unique()
        if len(m_list) > 0:
            cols = st.columns(4)
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Name'] == m]
                wa_m = m_data[m_data['Type'].str.contains('WhatsApp', case=False, na=False)]
                ot = len(wa_m[wa_m[wa_col].str.contains('On-Time', na=False, case=False)])
                lt = len(wa_m[wa_m[wa_col].str.contains('Late', na=False, case=False)])
                perc = (ot / (ot + lt) * 100) if (ot + lt) > 0 else 0
                with cols[i % 4]:
                    st.markdown(f'<div class="wa-card"><h5>{m}</h5><h2>{perc:.1f}%</h2><p>✅ On-Time: {ot} | ❌ Late: {lt}</p></div>', unsafe_allow_html=True)

    with tabs[2]: # 📈 Inbound SLA
        st.subheader("📈 Inbound SLA Summary")
        st.plotly_chart(px.bar(df_s, x='Month', y=to_n(df_s['PCA %']), title="PCA % Performance", text_auto='.1f', color_discrete_sequence=[DS_BLUE]), use_container_width=True)
        st.dataframe(df_s.style.set_properties(**{'color': DS_BLUE}), use_container_width=True, hide_index=True)

    with tabs[3]: # 🏆 Quality Board
        st.subheader("🏆 Quality Board")
        clean_q = df_q[(df_q['Agent Name'] != 'Total') & (df_q['Agent Name'] != '0') & (~df_q['Agent Name'].str.lower().isin(EXCLUDE_LOWER)) & (to_n(df_q['Total Calls']) > 0)].copy()
        q_plot = clean_q.rename(columns={'EC %': 'EC%', 'BC %': 'BC%'})
        fig_q = px.bar(q_plot, x='Agent Name', y=[to_n(q_plot['EC%']), to_n(q_plot['BC%'])], barmode='group', title="Agent Comparison", text_auto='.1f', color_discrete_sequence=[DS_BLUE, DS_LIGHT_BLUE])
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(clean_q.style.set_properties(**{'color': DS_BLUE}), use_container_width=True, hide_index=True)

    with tabs[4]: # 🎫 Ticket Explorer
        search = st.text_input("🔍 Search Anything...", "")
        exp_df = ff[ff.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else ff
        st.dataframe(exp_df.style.set_properties(**{'color': DS_BLUE}), use_container_width=True, hide_index=True)
