import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# 1. DATABASE CONNECTION
# Using your verified MongoDB credentials
MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

# 2. UI CONFIGURATION
st.set_page_config(page_title="UAV GCS Pro", layout="wide", initial_sidebar_state="expanded")

# Corrected Style Injector (Fixes the MarkdownMixin error)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ff00; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: SYSTEM CONTROL ---
with st.sidebar:
    st.header("🛰️ Command Center")
    st.caption("University of Technology | Mechatronics") #
    st.write("---")
    
    # CSV Data Importer
    st.subheader("Manual Data Import")
    uploaded_file = st.file_uploader("Upload Flight CSV", type="csv")
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            # Add timestamp to help with cloud sorting
            df_upload['timestamp'] = datetime.now()
            if st.button("Sync CSV to Cloud"):
                collection.insert_many(df_upload.to_dict('records'))
                st.success("Cloud Synchronized!")
        except Exception as e:
            st.error(f"Upload Error: {e}")

# --- DATA RECEIVER (FOR PICO W) ---
query_params = st.query_params
if query_params:
    try:
        new_entry = {
            "timestamp": datetime.now(),
            "temp": query_params.get("temp", 0),
            "gas": query_params.get("gas", 0),
            "lat": query_params.get("lat", 0),
            "lon": query_params.get("lon", 0),
            "alt": query_params.get("alt", 0)
        }
        collection.insert_one(new_entry)
        st.toast("Live Telemetry Received")
    except: pass

# --- DATA PROCESSING & CLEANING ---
# Fetching only the last 100 points to keep the Free Tier responsive
data = list(collection.find().sort("timestamp", -1).limit(100))

if data:
    df = pd.DataFrame(data)
    
    # STRICTURE DATA CLEANING (Fixes the 'nan' Map Crash)
    cols_to_clean = ['alt', 'gas', 'temp', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Fill missing values with 0 to prevent Plotly ValueErrors
    df = df.fillna(0)
    
    # --- UI LAYOUT ---
    st.title("🛸 UAV Air Pollution Monitoring Dashboard")
    st.markdown(f"**Operator:** Muhammad Jassim Mahmoud | **Status:** Connected to Cloud") #

    # ROW 1: MISSION CRITICAL GAUGES
    col1, col2, col3, col4 = st.columns(4)
    
    # MQ-135 Gas Intensity Gauge
    latest_gas = df['gas'].iloc[0]
    fig_gas = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = latest_gas,
        title = {'text': "Gas Concentration (V)"},
        gauge = {
            'axis': {'range': [0, 5]},
            'bar': {'color': "red" if latest_gas > 2 else "green"},
            'steps': [{'range': [0, 2], 'color': "gray"}, {'range': [2, 5], 'color': "black"}]
        }
    ))
    fig_gas.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="#161b22", font={'color': "white"})
    col1.plotly_chart(fig_gas, use_container_width=True)

    col2.metric("Altitude (m)", f"{df['alt'].iloc[0]:.1f}")
    col3.metric("Air Temp (°C)", f"{df['temp'].iloc[0]:.1f}")
    col4.metric("Logged Points", len(df))

    # ROW 2: SPATIAL ANALYSIS
    m_col1, m_col2 = st.columns([2, 1])
    
    with m_col1:
        st.subheader("📍 Geospatial Pollution Profile")
        # Color coding the path by gas severity
        fig_map = px.scatter_mapbox(df, lat="lat", lon="lon", color="gas", size="alt",
                                    color_continuous_scale="RdYlGn_r", size_max=12, zoom=13,
                                    mapbox_style="carto-darkmatter")
        fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#161b22")
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.subheader("📈 Vertical Data")
        # Gas vs Altitude scatter plot
        fig_scatter = px.scatter(df, x="alt", y="gas", color="temp", template="plotly_dark")
        fig_scatter.update_layout(height=480)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ROW 3: MISSION LOGS
    with st.expander("📝 View Raw Flight Telemetry"):
        st.dataframe(df.drop(columns=['_id']), use_container_width=True)

else:
    st.warning("Awaiting Data Stream. Ensure Pico W is connected to phone hotspot.")
