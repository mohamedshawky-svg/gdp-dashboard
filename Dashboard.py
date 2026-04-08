import streamlit as st
import pandas as pd
import plotly.express as px

# 1. إعدادات الصفحة - بدون أي تعقيدات CSS عشان نهرب من الـ Error
st.set_page_config(page_title="DSQUARES INSIGHTS HUB", layout="wide")

# 2. روابط البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
URL_F = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407"
URL_S = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0"
URL_Q = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747"

@st.cache_data(ttl=60)
def load_all_data():
    try:
        f = pd.read_csv(URL_F).dropna(how='all')
        s = pd.read_csv(URL_S).dropna(subset=['Month'])
        q = pd.read_csv(URL_Q).dropna(subset=['Agent Name'])
        for d in [f, s, q]:
            d.columns = d.columns.str.strip()
            for col in d.select_dtypes(['object']).columns:
                d[col] = d[col].astype(str).str.strip()
        # ترتيب الشهور زمنياً
        m_order = ['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', 
                   '26-Jul', '26-Aug', '26-Sep', '26-Oct', '26-Nov', '26-Dec']
        s['Month'] = pd.Categorical(s['Month'], categories=m_order, ordered=True)
        s = s.sort_values('Month')
        return f, s, q
    except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q = load_all_data()

if not df_f.empty:
    # --- 🕹️ القائمة الجانبية (كل الفلاتر بلا استثناء) ---
    st.sidebar.title("🎮 Global Control Center")
    def get_opt(df, col):
        return sorted([x for x in df[col].dropna().unique() if str(x).lower() not in ['nan','null','0']])

    f_month = st.sidebar.multiselect("🗓️ Months", get_opt(df_s, 'Month'), default=get_opt(df_s, 'Month'))
    f_proj = st.sidebar.multiselect("🏢 Projects", get_opt(df_f, 'Project'))
    f_merc = st.sidebar.multiselect("🛍️ Merchants", get_opt(df_f, 'Merchant'))
    f_agent = st.sidebar.multiselect("👤 Agents", get_opt(df_f, 'Agent'))
    f_type = st.sidebar.multiselect("🏷️ Ticket Types", get_opt(df_f, 'Ticket type'))
    f_subtype = st.sidebar.multiselect("📂 Ticket Subtypes", get_opt(df_f, 'Ticket subtype'))
    f_branch = st.sidebar.multiselect("📍 Branch User Name", get_opt(df_f, 'Branch User Name'))

    # تطبيق الفلترة
    ff = df_f.copy()
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]
    if f_merc: ff = ff[ff['Merchant'].isin(f_merc)]
    if f_agent: ff = ff[ff['Agent'].isin(f_agent)]
    if f_type: ff = ff[ff['Ticket type'].isin(f_type)]
    if f_subtype: ff = ff[ff['Ticket subtype'].isin(f_subtype)]
    if f_branch: ff = ff[ff['Branch User Name'].isin(f_branch)]
    fs = df_s[df_s['Month'].isin(f_month)]
    fq = df_q if not f_agent else df_q[df_q['Agent Name'].isin(f_agent)]

    st.title("📊 DSQUARES INSIGHTS HUB")
    t_ov, t_wa, t_sla, t_qual = st.tabs(["🏠 Overview", "💬 WhatsApp SLA", "📈 Inbound SLA", "🏆 Quality Ranking"])

    # --- 1. OVERVIEW (7 Bar Charts) ---
    with t_ov:
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Tickets", f"{len(ff):,}")
        k2.metric("Inbound Calls", f"{int(to_n(fs['Offered']).sum()):,}")
        k3.metric("WhatsApp Vol", f"{int(to_n(fs['Total WhatsApp']).sum()):,}")
        k4.metric("Avg Quality", f"{to_n(df_q['EC %']).mean():.1f}%")
        k5.metric("Merchants", ff['Merchant'].nunique())
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(ff['Merchant'].value_counts().head(10), title="Top 10 Merchants", template="plotly_dark"), use_container_width=True)
        with c2: st.plotly_chart(px.bar(ff['Branch User Name'].value_counts().head(10), title="Top 10 Branches", template="plotly_dark"), use_container_width=True)
        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(px.bar(ff['Project'].value_counts().head(10), title="Top 10 Projects", template="plotly_dark"), use_container_width=True)
        with c4: st.plotly_chart(px.bar(ff['Ticket type'].value_counts(), title="Ticket Types", template="plotly_dark"), use_container_width=True)
        c5, c6 = st.columns(2)
        with c5: st.plotly_chart(px.bar(ff['Ticket subtype'].value_counts().head(10), title="Top 10 Subtypes", template="plotly_dark"), use_container_width=True)
        with c6:
            m_data = ff[ff['Call Microtype'].notna() & (ff['Call Microtype'] != 'null')]
            st.plotly_chart(px.bar(m_data['Call Microtype'].value_counts(), title="Call Microtype", template="plotly_dark"), use_container_width=True)
        st.plotly_chart(px.bar(ff['Action taken'].value_counts(), title="Action Taken Breakdown", template="plotly_dark"), use_container_width=True)

    # --- 2. WhatsApp SLA (Real Data) ---
    with t_wa:
        st.subheader("💬 WhatsApp Monthly SLA Status")
        for _, row in fs.iterrows():
            m, total_wa = row['Month'], to_n(pd.Series([row['Total WhatsApp']])).values[0]
            wa_q = to_n(pd.Series([row.get('EC %.1', 95)])).values[0]
            on_t, late = int(total_wa * (wa_q/100)), int(total_wa - int(total_wa * (wa_q/100)))
            st.markdown(f"#### {m} Status")
            cw1, cw2 = st.columns(2); cw1.success(f"ON-TIME: {on_t}"); cw2.error(f"LATE: {late}"); st.divider()

    # --- 3. Inbound SLA ---
    with t_sla:
        st.plotly_chart(px.bar(fs, x='Month', y=['Offered', 'Answered'], barmode='group', template="plotly_dark", title="Inbound Performance"), use_container_width=True)
        fs['PCA_V'] = to_n(fs['PCA %'])
        st.plotly_chart(px.line(fs, x='Month', y='PCA_V', markers=True, title="PCA % Trend", template="plotly_dark"), use_container_width=True)

    # --- 4. Quality Ranking ---
    with t_qual:
        st.subheader("🏆 Quality Ranking & Calls")
        df_q['Calls_N'] = to_n(df_q['Total Calls'])
        st.plotly_chart(px.bar(df_q, x='Agent Name', y='Calls_N', title="Calls per Agent", template="plotly_dark"), use_container_width=True)
        st.dataframe(df_q[['Agent Name', 'Total Calls', 'EC %', 'BC %', 'NC %', 'Total WhatsApp']], use_container_width=True)
else:
    st.error("Check Google Sheet Permissions")