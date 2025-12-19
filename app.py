import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np
import os

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Dashboard Pangan Indonesia", layout="wide")
st.title("📊 Dashboard Produksi & Gap Supply–Demand Beras Indonesia")

# =============================
# LOAD GAP DATA (HEATMAP)
# =============================
@st.cache_data
def load_gap_data():
    try:
        df = pd.read_csv("gap_per_provinsi.csv")
        gdf = gpd.read_file("indonesia.geojson")
        return df, gdf
    except FileNotFoundError as e:
        st.error(f"File not found: {e.filename}")
        st.stop()

gap_df, gdf = load_gap_data()

# =============================
# HEATMAP
# =============================
st.subheader("🗺️ Heatmap Gap Supply–Demand Beras")
year_gap = st.slider(
    "Pilih Tahun untuk Heatmap",
    min_value=int(gap_df["Tahun"].min()),
    max_value=int(gap_df["Tahun"].max()),
    value=int(gap_df["Tahun"].min()),
    step=1
)

df_year = gap_df[gap_df["Tahun"]==year_gap].drop(columns="Tahun").T.reset_index()
df_year.columns = ["state","Gap_ton"]
df_year["state"] = df_year["state"].str.upper().str.strip()
gdf["state"] = gdf["state"].str.upper().str.strip()
gdf_merge = gdf.merge(df_year, on="state", how="left")

m = folium.Map(location=[-2.5, 118], zoom_start=5, tiles="cartodbpositron")
folium.Choropleth(
    geo_data=gdf_merge,
    data=gdf_merge,
    columns=["state","Gap_ton"],
    key_on="feature.properties.state",
    fill_color="YlOrRd",
    fill_opacity=0.8,
    line_opacity=0.2,
    nan_fill_color="lightgrey",
    legend_name="Gap Supply–Demand (ton)"
).add_to(m)
folium.GeoJson(
    gdf_merge,
    tooltip=folium.GeoJsonTooltip(
        fields=["state","Gap_ton"],
        aliases=["Provinsi","Gap (ton)"],
        localize=True
    )
).add_to(m)
st_folium(m, width=1400, height=700)

# =============================
# LOAD PRODUKSI DATA (WIDE → LONG)
# =============================
@st.cache_data
def load_produksi(csv_file="Produksi.csv"):
    BASE_DIR = os.path.dirname(__file__)
    csv_path = os.path.join(BASE_DIR, csv_file)

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        st.stop()

    # Normalisasi kolom
    df.columns = (
        df.columns.str.strip()
                  .str.replace(" ", "_")
                  .str.replace(r"[^\w]", "", regex=True)
                  .str.lower()
    )

    st.write("Kolom setelah normalisasi:", df.columns.tolist())

    if "provi
