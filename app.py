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

# ================================
# app.py
# ================================

import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np

st.set_page_config(page_title="Produksi vs Luas & Produktivitas", layout="wide")

st.title("Analisis Produksi vs Luas Lahan & Produktivitas")

# -------------------------------
# 1️⃣ Load Data
# -------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("produksi_long.csv")  
    df["Luas_Ha"] = df["Luas_Ha"].astype(float)
    df["Produktivitas"] = df["Produktivitas"].astype(float)
    df["Produksi"] = df["Produksi"].astype(float)
    return df

df_long = load_data()
import pandas as pd
import streamlit as st
import os

def load_data():
    BASE_DIR = os.path.dirname(__file__)
    csv_path = os.path.join(BASE_DIR, "produksi_long.csv")

    # --- Baca CSV dengan pengecekan file ---
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        st.error(f"File not found: {csv_path}")
        st.stop()

    # --- Normalisasi kolom supaya aman dari KeyError ---
    df.columns = df.columns.str.strip()         # hapus spasi di depan/akhir
    df.columns = df.columns.str.replace(" ", "_")  # ganti spasi dengan underscore
    df.columns = df.columns.str.lower()         # ubah semua jadi lowercase

    st.write("Columns after normalization:", df.columns.tolist())  # optional: cek kolom

    # --- Sekarang aman mengakses kolom ---
    # contoh: ubah kolom luas_ha jadi float
    if 'luas_ha' in df.columns:
        df['luas_ha'] = df['luas_ha'].astype(float)
    else:
        st.error("'luas_ha' column not found in CSV")
        st.stop()

    return df

# Panggil load_data() di main app
df_long = load_data()


# -------------------------------
# 2️⃣ Prediksi Produksi (Linear Regression)
# -------------------------------
X = df_long[["Luas_Ha","Produktivitas"]]
y = df_long["Produksi"]

model = LinearRegression()
model.fit(X, y)

df_long["Produksi_prediksi"] = model.predict(X)
df_long["Selisih"] = df_long["Produksi"] - df_long["Produksi_prediksi"]

# Tandai provinsi yang produksi rendah dibanding prediksi
df_long["Status"] = np.where(df_long["Selisih"]<0, "Rendah dari Prediksi", "Sesuai/Diatas Prediksi")

# -------------------------------
# 3️⃣ Sidebar: Pilih Tahun & Provinsi
# -------------------------------
tahun = st.sidebar.slider(
    "Pilih Tahun",
    min_value=int(df_long["Tahun"].min()),
    max_value=int(df_long["Tahun"].max()),
    value=int(df_long["Tahun"].min())
)

provinsi_list = df_long["Provinsi"].unique().tolist()
selected_provinsi = st.sidebar.multiselect(
    "Pilih Provinsi",
    options=provinsi_list,
    default=provinsi_list  # default tampil semua
)

df_plot = df_long[(df_long["Tahun"]==tahun) & (df_long["Provinsi"].isin(selected_provinsi))].copy()

# -------------------------------
# 4️⃣ Scatter Plot
# -------------------------------
fig = px.scatter(
    df_plot,
    x="Luas_Ha",
    y="Produksi",
    size="Produktivitas",
    color="Status",
    hover_data=["Provinsi","Produksi_prediksi","Selisih","Produktivitas","Luas_Ha"],
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

# -------------------------------
# 5️⃣ Tabel Provinsi Rendah Produksi
# -------------------------------
st.subheader("Provinsi Produksi Rendah Dibanding Prediksi")
st.dataframe(
    df_plot[df_plot["Status"]=="Rendah dari Prediksi"]
    .sort_values("Selisih")
    .reset_index(drop=True)
)

