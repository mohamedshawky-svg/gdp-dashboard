import streamlit as st
import pandas as pd
import plotly.express as px

# 1. إعدادات الصفحة
st.set_page_config(page_title="DSQUARES HUB", layout="wide")

# 2. روابط البيانات
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
URL_F = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407"
URL_S = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0"
URL_Q = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747"

@st.cache_data(ttl=2)
def load_and_sync():
    try:
        f = pd.read_csv(URL_F).dropna(how='all')
        s = pd.read_csv(URL_S).dropna(subset=['Month'])
        q = pd.read_csv(URL_Q).dropna(subset=['Agent Name'])
        
        for d in [f, s, q]:
            d.columns = d.columns.str.strip()
            for col in d.select_dtypes(['object']).columns:
                d[col] = d[col].astype(str).str.strip()
        
        q = q[~q['Agent Name'].str.contains('Total', case=False, na=False)]
        m_order = ['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', '26-Jul', '26-Aug']
        s['Month'] = pd.Categorical(s['Month'], categories=m_order, ordered=True)
        return f, s, q
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q = load_and_sync()

if not df_f.empty:
    # --- 🕹️ Sidebar (الـ 7 فلاتر كاملة) ---
    st.sidebar.title("🎮 Global Control Center")
    def get_opts(df, col):
        return sorted([str(x) for x in df[col].unique() if pd.notna(x) and str(x).lower() not in ['nan','null','0']]) if col in df.columns else []

    f_month = st.sidebar.multiselect("🗓️ Months", ['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', '26-Jul', '26-Aug'], default=['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', '26-Jul', '26-Aug'])
    f_agent = st.sidebar.multiselect("👤 Agents", get_opts(df_f, 'Agent'))
    f_proj = st.sidebar.multiselect("🏢 Projects", get_opts(df_f, 'Project'))
    f_merc = st.sidebar.multiselect("🛍️ Merchants", get_opts(df_f, 'Merchant'))
    f_type = st.sidebar.multiselect("🏷️ Ticket Type", get_opts(df_f, 'Ticket type'))
    f_subtype = st.sidebar.multiselect("📂 Subtype", get_opts(df_f, 'Ticket subtype'))
    f_branch = st.sidebar.multiselect("📍 Branch", get_opts(df_f, 'Branch User Name'))

    ff = df_f.copy()
    if f_agent: ff = ff[ff['Agent'].isin(f_agent)]
    if f_proj: ff = ff[ff['Project'].isin(f_proj)]
    if f_merc: ff = ff[ff['Merchant'].isin(f_merc)]
    if f_type: ff = ff[ff['Ticket type'].isin(f_type)]
    if f_subtype: ff = ff[ff['Ticket subtype'].isin(f_subtype)]
    if f_branch: ff = ff[ff['Branch User Name'].isin(f_branch)]
    
    fs = df_s[df_s['Month'].isin(f_month)]
    fq = df_q[df_q['Agent Name'].isin(f_agent)] if f_agent else df_q

    st.title("📊 DSQUARES INSIGHTS HUB")
    t_ov, t_wa, t_sla, t_qual = st.tabs(["🏠 Overview", "💬 WhatsApp SLA", "📈 Inbound SLA", "🏆 Quality Ranking"])

    # --- 1. OVERVIEW (7 Charts) ---
    with t_ov:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        k2.metric("Inbound Calls", f"{len(ff[ff['Type']=='Inbound']):,}")
        k3.metric("WhatsApp Vol", f"{len(ff[ff['Type']=='WhatsApp']):,}")
        k4.metric("Avg Quality", f"{to_n(fq['EC %']).mean():.1f}%")
        
        st.divider()
        # Row 1: Merchants & Projects
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(ff['Merchant'].value_counts().head(10), title="Top 10 Merchants", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        with c2: st.plotly_chart(px.bar(ff['Project'].value_counts().head(10), title="Top 10 Projects", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        
        # Row 2: Ticket Type & Subtype
        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(px.bar(ff['Ticket type'].value_counts(), title="Ticket Types Distribution", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        with c4: st.plotly_chart(px.bar(ff['Ticket subtype'].value_counts().head(10), title="Top 10 Ticket Subtypes", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        
        # Row 3: Branches & Microtypes
        c5, c6 = st.columns(2)
        with c5: st.plotly_chart(px.bar(ff['Branch User Name'].value_counts().head(10), title="Top 10 Branches", orientation='h', template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        with c6: st.plotly_chart(px.bar(ff[ff['Call Microtype']!='N/A']['Call Microtype'].value_counts().head(10), title="Top 10 Call Microtypes", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        
        # Row 4: Action Taken (Full Width)
        st.plotly_chart(px.bar(ff['Action taken'].value_counts().head(10), title="Action Taken Breakdown", template="plotly_dark"), config={'displayModeBar': True}, use_container_width=True)
        
        st.subheader("🎫 Ticket Explorer (Raw Data)")
        st.dataframe(ff[['Ticket ID', 'Type', 'Agent', 'Merchant', 'Project', 'Ticket type', 'Ticket subtype', 'Call Microtype', 'Action taken', 'Created time']], use_container_width=True)

    # --- بقية التبويبات (SLA & Quality) كما هي مضبوطة سابقاً ---
    with t_wa:
        st.subheader("💬 WhatsApp Monthly SLA Status")
        wa_col = 'WhatsApp SLA Status'
        if wa_col in ff.columns:
            wa_data = ff[ff['Type'] == 'WhatsApp'].copy()
            wa_data['M'] = wa_data['Created time'].str.extract(r'-(0[1-8])-').replace({'01':'26-Jan','02':'26-Feb','03':'26-Mar','04':'26-Apr','05':'26-May','06':'26-Jun','07':'26-Jul','08':'26-Aug'})
            monthly_sla = wa_data.groupby(['M', wa_col]).size().unstack(fill_value=0)
            available_cols = [c for c in ['On-Time', 'Late'] if c in monthly_sla.columns]
            st.table(monthly_sla[available_cols].reset_index().rename(columns={'M':'Month'}))
            st.plotly_chart(px.pie(wa_data, names=wa_col, hole=0.4, title="Overall Achievement", color_discrete_map={'On-Time':'#00CC96', 'Late':'#EF553B'}), config={'displayModeBar': True}, use_container_width=True)
        else: st.warning("SLA Column Not Found.")

    with t_sla:
        st.plotly_chart(px.bar(fs, x='Month', y=['Offered', 'Answered'], barmode='group', title="Inbound Performance"), config={'displayModeBar': True}, use_container_width=True)
        fs['PCA_Val'] = to_n(fs['PCA %'])
        st.plotly_chart(px.line(fs, x='Month', y='PCA_Val', title="PCA % Trend", markers=True), config={'displayModeBar': True}, use_container_width=True)

    with t_qual:
        st.subheader("🏆 Quality Detailed Ledger")
        fq_final = fq.copy()
        pct_cols = ['EC %', 'BC %', 'NC %', 'EC %.1', 'BC %.1', 'NC %.1']
        fq_display = fq_final.copy()
        for c in pct_cols:
            if c in fq_final.columns:
                val = to_n(fq_final[c])
                fq_display[c] = val.apply(lambda x: f"{x:.1f}%")
        total_row = pd.DataFrame([{ 'Agent Name': 'TOTAL SUMMARY', 'Login ID': '-', 'Total Calls': to_n(fq_final['Total Calls']).sum(), 'EC %': f"{to_n(fq_final['EC %']).mean():.1f}%", 'BC %': f"{to_n(fq_final['BC %']).mean():.1f}%", 'Total WhatsApp': to_n(fq_final['Total WhatsApp']).sum(), 'EC %.1': f"{to_n(fq_final['EC %.1']).mean():.1f}%", 'BC %.1': f"{to_n(fq_final['BC %.1']).mean():.1f}%" }])
        final_table = pd.concat([fq_display, total_row], ignore_index=True)
        disp = {'Agent Name': 'Agent', 'Total Calls': 'C-Vol', 'EC %': 'C-EC%', 'BC %': 'C-BC%', 'NC %': 'C-NC%', 'Total WhatsApp': 'W-Vol', 'EC %.1': 'W-EC%', 'BC %.1': 'W-BC%', 'NC %.1': 'W-NC%'}
        st.dataframe(final_table.rename(columns=disp), use_container_width=True)
        st.plotly_chart(px.bar(fq_final, x='Agent Name', y='EC %', title="Accuracy per Agent"), config={'displayModeBar': True}, use_container_width=True)

else: st.error("No Data.")