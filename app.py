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

# Custom Styling (Tryb Professional / Enterprise)
st.markdown("""
    <style>
    .main { background-color: #0b0f19; color: #e0e0e0; }
    .stMetric { background-color: #161b26; border: 1px solid #2d3748; padding: 15px; border-radius: 10px; }
    .stAlert { border-radius: 8px; }
    div[data-testid="stExpander"] { background-color: #161b26; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PASEK BOCZNY (KONFIGURATOR STRATEGICZNY) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/e/e5/Hydro-Qu%C3%A9bec.svg", width=200) # Logo HQ dla profesjonalizmu
    st.title("Strategic Configurator")
    
    target_year = st.selectbox("Horyzont planowania", [2025, 2035, 2050])
    
    st.subheader("🏗️ Miks Wytwórczy (GW)")
    s_hydro = st.slider("Hydro (Base + Peak)", 30.0, 50.0, 37.0, help="Główna baza systemowa HQ")
    s_wind = st.slider("Wind Power", 0.0, 30.0, 4.0, help="Lądowa i morska energetyka wiatrowa")
    s_pv = st.slider("Solar PV", 0.0, 15.0, 1.0)
    s_storage = st.slider("Energy Storage (GWh)", 0.0, 10.0, 1.0)

    st.divider()
    st.subheader("💰 Parametry Finansowe & Eksport")
    c_capex_wind = st.number_input("CAPEX Wind (M$/MW)", value=1.5)
    c_export_price = st.slider("Cena eksportu do USA ($/MWh)", 40, 200, 85)
    c_inter_cap = st.slider("Przepustowość łącz (Interconnectors GW)", 0.0, 10.0, 2.5)

# --- 3. SILNIK SYMULACJI (STRESS TEST) ---
def run_simulation(h_gw, w_gw, p_gw, year, inter_gw):
    # Generujemy profil tygodniowy (168h) - Scenariusz: Zimowy Szczyt
    hours = np.arange(168)
    
    # Popyt: bazowy + skok ze względu na elektryfikację (rok 2050 = +40% popytu)
    demand_multiplier = 1.0 if year == 2025 else (1.25 if year == 2035 else 1.45)
    base_demand = (28 + 12 * np.sin(np.linspace(0, 14 * np.pi, 168))) * demand_multiplier
    demand = base_demand + np.random.normal(0, 0.5, 168) # dodanie szumu
    
    # Produkcja
    gen_hydro = np.full(168, h_gw * 0.85) # Hydro pracuje stabilnie
    # Wiatr: profil zmienny (wieje mocniej w nocy/nad ranem)
    gen_wind = w_gw * (0.5 + 0.4 * np.cos(np.linspace(0, 6 * np.pi, 168))) 
    gen_pv = p_gw * np.maximum(0, np.sin(np.linspace(-np.pi/2, 13.5*np.pi, 168)))
    
    total_gen = gen_hydro + gen_wind + gen_pv
    balance = total_gen - demand
    
    # Eksport/Import
    export = np.minimum(np.maximum(0, balance), inter_gw)
    shortage = np.maximum(0, -balance)
    
    return hours, demand, gen_hydro, gen_wind, gen_pv, balance, export, shortage

h, dem, g_h, g_w, g_pv, bal, exp, sho = run_simulation(s_hydro, s_wind, s_pv, target_year, s_inter_cap)

# --- 4. DASHBOARD GŁÓWNY ---
st.title("Strategic Generation Mix & Investment Platform")
st.markdown(f"**Hydro-Québec Scenario Analysis Tool** | Horyzont: {target_year} | Scenariusz: Winter Peak Stress")

# Sekcja KPI
total_capex = (s_wind * c_capex_wind + (s_hydro-37) * 3.5) * 1000 # M$ (uproszczony koszt powyżej obecnej bazy)
weekly_revenue = (exp.sum() * c_export_price) / 1e3 # k$

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Szacowany CAPEX", f"{total_capex:,.0f} M$")
kpi2.metric("Przychody z Eksportu (Tydzień)", f"{weekly_revenue:,.2f} k$")
kpi3.metric("Deficyt Mocy (Max)", f"{sho.max():.2f} GW", delta="KRYTYCZNY" if sho.max() > 0 else "OK", delta_color="inverse")
kpi4.metric("Wykorzystanie Łączy", f"{(exp.mean()/s_inter_cap*100) if s_inter_cap > 0 else 0:.1f} %")

# --- 5. WIZUALIZACJA BILANSU ---

fig_main = go.Figure()
fig_main.add_trace(go.Scatter(x=h, y=dem, name="Popyt (Demand)", line=dict(color='white', width=3, dash='dot')))
fig_main.add_trace(go.Scatter(x=h, y=g_h, name="Hydro", stackgroup='one', fillcolor='#00aeef', line=dict(width=0)))
fig_main.add_trace(go.Scatter(x=h, y=g_w, name="Wind", stackgroup='one', fillcolor='#39b54a', line=dict(width=0)))
fig_main.add_trace(go.Scatter(x=h, y=g_pv, name="Solar PV", stackgroup='one', fillcolor='#ffc20e', line=dict(width=0)))

fig_main.update_layout(
    title="Godzinowe dopasowanie produkcji do popytu",
    template="plotly_dark",
    xaxis_title="Godzina analizowanego tygodnia",
    yaxis_title="Moc [GW]",
    legend=dict(orientation="h", y=1.1),
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig_main, use_container_width=True)

# --- 6. ANALIZA STRATEGICZNA (REKOMENDACJE) ---
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("💡 Wnioski Inwestycyjne")
    if sho.max() > 0:
        st.error(f"**Alert Stabilności:** Wykryto niedobór mocy rzędu {sho.max():.2f} GW w szczycie. Rekomendacja: Zwiększ moc hydro-szczytową lub dodaj {sho.max()*1.2:.1f} GWh magazynów energii.")
    else:
        st.success("**Miks Odporny:** System zachowuje stabilność nawet w scenariuszu wysokiej elektryfikacji.")
        
    if exp.mean() > s_inter_cap * 0.9:
        st.warning("**Wąskie Gardło:** Łącza z USA pracują na 90%+ wydajności. Kolejne inwestycje w OZE wymagają rozbudowy interkonektorów (Transmission CAPEX).")

with col_right:
    st.subheader("📊 Analiza Finansowa Eksportu")
    
    fig_rev = go.Figure()
    fig_rev.add_trace(go.Bar(x=h, y=exp, name="Eksport (GW)", marker_color='#10b981'))
    fig_rev.update_layout(template="plotly_dark", height=250, title="Profil wykorzystania eksportu")
    st.plotly_chart(fig_rev, use_container_width=True)

# --- 7. STOPKA ---
st.markdown("---")
st.caption("Hydro-Québec Strategic Planner | Free Electrons Edition | Simulation Engine: EnergyBalance v4.2")