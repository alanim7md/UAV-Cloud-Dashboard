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
# 2. UI & BRANDING CONFIGURATION
# ==========================================
st.set_page_config(page_title="UAV GCS Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00ff00; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.header("🛰️ Command Center")
    st.caption("University of Technology | Evening Study Program")
    st.write("---")
    
    st.subheader("Manual SD Card Import")
    uploaded_file = st.file_uploader("Upload flight_log.csv", type="csv")
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            # Reconstruct timeline from the Pico's 'time_s' column
            if 'time_s' in df_upload.columns:
                base_time = datetime.now()
                df_upload['timestamp'] = df_upload['time_s'].apply(lambda x: base_time + pd.Timedelta(seconds=float(x)))
            else:
                df_upload['timestamp'] = datetime.now()
                
            if st.button("Sync Offline CSV to Cloud"):
                collection.insert_many(df_upload.to_dict('records'))
                st.success("Black Box Synchronized! Refreshing...")
                st.rerun()
        except Exception as e:
            st.error(f"Upload Error: Check CSV Headers. {e}")

# ==========================================
# 3. LIVE TELEMETRY RECEIVER
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
# 4. DATA PROCESSING & CLEANING
# ==========================================
data = list(collection.find().sort("timestamp", -1).limit(1000))

if data:
    df = pd.DataFrame(data)
    df['_id'] = df['_id'].astype(str)
    
    cols_to_clean = ['alt', 'gas', 'temp', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.fillna(0)
    
    # ==========================================
    # 5. UI LAYOUT
    # ==========================================
    st.title("🛸 UAV Air Pollution Monitoring System")
    st.markdown(f"**Operator:** Muhammad Jassim Mahmoud | **Telemetry:** DHT22 Calibrated")

    # ROW 1: MISSION CRITICAL GAUGES
    col1, col2, col3, col4 = st.columns(4)
    
    latest_gas = df['gas'].iloc[0]
    fig_gas = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = latest_gas,
        title = {'text': "Calibrated Gas (V)"},
        gauge = {
            'axis': {'range': [0, 3.5]}, # Tuned for the lighter test max range
            'bar': {'color': "red" if latest_gas > 1.0 else "#00ff00"},
            'steps': [
                {'range': [0, 0.5], 'color': "gray"}, 
                {'range': [0.5, 3.5], 'color': "darkred"}
            ]
        }
    ))
    fig_gas.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="#161b22", font={'color': "white"})
    col1.plotly_chart(fig_gas, use_container_width=True)

    # Calculate Relative Altitude (Current - Lowest recorded point)
    lowest_alt = df['alt'].min()
    relative_alt = df['alt'].iloc[0] - lowest_alt if lowest_alt < 0 else df['alt'].iloc[0]
    
    col2.metric("Relative Altitude", f"{relative_alt:.1f} m", f"Raw Sensor: {df['alt'].iloc[0]:.1f}m")
    col3.metric("Ambient Temp", f"{df['temp'].iloc[0]:.1f} °C")
    col4.metric("Peak Pollution Detected", f"{df['gas'].max():.2f} V", "Hazard Level" if df['gas'].max() > 1.0 else "Normal")

    # ROW 2: SPATIAL ANALYSIS
    m_col1, m_col2 = st.columns([2, 1])
    
    with m_col1:
        st.subheader("📍 Geospatial Pollution Profile")
        
        # Map Safety Filter: Ignore null coordinates and use Gas for bubble size
        valid_map_df = df[(df['lat'] != 0) & (df['lon'] != 0)].copy()
        
        # Create a safe multiplier for the bubble size based on pollution intensity
        valid_map_df['gas_bubble_size'] = valid_map_df['gas'].apply(lambda x: (x * 10) if x > 0.1 else 1.0)
        
        fig_map = px.scatter_mapbox(valid_map_df, lat="lat", lon="lon", color="gas", size="gas_bubble_size",
                                    color_continuous_scale="RdYlGn_r", size_max=20, zoom=15,
                                    mapbox_style="carto-darkmatter")
        fig_map.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor="#161b22")
        st.plotly_chart(fig_map, use_container_width=True)

    with m_col2:
        st.subheader("📈 Flight Analytics")
        fig_poll = px.area(df, x="timestamp", y="gas", title="Pollution Timeline", color_discrete_sequence=["#ff4b4b"])
        fig_poll.update_layout(height=240, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_poll, use_container_width=True)
        
        fig_alt = px.line(df, x="timestamp", y="alt", title="Raw Altitude Profile", color_discrete_sequence=["#00d4ff"])
        fig_alt.update_layout(height=240, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_alt, use_container_width=True)

    # ROW 3: INTERACTIVE DATA MANAGEMENT
    st.write("---")
    st.subheader("🛠️ Database Management")
    st.caption("Double-click cells to edit. Select a row and press 'Delete' to remove anomalies. Click 'Commit' to save.")
    
    edited_df = st.data_editor(df, key="data_editor", num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Commit Changes to Cloud"):
        with st.spinner("Updating database..."):
            original_ids = set(df['_id'])
            new_ids = set(edited_df['_id'].dropna())
            deleted_ids = original_ids - new_ids
            
            for del_id in deleted_ids:
                collection.delete_one({"_id": ObjectId(del_id)})
            
            df_idx = df.set_index('_id')
            edit_idx = edited_df.dropna(subset=['_id']).set_index('_id')
            common_ids = df_idx.index.intersection(edit_idx.index)
            
            for row_id in common_ids:
                old_row = df_idx.loc[row_id]
                new_row = edit_idx.loc[row_id]
                
                if (old_row['alt'] != new_row['alt'] or old_row['gas'] != new_row['gas'] or old_row['temp'] != new_row['temp']):
                    update_data = {
                        "temp": float(new_row['temp']),
                        "gas": float(new_row['gas']),
                        "lat": float(new_row['lat']),
                        "lon": float(new_row['lon']),
                        "alt": float(new_row['alt'])
                    }
                    collection.update_one({"_id": ObjectId(row_id)}, {"$set": update_data})
            
            st.success("Database successfully updated!")
            st.rerun()

else:
    st.warning("Awaiting Data Stream. Ensure payload is transmitting and GPS has a lock.")
