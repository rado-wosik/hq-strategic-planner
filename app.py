import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="HQ Strategic Planner: Weather-Engine", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e0e0e0; }
    div[data-testid="stMetric"] { background-color: #161b26; border: 1px solid #2d3748; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PASEK BOCZNY ---
with st.sidebar:
    st.header("🌍 Weather & Time Settings")
    month = st.select_slider("Wybierz miesiąc analizy", 
                             options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                             value="Jan")
    
    st.divider()
    st.header("🏗️ Asset Mix (GW)")
    s_hydro = st.slider("Hydro Capacity", 30.0, 55.0, 37.0)
    s_wind = st.slider("Wind Capacity", 0.0, 30.0, 5.0)
    s_pv = st.slider("Solar PV Capacity", 0.0, 20.0, 2.0)
    
    st.divider()
    st.header("🌐 Market & Storage")
    s_inter_cap = st.slider("Interconnector Cap (GW)", 0.0, 10.0, 2.5)
    s_storage_gwh = st.slider("Battery Storage (GWh)", 0.0, 20.0, 2.0)

# --- 3. LOGIKA POGODOWA I PROFILI ---
def get_weather_factors(month):
    m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(month)
    
    # PV: Szczyt w czerwcu (1.0), minimum w grudniu (0.1)
    pv_seasonal = [0.15, 0.3, 0.6, 0.8, 0.95, 1.0, 0.98, 0.85, 0.65, 0.4, 0.2, 0.1][m_idx]
    
    # Wiatr: Najmocniejszy zimą (1.0), najsłabszy latem (0.4)
    wind_seasonal = [1.0, 0.95, 0.85, 0.7, 0.5, 0.4, 0.45, 0.5, 0.65, 0.8, 0.9, 0.98][m_idx]
    
    # Popyt: Zima w Quebec to ekstremum (1.0), lato niskie (0.5)
    demand_seasonal = [1.0, 0.9, 0.75, 0.6, 0.55, 0.5, 0.55, 0.52, 0.58, 0.7, 0.85, 0.95][m_idx]
    
    return pv_seasonal, wind_seasonal, demand_seasonal

def run_simulation(h_gw, w_gw, p_gw, month_str, inter_gw, storage_gwh):
    hours = np.arange(168) # 1 tydzień
    pv_f, wind_f, dem_f = get_weather_factors(month_str)
    
    # 1. Popyt (Dwa szczyty: ranny i wieczorny + sezonowość)
    daily_pattern = 25 + 10 * np.sin(np.linspace(0, 14 * np.pi, 168)) + 5 * np.cos(np.linspace(0, 7 * np.pi, 168))
    demand = daily_pattern * dem_f
    
    # 2. PV (Dzwon słoneczny, zależy od pory roku)
    # Sinusoida ograniczona do zera w nocy
    pv_daily = np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5 * np.pi, 168)))
    gen_pv = p_gw * pv_daily * pv_f
    
    # 3. Wiatr (Zmienny, silniejszy w nocy, zależny od sezonu)
    wind_daily = 0.6 + 0.3 * np.cos(np.linspace(0, 10 * np.pi, 168))
    gen_wind = w_gw * wind_daily * wind_f
    
    # 4. Hydro (Regulator)
    # Hydro pokrywa to, czego nie daje OZE, do granicy swojej mocy
    net_demand = demand - (gen_pv + gen_wind)
    gen_hydro = np.clip(net_demand, h_gw * 0.3, h_gw) # HQ rzadko schodzi poniżej 30% bazy
    
    balance = (gen_hydro + gen_pv + gen_wind) - demand
    export = np.minimum(np.maximum(0, balance), inter_gw)
    shortage = np.maximum(0, -balance)
    
    return hours, demand, gen_hydro, gen_wind, gen_pv, export, shortage

h, dem, g_h, g_w, g_pv, exp, sho = run_simulation(s_hydro, s_wind, s_pv, month, s_inter_cap, s_storage_gwh)

# --- 4. UI DASHBOARD ---
st.title(f"Hydro-Québec: {month} Strategy Outlook")

# Metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Popyt Średni", f"{dem.mean():.1f} GW")
with c2:
    st.metric("OZE Efficiency", f"{( (g_w.mean()+g_pv.mean()) / (s_wind+s_pv+0.001)*100 ):.1f}%")
with c3:
    st.metric("Max Shortage", f"{sho.max():.2f} GW")
with c4:
    st.metric("Est. Export Rev.", f"{(exp.sum() * 85 / 1000):,.1f} k$")

# --- 5. WYKRES GŁÓWNY ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=h, y=dem, name="Demand (Licznik)", line=dict(color='white', width=3, dash='dot')))
fig.add_trace(go.Scatter(x=h, y=g_h, name="Hydro (Regulator)", stackgroup='one', fillcolor='#00aeef'))
fig.add_trace(go.Scatter(x=h, y=g_w, name="Wind (Winter Ally)", stackgroup='one', fillcolor='#39b54a'))
fig.add_trace(go.Scatter(x=h, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e'))

fig.update_layout(
    title=f"Profil energetyczny tygodnia: {month}",
    template="plotly_dark",
    yaxis_title="GW",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. SEKCJA ANALITYCZNA ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📋 Charakterystyka Sezonowa")
    if month in ["Dec", "Jan", "Feb"]:
        st.info("❄️ **ZIMA:** Wysoki popyt grzewczy. Wiatr pracuje na 90-100% wydajności. PV niemal nieobecne. Hydro musi pracować w trybie szczytowym.")
    elif month in ["Jun", "Jul", "Aug"]:
        st.success("☀️ **LATO:** Popyt niski. PV na maksimum. Nadwyżki energii hydro akumulowane w zbiornikach lub eksportowane do USA.")
    elif month in ["Apr", "May"]:
        st.warning("🌊 **SPRING FRESHET:** Wysokie dopływy do zbiorników. Ryzyko nadprodukcji. Optymalny czas na serwis turbin wiatrowych.")

with col_b:
    st.subheader("⚡ Interkonektory & Stabilność")
    fig_exp = go.Figure(go.Bar(x=h, y=exp, name="Export to USA", marker_color='#10b981'))
    fig_exp.update_layout(template="plotly_dark", height=200, margin=dict(t=0, b=0))
    st.plotly_chart(fig_exp, use_container_width=True)

st.divider()
st.caption("HQ Strategic Planner 2.0 | Weather-Engine Integrated")