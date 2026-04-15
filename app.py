import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================
MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

# ==========================================
# 2. UI CONFIGURATION & BRANDING
# ==========================================
st.set_page_config(page_title="UAV GCS Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ff00; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: SYSTEM CONTROL ---
with st.sidebar:
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
            
            # Spread timestamps out realistically using the flight seconds
            if 'time' in df_upload.columns:
                base_time = datetime.now()
                df_upload['timestamp'] = df_upload['time'].apply(lambda x: base_time + pd.Timedelta(seconds=float(x)))
            else:
                df_upload['timestamp'] = datetime.now()
                
            if st.button("Sync CSV to Cloud"):
                collection.insert_many(df_upload.to_dict('records'))
                st.success("Cloud Synchronized! Refreshing...")
                st.rerun()
        except Exception as e:
            st.error(f"Upload Error: {e}")

# ==========================================
# 3. LIVE PICO W RECEIVER
# ==========================================
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

# ==========================================
# 4. DATA PROCESSING & VISUALIZATION
# ==========================================
data = list(collection.find().sort("timestamp", -1).limit(1000))

if data:
    df = pd.DataFrame(data)
    df['_id'] = df['_id'].astype(str)
    
    # Clean data to prevent chart crashes
    for col in ['alt', 'gas', 'temp', 'lat', 'lon']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.fillna(0)
    
    # --- DASHBOARD HEADER ---
    st.title("🛸 UAV Air Pollution Monitoring System")
    st.markdown("**Operator:** Muhammad Jassim Mahmoud | **Status:** Connected to Atlas Database")

    # --- ROW 1: MISSION METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    
    latest_gas = df['gas'].iloc[0]
    fig_gas = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = latest_gas,
        title = {'text': "Current Gas (V)"},
        gauge = {'axis': {'range': [0, 5]}, 'bar': {'color': "red" if latest_gas > 2 else "green"}}
    ))
    fig_gas.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="#161b22", font={'color': "white"})
    col1.plotly_chart(fig_gas, use_container_width=True)

    col2.metric("Current Altitude", f"{df['alt'].iloc[0]:.1f} m", f"Peak: {df['alt'].max():.1f} m")
    col3.metric("Ambient Temp", f"{df['temp'].iloc[0]:.1f} °C")
    col4.metric("Peak Pollution", f"{df['gas'].max():.2f} V", "Hazard" if df['gas'].max() > 2.5 else "Safe")

    # --- ROW 2: 2D & 3D GEOSPATIAL PROFILES ---
    m_col1, m_col2 = st.columns([1, 1])
    
    with m_col1:
        st.subheader("📍 2D Pollution Map")
        valid_map_df = df[(df['lat'] != 0) & (df['lon'] != 0)].copy()
        valid_map_df['alt_safe'] = valid_map_df['alt'].apply(lambda x: x if x > 0 else 0.1)
        
        fig_map = px.scatter_mapbox(valid_map_df, lat="lat", lon="lon", color="gas", size="alt_safe",
                                    color_continuous_scale="RdYlGn_r", size_max=15, zoom=14,
                                    mapbox_style="carto-darkmatter")
        fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#161b22")
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.subheader("🌐 3D Flight Trajectory")
        fig_3d = px.scatter_3d(valid_map_df, x='lat', y='lon', z='alt', color='gas',
                               color_continuous_scale="RdYlGn_r", labels={'gas': 'Pollution (V)'})
        # Force lines between the scatter points to draw the flight path
        fig_3d.update_traces(mode='lines+markers', marker=dict(size=4), line=dict(width=3, color='rgba(150, 150, 150, 0.5)'))
        fig_3d.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#161b22")
        st.plotly_chart(fig_3d, use_container_width=True)

    # --- ROW 3: DATABASE MANAGER ---
    st.write("---")
    st.subheader("🛠️ Database Management")
    edited_df = st.data_editor(df, key="data_editor", num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Commit Changes to Cloud"):
        with st.spinner("Updating database..."):
            original_ids = set(df['_id'])
            new_ids = set(edited_df['_id'].dropna())
            
            # Handle Deletions
            for del_id in (original_ids - new_ids):
                collection.delete_one({"_id": ObjectId(del_id)})
            
            # Handle Modifications
            df_idx = df.set_index('_id')
            edit_idx = edited_df.dropna(subset=['_id']).set_index('_id')
            common_ids = df_idx.index.intersection(edit_idx.index)
            
            for row_id in common_ids:
                old_row = df_idx.loc[row_id]
                new_row = edit_idx.loc[row_id]
                
                if (old_row['alt'] != new_row['alt'] or old_row['gas'] != new_row['gas'] or old_row['temp'] != new_row['temp']):
                    collection.update_one({"_id": ObjectId(row_id)}, {"$set": {
                        "temp": float(new_row['temp']), "gas": float(new_row['gas']),
                        "lat": float(new_row['lat']), "lon": float(new_row['lon']), "alt": float(new_row['alt'])
                    }})
            
            st.success("Database successfully updated!")
            st.rerun()
else:
    st.warning("Awaiting Data Stream. Ensure payload is transmitting.")
