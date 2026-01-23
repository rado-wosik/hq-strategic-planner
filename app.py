import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Data Bridge Engine | HQ Strategic Planner", layout="wide")

# CSS: Wymuszenie stałej widoczności tekstów w sidebarze i wysokiego kontrastu
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #0b0f19; color: #e0e0e0; }
    
    /* SIDEBAR FIX: Stała widoczność tekstów */
    section[data-testid="stSidebar"] { 
        background-color: #161b26; 
        border-right: 1px solid #2d3748; 
    }
    
    /* Wymuszenie koloru dla wszystkich tekstów w sidebarze */
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span { 
        color: #ffffff !important; 
        opacity: 1 !important;
        font-weight: 600 !important;
    }

    /* Nagłówki Brandingowe */
    .project-header { color: #00aeef; font-size: 1rem; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; }
    .engine-header { color: #ffffff; font-size: 2.5rem; font-weight: 800; margin-top: -10px; }

    /* KPI Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1c2331; 
        border: 1px solid #3b445c; 
        padding: 20px; 
        border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] > div { color: #ffffff !important; font-size: 1.1rem !important; }
    div[data-testid="stMetricValue"] > div { color: #00aeef !important; font-size: 2.2rem !important; font-weight: 800 !important; }

    /* Fix dla linków i tekstu głównego */
    .stMarkdown, p, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (STABILNY I CZYTELNY) ---
with st.sidebar:
    st.markdown('<p style="color: #00aeef; font-weight: 900; font-size: 1.2rem; margin-bottom: 0;">DATA BRIDGE ENGINE</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 1.5rem; font-weight: 800; margin-top: 0; color: #ffffff;">Strategic Planner</p>', unsafe_allow_html=True)
    
    st.divider()
    
    # Month Selection
    selected_month = st.select_slider("Analysis Month", 
                             options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                             value="Jan")
    
    st.divider()
    st.markdown("### Generation Mix (GW)")
    s_hydro = st.slider("Hydro Assets", 30.0, 55.0, 37.0)
    s_wind = st.slider("Wind Power", 0.0, 30.0, 5.0)
    s_pv = st.slider("Solar PV", 0.0, 20.0, 2.0)
    
    st.divider()
    st.markdown("### Grid Infrastructure")
    s_inter_cap = st.slider("Interconnection Cap (GW)", 0.0, 10.0, 2.5)

# --- 3. CORE LOGIC (TIME & WEATHER) ---
def get_weather_factors(month):
    m_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    idx = m_list.index(month)
    return [0.15, 0.3, 0.6, 0.8, 0.95, 1.0, 0.98, 0.85, 0.65, 0.4, 0.2, 0.1][idx], \
           [1.0, 0.95, 0.85, 0.7, 0.5, 0.4, 0.45, 0.5, 0.65, 0.8, 0.9, 0.98][idx], \
           [1.0, 0.9, 0.75, 0.6, 0.55, 0.5, 0.55, 0.52, 0.58, 0.7, 0.85, 0.95][idx]

pv_f, wind_f, dem_f = get_weather_factors(selected_month)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
time_axis = [f"{d} {h:02d}:00" for d in days for h in range(24)]

demand = (26 + 11 * np.sin(np.linspace(0, 14 * np.pi, 168)) + 4 * np.cos(np.linspace(0, 7 * np.pi, 168))) * dem_f
demand[120:] *= 0.88 # Weekend reduction
g_pv = s_pv * np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5 * np.pi, 168))) * pv_f
g_w = s_wind * (0.6 + 0.3 * np.cos(np.linspace(0, 10 * np.pi, 168))) * wind_f
g_h = np.clip(demand - (g_pv + g_w), s_hydro * 0.35, s_hydro)

export = np.minimum(np.maximum(0, (g_h + g_pv + g_w) - demand), s_inter_cap)
shortage = np.maximum(0, demand - (g_h + g_pv + g_w))

# --- 4. MAIN UI ---
st.markdown('<p class="project-header">Strategic Evolution: Hydro-Québec 2050</p>', unsafe_allow_html=True)
st.markdown('<p class="engine-header">Data Bridge Engine</p>', unsafe_allow_html=True)

# Metrics
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Demand", f"{demand.mean():.1f} GW")
k2.metric("VRE Efficiency", f"{((g_w.mean()+g_pv.mean())/(s_wind+s_pv+0.1)*100):.1f}%")
k3.metric("Peak Shortage", f"{shortage.max():.2f} GW")
k4.metric("Weekly Export (Est.)", f"{(export.sum()*85/1000):,.0f} k$")

# --- 5. MAIN CHART ---

fig = go.Figure()
fig.add_trace(go.Scatter(x=time_axis, y=demand, name="Total Demand", line=dict(color='#ffffff', width=4, dash='dot')))
fig.add_trace(go.Scatter(x=time_axis, y=g_h, name="Hydro", stackgroup='one', fillcolor='#00aeef', line=dict(width=0)))
fig.add_trace(go.Scatter(x=time_axis, y=g_w, name="Wind", stackgroup='one', fillcolor='#39b54a', line=dict(width=0)))
fig.add_trace(go.Scatter(x=time_axis, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e', line=dict(width=0)))

fig.update_layout(
    template="plotly_dark", height=580, 
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=14, color="#ffffff")),
    xaxis=dict(gridcolor='#2d3748', tickfont=dict(color='#ffffff', size=12), tickmode='array', tickvals=time_axis[::24], ticktext=days),
    yaxis=dict(gridcolor='#2d3748', tickfont=dict(color='#ffffff', size=12), title="Power [GW]")
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. ANALYTICS ---
st.divider()
cl, cr = st.columns(2)

with cl:
    st.subheader("Seasonal Insights")
    if selected_month in ["Dec", "Jan", "Feb"]: st.error("❄️ **WINTER:** Extreme heating peaks. High wind yields.")
    elif selected_month in ["Mar", "Apr", "May"]: st.warning("🌊 **SPRING:** Freshet period. High hydro-inflow.")
    elif selected_month in ["Jun", "Jul", "Aug"]: st.success("☀️ **SUMMER:** Optimal Solar output. Low demand.")
    else: st.info("🍂 **AUTUMN:** Transition season. Rising evening peaks.")

with cr:
    st.subheader("Export Dispatch (GW)")
    
    fig_e = go.Figure(go.Bar(x=time_axis, y=export, name="Export", marker_color='#10b981'))
    fig_e.update_layout(
        template="plotly_dark", height=250, margin=dict(t=10, b=10), paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(tickmode='array', tickvals=time_axis[::24], ticktext=days, tickfont=dict(color='#ffffff')),
        yaxis=dict(tickfont=dict(color='#ffffff'))
    )
    st.plotly_chart(fig_e, use_container_width=True)

st.divider()
st.caption("Data Bridge Engine v2.7 | Hydro-Québec Deployment")