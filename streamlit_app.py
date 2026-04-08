import streamlit as st
import pandas as pd
import plotly.express as px

# 1. إعدادات الصفحة
st.set_page_config(page_title="DSQUARES HUB", layout="wide")

# --- 🔒 نظام الصلاحيات ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Welcome to DSQUARES HUB")
    pwd = st.text_input("Access Code:", type="password")
    if st.button("Login"):
        if pwd == "admin123": st.session_state['auth'] = "admin"
        elif pwd == "team-ds": st.session_state['auth'] = "team"
        else: st.error("Wrong Code!")
        if st.session_state['auth']: st.rerun()
    st.stop()

user_role = st.session_state['auth']

# 2. روابط البيانات (تأكد إن دي الروابط الصح بتاعتك)
S_ID = "18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc"
URL_F = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=1278191407"
URL_S = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=0"
URL_Q = f"https://docs.google.com/spreadsheets/d/{S_ID}/export?format=csv&gid=468167747"

@st.cache_data(ttl=2)
def load_and_sync():
    try:
        # قراءة البيانات مع التأكد من الروابط
        f = pd.read_csv(URL_F).dropna(how='all')
        s = pd.read_csv(URL_S).dropna(subset=['Month'])
        q = pd.read_csv(URL_Q).dropna(subset=['Agent Name'])
        
        # تنظيف أسماء الأعمدة من أي مسافات مستخبية
        for d in [f, s, q]:
            d.columns = d.columns.str.strip()
            for col in d.select_dtypes(['object']).columns:
                d[col] = d[col].astype(str).str.strip()
        
        return f, s, q
    except Exception as e:
        st.error(f"Error loading data: {e}") # ده هيقولنا المشكلة فين بالظبط لو فشل
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_f, df_s, df_q = load_and_sync()

# التحقق إن الجدول الأساسي فيه بيانات
if not df_f.empty:
    st.sidebar.title(f"👤 Role: {user_role.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state['auth'] = False
        st.rerun()

    # --- الفلاتر (تأكد إن الأسماء دي موجودة في الشيت بالظبط) ---
    all_agents = sorted(df_f['Agent'].unique()) if 'Agent' in df_f.columns else []
    f_agent = st.sidebar.multiselect("👤 Select Agents", all_agents)
    
    ff = df_f.copy()
    if f_agent: ff = ff[ff['Agent'].isin(f_agent)]

    # --- القوائم (Tabs) ---
    tabs_labels = ["🏠 Overview"]
    if user_role == "admin":
        tabs_labels += ["💬 WhatsApp SLA", "📈 Inbound SLA", "🏆 Quality Ranking"]
    
    tabs = st.tabs(tabs_labels)

    with tabs[0]:
        st.title("📊 DSQUARES INSIGHTS HUB")
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Tickets", f"{len(ff):,}")
        
        # عرض الـ Charts
        if 'Merchant' in ff.columns:
            st.plotly_chart(px.bar(ff['Merchant'].value_counts().head(10), title="Top 10 Merchants"), use_container_width=True)
        
        # الجدول والبحث
        st.divider()
        search_query = st.text_input("🔍 Search tickets:")
        if search_query:
            ff_display = ff[ff.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
        else: ff_display = ff
        st.dataframe(ff_display.head(100), use_container_width=True)

else:
    st.warning("⚠️ Data is empty. Please check your Google Sheet link and GID.")
    st.info(f"Link used: {URL_F}")