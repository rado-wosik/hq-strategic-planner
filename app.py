import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Data Bridge Engine | HQ Strategic Planner", layout="wide")

# CSS: High-Contrast Enterprise Design
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #05070a; color: #ffffff; }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #10141d; border-right: 1px solid #2d3748; }
    
    /* Project Branding */
    .project-header { color: #00aeef; font-size: 0.9rem; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; margin-bottom: -10px; }
    .engine-header { color: #ffffff; font-size: 2.5rem; font-weight: 800; margin-bottom: 20px; }

    /* KPI Cards - Maximum Contrast */
    div[data-testid="stMetric"] {
        background-color: #1a1f2c; 
        border: 2px solid #3b445c; 
        padding: 20px; 
        border-radius: 12px;
    }
    div[data-testid="stMetricLabel"] > div {
        color: #ffffff !important; 
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        opacity: 0.9;
    }
    div[data-testid="stMetricValue"] > div {
        color: #ffffff !important; 
        font-size: 2rem !important;
        font-weight: 800 !important;
    }

    /* Sidebar text clarity */
    .stSlider label, .stSelectbox label { color: #ffffff !important; font-size: 1rem !important; font-weight: 600 !important; }
    .stMarkdown, p, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (CONTROLS) ---
with st.sidebar:
    st.markdown('<p style="color: #00aeef; font-weight: bold; margin-bottom: 0;">DATA BRIDGE ENGINE</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1.4rem; font-weight: 800; margin-top: 0; color: #ffffff;">HQ Strategic Planner</p>', unsafe_allow_html=True)
    
    st.divider()
    selected_month = st.select_slider("Analysis Month", 
                             options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                             value="Jan")
    
    st.markdown("### Generation Mix (GW)")
    s_hydro = st.slider("Hydro Assets", 30.0, 55.0, 37.0)
    s_wind = st.slider("Wind Power", 0.0, 30.0, 5.0)
    s_pv = st.slider("Solar PV", 0.0, 20.0, 2.0)
    
    st.divider()
    st.markdown("### Grid & Market")
    s_inter_cap = st.slider("Interconnection Capacity (GW)", 0.0, 10.0, 2.5)

# --- 3. CORE LOGIC (WEATHER & PROFILES) ---
def get_weather_data(month):
    m_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m_idx = m_list.index(month)
    # Seasonality factors: PV, Wind, Demand
    pv_f = [0.15, 0.3, 0.6, 0.8, 0.95, 1.0, 0.98, 0.85, 0.65, 0.4, 0.2, 0.1][m_idx]
    wind_f = [1.0, 0.95, 0.85, 0.7, 0.5, 0.4, 0.45, 0.5, 0.65, 0.8, 0.9, 0.98][m_idx]
    dem_f = [1.0, 0.9, 0.75, 0.6, 0.55, 0.5, 0.55, 0.52, 0.58, 0.7, 0.85, 0.95][m_idx]
    return pv_f, wind_f, dem_f

pv_f, wind_f, dem_f = get_weather_data(selected_month)
h_range = np.arange(168) # 1 week

# Simulation Engine
demand = (26 + 11 * np.sin(np.linspace(0, 14 * np.pi, 168)) + 4 * np.cos(np.linspace(0, 7 * np.pi, 168))) * dem_f
g_pv = s_pv * np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5 * np.pi, 168))) * pv_f
g_w = s_wind * (0.6 + 0.3 * np.cos(np.linspace(0, 10 * np.pi, 168))) * wind_f
g_h = np.clip(demand - (g_pv + g_w), s_hydro * 0.35, s_hydro)

balance = (g_h + g_pv + g_w) - demand
export = np.minimum(np.maximum(0, balance), s_inter_cap)
shortage = np.maximum(0, -balance)

# --- 4. MAIN DASHBOARD ---
st.markdown('<p class="project-header">Strategic Evolution: Hydro-Québec 2050</p>', unsafe_allow_html=True)
st.markdown('<p class="engine-header">Data Bridge Engine</p>', unsafe_allow_html=True)

# KPI Section
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Demand", f"{demand.mean():.1f} GW")
k2.metric("VRE Efficiency", f"{((g_w.mean()+g_pv.mean())/(s_wind+s_pv+0.1)*100):.1f}%")
k3.metric("Peak Shortage", f"{shortage.max():.2f} GW")
k4.metric("Est. Weekly Export", f"{(export.sum()*85/1000):,.0f} k$")

# --- 5. VISUALIZATION ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=h_range, y=demand, name="Total Demand", line=dict(color='#ffffff', width=4, dash='dot')))
fig.add_trace(go.Scatter(x=h_range, y=g_h, name="Hydro Generation", stackgroup='one', fillcolor='#00aeef', line=dict(width=0)))
fig.add_trace(go.Scatter(x=h_range, y=g_w, name="Wind Generation", stackgroup='one', fillcolor='#39b54a', line=dict(width=0)))
fig.add_trace(go.Scatter(x=h_range, y=g_pv, name="Solar PV Generation", stackgroup='one', fillcolor='#ffc20e', line=dict(width=0)))

fig.update_layout(
    template="plotly_dark",
    height=550,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
        font=dict(size=13, color="#ffffff")
    ),
    xaxis=dict(gridcolor='#2d3748', tickfont=dict(color='#ffffff'), title="Hours of the Week"),
    yaxis=dict(gridcolor='#2d3748', tickfont=dict(color='#ffffff'), title="Power [GW]")
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. SEASONAL INSIGHTS ---
st.divider()
c_left, c_right = st.columns(2)

with c_left:
    st.subheader("Seasonal Scenario Analysis")
    if selected_month in ["Dec", "Jan", "Feb"]:
        st.error("❄️ **WINTER SEASON:** Peak heating demand. Wind assets are the primary VRE contributor. Hydro reservoirs are in draw-down mode.")
    elif selected_month in ["Mar", "Apr", "May"]:
        st.warning("🌊 **SPRING SEASON:** Freshet (spring runoff) detected. High hydro inflows. Potential for maximum export or system curtailment.")
    elif selected_month in ["Jun", "Jul", "Aug"]:
        st.success("☀️ **SUMMER SEASON:** Lower domestic demand. Peak Solar PV performance. Opportunity for reservoir accumulation and asset maintenance.")
    else:
        st.info("🍂 **AUTUMN SEASON:** Transition period. Increasing wind generation and rising evening peaks.")

with c_right:
    st.subheader("Export Dispatch (USA Interconnects)")
    
    fig_e = go.Figure(go.Bar(x=h_range, y=export, name="Export dispatched", marker_color='#10b981'))
    fig_e.update_layout(
        template="plotly_dark", height=220, margin=dict(t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(tickfont=dict(color='#ffffff')), yaxis=dict(tickfont=dict(color='#ffffff'))
    )
    st.plotly_chart(fig_e, use_container_width=True)

st.markdown("---")
st.caption("Data Bridge Engine v2.5 | Strategic Simulation Environment | Hydro-Québec Deployment")