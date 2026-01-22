import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Hydro-Québec Strategic Planner 2050", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Enterprise Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #e0e0e0; }
    div[data-testid="stMetric"] { background-color: #161b26; border: 1px solid #2d3748; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PASEK BOCZNY (KONFIGURATOR) ---
with st.sidebar:
    # Zabezpieczone ładowanie logo
    try:
        st.image("databridge-logo-scaled.jpg", width='stretch')
    except:
        st.header("HYDRO-QUÉBEC")
    
    st.title("Strategic Configurator")
    target_year = st.selectbox("Horyzont planowania", [2025, 2035, 2050])
    
    st.subheader("🏗️ Miks Wytwórczy (GW)")
    s_hydro = st.slider("Hydro (Base + Peak)", 30.0, 50.0, 37.0)
    s_wind = st.slider("Wind Power", 0.0, 30.0, 4.0)
    s_pv = st.slider("Solar PV", 0.0, 15.0, 1.0)
    
    st.divider()
    st.subheader("🌐 Rynek & Koszty")
    # Ujednolicone nazwy zmiennych (z prefiksem s_)
    s_inter_cap = st.slider("Przepustowość łącz (GW)", 0.0, 10.0, 2.5)
    s_export_price = st.slider("Cena eksportu ($/MWh)", 40, 200, 85)
    s_capex_wind = st.number_input("CAPEX Wind (M$/MW)", value=1.5)

# --- 3. SILNIK SYMULACJI ---
def run_simulation(h_gw, w_gw, p_gw, year, inter_gw):
    hours = np.arange(168)
    
    # Skalowanie popytu zależnie od roku (elektryfikacja)
    mult = 1.0 if year == 2025 else (1.25 if year == 2035 else 1.45)
    demand = (28 + 12 * np.sin(np.linspace(0, 14 * np.pi, 168))) * mult
    
    # Produkcja
    gen_hydro = np.full(168, h_gw * 0.85)
    gen_wind = w_gw * (0.5 + 0.4 * np.cos(np.linspace(0, 6 * np.pi, 168))) 
    gen_pv = p_gw * np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5*np.pi, 168)))
    
    total_gen = gen_hydro + gen_wind + gen_pv
    balance = total_gen - demand
    
    # Bilans handlowy
    export = np.minimum(np.maximum(0, balance), inter_gw)
    shortage = np.maximum(0, -balance)
    
    return hours, demand, gen_hydro, gen_wind, gen_pv, balance, export, shortage

# Wywołanie funkcji z poprawnymi nazwami zmiennych
h, dem, g_h, g_w, g_pv, bal, exp, sho = run_simulation(s_hydro, s_wind, s_pv, target_year, s_inter_cap)

# --- 4. DASHBOARD ---
st.title(f"Strategic Generation Mix & Investment Platform {target_year}")

# Obliczenia KPI
total_capex = (s_wind * s_capex_wind + (s_hydro-37) * 3.5) * 1000 
weekly_rev = (exp.sum() * s_export_price) / 1000

k1, k2, k3 = st.columns(3)
k1.metric("Szacowany CAPEX", f"{total_capex:,.0f} M$")
k2.metric("Przychód z Eksportu", f"{weekly_rev:,.2f} k$")
k3.metric("Max Deficyt Mocy", f"{sho.max():.2f} GW")

# Wykres bilansu

fig = go.Figure()
fig.add_trace(go.Scatter(x=h, y=dem, name="Demand", line=dict(color='white', width=3, dash='dot')))
fig.add_trace(go.Scatter(x=h, y=g_h, name="Hydro", stackgroup='one', fillcolor='#00aeef'))
fig.add_trace(go.Scatter(x=h, y=g_w, name="Wind", stackgroup='one', fillcolor='#39b54a'))
fig.add_trace(go.Scatter(x=h, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e'))

fig.update_layout(template="plotly_dark", height=500, xaxis_title="Godziny (Stress Test Week)", yaxis_title="GW")
st.plotly_chart(fig, width='stretch')

# Sekcja analizy
c1, c2 = st.columns(2)
with c1:
    st.subheader("💡 Strategia Inwestycyjna")
    if sho.max() > 0:
        st.error(f"Krytyczny brak mocy! Potrzebne dodatkowe {sho.max()*1.1:.1f} GW rezerwy.")
    else:
        st.success("Miks jest bezpieczny dla tego scenariusza popytu.")

with c2:
    st.subheader("📊 Analiza Eksportu")
    
    fig_exp = go.Figure(go.Bar(x=h, y=exp, name="Export", marker_color='#10b981'))
    fig_exp.update_layout(template="plotly_dark", height=250)
    st.plotly_chart(fig_exp, width='stretch')