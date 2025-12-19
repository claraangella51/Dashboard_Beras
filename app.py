import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# =============================
# CONFIG
# =============================
st.set_page_config(layout="wide")
st.title("🗺️ Heatmap Gap Supply–Demand Beras Indonesia")

# =============================
# LOAD DATA
# =============================
@st.cache_data
def load_data():
    df = pd.read_csv("gap_per_provinsi.csv")
    gdf = gpd.read_file("indonesia.geojson")
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

import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
from sklearn.linear_model import LinearRegression

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="Produksi vs Luas & Produktivitas", layout="wide")
st.title("Analisis Produksi vs Luas Lahan & Produktivitas")

# =============================
# LOAD DATA
# =============================
import pandas as pd
import streamlit as st
import os

@st.cache_data
def load_data(csv_file="Produksi.csv"):
    """
    Membaca CSV wide format, convert ke long format,
    normalisasi kolom, dan pastikan tipe data numeric.
    """
    BASE_DIR = os.path.dirname(__file__)
    csv_path = os.path.join(BASE_DIR, csv_file)

    # --- Baca CSV ---
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        st.stop()

    # --- Normalisasi nama kolom (hapus spasi, lowercase, ganti spasi dengan underscore) ---
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
    
    st.write("Kolom asli CSV setelah normalisasi:", df.columns.tolist())  # Optional: debug

    # --- Tentukan kolom yang tidak berubah antar tahun (id_vars) ---
    id_vars = ["provinsi", "luas_panen_(ha)", "produktivitas_(ku/ha)"]  # pastikan kolom ini ada
    for col in id_vars:
        if col not in df.columns:
            st.error(f"Column '{col}' tidak ditemukan di CSV")
            st.stop()

    # --- Kolom tahun adalah kolom selain id_vars ---
    value_vars = [col for col in df.columns if col not in id_vars]
    if len(value_vars) == 0:
        st.error("Tidak ada kolom tahun ditemukan di CSV")
        st.stop()

    # --- Melt wide → long ---
    df_long = df.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="tahun",
        value_name="produksi"
    )

    # --- Pastikan tipe data ---
    df_long["tahun"] = df_long["tahun"].astype(int)
    df_long["produksi"] = pd.to_numeric(df_long["produksi"], errors="coerce")
    df_long["luas_panen_(ha)"] = pd.to_numeric(df_long["luas_panen_(ha)"], errors="coerce")
    df_long["produktivitas_(ku/ha)"] = pd.to_numeric(df_long["produktivitas_(ku/ha)"], errors="coerce")

    return df_long


df_long = load_data()

# =============================
# LINEAR REGRESSION
# =============================
X = df_long[["Luas_Ha","produktivitas_(ku/ha)"]]
y = df_long["produksi"]
model = LinearRegression()
model.fit(X, y)

df_long["produksi_prediksi"] = model.predict(X)
df_long["selisih"] = df_long["produksi"] - df_long["produksi_prediksi"]
df_long["status"] = np.where(df_long["selisih"]<0,"Rendah dari Prediksi","Sesuai/Diatas Prediksi")

# =============================
# SIDEBAR: Pilih Tahun & Provinsi
# =============================
tahun = st.sidebar.slider(
    "Pilih Tahun",
    min_value=int(df_long["tahun"].min()),
    max_value=int(df_long["tahun"].max()),
    value=int(df_long["tahun"].min())
)

provinsi_list = df_long["provinsi"].unique().tolist()
selected_provinsi = st.sidebar.multiselect(
    "Pilih Provinsi",
    options=provinsi_list,
    default=provinsi_list
)

df_plot = df_long[(df_long["tahun"]==tahun) & (df_long["provinsi"].isin(selected_provinsi))]

# =============================
# SCATTER PLOT
# =============================
fig = px.scatter(
    df_plot,
    x="Luas_Ha",
    y="produksi",
    size="produktivitas_(ku/ha)",
    color="status",
    hover_data=["provinsi","produksi_prediksi","selisih","produktivitas_(ku/ha)","Luas_Ha"],
    size_max=35,
    color_discrete_map={"Rendah dari Prediksi":"red","Sesuai/Diatas Prediksi":"green"}
)

fig.update_layout(
    title=f"Produksi vs Luas Lahan & Produktivitas ({tahun})",
    xaxis_title="Luas Panen (ha)",
    yaxis_title="Produksi (ton)",
    legend_title="Status Produksi",
    width=1200,
    height=800
)

st.plotly_chart(fig, use_container_width=True)

# =============================
# TABEL PROVINSI PRODUKSI RENDAH
# =============================
st.subheader("Provinsi Produksi Rendah Dibanding Prediksi")
st.dataframe(
    df_plot[df_plot["status"]=="Rendah dari Prediksi"]
    .sort_values("selisih")
    .reset_index(drop=True)
)
