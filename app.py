import streamlit as st
import pandas as pd
import pymongo
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. DATABASE & CONFIGURATION
# ==========================================
# Auto-refresh every 5 seconds to catch n8n updates
st_autorefresh(interval=5000, key="uav_live_update")

MONGO_URL = "mongodb+srv://mohamedjasimalani_db_user:ALWVoICT5PA3DP7n@uav.mxvutct.mongodb.net/?appName=UAV"
client = pymongo.MongoClient(MONGO_URL)
db = client.UAV_Project
collection = db.logs

st.set_page_config(page_title="UAV Control Center", layout="wide")

# Custom CSS for university branding
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .uni-text { text-align: right; color: #58a6ff; font-weight: bold; margin-bottom: 0px; }
    .sub-text { text-align: right; color: #8b949e; font-size: 14px; margin-top: 0px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATA PROCESSING
# ==========================================
data = list(collection.find().sort("timestamp", -1).limit(500))

def get_gas_status(voltage):
    if voltage < 0.4: return "🍃 Clean", "#00ff00"
    elif voltage < 1.0: return "⚠️ Moderate", "#ffa500"
    else: return "🚨 Hazardous", "#ff0000"

if data:
    df = pd.DataFrame(data)
    numeric_cols = ['temp', 'hum', 'gas', 'alt', 'lat', 'lon', 'flight_time', 'sd_status']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.fillna(0)
    
    latest = df.iloc[0]
    status_text, status_color = get_gas_status(latest['gas'])

    # ==========================================
    # 3. HEADER WITH UNIVERSITY BRANDING (RIGHT SIDE)
    # ==========================================
    head_left, head_right = st.columns([3, 1])
    
    with head_left:
        st.title("🛸 UAV Air Pollution Monitoring")
        st.subheader(f"System Status: {status_text}")
    
    with head_right:
        # Check if logo exists, otherwise use placeholder
        try:
            st.image("logo.png", width=100)
        except:
            st.markdown("<h1 style='text-align: right;'>🎓</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='uni-text'>Mohammed Jassim Mahmoud</p>", unsafe_allow_html=True)
        st.markdown("<p class='sub-text'>College of Control and Systems Engineering</p>", unsafe_allow_html=True)

    st.write("---")

    # ==========================================
    # 4. DASHBOARD METRICS
    # ==========================================
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Smoke/Gas Level", f"{latest['gas']:.2f} V", status_text)
    m2.metric("Flight Duration", f"{int(latest['flight_time']//60)}m {int(latest['flight_time']%60)}s")
    m3.metric("Humidity", f"{latest['hum']:.1f}%")
    
    sd_health = "✅ OK" if latest['sd_status'] == 1 else "❌ FAIL"
    m4.metric("Black Box (SD)", sd_health)

    # ==========================================
    # 5. 3D TRAJECTORY & GAUGES
    # ==========================================
    col_map, col_anl = st.columns([2, 1])

    with col_map:
        st.write("### 🌐 3D Geospatial Trajectory")
        map_df = df[(df['lat'] != 0) & (df['lon'] != 0)].copy()
        if not map_df.empty:
            fig_3d = px.line_3d(map_df, x='lat', y='lon', z='alt', color='gas',
                                color_continuous_scale="RdYlGn_r",
                                labels={'gas': 'Pollution (V)'})
            fig_3d.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_3d, use_container_width=True)
        else:
            st.info("Awaiting GPS Lock... Map will render once satellites are acquired.")

    with col_anl:
        st.write("### 📈 Sensor Correlation")
        # Overlap Chart
        fig_overlap = go.Figure()
        fig_overlap.add_trace(go.Scatter(x=df.index, y=df['gas'], name="Gas (V)", line=dict(color='red')))
        fig_overlap.add_trace(go.Scatter(x=df.index, y=df['temp'], name="Temp (C)", line=dict(color='orange'), yaxis="y2"))
        
        fig_overlap.update_layout(
            template="plotly_dark", height=450,
            yaxis=dict(title="Gas Voltage"),
            yaxis2=dict(title="Temperature", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_overlap, use_container_width=True)

else:
    st.warning("📡 System Offline: Waiting for data from n8n...")
