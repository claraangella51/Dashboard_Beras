import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# =============================
# CONFIG
# =============================
st.set_page_config(layout="wide")
st.title("🗺️ Heatmap Gap Supply–Demand Pangan Indonesia")

# =============================
# LOAD DATA
# =============================
@st.cache_data
def load_data():
    df = pd.read_csv("data/gap_per_provinsi.csv")
    gdf = gpd.read_file("data/indonesia_provincies.geojson")
    return df, gdf

df, gdf = load_data()

# =============================
# SLIDER TAHUN
# =============================
year = st.slider(
    "Pilih Tahun",
    min_value=int(df["Tahun"].min()),
    max_value=int(df["Tahun"].max()),
    value=2021,
    step=1
)

# =============================
# TRANSFORM DATA (WIDE → LONG)
# =============================
df_year = df[df["Tahun"] == year].drop(columns="Tahun").T.reset_index()
df_year.columns = ["state", "Gap_ton"]

df_year["state"] = df_year["state"].str.upper().str.strip()
gdf["state"] = gdf["state"].str.upper().str.strip()

# =============================
# MERGE
# =============================
gdf_merge = gdf.merge(df_year, on="state", how="left")

# =============================
# FOLIUM MAP
# =============================
m = folium.Map(
    location=[-2.5, 118],
    zoom_start=5,
    tiles="cartodbpositron"
)

folium.Choropleth(
    geo_data=gdf_merge,
    data=gdf_merge,
    columns=["state", "Gap_ton"],
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
        fields=["state", "Gap_ton"],
        aliases=["Provinsi", "Gap (ton)"],
        localize=True
    )
).add_to(m)

# =============================
# DISPLAY MAP
# =============================
st_folium(m, width=1400, height=700)
