import streamlit as st
import pandas as pd
import plotly.express as px

# 1. إعدادات الصفحة
st.set_page_config(page_title="DSQUARES HUB", layout="wide")

# --- 🔒 نظام الصلاحيات (البوابة) ---
if 'auth' not in st.session_state:
    st.session_state['auth'] = False

if not st.session_state['auth']:
    st.title("🔐 Welcome to DSQUARES HUB")
    st.write("Please enter your access code to view the dashboard.")
    pwd = st.text_input("Access Code:", type="password")
    if st.button("Login"):
        if pwd == "admin123": # الباسورد الشاملة ليك (بتشوف كل حاجة)
            st.session_state['auth'] = "admin"
            st.rerun()
        elif pwd == "team-ds": # باسورد الفريق (بيشوفوا الـ Overview بس)
            st.session_state['auth'] = "team"
            st.rerun()
        else:
            st.error("Invalid Code! Please contact Mohamed Shawky.")
    st.stop()

user_role = st.session_state['auth']

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
        m_order = ['26-Jan', '26-Feb', '26-Mar', '26-Apr', '26-May', '26-Jun', '26-Jul', '26-Aug']
        s['Month'] = pd.Categorical(s['Month'], categories=m_order, ordered=True)
        return f, s, q
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def to_n(series):
    return pd.to_numeric(series.astype(str).str.replace('%','').str.replace(',',''), errors='coerce').fillna(0)

df_f, df_s, df_q = load_and_sync()

if not df_f.empty:
    # --- 🕹️ Sidebar ---
    st.sidebar.title(f"👤 Role: {user_role.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state['auth'] = False
        st.rerun()
    
    # الفلاتر
    all_agents = sorted(df_f['Agent'].unique())
    f_agent = st.sidebar.multiselect("👤 Select Agents", all_agents)
    
    ff = df_f.copy()
    if f_agent: ff = ff[ff['Agent'].isin(f_agent)]

    # --- تحديد الـ Tabs المسموحة ---
    tabs_labels = ["🏠 Overview"]
    if user_role == "admin":
        tabs_labels += ["💬 WhatsApp SLA", "📈 Inbound SLA", "🏆 Quality Ranking"]
    
    st.title("📊 DSQUARES INSIGHTS HUB")
    tabs = st.tabs(tabs_labels)

    # --- 1. OVERVIEW (متاح للكل) ---
    with tabs[0]:
        k1, k2, k3 = st.columns(3)