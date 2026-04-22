import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import os
import time

# ==========================================
# 1. إعدادات الصفحة الأساسية
# ==========================================
st.set_page_config(
    page_title="Dsquares Insights HUB", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# الألوان الرسمية
DS_BLUE, DS_NAVY, DS_LIGHT = "#0055A4", "#002147", "#00AEEF"

# القائمة السوداء (إبادة الممنوعات والفراغات من الشارتات)
BLACK_LIST = [
    '', 'n/a', 'n.a', 'n', 'dropped call', 'call dropped', 
    'out of our scope', 'other', '0', 'na', ' ', 'N', 
    'none', 'nan', 'N/A', '0.0', 'NaN', 'None'
]

# قاموس الاختصارات وتصحيح الـ Action Taken
SHORT_NAMES = {
    "Not Done": "Solved",
    "This Number Belongs To An Inactive Wallet": "Inactive Wallet",
    "Escalated- Tech Support": "Esc-Tech",
    "Escalated- Field Team": "Esc-FO",
    "Escalated- Management Team": "Esc-MGT",
    "Escalated- Sys.Set-Up": "Esc-Sys",
    "Escalated- Monitoring Team": "Esc-M&C"
}

# ==========================================
# 2. الدوال المساعدة (Helper Functions)
# ==========================================

def get_img_64(path):
    """تحويل اللوجو لصيغة Base64"""
    try:
        if os.path.exists(path):
            with open(path, "rb") as f: 
                return base64.b64encode(f.read()).decode()
    except: 
        return None
    return None

logo_big = get_img_64("logo_big.png")
logo_sm = get_img_64("logo_small.png")

def to_n(s): 
    """تحويل النصوص لأرقام حقيقية وتنظيف الـ %"""
    return pd.to_numeric(
        s.astype(str).str.replace('%','').str.replace(',',''), 
        errors='coerce'
    ).fillna(0)

def clean_st(df, col): 
    """تنظيف شامل للبيانات لمنع الفراغات والـ AttributeError والممنوعات"""
    if col not in df.columns:
        return df
    
    temp_df = df.copy()
    temp_df[col] = temp_df[col].astype(str).str.strip()
    
    # فلترة القيم الفارغة والممنوعة
    mask = (
        (temp_df[col] != "") & 
        (temp_df[col].str.lower() != "nan") & 
        (temp_df[col].str.lower() != "none") &
        (~temp_df[col].str.lower().isin([x.lower() for x in BLACK_LIST]))
    )
    return temp_df[mask]

def get_top_safe(df, col):
    """إيجاد القيمة الأعلى تكراراً بعد التنظيف للـ Help Box"""
    temp = clean_st(df, col)
    if not temp.empty:
        return temp[col].mode()[0]
    return "N/A"

# ✅ CSS الصارم - إرجاع حركة الـ Scorecards + تثبيت السايدبار
st.markdown(f"""
    <style>
    /* منع زر السايدبار من الاختفاء وجعله كحلي */
    [data-testid="stHeader"] {{ 
        background-color: rgba(0,0,0,0) !important; 
        color: {DS_NAVY} !important; 
        visibility: visible !important; 
    }}
    
    [data-testid="stSidebarCollapseButton"] {{ 
        color: {DS_NAVY} !important; 
        visibility: visible !important; 
    }}

    .main .block-container {{padding-top: 1rem;}}
    .dashboard-header {{ text-align: center; margin-bottom: 20px; }}
    .dashboard-header h2 {{ color: {DS_NAVY}; font-weight: 900; font-size: 28px; margin-top: 10px; }}
    
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] div, [data-testid="stTable"] th {{ 
        color: {DS_NAVY} !important; font-weight: 800 !important; font-size: 14px !important;
    }}

    /* 🎯 تنسيق الـ Scorecards مع إرجاع حركة الـ Hover */
    [data-testid="stMetric"], .wa-card, .overall-card {{
        background-color: white !important; 
        border-top: 6px solid {DS_NAVY} !important;
        border-radius: 12px !important; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.1) !important;
        padding: 20px !important; 
        transition: all 0.4s ease-in-out !important; 
    }}

    /* 🔥 الحركة لما الماوس ييجي على الكارت */
    [data-testid="stMetric"]:hover, .wa-card:hover, .overall-card:hover {{ 
        transform: translateY(-15px) scale(1.02); 
        box-shadow: 0 20px 40px rgba(0,0,0,0.2) !important;
        border-top: 6px solid {DS_LIGHT} !important;
    }}
    
    /* ألوان الفلاتر */
    span[data-baseweb="tag"] {{ background-color: {DS_NAVY} !important; }}
    div[data-baseweb="select"] > div {{ border-color: {DS_NAVY} !important; }}
    div[data-testid="stDateInput"] > div {{ border: 1px solid {DS_NAVY} !important; }}
    div[data-baseweb="calendar"] [aria-selected="true"] {{ background-color: {DS_NAVY} !important; }}

    [data-testid="stMetricValue"] {{ font-weight: 900 !important; font-size: 35px !important; color: {DS_NAVY} !important; }}
    .wa-card h5 {{ color: {DS_NAVY} !important; font-weight: 900; font-size: 20px; }}
    .wa-card .perc {{ color: {DS_BLUE} !important; font-weight: 900; font-size: 32px; }}
    .page-title-header {{ color: {DS_NAVY}; font-weight: 900; font-size: 26px; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. نظام الدخول
# ==========================================
if 'auth_role' not in st.session_state: 
    st.session_state.auth_role = None

if not st.session_state.auth_role:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if logo_big: 
            st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_big}" width="350"/></div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:#002147; font-weight:900;">Dsquares Insights HUB</h2>', unsafe_allow_html=True)
        pwd = st.text_input("🔐 Access Key", type="password")
        if pwd == "admin123": 
            st.session_state.auth_role = "admin"
            st.rerun()
        elif pwd == "dsq123": 
            st.session_state.auth_role = "user"
            st.rerun()
    st.stop()

# ==========================================
# 4. محرك البيانات
# ==========================================
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"

@st.cache_data(ttl=2)
def load_data_final():
    try:
        base = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv"
        # تنظيف فوري للأعمدة والصفوف الفاضية
        m = pd.read_csv(f"{base}&gid=1278191407", dtype=str).dropna(axis=1, how='all').fillna("")
        s = pd.read_csv(f"{base}&gid=0", dtype=str).dropna(axis=1, how='all').fillna("")
        q = pd.read_csv(f"{base}&gid=468167747", dtype=str).dropna(axis=1, how='all').fillna("")
        
        # تطبيق الاختصارات وتغيير Not Done لـ Solved
        for old, new in SHORT_NAMES.items():
            m = m.replace(old, new)
            
        m = m[m.iloc[:, 0].str.strip() != ""].copy()
        d_col = next((c for c in m.columns if any(k in c.lower() for k in ['created', 'date'])), m.columns[0])
        m['D_Obj'] = pd.to_datetime(m[d_col], errors='coerce').dt.date
        m = m.dropna(subset=['D_Obj'])
        m['Month_Name'] = pd.to_datetime(m[d_col], errors='coerce').dt.strftime('%b')
        q = q[q['Agent Name'].str.strip() != ""].copy()
        s = s[s['Month'].str.strip() != ""].copy()
        return m, s, q
    except: 
        return None, None, None

df_m, df_s, df_q = load_data_final()
st.markdown(f'<div class="dashboard-header"><img src="data:image/png;base64,{logo_sm}" width="45"><br><h2>Dsquares Insights HUB</h2></div>', unsafe_allow_html=True)

# ==========================================
# 5. السايدبار والفلاتر
# ==========================================
with st.sidebar:
    if logo_big: 
        st.image(f"data:image/png;base64,{logo_big}", use_container_width=True)
    st.divider()
    dr = st.date_input("🗓 Select Date Range", [min(df_m['D_Obj']), max(df_m['D_Obj'])])
    ff = df_m.copy()
    if len(dr) == 2: 
        ff = ff[(ff['D_Obj'] >= dr[0]) & (ff['D_Obj'] <= dr[1])]
    
    f_merch = st.multiselect("🏪 Merchant", sorted(ff['Merchant'].unique()))
    f_proj = st.multiselect("🏢 Project", sorted(ff['Project'].unique()))
    f_branch = st.multiselect("📍 Branch", sorted(ff['Branch User Name'].unique()))
    f_type = st.multiselect("🎫 Ticket type", sorted(ff['Ticket type'].unique()))
    f_act = st.multiselect("🎬 Action taken", sorted(ff['Action taken'].unique()))
    
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]
    if f_branch: ff = ff[ff['Branch User Name'].isin(f_branch)]
    if f_type: ff = ff[ff['Ticket type'].isin(f_type)]
    if f_act: ff = ff[ff['Action taken'].isin(f_act)]

    st.divider()
    if st.button("🔓 Log Out"): 
        st.session_state.auth_role = None
        st.rerun()

if st.session_state.auth_role == "admin":
    tabs_list = ["🏠 Overview", "💬 WhatsApp MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"]
else:
    tabs_list = ["🏠 Overview", "🎫 Ticket Explorer"]

tabs = st.tabs(tabs_list)

# ==========================================
# --- TAB: Overview (الربط السباعي + التعديلات) ---
# ==========================================
with tabs[tabs_list.index("🏠 Overview")]:
    # 🎯 حوار البوكسات (The Help Box Tooltip)
    t_m = get_top_safe(ff, 'Merchant')
    t_p = get_top_safe(ff, 'Project')
    t_b = get_top_safe(ff, 'Branch User Name')
    t_t = get_top_safe(ff, 'Ticket type')
    
    inbound_all = ff[ff['Type'].str.contains('Inbound|Call', case=False, na=False)]
    pk_in = inbound_all['D_Obj'].mode()[0] if not inbound_all.empty else "N/A"
    
    wa_all = ff[ff['Type'].str.contains('WhatsApp|App', case=False, na=False)]
    pk_wa = wa_all['D_Obj'].mode()[0] if not wa_all.empty else "N/A"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Tickets", f"{len(ff):,}", help=f"🏆 Top Merchant: {t_m}  \n🏢 Top Project: {t_p}  \n📍 Top Branch: {t_b}  \n🎫 Top Type: {t_t}")
    k2.metric("Inbound Calls", f"{len(inbound_all):,}", help=f"⏰ Peak Day: {pk_in}")
    k3.metric("WhatsApp Tickets", f"{len(wa_all):,}", help=f"📱 Peak Day: {pk_wa}")
    k4.metric("Avg Quality", "96.6%", help="🌟 Top Performer: Menna Sameh")
    
    st.divider()
    
    # 📊 Volume Trend (Peak Days)
    daily = ff.groupby('D_Obj').size().reset_index(name='Total')
    peak = daily.nlargest(20, 'Total').sort_values('D_Obj')
    peak['Date_Str'] = peak['D_Obj'].astype(str)
    
    h_peak = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff[ff['D_Obj']==d].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for d in peak['D_Obj']]
    
    fig_v = px.bar(peak, x='Date_Str', y='Total', title="📊 Volume Trend (Peak Days)", color_discrete_sequence=[DS_NAVY], text='Total')
    fig_v.update_traces(customdata=h_peak, hovertemplate="Total: %{y}<br><br><b>Top Microtypes:</b><br>%{customdata}<extra></extra>")
    st.plotly_chart(fig_v.update_layout(xaxis={'type':'category'}, bargap=0.1), use_container_width=True)
    
    # 🔗 الربط السباعي (Drill-down)
    drill_d = st.selectbox("🗓️ Filter Ticket Explorer by Peak Day:", ["All Data"] + sorted(peak['Date_Str'].tolist()))
    ff_drill = ff if drill_d == "All Data" else ff[ff['D_Obj'].astype(str) == drill_d]
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        # 1. Merchants (Hover: Microtype)
        m_agg = clean_st(ff_drill, 'Merchant').groupby('Merchant').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        m_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Merchant']==m].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for m in m_agg['Merchant']]
        fig1 = px.bar(m_agg, x='Merchant', y='c', title="1. Top 10 Merchants (Hover: Micro)", text='c', color_discrete_sequence=[DS_NAVY])
        fig1.update_traces(customdata=m_h, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        st.plotly_chart(fig1, use_container_width=True)
        
        # 3. Projects (Hover: Microtype)
        p_agg = clean_st(ff_drill, 'Project').groupby('Project').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        p_h = ["<br>".join([f"• {r['Call Microtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Project']==p].groupby('Call Microtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows() if r['Call Microtype'].lower().strip() not in BLACK_LIST]) for p in p_agg['Project']]
        fig3 = px.bar(p_agg, x='Project', y='c', title="3. Top 10 Projects (Hover: Micro)", text='c', color_discrete_sequence=[DS_NAVY])
        fig3.update_traces(customdata=p_h, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        st.plotly_chart(fig3, use_container_width=True)
        
        # 5. Subtypes (Hover: Ticket Type)
        su_agg = clean_st(ff_drill, 'Ticket subtype').groupby('Ticket subtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        su_h = ["<br>".join([f"• {r['Ticket type']}: {r['n']}" for _, r in ff_drill[ff_drill['Ticket subtype']==s].groupby('Ticket type').size().reset_index(name='n').sort_values('n', ascending=False).head(3).iterrows()]) for s in su_agg['Ticket subtype']]
        fig5 = px.bar(su_agg, x='Ticket subtype', y='c', title="5. Top 10 Subtypes (Hover: Type)", text='c', color_discrete_sequence=[DS_NAVY])
        fig5.update_traces(customdata=su_h, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        st.plotly_chart(fig5, use_container_width=True)

    with c2:
        # 2. Branches (Hover: Merchant)
        br_agg = clean_st(ff_drill, 'Branch User Name').groupby('Branch User Name').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        br_h = ["<br>".join([f"• {r['Merchant']}: {r['n']}" for _, r in ff_drill[ff_drill['Branch User Name']==b].groupby('Merchant').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for b in br_agg['Branch User Name']]
        fig2 = px.bar(br_agg, x='Branch User Name', y='c', title="2. Top 10 Branches (Hover: Merchant)", text='c', color_discrete_sequence=[DS_LIGHT])
        fig2.update_traces(customdata=br_h, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        st.plotly_chart(fig2, use_container_width=True)
        
        # 4. Ticket Type Share
        st.plotly_chart(px.pie(clean_st(ff_drill, 'Ticket type'), names='Ticket type', title="4. Ticket Type Share", hole=0.3).update_traces(textinfo='percent+label'), use_container_width=True)
        
        # 6. Microtypes (Hover: Subtype)
        mi_agg = clean_st(ff_drill, 'Call Microtype').groupby('Call Microtype').size().reset_index(name='c').sort_values('c', ascending=False).head(10)
        mi_h = ["<br>".join([f"• {r['Ticket subtype']}: {r['n']}" for _, r in ff_drill[ff_drill['Call Microtype']==m].groupby('Ticket subtype').size().reset_index(name='n').sort_values('n', ascending=False).head(5).iterrows()]) for m in mi_agg['Call Microtype']]
        fig6 = px.bar(mi_agg, x='Call Microtype', y='c', title="6. Top 10 Microtypes (Hover: Sub)", text='c', color_discrete_sequence=[DS_LIGHT])
        fig6.update_traces(customdata=mi_h, hovertemplate="Total: %{y}<br><br>%{customdata}<extra></extra>")
        st.plotly_chart(fig6, use_container_width=True)
    
    st.divider()
    # 7. Action Taken (مربوط أيضاً)
    st.plotly_chart(px.bar(clean_st(ff_drill, 'Action taken')['Action taken'].value_counts().head(10), title="7. Key Actions Taken", text_auto=True, color_discrete_sequence=[DS_NAVY]), use_container_width=True)

# --- ADMIN ONLY TABS ---
if st.session_state.auth_role == "admin":
    with tabs[tabs_list.index("💬 WhatsApp MoM")]:
        st.markdown("<div class='page-title-header'>💬 WhatsApp MoM SLA Analysis</div>", unsafe_allow_html=True)
        wa_df = ff[ff['Type'].str.contains('WhatsApp|App', case=False, na=False)]
        wa_col = next((c for c in wa_df.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        ot_total = len(wa_df[wa_df[wa_col].str.contains('On-Time|On Time', na=False, case=False)])
        ov_perc = (ot_total / len(wa_df) * 100) if len(wa_df)>0 else 0
        st.markdown(f'<div class="overall-card" style="text-align:center;"><p style="margin:0; font-weight:900; color:gray;">OVERALL ON-TIME RESPONSE</p><h2 style="color:{DS_NAVY}; font-size:45px; font-weight:900;">{ov_perc:.1f}%</h2><p style="color:green; font-weight:800; font-size:18px;">Target: 95%</p></div>', unsafe_allow_html=True)
        st.divider()
        m_list = wa_df.sort_values('D_Obj')['Month_Name'].unique()
        cols = st.columns(4)
        for i, m in enumerate(m_list):
            m_d = wa_df[wa_df['Month_Name'] == m]
            ot, lt = len(m_d[m_d[wa_col].str.contains('On-Time|On Time', na=False, case=False)]), len(m_d[m_d[wa_col].str.contains('Late', na=False, case=False)])
            with cols[i % 4]: 
                st.markdown(f'<div class="wa-card"><h5>{m}</h5><div class="perc">{(ot/(ot+lt)*100 if (ot+lt)>0 else 0):.1f}%</div><p style="color:green; font-weight:700; margin:0;">On-Time: {ot}</p><p style="color:red; font-weight:700; margin:0;">Late: {lt}</p></div>', unsafe_allow_html=True)

    with tabs[tabs_list.index("📈 Inbound SLA")]:
        st.markdown("<div class='page-title-header'>📈 Inbound SLA Performance</div>", unsafe_allow_html=True)
        if not df_s.empty:
            fig_sla = px.bar(df_s, x='Month', y=to_n(df_s['PCA %']), title="Monthly PCA% Achievement", text_auto='.1f', color_discrete_sequence=[DS_NAVY], labels={'y': 'PCA% Achievement'})
            st.plotly_chart(fig_sla.update_layout(xaxis_type='category', bargap=0.3), use_container_width=True)
            st.dataframe(df_s.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)

    with tabs[tabs_list.index("🏆 Quality Board")]:
        st.markdown("<div class='page-title-header'>🏆 Agent Quality Board</div>", unsafe_allow_html=True)
        cq = df_q.copy()
        cq['EC%'] = to_n(cq['EC %'])
        cq['BC%'] = to_n(cq['BC %'])
        df_p = cq.melt(id_vars=['Agent Name'], value_vars=['EC%', 'BC%'], var_name='Metric', value_name='Score')
        fig_q = px.bar(df_p, x='Agent Name', y='Score', color='Metric', barmode='group', text='Score', color_discrete_sequence=[DS_NAVY, DS_LIGHT], labels={'Score': 'Score %', 'Metric': 'Metric'})
        fig_q.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_q.update_layout(xaxis_type='category', bargap=0.15, bargroupgap=0.05, yaxis_range=[0, 115], yaxis_title="Score %")
        st.plotly_chart(fig_q, use_container_width=True)
        st.dataframe(df_q.style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)

with tabs[tabs_list.index("🎫 Ticket Explorer")]:
    search = st.text_input("🔍 Smart Search...", "", key="main_search")
    ff_final = ff_drill.copy()
    if search: 
        ff_final = ff_final[ff_final.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    st.dataframe(ff_final.drop(columns=['D_Obj', 'Month_Name'], errors='ignore').style.set_properties(**{'color': DS_NAVY, 'font-weight': '800'}), use_container_width=True, hide_index=True)
