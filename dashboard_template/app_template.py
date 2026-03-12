"""
🌍 Hackathon IndabaX Cameroon 2026
Dashboard Template — Streamlit

Usage: streamlit run dashboard_template/app_template.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Qualité de l'Air — Cameroun",
    page_icon="🌍",
    layout="wide",
)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_excel("data/Dataset_complet_Meteo.xlsx")
    num_cols = [
        "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
        "precipitation_sum", "wind_speed_10m_max", "shortwave_radiation_sum",
        "et0_fao_evapotranspiration", "sunshine_duration", "latitude", "longitude",
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["month"] = df["time"].dt.month
    df["year"]  = df["time"].dt.year
    df["is_dry_season"] = df["month"].isin([11, 12, 1, 2, 3]).astype(int)
    df["is_no_wind"]    = (df["wind_speed_10m_max"] < 5).astype(int)
    df["is_no_rain"]    = (df["precipitation_sum"] < 0.1).astype(int)
    # Proxy PM2.5
    df["pm25_proxy"] = (
        0.35 * df["temperature_2m_mean"].fillna(df["temperature_2m_mean"].mean())
        + 0.25 * df["shortwave_radiation_sum"].fillna(0)
        + 0.20 * df["et0_fao_evapotranspiration"].fillna(0)
        + 8.0  * df["is_no_wind"]
        + 5.0  * df["is_no_rain"]
        + 4.0  * df["is_dry_season"]
    ).clip(lower=0)
    return df

df = load_data()

# ── Risk classification ───────────────────────────────────────────────────────
def classify_risk(value):
    if value < 20:   return "🟢 Bon", "success"
    elif value < 35: return "🟡 Modéré", "warning"
    elif value < 55: return "🟠 Dégradé", "warning"
    else:            return "🔴 Dangereux", "error"

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.shields.io/badge/IndabaX-Cameroon%202026-green?style=for-the-badge", use_column_width=True)
st.sidebar.title("🎛️ Filtres")

selected_region = st.sidebar.selectbox("Région", ["Toutes"] + sorted(df["region"].unique()))
if selected_region != "Toutes":
    cities = sorted(df[df["region"] == selected_region]["city"].unique())
else:
    cities = sorted(df["city"].unique())

selected_city = st.sidebar.selectbox("Ville", ["Toutes"] + cities)
year_range    = st.sidebar.slider("Année", 2020, 2025, (2020, 2025))
lang          = st.sidebar.radio("Langue / Language", ["🇫🇷 Français", "🇬🇧 English"])

# ── Filter data ───────────────────────────────────────────────────────────────
mask = df["year"].between(*year_range)
if selected_region != "Toutes":
    mask &= df["region"] == selected_region
if selected_city != "Toutes":
    mask &= df["city"] == selected_city
df_filtered = df[mask]

# ── Header ────────────────────────────────────────────────────────────────────
title = "🌍 Qualité de l'Air au Cameroun" if lang.startswith("🇫🇷") else "🌍 Air Quality in Cameroon"
st.title(title)
sub   = "Tableau de Bord — Hackathon IndabaX 2026" if lang.startswith("🇫🇷") else "Dashboard — IndabaX Hackathon 2026"
st.caption(sub)
st.divider()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
avg_pm25  = df_filtered["pm25_proxy"].mean()
avg_temp  = df_filtered["temperature_2m_mean"].mean()
avg_wind  = df_filtered["wind_speed_10m_max"].mean()
avg_rain  = df_filtered["precipitation_sum"].mean()
risk_label, risk_style = classify_risk(avg_pm25)

col1.metric("🌫️ Indice PM2.5 Proxy", f"{avg_pm25:.1f}", risk_label)
col2.metric("🌡️ Température Moy.", f"{avg_temp:.1f} °C")
col3.metric("🌬️ Vent Max Moy.", f"{avg_wind:.1f} km/h")
col4.metric("🌧️ Précipitations Moy.", f"{avg_rain:.1f} mm")

# ── Alert banner ──────────────────────────────────────────────────────────────
if avg_pm25 >= 55:
    st.error(f"🔴 **ALERTE** — Qualité de l'air dangereuse (Indice : {avg_pm25:.0f})")
elif avg_pm25 >= 35:
    st.warning(f"🟠 **ATTENTION** — Qualité de l'air dégradée (Indice : {avg_pm25:.0f})")
else:
    st.success(f"🟢 Qualité de l'air satisfaisante (Indice : {avg_pm25:.0f})")

st.divider()

# ── Row 1: Map + Trend ────────────────────────────────────────────────────────
col_left, col_right = st.columns([1.3, 1])

with col_left:
    st.subheader("🗺️ Carte de Chaleur — PM2.5 Proxy" if lang.startswith("🇫🇷") else "🗺️ Heatmap — PM2.5 Proxy")
    city_stats = df_filtered.groupby(["city", "region", "latitude", "longitude"]).agg(
        pm25=("pm25_proxy", "mean"),
        temp=("temperature_2m_mean", "mean"),
    ).reset_index().round(2)

    fig_map = px.scatter_mapbox(
        city_stats, lat="latitude", lon="longitude",
        color="pm25", size="pm25",
        hover_name="city", hover_data={"region": True, "temp": True},
        color_continuous_scale=["#00CC44", "#FFDD00", "#FF6600", "#CC0000"],
        size_max=20, zoom=5, mapbox_style="open-street-map",
    )
    fig_map.update_layout(height=400, margin=dict(r=0, t=0, l=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

with col_right:
    st.subheader("📈 Évolution Mensuelle" if lang.startswith("🇫🇷") else "📈 Monthly Trend")
    monthly = df_filtered.groupby("month").agg(
        pm25=("pm25_proxy", "mean"),
        temp=("temperature_2m_mean", "mean"),
    ).reset_index()
    month_labels = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"]
    monthly["month_label"] = monthly["month"].apply(lambda x: month_labels[x-1])

    fig_trend = go.Figure()
    fig_trend.add_bar(x=monthly["month_label"], y=monthly["pm25"], name="PM2.5 Proxy",
                      marker_color="salmon", opacity=0.8)
    fig_trend.add_scatter(x=monthly["month_label"], y=monthly["temp"], name="Temp. (°C)",
                          mode="lines+markers", yaxis="y2", line=dict(color="steelblue", width=2.5))
    fig_trend.update_layout(
        yaxis=dict(title="PM2.5 Proxy"),
        yaxis2=dict(title="Température (°C)", overlaying="y", side="right"),
        legend=dict(orientation="h"), height=380,
        margin=dict(t=20, b=40)
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Row 2: Boxplots + Wind ────────────────────────────────────────────────────
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📦 PM2.5 Proxy par Région" if lang.startswith("🇫🇷") else "📦 PM2.5 Proxy by Region")
    fig_box = px.box(df_filtered, x="pm25_proxy", y="region",
                     color="region", orientation="h",
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig_box.update_layout(height=380, showlegend=False, margin=dict(t=20, b=20))
    st.plotly_chart(fig_box, use_container_width=True)

with col_b:
    st.subheader("🌬️ Vitesse du Vent par Région" if lang.startswith("🇫🇷") else "🌬️ Wind Speed by Region")
    wind_region = df_filtered.groupby("region")["wind_speed_10m_max"].mean().sort_values()
    fig_wind = px.bar(wind_region, orientation="h",
                      labels={"value": "Vitesse moy. (km/h)", "index": "Région"},
                      color=wind_region.values, color_continuous_scale="Blues")
    fig_wind.update_layout(height=380, showlegend=False, margin=dict(t=20, b=20))
    st.plotly_chart(fig_wind, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🌍 Hackathon IndabaX Cameroon 2026 — Data: Open-Meteo API | Template — à personnaliser !")
