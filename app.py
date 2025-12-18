# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json

# -----------------------------
# Streamlit page config
# -----------------------------
st.set_page_config(page_title="Dashboard Pangan Nasional", layout="wide")

# -----------------------------
# Load Dataset Produksi Provinsi
# -----------------------------
produksi_long = pd.read_csv("produksi_long.csv")  # path absolut
with open("indonesia_provinces.geojson", encoding="utf-8") as f:
    geojson = json.load(f)

# Sidebar: Tahun Peta Provinsi
st.sidebar.header("Filter Data")
tahun_min_prov = int(produksi_long['Tahun'].min())
tahun_max_prov = int(produksi_long['Tahun'].max())
tahun_map = st.sidebar.slider(
    "Pilih Tahun Peta Provinsi", 
    min_value=tahun_min_prov, 
    max_value=tahun_max_prov, 
    value=tahun_max_prov
)

# Filter data provinsi
df_tahun = produksi_long[produksi_long['Tahun'] == tahun_map].copy()
df_tahun = df_tahun.dropna(subset=['Produksi'])
df_tahun['Produksi_ton'] = df_tahun['Produksi']

# Standardisasi nama provinsi agar sesuai GeoJSON
df_tahun['Provinsi'] = (
    df_tahun['Provinsi']
    .str.title()
    .str.replace('Dki', 'DKI', regex=False)
    .str.replace('Di Yogyakarta', 'Yogyakarta', regex=False)
)

# -----------------------------
# Choropleth Produksi Provinsi
# -----------------------------
st.subheader(f"Peta Produksi Beras per Provinsi Tahun {tahun_map}")
fig_map = px.choropleth(
    df_tahun,
    geojson=geojson,
    locations="Provinsi",
    featureidkey="properties.state",
    color="Produksi_ton",
    color_continuous_scale="YlGn",
    title=f"Peta Produksi Beras per Provinsi Tahun {tahun_map}"
)
fig_map.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig_map, use_container_width=True)

# Tabel Produksi Provinsi
st.subheader(f"Data Produksi Provinsi Tahun {tahun_map}")
st.dataframe(df_tahun[['Provinsi','Produksi_ton']].reset_index(drop=True))

# -----------------------------
# Load Dataset Nasional
# -----------------------------
data_nasional = pd.read_csv("data_nasional.csv")  # path absolut

# Hitung gap supply-demand nasional
data_nasional['gap_ton'] = data_nasional['produksi_ton'] + data_nasional['impor_ton'] - data_nasional['konsumsi_ton']

# Sidebar: Tahun Nasional
tahun_min = int(data_nasional['tahun'].min())
tahun_max = int(data_nasional['tahun'].max())
tahun_nasional = st.sidebar.slider(
    "Pilih Tahun Nasional", 
    min_value=tahun_min, 
    max_value=tahun_max, 
    value=tahun_max
)

# Filter data nasional berdasarkan tahun
data_tahun = data_nasional[data_nasional['tahun'] == tahun_nasional].copy()

# -----------------------------
# Metrics Nasional
# -----------------------------
total_produksi = data_tahun['produksi_ton'].values[0]
total_konsumsi = data_tahun['konsumsi_ton'].values[0]
total_impor = data_tahun['impor_ton'].values[0]
total_gap = data_tahun['gap_ton'].values[0]
gap_pct = (total_gap / total_konsumsi) * 100 if total_konsumsi != 0 else 0

st.subheader(f"Metrics Nasional Beras Tahun {tahun_nasional}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Produksi Nasional (ton)", f"{total_produksi:,.0f}")
col2.metric("Konsumsi Nasional (ton)", f"{total_konsumsi:,.0f}")
col3.metric("Impor Nasional (ton)", f"{total_impor:,.0f}")
col4.metric("Gap Supply-Demand (ton)", f"{total_gap:,.0f}", f"{gap_pct:.1f}%")

# -----------------------------
# Tren Nasional
# -----------------------------
st.subheader("Tren Produksi, Konsumsi, Impor, Gap Nasional")
fig_trend = px.line(
    data_nasional,
    x='tahun',
    y=['produksi_ton','konsumsi_ton','impor_ton','gap_ton'],
    labels={'value':'Ton', 'variable':'Metrik'},
    markers=True
)
st.plotly_chart(fig_trend, use_container_width=True)
