import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Data Bridge Engine", layout="wide")

# CSS: Custom Clean Design
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #05080d; color: #ffffff; }
    
    /* SIDEBAR CLEANUP */
    [data-testid="stSidebar"] {
        background-color: #0f141c;
        border-right: 1px solid #1e2633;
        min-width: 320px !important;
    }
    
    /* Sidebar Labels & Text */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        margin-bottom: 5px !important;
    }

    /* Styling Headers */
    .section-header {
        color: #00aeef;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 25px;
        margin-bottom: 10px;
        border-bottom: 1px solid #1e2633;
        padding-bottom: 5px;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #161c26; 
        border: 1px solid #232d3d; 
        padding: 20px; 
        border-radius: 8px;
    }
    div[data-testid="stMetricValue"] > div { color: #00aeef !important; font-weight: 800 !important; }

    /* Buttons & Sliders Color */
    .stSlider > div [data-baseweb="slider"] { color: #00aeef; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (REDESIGNED) ---
with st.sidebar:
    # Top Branding
    st.markdown('<p style="color: #00aeef; font-weight: 900; font-size: 1.6rem; margin-bottom: -5px;">DATA BRIDGE</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1rem; color: #ffffff; opacity: 0.8;">STRATEGIC ENGINE v2.8</p>', unsafe_allow_html=True)
    
    # Section 1: Timeframe
    st.markdown('<div class="section-header">ENVIRONMENT</div>', unsafe_allow_html=True)
    selected_month = st.select_slider("Forecast Month", 
                             options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                             value="Jan")
    
    # Section 2: Capacity
    st.markdown('<div class="section-header">GENERATION MIX (GW)</div>', unsafe_allow_html=True)
    s_hydro = st.slider("Hydro Power", 30, 60, 37)
    s_wind = st.slider("Wind Power", 0, 40, 5)
    s_pv = st.slider("Solar PV", 0, 25, 2)
    
    # Section 3: Infrastructure
    st.markdown('<div class="section-header">INFRASTRUCTURE</div>', unsafe_allow_html=True)
    s_inter_cap = st.slider("Interconnectors (GW)", 0.0, 15.0, 2.5)

# --- 3. LOGIC (STABLE CALCULATIONS) ---
def get_weather_factors(month):
    m_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    idx = m_list.index(month)
    return [0.1, 0.25, 0.5, 0.8, 0.95, 1.0, 0.95, 0.8, 0.6, 0.35, 0.15, 0.05][idx], \
           [1.0, 0.9, 0.8, 0.65, 0.45, 0.35, 0.4, 0.45, 0.6, 0.8, 0.9, 0.95][idx], \
           [1.0, 0.9, 0.75, 0.6, 0.55, 0.5, 0.55, 0.52, 0.58, 0.7, 0.85, 0.95][idx]

pv_f, wind_f, dem_f = get_weather_factors(selected_month)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
time_axis = [f"{d} {h:02d}:00" for d in days for h in range(24)]

# Generation Profiles
demand = (28 + 10 * np.sin(np.linspace(0, 14 * np.pi, 168))) * dem_f
demand[120:] *= 0.85 # Weekend drop
g_pv = s_pv * np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5 * np.pi, 168))) * pv_f
g_w = s_wind * (0.6 + 0.3 * np.cos(np.linspace(0, 10 * np.pi, 168))) * wind_f
g_h = np.clip(demand - (g_pv + g_w), s_hydro * 0.4, s_hydro)

export = np.minimum(np.maximum(0, (g_h + g_pv + g_w) - demand), s_inter_cap)
shortage = np.maximum(0, demand - (g_h + g_pv + g_w))

# --- 4. MAIN DASHBOARD ---
st.markdown('<p style="color: #00aeef; font-weight: bold; margin-bottom: -10px;">HQ EVOLUTION 2050</p>', unsafe_allow_html=True)
st.title("Strategic Generation Mix Analysis")

# KPI Summary
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Demand", f"{demand.mean():.1f} GW")
k2.metric("VRE Yield", f"{((g_w.mean()+g_pv.mean())/(s_wind+s_pv+0.1)*100):.1f}%")
k3.metric("Peak Deficit", f"{shortage.max():.2f} GW")
k4.metric("Est. Revenue", f"{(export.sum()*85/1000):,.0f} k$")

# --- 5. MAIN VISUALIZATION ---

fig = go.Figure()
fig.add_trace(go.Scatter(x=time_axis, y=demand, name="System Demand", line=dict(color='#ffffff', width=3, dash='dot')))
fig.add_trace(go.Scatter(x=time_axis, y=g_h, name="Hydro Base", stackgroup='one', fillcolor='#00aeef', line=dict(width=0)))
fig.add_trace(go.Scatter(x=time_axis, y=g_w, name="Wind Assets", stackgroup='one', fillcolor='#39b54a', line=dict(width=0)))
fig.add_trace(go.Scatter(x=time_axis, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e', line=dict(width=0)))

fig.update_layout(
    template="plotly_dark", height=500, margin=dict(t=30, b=10),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=12)),
    xaxis=dict(tickmode='array', tickvals=time_axis[::24], ticktext=days, gridcolor='#1e2633'),
    yaxis=dict(gridcolor='#1e2633', title="Power Output [GW]")
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. EXPORT & INSIGHTS ---
col_left, col_right = st.columns([1, 1.5])
with col_left:
    st.markdown('<div style="background-color: #161c26; padding: 20px; border-radius: 8px; border-left: 5px solid #00aeef;">'
                f'<b>Current Scenario: {selected_month}</b><br>'
                f'The system is currently <b>{"STABLE" if shortage.max() == 0 else "AT RISK"}</b>. '
                f'Interconnector utilization stands at <b>{export.mean()/s_inter_cap*100:.1f}%</b>.'
                '</div>', unsafe_allow_html=True)

with col_right:
    
    fig_e = go.Figure(go.Bar(x=time_axis, y=export, name="Export dispatched", marker_color='#10b981'))
    fig_e.update_layout(template="plotly_dark", height=200, margin=dict(t=0, b=0), paper_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(tickmode='array', tickvals=time_axis[::24], ticktext=days))
    st.plotly_chart(fig_e, use_container_width=True)