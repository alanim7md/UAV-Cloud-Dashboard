import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
import plotly.express as px
import plotly.graph_objects as go
import os

# 1. DATABASE CONNECTION
MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

# 2. UI CONFIGURATION
st.set_page_config(page_title="UAV GCS Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ff00; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: SYSTEM CONTROL & BRANDING ---
with st.sidebar:
    # Look for a local logo file, otherwise fallback to text
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.header("🛰️ Command Center")
    st.caption("University of Technology | Evening Study Program")
    st.write("---")
    
    st.subheader("Manual Data Import")
    uploaded_file = st.file_uploader("Upload Flight CSV", type="csv")
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            df_upload['timestamp'] = datetime.now()
            if st.button("Sync CSV to Cloud"):
                collection.insert_many(df_upload.to_dict('records'))
                st.success("Cloud Synchronized! Refreshing...")
                st.rerun()
        except Exception as e:
            st.error(f"Upload Error: {e}")

# --- DATA RECEIVER (FOR PICO W) ---
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

# --- DATA PROCESSING & CLEANING ---
# Increased limit to 1000 for a more "measurable" and substantial dataset
data = list(collection.find().sort("timestamp", -1).limit(1000))

if data:
    df = pd.DataFrame(data)
    
    # Convert MongoDB ObjectId to string for Streamlit compatibility
    df['_id'] = df['_id'].astype(str)
    
    cols_to_clean = ['alt', 'gas', 'temp', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.fillna(0)
    
    # --- UI LAYOUT ---
    st.title("🛸 UAV Air Pollution Monitoring System")
    st.markdown(f"**Operator:** Muhammad Jassim Mahmoud | **Status:** Connected to Atlas Database")

    # ROW 1: MISSION CRITICAL GAUGES & PEAK STATS
    col1, col2, col3, col4 = st.columns(4)
    
    latest_gas = df['gas'].iloc[0]
    fig_gas = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = latest_gas,
        title = {'text': "Current Gas (V)"},
        gauge = {
            'axis': {'range': [0, 5]},
            'bar': {'color': "red" if latest_gas > 2 else "green"},
            'steps': [{'range': [0, 2], 'color': "gray"}, {'range': [2, 5], 'color': "black"}]
        }
    ))
    fig_gas.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="#161b22", font={'color': "white"})
    col1.plotly_chart(fig_gas, use_container_width=True)

    col2.metric("Current Altitude", f"{df['alt'].iloc[0]:.1f} m", f"Peak: {df['alt'].max():.1f} m")
    col3.metric("Ambient Temp", f"{df['temp'].iloc[0]:.1f} °C")
    col4.metric("Peak Pollution Detected", f"{df['gas'].max():.2f} V", "Hazard Level" if df['gas'].max() > 2.5 else "Safe")

    # ROW 2: SPATIAL ANALYSIS
    m_col1, m_col2 = st.columns([2, 1])
    
    with m_col1:
        st.subheader("📍 Geospatial Pollution Profile")
        fig_map = px.scatter_mapbox(df, lat="lat", lon="lon", color="gas", size="alt",
                                    color_continuous_scale="RdYlGn_r", size_max=15, zoom=13,
                                    mapbox_style="carto-darkmatter")
        fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#161b22")
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.subheader("📈 Flight Analytics")
        fig_poll = px.area(df, x="timestamp", y="gas", title="Pollution Timeline", color_discrete_sequence=["#ff4b4b"])
        fig_poll.update_layout(height=240, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_poll, use_container_width=True)
        
        fig_alt = px.line(df, x="timestamp", y="alt", title="Altitude Profile", color_discrete_sequence=["#00d4ff"])
        fig_alt.update_layout(height=240, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_alt, use_container_width=True)

    # ROW 3: INTERACTIVE DATA MANAGEMENT
    st.write("---")
    st.subheader("🛠️ Database Management")
    st.caption("Double-click any cell to edit data. Select a row and press 'Delete' on your keyboard to remove a spike. You MUST click 'Commit' to save to MongoDB.")
    
    # The interactive data editor
    edited_df = st.data_editor(df, key="data_editor", num_rows="dynamic", use_container_width=True)
    
    # Sync Logic
    if st.button("💾 Commit Changes to Cloud"):
        with st.spinner("Updating database..."):
            # 1. Handle Deletions (IDs that exist in MongoDB but were deleted from the UI)
            original_ids = set(df['_id'])
            new_ids = set(edited_df['_id'].dropna())
            deleted_ids = original_ids - new_ids
            
            for del_id in deleted_ids:
                collection.delete_one({"_id": ObjectId(del_id)})
            
            # 2. Handle Modifications (Updates to existing rows)
            # Find rows where values changed
            comparison = df.compare(edited_df, keep_shape=True, keep_equal=False)
            if not comparison.empty:
                for index, row in edited_df.iterrows():
                    # Only update if the row still exists and was modified
                    if str(row['_id']) in original_ids:
                        update_data = {
                            "temp": row['temp'],
                            "gas": row['gas'],
                            "lat": row['lat'],
                            "lon": row['lon'],
                            "alt": row['alt']
                        }
                        collection.update_one({"_id": ObjectId(row['_id'])}, {"$set": update_data})
            
            st.success("Database successfully updated!")
            st.rerun()

else:
    st.warning("Awaiting Data Stream. Ensure payload is transmitting.")
