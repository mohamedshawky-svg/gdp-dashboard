import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dsquares Hub", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;color:white;} div[data-testid='stMetricValue']{color:#00d2ff;text-shadow:0 0 10px #00d2ff;}</style>", unsafe_allow_label_html=True)

st.title("📊 DSQUARES INSIGHTS HUB")

url = "https://docs.google.com/spreadsheets/d/18ujwRjkA8L3BIJzevw1QCxjtjIRXdgQ8Du6P2m9LYRc/export?format=csv"

try:
    df = pd.read_csv(url)
    c1, c2 = st.columns(2)
    c1.metric("TOTAL TICKETS", len(df))
    if 'Type' in df.columns:
        st.plotly_chart(px.pie(df, names='Type', template="plotly_dark", hole=0.4), use_container_width=True)
    st.subheader("Live Stream")
    st.dataframe(df.tail(10), use_container_width=True)
except Exception as e:
    st.error(f"Waiting for Data... Error: {e}")