import streamlit as st
import pandas as pd
import plotly.express as px

# 1. إعداد الصفحة
st.set_page_config(page_title="DSQUARES INSIGHTS HUB", layout="wide")

# 2. روابط البيانات
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
        
        for d in [f, s, q]:
            d.columns = d.columns.str.strip()
            for col in d.columns: d[col] = d[col].astype(str).str.strip()
        
        m_col = next((c for c in f.columns if 'created' in c.lower() or 'month' in c.lower()), f.columns[0])
        f['Month_Ref'] = pd.to_datetime(f[m_col], errors='coerce').dt.strftime('26-%b')
        f['Month_Ref'] = f['Month_Ref'].fillna("N/A")
        
        m_order = ['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', 
                   '26-Jul', '26-Aug', '26-Sep', '26-Oct', '26-Nov', '26-Dec']
        return f, s, q, m_order
    except: return None, None, None, []

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q, master_order = load_all_data()

if df_f is not None:
    # --- Sidebar (الفلاتر الكاملة) ---
    st.sidebar.title("🎮 Global Filters")
    
    # فلتر الشهور (بيقرأ المتاح في الشيت)
    current_avail_m = [m for m in master_order if m in df_f['Month_Ref'].unique() or m in df_s['Month'].unique()]
    f_month = st.sidebar.multiselect("🗓️ Select Months", current_avail_m, default=current_avail_m)
    
    f_merch = st.sidebar.multiselect("🏪 Filter Merchant", sorted(df_f['Merchant'].unique()))
    br_col = next((c for c in df_f.columns if 'branch user name' in c.lower()), "Branch User Name")
    f_branch = st.sidebar.multiselect("📍 Filter Branch User", sorted(df_f[br_col].unique()))
    f_agent = st.sidebar.multiselect("🎧 Filter Agent", sorted(df_f['Agent'].unique()))
    p_col = next((c for c in df_f.columns if 'project' in c.lower()), "Project")
    f_proj = st.sidebar.multiselect("🏢 Filter Project", sorted(df_f[p_col].unique()), default=sorted(df_f[p_col].unique()))

    # --- تطبيق الفلترة ---
    ff = df_f[df_f['Month_Ref'].isin(f_month)]
    if f_merch: ff = ff[ff['Merchant'].isin(f_merch)]
    if f_branch: ff = ff[ff[br_col].isin(f_branch)]
    if f_agent: ff = ff[ff['Agent'].isin(f_agent)]
    if f_proj: ff = ff[ff[p_col].isin(f_proj)]
    
    fs = df_s[df_s['Month'].isin(f_month)]

    st.title("📊 DSQUARES INSIGHTS HUB")
    t1, t2, t3, t4, t5 = st.tabs(["🏠 Overview", "💬 WhatsApp SLA MoM", "📈 Inbound SLA", "🏆 Quality Board", "🎫 Ticket Explorer"])

    with t1:
        # 🟢 الـ Scorecards المطلوبة بالظبط
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tickets", f"{len(ff):,}")
        k2.metric("Total Inbound", f"{int(to_n(fs['Offered']).sum()):,}")
        
        wa_col = next((c for c in ff.columns if 'sla status' in c.lower()), "WhatsApp SLA Status")
        # حساب إجمالي الواتساب (التذاكر اللي نوعها WhatsApp)
        wa_count = len(ff[ff['Type'].str.contains('App', case=False, na=False)])
        k3.metric("Total WhatsApp", f"{wa_count:,}")
        
        q_avg = to_n(df_q['EC %'])
        k4.metric("Avg Quality %", f"{q_avg[q_avg > 0].mean():.1f}%")
        
        st.divider()
        # 📊 الـ 7 Charts الأساسية
        st.plotly_chart(px.bar(ff['Merchant'].value_counts().head(10), title="1. Top Merchants", template="plotly_dark", color_discrete_sequence=['#00CC96']), use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(ff[br_col].value_counts().head(10), title="2. Top Branches"), use_container_width=True)
        with c2: st.plotly_chart(px.bar(ff[p_col].value_counts().head(10), title="3. Top Projects"), use_container_width=True)
        
        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(px.bar(ff['Ticket type'].value_counts(), title="4. Ticket Type Breakdown"), use_container_width=True)
        with c4: st.plotly_chart(px.bar(ff['Ticket subtype'].value_counts().head(10), title="5. Top Subtypes"), use_container_width=True)
            
        c5, c6 = st.columns(2)
        with c5: st.plotly_chart(px.bar(ff['Call Microtype'].value_counts().head(10), title="6. Microtypes"), use_container_width=True)
        with c6: st.plotly_chart(px.bar(ff['Action taken'].value_counts().head(10), title="7. Actions Taken"), use_container_width=True)

    with t2:
        st.subheader("💬 WhatsApp SLA MoM")
        m_list = [m for m in master_order if m in ff['Month_Ref'].unique()]
        if m_list:
            cols = st.columns(len(m_list))
            for i, m in enumerate(m_list):
                m_data = ff[ff['Month_Ref'] == m]
                ot = len(m_data[m_data[wa_col].str.contains('Time', case=False, na=False)])
                lt = len(m_data[m_data[wa_col].str.contains('Late', case=False, na=False)])
                total = ot + lt
                perc = (ot / total * 100) if total > 0 else 0
                with cols[i]:
                    st.markdown(f"""<div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #00CC96;">
                        <h4 style="margin:0; color: #00CC96;">{m}</h4>
                        <p style="margin:5px 0 0 0;">✅ OT: <b>{ot}</b> | ❌ LT: <b>{lt}</b></p>
                        <p style="margin:5px 0 0 0; color:#00CC96; font-size:20px;">🎯 <b>{perc:.1f}%</b></p>
                    </div>""", unsafe_allow_html=True)

    with t3:
        st.subheader("📈 Inbound SLA Details")
        fs['SL%'] = (to_n(fs['Answered']) / to_n(fs['Offered']) * 100).fillna(0)
        st.plotly_chart(px.bar(fs, x='Month', y='SL%', title="Service Level % MoM", text_auto='.1f', color_discrete_sequence=['#00CC96']), use_container_width=True)
        # الجدول اللي طلبته في الصورة الأخيرة
        st.table(fs[['Month', 'Offered', 'Answered', 'Unanswered', 'PCA %', 'Abandoned%']])

    with t4:
        st.subheader("🏆 Quality Board")
        clean_q = df_q[(df_q['Agent Name'] != '0') & (df_q['Agent Name'] != 'Total')]
        st.plotly_chart(px.bar(clean_q, x='Agent Name', y=[to_n(clean_q['EC %']), to_n(clean_q['BC %'])], barmode='group', title="Agent Performance"), use_container_width=True)
        st.dataframe(clean_q, use_container_width=True)

    with t5:
        st.subheader("🎫 Smart Ticket Explorer")
        search_query = st.text_input("🔍 Search by ID, Merchant, Branch, Agent...", "")
        explorer_df = ff.copy()
        if search_query:
            mask = explorer_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
            explorer_df = explorer_df[mask]
        st.write(f"Showing {len(explorer_df)} tickets")
        st.dataframe(explorer_df, use_container_width=True)

else:
    st.error("Connection Failed. Check GID Access.")
