import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Data Bridge | HQ Strategic Planner", layout="wide")

# CSS: Poprawa czytelności kafli KPI i branding
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e0e0e0; }
    
    /* Stylizacja kafli KPI dla maksymalnej czytelności */
    div[data-testid="stMetric"] {
        background-color: #222939; 
        border: 1px solid #3b445c; 
        padding: 20px; 
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Kolor etykiet (np. Popyt Średni) */
    div[data-testid="stMetricLabel"] > div {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
    
    /* Kolor wartości (np. 13.8 GW) */
    div[data-testid="stMetricValue"] > div {
        color: #00aeef !important;
    }
    
    .stAlert { border-radius: 8px; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PASEK BOCZNY ---
with st.sidebar:
    # Branding Data Bridge
    st.image("http://www.databridge.pl/wp-content/uploads/2022/03/databridge-logo-scaled.jpg", use_container_width=True)
    
    st.markdown("### Weather & Time Settings")
    month = st.select_slider("Miesiąc analizy", 
                             options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                             value="Jan")
    
    st.divider()
    st.markdown("### Asset Mix (GW)")
    s_hydro = st.slider("Hydro Capacity", 30.0, 55.0, 37.0)
    s_wind = st.slider("Wind Capacity", 0.0, 30.0, 5.0)
    s_pv = st.slider("Solar PV Capacity", 0.0, 20.0, 2.0)
    
    st.divider()
    st.markdown("### Market & Storage")
    s_inter_cap = st.slider("Interconnector Cap (GW)", 0.0, 10.0, 2.5)
    s_storage_gwh = st.slider("Battery Storage (GWh)", 0.0, 20.0, 2.0)

# --- 3. LOGIKA POGODOWA ---
def get_weather_factors(month):
    m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(month)
    pv_seasonal = [0.15, 0.3, 0.6, 0.8, 0.95, 1.0, 0.98, 0.85, 0.65, 0.4, 0.2, 0.1][m_idx]
    wind_seasonal = [1.0, 0.95, 0.85, 0.7, 0.5, 0.4, 0.45, 0.5, 0.65, 0.8, 0.9, 0.98][m_idx]
    demand_seasonal = [1.0, 0.9, 0.75, 0.6, 0.55, 0.5, 0.55, 0.52, 0.58, 0.7, 0.85, 0.95][m_idx]
    return pv_seasonal, wind_seasonal, demand_seasonal

def run_simulation(h_gw, w_gw, p_gw, month_str, inter_gw):
    hours = np.arange(168)
    pv_f, wind_f, dem_f = get_weather_factors(month_str)
    
    daily_pattern = 25 + 10 * np.sin(np.linspace(0, 14 * np.pi, 168)) + 5 * np.cos(np.linspace(0, 7 * np.pi, 168))
    demand = daily_pattern * dem_f
    
    pv_daily = np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5 * np.pi, 168)))
    gen_pv = p_gw * pv_daily * pv_f
    
    wind_daily = 0.6 + 0.3 * np.cos(np.linspace(0, 10 * np.pi, 168))
    gen_wind = w_gw * wind_daily * wind_f
    
    net_demand = demand - (gen_pv + gen_wind)
    gen_hydro = np.clip(net_demand, h_gw * 0.3, h_gw)
    
    balance = (gen_hydro + gen_pv + gen_wind) - demand
    export = np.minimum(np.maximum(0, balance), inter_gw)
    shortage = np.maximum(0, -balance)
    
    return hours, demand, gen_hydro, gen_wind, gen_pv, export, shortage

h, dem, g_h, g_w, g_pv, exp, sho = run_simulation(s_hydro, s_wind, s_pv, month, s_inter_cap)

# --- 4. DASHBOARD ---
st.title(f"Strategic Outlook: {month}")
st.markdown("Hydro-Québec Generation Mix Stress-Test Platform")

# Sekcja KPI - Teraz z poprawionym kontrastem
c1, c2, c3, c4 = st.columns(4)
c1.metric("Popyt Średni", f"{dem.mean():.1f} GW")
c2.metric("OZE Efficiency", f"{( (g_w.mean()+g_pv.mean()) / (s_wind+s_pv+0.001)*100 ):.1f}%")
c3.metric("Max Shortage", f"{sho.max():.2f} GW")
c4.metric("Est. Export Rev.", f"{(exp.sum() * 85 / 1000):,.1f} k$")

# --- 5. WYKRES GŁÓWNY ---

fig = go.Figure()
fig.add_trace(go.Scatter(x=h, y=dem, name="Global Demand", line=dict(color='#ffffff', width=3, dash='dot')))
fig.add_trace(go.Scatter(x=h, y=g_h, name="Hydro (Base/Peak)", stackgroup='one', fillcolor='#00aeef', line=dict(width=0)))
fig.add_trace(go.Scatter(x=h, y=g_w, name="Wind (Winter Ally)", stackgroup='one', fillcolor='#39b54a', line=dict(width=0)))
fig.add_trace(go.Scatter(x=h, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e', line=dict(width=0)))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis_title="GW",
    xaxis_title="Godziny Tygodnia",
    legend=dict(orientation="h", y=1.1)
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. ANALIZA ---
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Seasonal Summary")
    if month in ["Dec", "Jan", "Feb"]:
        st.info("Krytyczny popyt grzewczy. Wiatr kluczowy dla stabilności systemu.")
    elif month in ["Apr", "May"]:
        st.warning("Okres Spring Freshet. Wysokie dopływy do zbiorników hydro.")
    else:
        st.success("Warunki optymalne. Wysoki potencjał eksportowy PV + Hydro.")

with col_b:
    st.subheader("Export Analysis")
    
    fig_exp = go.Figure(go.Bar(x=h, y=exp, name="Export to USA", marker_color='#10b981'))
    fig_exp.update_layout(template="plotly_dark", height=200, margin=dict(t=0, b=0), paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_exp, use_container_width=True)

st.divider()
st.caption("Data Bridge Enterprise | Strategic Planning Tool for Hydro-Québec")