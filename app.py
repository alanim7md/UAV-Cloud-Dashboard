import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# 1. Database Connection
MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

# UI Configuration
st.set_page_config(page_title="UAV GCS Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for that "Engineering" look
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_content=True)

# --- SIDEBAR: MANUAL UPLOAD & STATUS ---
with st.sidebar:
    st.header("🛰️ Command Center")
    st.info("Evening Study Program - Mechatronics") #
    
    st.subheader("Manual Data Import")
    uploaded_file = st.file_uploader("Upload Flight CSV", type="csv")
    
    if uploaded_file is not None:
        df_upload = pd.read_csv(uploaded_file)
        # Ensure timestamp is added for the database
        df_upload['timestamp'] = datetime.now()
        if st.button("Sync CSV to Cloud"):
            collection.insert_many(df_upload.to_dict('records'))
            st.success("Cloud Synchronized!")

# --- DATA PROCESSING ---
# Handle incoming Live Pings (Pico W)
query_params = st.query_params
if query_params:
    try:
        new_entry = {
            "timestamp": datetime.now(),
            "temp": float(query_params.get("temp", 0)),
            "gas": float(query_params.get("gas", 0)),
            "lat": float(query_params.get("lat", 0)),
            "lon": float(query_params.get("lon", 0)),
            "alt": float(query_params.get("alt", 0))
        }
        collection.insert_one(new_entry)
        st.toast("Live Telemetry Received")
    except: pass

# Fetch all data
data = list(collection.find().sort("timestamp", -1))

if data:
    df = pd.DataFrame(data)
    
    # --- UI LAYOUT ---
    st.title("🛸 UAV Air Pollution Monitoring System")
    st.caption(f"Project by Muhammad Jassim Mahmoud | University of Technology") #

    # TOP ROW: THE GAUGES
    col1, col2, col3, col4 = st.columns(4)
    
    # Current Gas Sensor (MQ-135)
    gas_val = df['gas'].iloc[0]
    fig_gas = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = gas_val,
        title = {'text': "Gas Concentration (V)"},
        gauge = {'axis': {'range': [0, 5]}, 'bar': {'color': "#00ff00" if gas_val < 2 else "#ff0000"}}
    ))
    fig_gas.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="#161b22", font={'color': "white"})
    col1.plotly_chart(fig_gas, use_container_width=True)

    col2.metric("Current Altitude", f"{df['alt'].iloc[0]}m", delta=f"{df['alt'].iloc[0] - df['alt'].iloc[1] if len(df)>1 else 0}m")
    col3.metric("Ambient Temp", f"{df['temp'].iloc[0]}°C")
    col4.metric("Total Logs", len(df))

    # MIDDLE ROW: THE MAP & ANALYTICS
    m_col1, m_col2 = st.columns([2, 1])
    
    with m_col1:
        st.subheader("📍 Geospatial Pollution Mapping")
        # Color path by Gas Concentration
        fig_map = px.scatter_mapbox(df, lat="lat", lon="lon", color="gas", size="alt",
                                    color_continuous_scale=px.colors.cyclical.IceFire, size_max=15, zoom=12,
                                    mapbox_style="carto-darkmatter")
        fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.subheader("📈 Vertical Profile")
        fig_alt = px.line(df, x="timestamp", y="alt", title="Flight Path (Altitude)")
        fig_alt.update_layout(height=240, template="plotly_dark")
        st.plotly_chart(fig_alt, use_container_width=True)
        
        fig_poll = px.area(df, x="timestamp", y="gas", title="Pollution Over Time")
        fig_poll.update_layout(height=240, template="plotly_dark")
        st.plotly_chart(fig_poll, use_container_width=True)

    # BOTTOM ROW: DETAILED TABLE
    with st.expander("📝 Full Mission Log (CSV Format)"):
        st.dataframe(df.drop(columns=['_id']), use_container_width=True)

else:
    st.warning("Awaiting Data Stream...")