import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import plotly.express as px

# 1. Database Connection
# Replace the string below with your exact one if different
MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

st.set_page_config(page_title="UAV Telemetry GCS", layout="wide")
st.title("🛸 UAV Air Pollution Cloud Dashboard")

# 2. DATA RECEIVER (The endpoint for your Pico W)
# Your Pico will ping: your-site.render.com/?temp=25&gas=0.15&lat=33.3&lon=44.4&alt=12
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
        st.toast("🚀 New Flight Data Received!")
    except Exception as e:
        st.error(f"Data error: {e}")

# 3. VISUALIZATION DASHBOARD
data = list(collection.find().sort("timestamp", -1))

if data:
    df = pd.DataFrame(data)
    
    # Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Altitude", f"{df['alt'].iloc[0]} m")
    col2.metric("Gas Voltage", f"{df['gas'].iloc[0]} V")
    col3.metric("Last Temp", f"{df['temp'].iloc[0]} °C")

    # Interactive Map
    st.subheader("📍 Real-time Flight Path")
    # Streamlit's st.map expects 'lat' and 'lon' columns
    st.map(df)

    # Pollution Analysis Graph
    st.subheader("📊 Altitude vs. Gas Concentration")
    fig = px.scatter(df, x="alt", y="gas", color="temp", 
                     labels={"alt": "Altitude (m)", "gas": "MQ-135 (V)"},
                     title="Pollution Profile")
    st.plotly_chart(fig, use_container_width=True)

    # Raw Data Table
    with st.expander("View Raw Flight Logs"):
        st.write(df.drop(columns=['_id']))
else:
    st.warning("No flight data found. Connect your Pico W to start logging.")